from api import API
from cache import Cache
from game import Game


class GameCache(Cache):
    def update(self, force=False):
        if not force and self.is_valid():
            return False
        self.set_data(Game, lambda game: game.instance_id, API.get_games())
