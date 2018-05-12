import logging

import telegram
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from action import ActionTypes, \
    ActionBuilder
from cache import NotFoundError
from database import Database
from gamecache import GameCache
from location import Location
from locationcache import LocationCache
from playercache import PlayerCache


class FrisbeerBot:
    def __init__(self, api_key):
        self.updater = Updater(api_key)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.greet))
        self.updater.dispatcher.add_handler(CommandHandler('games', self.games))
        self.updater.dispatcher.add_handler(CommandHandler('new_game', self.new_game))
        self.updater.dispatcher.add_handler(CommandHandler('rank', self.rank))
        self.updater.dispatcher.add_handler(CommandHandler('register', self.register))
        self.updater.dispatcher.add_handler(CommandHandler('location', self.location))
        self.updater.dispatcher.add_handler(CommandHandler('notification_channel', self.notification_channel))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))

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
        action.run_callback(bot, update, self.game_cache, self.player_cache, self.location_cache)

    def greet(self, bot: Bot, update: Update):
        update.message.reply_text('Lets play frisbeer!\n Start with /game')

    def games(self, bot: Bot, update: Update):
        ActionBuilder.start(ActionBuilder.create(ActionTypes.GAME_MENU),
                            update, self.game_cache, self.player_cache, self.location_cache)

    def new_game(self, bot: Bot, update: Update):
        ActionBuilder.start(ActionBuilder.create(ActionTypes.CREATE_GAME),
                            update, self.game_cache, self.player_cache, self.location_cache)

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
            try:
                lon = float(l[1])
                lat = float(l[2])
            except ValueError:
                reply(usage)
                return
            created = Location.create(l[0], lon, lat)
            if not created:
                reply(usage)
                return
        else:
            reply(usage)
            return
        self.location_cache.update_instance(created)
        reply("Created location {}".format(created.name))

    def notification_channel(self, bot, update):
        logging.info("Registering notification channel")
        channel_id = update.message.chat.id
        channel = Database.get_notification_channel_by_id(channel_id)
        if channel is None:
            channel = Database.register_channel(channel_id)
            update.message.reply_text("Registered this channel to receive notifications")
        else:
            Database.delete_channel(channel_id)
            update.message.reply_text("Unregistered this channel from notifications")
