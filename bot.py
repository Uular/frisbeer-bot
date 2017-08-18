from datetime import datetime, date, timedelta

import logging

import telegram
from random_words import RandomWords
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from action import Action, CreateGameAction, ListGamesAction, ActionTypes, GameMenuAction, \
    InspectGameAction
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
        CHOOSE_ACTION = "Choose action"
        CREATE_A_GAME = "Create a new game"
        LIST_GAMES = "List games"
        ENTER_DATE = "Give a date"
        ENTER_TIME = "Give a time"
        WANT_TO_JOIN = "Join game"
        CREATE_GAME = "Create game"
        EDIT_GAME = "Edit game"
        UPCOMING_GAMES = "Upcoming games"
        NO_UPCOMING_GAMES = "No upcoming games"
        BACK = "Back"
        LEAVE_GAME = "Leave game"
        RANDOM_JARGON = "jargon"

    def __init__(self, api_key):
        self.updater = Updater(api_key)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.greet))
        self.updater.dispatcher.add_handler(CommandHandler('game', self.game))
        self.updater.dispatcher.add_handler(CommandHandler('rank', self.rank))
        self.updater.dispatcher.add_handler(CommandHandler('register', self.register))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))

        self.actions = {
            ActionTypes.CREATE_GAME: self._create_game,
            ActionTypes.LIST_GAMES: self._list_games,
            ActionTypes.JOIN_GAME: self._inspect_game,
            ActionTypes.GAME_MENU: self._game_menu,
        }

        API.login("", "")
        self.game_cache = GameCache()
        self.game_cache.update()
        self.player_cache = PlayerCache()
        self.player_cache.update()

    def callback(self, bot, update):
        query = update.callback_query
        logging.info("Callback with data {}".format(query.data))
        action = Action.from_json(query.data)
        logging.info("Action type is {}".format(ActionTypes(action.type)))
        self.actions.get(action.type, self._nop)(bot, update, action)

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    @staticmethod
    def _game_menu(bot, update, action):
        game_keyboard = Keyboard()
        game_keyboard.add(Bot.Texts.CREATE_A_GAME, CreateGameAction(), 1, 1)
        game_keyboard.add(Bot.Texts.LIST_GAMES, ListGamesAction(), 2, 1)
        update.callback_query.message.edit_text(Bot.Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

    @staticmethod
    def greet(bot, update):
        update.message.reply_text('Lets play frisbeer!\n Start with /game')

    @staticmethod
    def game(bot, update):
        game_keyboard = Keyboard()
        game_keyboard.add(Bot.Texts.CREATE_A_GAME, CreateGameAction(), 1, 1)
        game_keyboard.add(Bot.Texts.LIST_GAMES, ListGamesAction(), 2, 1)
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

    def _inspect_game(self, bot, update, action: InspectGameAction):
        logging.info("Inspecting game {}".format(action.get_game_id()))
        keyboard = Keyboard()
        keyboard.add(Bot.Texts.BACK, ListGamesAction(), 1, 2)
        update.callback_query.message.edit_text("Loading...", reply_markup=keyboard.create())
        game_id = action.get_game_id()
        if not game_id:
            logging.warning("No instance id in join action")
            return Bot._nop(bot, update, action)
        try:
            game = self.game_cache.get(game_id)
        except NotFoundError:
            logging.warning("Game with id {} not found", game_id)
            self._nop(bot, update, action)
            return

        user = self.get_user(update)
        if action.get_phase() == 1:
            if user:
                if not game.is_in_game(user):
                    keyboard.add(Bot.Texts.WANT_TO_JOIN, action.set_phases([2]), 1, 1)
                else:
                    keyboard.add(Bot.Texts.LEAVE_GAME, action.set_phases([5]), 1, 1)
            update.callback_query.message.edit_text(game.long_str(), reply_markup=keyboard.create())
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
            self._inspect_game(bot, update, action.set_phases([1]))
        elif action.get_phase() == 5:
            action.increase_phase()
            keyboard = YesNoKeyboard(action)
            update.callback_query.message.edit_text(Bot.Texts.LEAVE_GAME + "\n" + game.long_str(),
                                                    reply_markup=keyboard.create())
        elif action.get_phase() == 6:
            if action.callback_data:
                game = game.leave(user)
                self.game_cache.update_instance(game)
            self._inspect_game(bot, update, action.set_phases([1]))

    def _create_game(self, bot, update, action):
        action = CreateGameAction.from_action(action)
        old_phase = action.get_phase()
        if old_phase == 1:
            # Create the game
            game = Database.create_game()
            action.set_unfinished_game_id(game.id)
            rw = RandomWords()
            name = "#" + "".join([word.title() for word in rw.random_words(count=3)])
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
            created_game = Game.create(game.name, game.date)
            self._inspect_game(bot, update, InspectGameAction().set_game_id(created_game.id))
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
            # Confirm creation
            keyboard = Keyboard()
            keyboard.add(Bot.Texts.CREATE_GAME, action, 1, 1)
            keyboard.add(Bot.Texts.EDIT_GAME, CreateGameAction(), 2, 1)
            text = "{}".format(game.date)
        else:
            Bot._nop(bot, update, action)
            return
        update.callback_query.message.edit_text(game.name + " " + text, reply_markup=keyboard.create())

    def _list_games(self, bot, update, action):
        update.callback_query.message.edit_text(Bot.Texts.LOADING)
        games = self.game_cache.filter(lambda game: game.state in [Game.State.PENDING, Game.State.READY])
        keyboard = Keyboard()
        text = Bot.Texts.UPCOMING_GAMES if games else Bot.Texts.NO_UPCOMING_GAMES
        user = self.get_user(update)
        for i in range(len(games)):
            game = games[i]
            keyboard.add(str(game), InspectGameAction().set_game_id(game.id), i, 1)
            if user:
                if not game.is_in_game(user):
                    keyboard.add(Bot.Texts.WANT_TO_JOIN, InspectGameAction().set_game_id(game.id).set_phases([2]), i, 2)
                else:
                    keyboard.add(Bot.Texts.LEAVE_GAME, InspectGameAction().set_game_id(game.id).set_phases([5]), i, 2)
        if not games:
            keyboard.add(Bot.Texts.CREATE_GAME, CreateGameAction(), 0, 1)
        keyboard.add(Bot.Texts.BACK, GameMenuAction(), len(games), 2)
        update.callback_query.message.edit_text(text, reply_markup=keyboard.create())

    @staticmethod
    def _nop(bot, update, action):
        logging.info("Nop")
        update.callback_query.answer()

    def get_user(self, update):
        telegram_user_id = update.effective_user.id
        registered_user = Database.user_by_telegram_id(telegram_user_id)

        if registered_user:
            user = self.player_cache.filter(lambda player: player.id == registered_user.frisbeer_id)
            if len(user) > 1:
                logging.warning("Got more than one user back from registered users")
                update.callback_query.answer()
                return
            return user[0]
