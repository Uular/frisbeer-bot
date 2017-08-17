from api import API
from cache import Cache
from player import Player


class PlayerCache(Cache):
    def update(self, force=False):
        if not force and self.is_valid():
            return False
        self.set_data(Player, lambda player: player.nick, API.get_players())
