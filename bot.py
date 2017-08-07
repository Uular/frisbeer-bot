from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from action import Action
from game import Game
from keyboard import Keyboard


class Bot:
    class Texts:
        NAME_THE_GAME = "Please give a name to the game"
        CHOOSE_ACTION = "Choose action"
        START_A_GAME = "Start a new game"
        LIST_GAMES = "List games"
        ENTER_DATE = "Give a date"
        ENTER_TIME = "Give a time"
        WANT_TO_JOIN = "Join game"
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
            Action.JOIN_GAME: self._join_game
        }

    @staticmethod
    def greet(bot, update):
        update.message.reply_text('Lets play frisbeer!\n Start with /rank <nick>')

    @staticmethod
    def game(bot, update):
        game_keyboard = Keyboard()
        game_keyboard.add(Bot.Texts.START_A_GAME, Action.create(), 1, 1)
        game_keyboard.add(Bot.Texts.LIST_GAMES, Action.list(), 2, 1)
        update.message.reply_text(Bot.Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

    def rank(self, bot, update):
        pass

    def register(self, bot, update):
        pass

    def callback(self, bot, update):
        query = update.callback_query
        action = Action.parse(query.data)
        self.actions.get(action.action, self._nop)(bot, update, action)

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    @staticmethod
    def _inspect_game(bot, update, action):
        update.callback_query.message.edit_text(Bot.Texts)

    @staticmethod
    def _join_game(bot, update, action):
        keyboard = Keyboard()
        keyboard.add("Yes", action.copy_with_data("Yes"), 1, 1)
        keyboard.add("No", action.copy_with_data("No"), 1, 1)
        update.callback_query.message.edit_text(Bot.Texts.WANT_TO_JOIN, reply_markup=keyboard.create())

    @staticmethod
    def _create_game(bot, update, action):
        action.phase += 1
        if action.phase == 1:
            keyboard = Keyboard()
            for i in range(3):
                keyboard.add(Bot.Texts.RANDOM_JARGON, action, i, 1)
            update.callback_query.message.edit_text(Bot.Texts.NAME_THE_GAME, reply_markup=keyboard.create())
        elif action.phase == 2:
            keyboard = Keyboard()
            days = ["Today", "Tomorrow", "+2", "+3", "+4", "+5"]
            for i in range(len(days)):
                keyboard.add(days[i], action.copy_with_data(days[i]), 1, i)
            update.callback_query.message.edit_text(Bot.Texts.ENTER_DATE, reply_markup=keyboard.create())
        elif action.phase == 3:
            keyboard = Keyboard()
            for time in range(24):
                keyboard.add(str(time), action.copy_with_data(time), int(time / 8) + 1, time % 8 + 1)
            update.callback_query.message.edit_text(Bot.Texts.ENTER_TIME, reply_markup=keyboard.create())
        elif action.phase == 4:
            keyboard = Keyboard()
            for time in range(4):
                keyboard.add("{}:{}".format(str(action.data).zfill(2), str(time * 5).zfill(2)),
                             action.copy_with_data(time * 15), 1, time)
            update.callback_query.message.edit_text(Bot.Texts.ENTER_TIME, reply_markup=keyboard.create())
        elif action.phase == 6:
            keyboard = Keyboard()


        elif action.phase == 6:
            game = Game.create()
            Bot._inspect_game(bot, update, Action.inspect_game(game.instance_id))
        else:
            Bot._nop(bot, update, action)

    @staticmethod
    def _nop(bot, update, action):
        update.callback_query.answer()
