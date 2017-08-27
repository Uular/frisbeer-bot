import logging
import sys

from frisbeerbot import FrisbeerBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

"""
def game(bot, update):
    keyboard = [
        [InlineKeyboardButton("New game", callback_data=json.dumps({"action": "create"})),
         InlineKeyboardButton("List pending games", callback_data=json.dumps({"action": "list"}))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)


def filter_pending(game):
    return game.state == Game.State.PENDING


def create_game(bot, update, query):
    game = Game.create()


def inspect_game(bot, update, query):
    pass


def list_pending_games(bot, update):
    pass


def join_game(bot, update):
    pass


def button_callback(bot, update):

    actions = {
        Action.CREATE: create_game,
        Action.INSPECT: inspect_game,
        Action.LIST: list_pending_games,
        Action.JOIN: join_game
    }
    action = Action(data["action"])
    actions[action](bot, update)

    games = Game.filter(filter_pending)
    keyboard = [
        [InlineKeyboardButton("{}, {} {}/6".format(game.name, game.date, len(game.players)),
                              callback_data=json.dumps({"action": "inspect", "id": game.instance_id}))]
        for game in games
    ]

    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text('Please choose:', reply_markup=reply_markup)
    else:
        keyboard = [[InlineKeyboardButton("Create a new game", callback_data=json.dumps({"action": "create"}))]]
        query.message.edit_text("No games available", reply_markup=InlineKeyboardMarkup(keyboard))


def rank(bot, update):
    usage = "Usage: /rank <nick> \nor register your frisbeer nick with /register <nick>"
    reply = update.message.reply_text
    logging.info("Rank query")
    logging.debug(update.message.text)
    try:
        nick = update.message.text.split("/rank ", 1)[1]
    except IndexError:
        # No nick provided by user
        telegram_username = update.message.from_user.username
        if not telegram_username or not len(telegram_username):
            reply(usage)
            return
        user = session.query(User).filter(User.telegram_username == update.message.from_user.username).first()
        if not user:
            reply(usage)
            return
        nick = user.frisbeer_nick
    else:
        # Provided nick may be a Telegram username
        if nick.startswith('@') and len(nick) > 1:
            user = session.query(User).filter(User.telegram_username == nick[1:]).first()
            if user:
                nick = user.frisbeer_nick

    player = Player.by_nick(nick)
    reply(str(player))
"""

bot = FrisbeerBot(sys.argv[1])
bot.start()
