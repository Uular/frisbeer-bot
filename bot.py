from datetime import datetime, date, timedelta

import logging

import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from action import Action
from api import API
from cache import NotFoundError
from database import Database
from game import Game
from gamecache import GameCache
from keyboard import Keyboard, YesNoKeyboard
from playercache import PlayerCache


class Bot:
    class Texts:
        LOADING = "Loading..."
        NAME_THE_GAME = "Please give a name to the game"
        CHOOSE_ACTION = "Choose action"
        START_A_GAME = "Start a new game"
        LIST_GAMES = "List games"
        ENTER_DATE = "Give a date"
        ENTER_TIME = "Give a time"
        WANT_TO_JOIN = "Join game"
        CREATE_GAME = "Create game"
        EDIT_GAME = "Edit game"
        UPCOMING_GAMES = "Upcoming games"
        NO_UPCOMING_GAMES = "No upcoming games"
        BACK = "Back"
        RANDOM_JARGON = "jargon"

    def __init__(self, api_key):
        self.updater = Updater(api_key)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.greet))
        self.updater.dispatcher.add_handler(CommandHandler('game', self.game))
        self.updater.dispatcher.add_handler(CommandHandler('rank', self.rank))
        self.updater.dispatcher.add_handler(CommandHandler('register', self.register))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))

        self.actions = {
            Action.CREATE_GAME: self._create_game,
            Action.INSPECT_GAME: self._inspect_game,
            Action.JOIN_GAME: self._join_game,
            Action.LIST_GAMES: self._list_games,
            Action.GAME_MENU: self._game_menu
        }

        API.login("", "")
        self.game_cache = GameCache()
        self.game_cache.update()
        self.player_cache = PlayerCache()
        self.player_cache.update()

    def callback(self, bot, update):
        query = update.callback_query
        action = Action.parse(query.data)
        self.actions.get(action.action, self._nop)(bot, update, action)

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    @staticmethod
    def greet(bot, update):
        update.message.reply_text('Lets play frisbeer!\n Start with /game')

    @staticmethod
    def game(bot, update):
        game_keyboard = Keyboard()
        game_keyboard.add(Bot.Texts.START_A_GAME, Action.create_game(), 1, 1)
        game_keyboard.add(Bot.Texts.LIST_GAMES, Action.list_games(), 2, 1)
        update.message.reply_text(Bot.Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

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

    @staticmethod
    def _game_menu(bot, update, action):
        game_keyboard = Keyboard()
        game_keyboard.add(Bot.Texts.START_A_GAME, Action.create_game(), 1, 1)
        game_keyboard.add(Bot.Texts.LIST_GAMES, Action.list_games(), 2, 1)
        update.callback_query.message.edit_text(Bot.Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

    def _inspect_game(self, bot, update, action):
        keyboard = Keyboard()
        update.callback_query.message.edit_text("Loading...", reply_markup=keyboard.create())
        keyboard.add(Bot.Texts.BACK, Action.list_games(), 10, 1)
        game = self.game_cache.get(action.id)
        update.callback_query.message.edit_text(str(game), reply_markup=keyboard.create())

    def _join_game(self, bot, update, action):
        if not action.id:
            logging.debug("No instance id in join action")
            return Bot._nop(bot, update, action)
        d = action.get_data()
        try:
            game = self.game_cache.get(action.id)
        except NotFoundError:
            self._nop(bot, update, action)
        telegram_user_id = update.effective_user.id
        if d is None:
            keyboard = YesNoKeyboard(action, "join_game")
            update.callback_query.message.edit_text(Bot.Texts.WANT_TO_JOIN, reply_markup=keyboard.create())
        elif d:
            game.join()
            self._inspect_game(bot, update, action)
        else:
            self.actions[action.return_action](bot, update, None)

    def _create_game(self, bot, update, action):
        old_phase = action.phase
        if old_phase == 1:
            # Create the game
            game = Database.create_game()
            action.id = game.id
        game = Database.game_by_id(action.id)
        if not game:
            return
        if old_phase == 2:
            # Set name the game
            game.name = action.get_data()
            Database.save()
        elif old_phase == 3:
            # Save the date
            now = date.today() + timedelta(days=action.get_data())
            game.date = now
            Database.save()
        elif old_phase == 4:
            # Save hour
            game.date += timedelta(hours=action.get_data())
            Database.save()
        elif old_phase == 5:
            # Save minutes
            game.date += timedelta(minutes=action.get_data())
            Database.save()
        elif old_phase == 6:
            created_game = Game.create(game.name, game.date)
            self._inspect_game(bot, update, Action.inspect_game(created_game.instance_id))
            return

        action.increase_phase()
        new_phase = action.phase

        if new_phase == 2:
            # Query a name
            keyboard = Keyboard()
            for i in range(3):
                keyboard.add(Bot.Texts.RANDOM_JARGON + str(i), action.copy().set_data("jargon" + str(i)), i, 1)
            text = Bot.Texts.NAME_THE_GAME
        elif new_phase == 3:
            # Query a date
            keyboard = Keyboard()
            days = ["Today", "Tomorrow", "+2", "+3", "+4", "+5"]
            for i in range(len(days)):
                keyboard.add(days[i], action.copy().set_data(i), 1, i)
            text = Bot.Texts.ENTER_DATE
        elif new_phase == 4:
            # Query hour
            keyboard = Keyboard()
            start = datetime.now().hour if game.date.date() == date.today() else 0
            for time in range(start, 24):
                keyboard.add(str(time), action.copy().set_data(time), int(time / 8) + 1, time % 8 + 1)
            text = Bot.Texts.ENTER_TIME
        elif new_phase == 5:
            # Query minutes
            keyboard = Keyboard()
            for time in range(4):
                hours = action.get_data()
                keyboard.add("{}:{}".format(str(hours).zfill(2), str(time * 15).zfill(2)),
                             action.copy().set_data(time * 15), 1, time)
            text = Bot.Texts.ENTER_TIME
        elif new_phase == 6:
            # Confirm creation
            keyboard = Keyboard()
            keyboard.add(Bot.Texts.CREATE_GAME, action, 1, 1)
            keyboard.add(Bot.Texts.EDIT_GAME, action.create_game(), 2, 1)
            text = "{} - {}".format(game.name, game.date)
        else:
            Bot._nop(bot, update, action)
            return
        update.callback_query.message.edit_text(text, reply_markup=keyboard.create())

    def _list_games(self, bot, update, action):
        update.callback_query.message.edit_text(Bot.Texts.LOADING)
        games = self.game_cache.filter(lambda game: game.state in [Game.State.PENDING, Game.State.READY])
        keyboard = Keyboard()
        text = Bot.Texts.UPCOMING_GAMES if games else Bot.Texts.NO_UPCOMING_GAMES
        for i in range(len(games)):
            game = games[i]
            keyboard.add(str(game), Action.inspect_game(game.instance_id), i, 1)
            keyboard.add("Join", Action.join_game(game.instance_id), i, 2)
        if not games:
            keyboard.add(Bot.Texts.CREATE_GAME, Action.create_game(), 0, 1)
        keyboard.add(Bot.Texts.BACK, Action.game_menu(), len(games), 2)
        update.callback_query.message.edit_text(text, reply_markup=keyboard.create())

    @staticmethod
    def _nop(bot, update, action):
        update.callback_query.answer()
