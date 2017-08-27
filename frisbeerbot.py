from datetime import datetime, date, timedelta

import logging

import telegram
from random_words import RandomWords
from telegram import Message, Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from action import Action, CreateGameAction, ActionTypes, \
    InspectGameAction, ActionBuilder
from api import API
from cache import NotFoundError
from database import Database
from game import Game
from gamecache import GameCache
from keyboard import Keyboard
from location import Location
from locationcache import LocationCache
from playercache import PlayerCache
from texts import Texts


class FrisbeerBot:
    def __init__(self, api_key):
        self.updater = Updater(api_key)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.greet))
        self.updater.dispatcher.add_handler(CommandHandler('game', self.game))
        self.updater.dispatcher.add_handler(CommandHandler('rank', self.rank))
        self.updater.dispatcher.add_handler(CommandHandler('register', self.register))
        self.updater.dispatcher.add_handler(CommandHandler('location', self.location))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))

        API.login("admin", "adminpassu")
        self.game_cache = GameCache()
        self.game_cache.update()
        self.player_cache = PlayerCache()
        self.player_cache.update()
        self.location_cache = LocationCache()
        self.location_cache.update()

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    def callback(self, bot: Bot, update: Update):
        query = update.callback_query
        logging.info("Callback with data {}".format(query.data))
        action = ActionBuilder.from_callback_data(query.data)
        # logging.info("Action type is {}".format(ActionTypes(action.type)))
        action.run_callback(update, self.game_cache, self.player_cache, self.location_cache)

    def greet(self, bot, update):
        update.message.reply_text('Lets play frisbeer!\n Start with /game')

    def game(self, bot, update):
        name = update.message.text.split("/game")[1].strip()
        if not name:
            FrisbeerBot._present_game_menu(update.message)
        else:
            message = update.message.reply_text("Creating a game")
            self._create_game(bot, message, update, CreateGameAction().with_callback_data(name))

    def register(self, bot, update):
        logging.info("Registering nick")
        logging.debug(update.message.text)
        logging.debug(update.message.from_user.username)
        reply = update.message.reply_text
        telegram_username = update.message.from_user.username
        telegram_user_id = update.message.from_user.id

        try:
            frisbeer_nick = update.message.text.split("register ", 1)[1]
        except IndexError:
            reply("Usage: /register <frisbeer nick>")
            return

        telegram_user = Database.user_by_telegram_id(telegram_user_id)
        try:
            frisbeer_user = self.player_cache.filter(lambda player: player.nick == frisbeer_nick)[0]
        except IndexError:
            reply("No such frisbeer nick")
            return

        if telegram_user is None:
            telegram_user = Database.create_user(frisbeer_user.id,
                                                 frisbeer_user.nick,
                                                 telegram_user_id,
                                                 telegram_username)
            reply("Paired {} with your username".format(frisbeer_nick))
        else:
            telegram_user.frisbeer_nick = frisbeer_user.nick
            telegram_user.frisbeer_id = frisbeer_user.id
            reply("Updated nick to {}".format(frisbeer_nick))
        Database.save()

    def rank(self, bot, update):
        usage = "Usage: /rank <frisbeer nick | telegram username> \n" \
                "or register your frisbeer nick with /register <frisbeer nick>"
        reply = update.message.reply_text
        logging.info("Rank query")
        logging.debug(update.message.text)
        try:
            nick = update.message.text.split("/rank ", 1)[1]
        except IndexError:
            # No nick provided by user
            telegram_user_id = update.message.from_user.id
            user = Database.user_by_telegram_id(telegram_user_id)
            if not user:
                reply(usage)
                return
            nick = user.frisbeer_nick
        else:
            # Provided nick may be a Telegram username
            if nick.startswith('@') and len(nick) > 1:
                user = Database.user_by_telegram_username(nick[1:]).first()
                if user:
                    nick = user.frisbeer_nick

        try:
            player = self.player_cache.get(nick)
        except NotFoundError:
            player = self.player_cache.fuzzy_get(nick)
        if player.rank:
            reply('{} - score: {}, rank {} <a href="{}">&#8203;</a>'
                  .format(player.nick, player.score, player.rank.name, player.rank.image_url),
                  parse_mode=telegram.ParseMode.HTML)
        else:
            reply('{} - score {}'.format(player.nick, player.score))

    def location(self, bot, update):
        logging.info("Adding location")
        usage = "Usage: /location name [;longitude;latitude]"
        logging.debug(update.message.text)
        logging.debug(update.message.from_user.username)
        reply = update.message.reply_text

        try:
            location = update.message.text.split("location ", 1)[1].strip()
        except IndexError:
            reply(usage)
            return
        if not location:
            reply(usage)
            return
        l = location.rsplit(";", 2)
        if len(l) == 1:
            created = Location.create(l[0])
        elif len(l) == 3:
            created = Location.create(l[0], float(l[1]), float(l[2]))
        else:
            reply(usage)
            return
        self.location_cache.update_instance(created)
        reply("Created location {}".format(created.name))

    @staticmethod
    def _present_game_menu(message: Message):
        """
        Create base menu for starting or listing games
        :param message: Telegram message to reply
        :return: None
        """
        game_keyboard = Keyboard()
        game_keyboard.add(Texts.CREATE_A_GAME,
                          ActionBuilder.action_as_callback_data(ActionTypes.CREATE_GAME), 1, 1)
        game_keyboard.add(Texts.LIST_GAMES,
                          ActionBuilder.action_as_callback_data(ActionTypes.LIST_GAMES), 2, 1)
        message.reply_text(Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

    def _game_menu(self, bot, message: Message, update: Update, action: Action):
        self._present_game_menu(message)

    def _create_game(self, bot, message: Message, update: Update, action):
        action = CreateGameAction.from_action(action)
        old_phase = action.get_phase()
        if old_phase == 1:
            # Create the game
            game = Database.create_game()
            action.set_unfinished_game_id(game.id)
            rw = RandomWords()
            name = action.callback_data if action.callback_data else \
                "#" + "".join([word.title() for word in rw.random_words(count=3)])
            game.name = name
            Database.save()
        game = Database.game_by_id(action.get_unfinished_game_id())
        if not game:
            return
        if old_phase == 2:
            # Save the date
            now = date.today() + timedelta(days=action.callback_data)
            game.date = now
            Database.save()
        elif old_phase == 3:
            # Save hour
            game.date += timedelta(hours=action.callback_data)
            Database.save()
        elif old_phase == 4:
            # Save minutes
            game.date += timedelta(minutes=action.callback_data)
            Database.save()
        elif old_phase == 5:
            game.location = action.callback_data
            Database.save()
        elif old_phase == 6:
            created_game = Game.create(game.name, game.date, game.location)
            self.game_cache.update_instance(created_game)
            self._inspect_game(bot, message, update, InspectGameAction().set_game_id(created_game.id))
            return

        new_phase = action.increase_phase()

        if new_phase == 2:
            # Query a date
            keyboard = Keyboard()
            days = ["Today", "Tomorrow", "+2", "+3", "+4", "+5"]
            for i in range(len(days)):
                keyboard.add(days[i], action.copy_with_callback_data(i), 1, i)
            text = Bot.Texts.ENTER_DATE
        elif new_phase == 3:
            # Query hour
            keyboard = Keyboard()
            start = datetime.now().hour if game.date.date() == date.today() else 0
            for time in range(start, 24):
                keyboard.add(str(time), action.copy_with_callback_data(time), int(time / 8) + 1, time % 8 + 1)
            text = Bot.Texts.ENTER_TIME
        elif new_phase == 4:
            # Query minutes
            keyboard = Keyboard()
            for time in range(4):
                hours = action.callback_data
                keyboard.add("{}:{}".format(str(hours).zfill(2), str(time * 15).zfill(2)),
                             action.copy_with_callback_data(time * 15), 1, time)
            text = Bot.Texts.ENTER_TIME
        elif new_phase == 5:
            keyboard = Keyboard()
            i = 0
            for location in self.location_cache.get_all():
                keyboard.add("{}".format(location.name), action.copy_with_callback_data(location.id), i, 1)
                i += 1
            text = Bot.Texts.ENTER_LOCATION
        elif new_phase == 6:
            # Confirm creation
            keyboard = Keyboard()
            keyboard.add(Bot.Texts.CREATE_GAME, action, 1, 1)
            keyboard.add(Bot.Texts.EDIT_GAME, CreateGameAction(), 2, 1)
            text = "{} {}".format(game.date, self.location_cache.get(game.location))
        else:
            self._nop(bot, message, update, action)
            return
        message.edit_text(game.name + " " + text, reply_markup=keyboard.create())

    def _nop(self, bot, message: Message, update: Update, action: Action):
        logging.info("Nop")
        if update.callback_query:
            update.callback_query.answer()
