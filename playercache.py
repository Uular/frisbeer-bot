from api import API
from cache import Cache
from player import Player


class PlayerCache(Cache):
    def __init__(self):
        super().__init__(Player, lambda player: player.nick)

    def update(self, force=False):
        if not force and self.is_valid():
            return False
        self.set_data(API.get_players())
