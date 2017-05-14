import logging
import sys
from telegram.ext import Updater, CommandHandler
from player import Player

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


def start(bot, update):
    update.message.reply_text('Lets play frisbeer!\n Start with /rank <nick>')


def game(bot, update):
    update.message.reply_text("Soon...")


def rank(bot, update):
    logging.info("Rank query")
    logging.debug(update.message.text)
    try:
        nick = update.message.text.split("/rank ", 1)[1]
    except IndexError:
        update.message.reply_text("Usage: /rank <nick>")
        return
    player = Player.by_nick(nick)
    update.message.reply_text(str(player))


updater = Updater(sys.argv[1])

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('game', game))
updater.dispatcher.add_handler(CommandHandler('rank', rank))

updater.start_polling()
updater.idle()
