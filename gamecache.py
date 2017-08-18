from api import API
from cache import Cache
from game import Game


class GameCache(Cache):
    def __init__(self):
        super().__init__(Game, lambda game: game.id)

    def update(self, force=False):
        if not force and self.is_valid():
            return False
        self.set_data(API.get_games())
