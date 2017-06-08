import logging
import sys

from sqlalchemy.orm import sessionmaker
from telegram.ext import Updater, CommandHandler
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from player import Player

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG,
                    filename="log.txt")


def start(bot, update):
    update.message.reply_text('Lets play frisbeer!\n Start with /rank <nick>')


def game(bot, update):
    update.message.reply_text("Soon...")


def rank(bot, update):
    usage = "Usage: /rank <nick> \nor register your frisbeer nick with /register <nick>"
    reply = update.message.reply_text
    logging.info("Rank query")
    logging.debug(update.message.text)
    try:
        nick = update.message.text.split("/rank ", 1)[1]
    except IndexError:
        telegram_username = update.message.from_user.username
        if not telegram_username or not len(telegram_username):
            reply(usage)
            return
        user = session.query(User).filter(User.telegram_username == update.message.from_user.username).first()
        if not user:
            reply(usage)
            return
        nick = user.frisbeer_nick
    player = Player.by_nick(nick)
    reply(str(player))


def register(bot, update):
    logging.info("Registering nick")
    logging.debug(update.message.text)
    logging.debug(update.message.from_user.username)
    reply = update.message.reply_text
    telegram_username = update.message.from_user.username

    if not telegram_username:
        reply("First set up a Telegram username in settings")
        return

    try:
        frisbeer_nick = update.message.text.split("register ", 1)[1]
    except IndexError:
        reply("Usage: /register <frisbeer nick>")
        return

    user = session.query(User).filter(User.telegram_username == telegram_username).first()
    if user is None:
        user = User(telegram_username=telegram_username, frisbeer_nick=frisbeer_nick)
        session.add(user)
        session.commit()
        reply("Paired {} with your username".format(frisbeer_nick))
    else:
        user.frisbeer_nick = frisbeer_nick
        session.commit()
        reply("Updated nick to {}".format(frisbeer_nick))


engine = create_engine('sqlite:///db.sqlite3', echo=True)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    frisbeer_nick = Column(String)
    telegram_username = Column(String, unique=True)

    def __repr__(self):
        return "{} - {}".format(self.telegram_nick, self.frisbeer_nick)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

updater = Updater(sys.argv[1])

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('game', game))
updater.dispatcher.add_handler(CommandHandler('rank', rank))
updater.dispatcher.add_handler(CommandHandler('register', register))

updater.start_polling()
updater.idle()
