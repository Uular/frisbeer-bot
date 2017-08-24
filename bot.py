from datetime import datetime, date, timedelta

import logging

import telegram
from random_words import RandomWords
from telegram import Message, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from action import Action, CreateGameAction, ListGamesAction, ActionTypes, GameMenuAction, \
    InspectGameAction, DeleteGameAction
from api import API
from cache import NotFoundError
from database import Database
from game import Game
from gamecache import GameCache
from keyboard import Keyboard, YesNoKeyboard
from locationcache import LocationCache
from player import Player
from playercache import PlayerCache


class Bot:
    class Texts:
        LOADING = "Loading..."
        CHOOSE_ACTION = "Choose action"
        CREATE_A_GAME = "Create a new game"
        LIST_GAMES = "List games"
        ENTER_DATE = "Give a date"
        ENTER_TIME = "Give a time"
        ENTER_LOCATION = "Give a location"
        WANT_TO_JOIN = "Join game"
        CREATE_GAME = "Create game"
        EDIT_GAME = "Edit game"
        UPCOMING_GAMES = "Upcoming games"
        NO_UPCOMING_GAMES = "No upcoming games"
        BACK = "Back"
        LEAVE_GAME = "Leave game"
        DELETE_GAME = "Delete game"

    def __init__(self, api_key):
        self.updater = Updater(api_key)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.greet))
        self.updater.dispatcher.add_handler(CommandHandler('game', self.game))
        self.updater.dispatcher.add_handler(CommandHandler('rank', self.rank))
        self.updater.dispatcher.add_handler(CommandHandler('register', self.register))
        self.updater.dispatcher.add_handler(CommandHandler('location', self.location))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))

        self.actions = {
            ActionTypes.CREATE_GAME: self._create_game,
            ActionTypes.LIST_GAMES: self._list_games,
            ActionTypes.JOIN_GAME: self._inspect_game,
            ActionTypes.GAME_MENU: self._game_menu,
            ActionTypes.DELETE_GAME: self._delete_game,
        }

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

    def greet(self, bot, update):
        update.message.reply_text('Lets play frisbeer!\n Start with /game')

    def game(self, bot, update):
        name = update.message.text.split("/game")[1].strip()
        if not name:
            Bot._present_game_menu(update.message)
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

    def location(self, bot, update, action):
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
        l = location.rsplit(";", 1)
        if len(l) == 1:
            pass
        elif len(l) == 3:
            pass
        else:
            reply(usage)
            return

    def callback(self, bot, update):
        query = update.callback_query
        logging.info("Callback with data {}".format(query.data))
        action = Action.from_json(query.data)
        logging.info("Action type is {}".format(ActionTypes(action.type)))
        self.actions.get(action.type, self._nop)(bot, update.callback_query.message, update, action)

    @staticmethod
    def _present_game_menu(message: Message):
        """
        Create base menu for starting or listing games
        :param message: Telegram message to reply
        :return: None
        """
        game_keyboard = Keyboard()
        game_keyboard.add(Bot.Texts.CREATE_A_GAME, CreateGameAction(), 1, 1)
        game_keyboard.add(Bot.Texts.LIST_GAMES, ListGamesAction(), 2, 1)
        message.reply_text(Bot.Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

    def _game_menu(self, bot, message: Message, update: Update, action: Action):
        self._present_game_menu(message)

    def _inspect_game(self, bot, message: Message, update: Update, action: InspectGameAction):
        logging.info("Inspecting game {}".format(action.get_game_id()))
        keyboard = Keyboard()
        keyboard.add(Bot.Texts.BACK, ListGamesAction(), 10, 1)
        message.edit_text("Loading...", reply_markup=keyboard.create())
        game_id = action.get_game_id()
        if not game_id:
            logging.warning("No instance id in join action")
            return self._nop(bot, message, update, action)
        try:
            game = self.game_cache.get(game_id)
        except NotFoundError:
            logging.warning("Game with id {} not found", game_id)
            self._nop(bot, message, update, action)
            return

        user = self.get_player(update)
        if action.get_phase() == 1:
            if user:
                if not game.is_in_game(user):
                    keyboard.add(Bot.Texts.WANT_TO_JOIN, action.set_phases([2]), 1, 1)
                    if not game.players:
                        keyboard.add(Bot.Texts.DELETE_GAME, DeleteGameAction().set_game_id(game.id), 2, 1)
                else:
                    keyboard.add(Bot.Texts.LEAVE_GAME, action.set_phases([5]), 1, 1)
            message.edit_text(game.long_str(), reply_markup=keyboard.create())
            return

        else:
            if not user:
                logging.info("User not registered")
                update.callback_query.message.reply_text("Please register first using /register <frisbeer nick>")
                update.callback_query.answer()
                return
        if action.get_phase() == 2:
            action.increase_phase()
            keyboard = YesNoKeyboard(action)
            update.callback_query.message.edit_text(Bot.Texts.WANT_TO_JOIN + "\n" + game.long_str(),
                                                    reply_markup=keyboard.create())
        elif action.get_phase() == 3:
            if action.callback_data:
                game = game.join(user)
                self.game_cache.update_instance(game)
            self._inspect_game(bot, message, update, action.set_phases([1]))
        elif action.get_phase() == 5:
            action.increase_phase()
            keyboard = YesNoKeyboard(action)
            update.callback_query.message.edit_text(Bot.Texts.LEAVE_GAME + "\n" + game.long_str(),
                                                    reply_markup=keyboard.create())
        elif action.get_phase() == 6:
            if action.callback_data:
                game = game.leave(user)
                self.game_cache.update_instance(game)
            self._inspect_game(bot, message, update, action.set_phases([1]))

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

    def _list_games(self, bot, message: Message, update: Update, action: Action):
        update.callback_query.message.edit_text(Bot.Texts.LOADING)
        games = self.game_cache.filter(lambda game: game.state in [Game.State.PENDING, Game.State.READY])
        games = sorted(games, key=lambda game: game.date)
        keyboard = Keyboard()
        text = Bot.Texts.UPCOMING_GAMES if games else Bot.Texts.NO_UPCOMING_GAMES
        user = self.get_player(update)
        for i in range(len(games)):
            game = games[i]
            keyboard.add("{} {}/6 {}".format(game.date.strftime("%a %d. %b %H:%M"),
                                             len(game.players),
                                             game.name),
                         InspectGameAction().set_game_id(game.id), i, 1)
            if user:
                if not game.is_in_game(user):
                    keyboard.add(Bot.Texts.WANT_TO_JOIN, InspectGameAction().set_game_id(game.id).set_phases([2]), i, 2)
                else:
                    keyboard.add(Bot.Texts.LEAVE_GAME, InspectGameAction().set_game_id(game.id).set_phases([5]), i, 2)
        if not games:
            keyboard.add(Bot.Texts.CREATE_GAME, CreateGameAction(), 0, 1)
        keyboard.add(Bot.Texts.BACK, GameMenuAction(), len(games), 2)
        update.callback_query.message.edit_text(text, reply_markup=keyboard.create())

    def _delete_game(self, bot, message: Message, update: Update, action: DeleteGameAction):
        game = self.game_cache.get(action.get_game_id())
        if not game:
            self._nop(bot, message, update, action)
            return
        if action.get_phase() == 1:
            action.increase_phase()
            keyboard = YesNoKeyboard(action)
            message.edit_text("Delete game {}".format(game.name), reply_markup=keyboard.create())
        elif action.get_phase() == 2:
            if action.callback_data:
                game.delete()
                self.game_cache.delete_instance(game)
                self._list_games(bot, message, update, ListGamesAction())
            else:
                self._inspect_game(bot, message, update, InspectGameAction().set_game_id(game.id))

    def _nop(self, bot, message: Message, update: Update, action: Action):
        logging.info("Nop")
        if update.callback_query:
            update.callback_query.answer()

    def get_player(self, update) -> Player:
        """
        Get frisbeer user from update telegram user
        :param update: telegram update object
        :return: User from cache from None
        """
        telegram_user_id = update.effective_user.id
        registered_user = Database.user_by_telegram_id(telegram_user_id)

        if registered_user:
            user = self.player_cache.filter(lambda player: player.id == registered_user.frisbeer_id)
            if len(user) > 1:
                logging.warning("Got more than one user back from registered users")
                update.callback_query.answer()
                return
            return user[0]
