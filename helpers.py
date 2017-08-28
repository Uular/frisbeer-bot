import logging

from telegram import Update

from database import Database
from player import Player
from playercache import PlayerCache


def get_player(player_cache: PlayerCache, update: Update) -> Player:
    """
    Get frisbeer user from update telegram user
    :param player_cache: cache of players
    :param update: telegram update object
    :return: User from cache from None
    """
    telegram_user_id = update.effective_user.id
    registered_user = Database.user_by_telegram_id(telegram_user_id)

    if registered_user:
        user = player_cache.filter(lambda player: player.id == registered_user.frisbeer_id)
        if len(user) > 1:
            logging.warning("Got more than one user back from registered users")
            update.callback_query.answer()
            return
        return user[0]
