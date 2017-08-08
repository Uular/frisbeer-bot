from datetime import datetime
import logging
from enum import Enum
from typing import List

from api import API
from cache import Cache
from cacheable import Cacheable
from player import Player


class Game(Cacheable):
    class State(Enum):
        PENDING = 0
        READY = 1
        PLAYED = 2
        APPROVED = 3

    ID = "id"
    NAME = "name"
    DATE = "date"
    STATE = "state"
    PLAYERS = "players"

    _cache = None

    def __init__(self, instance_id: int, name: str, date: datetime, state: State, players: List[Player]):
        self.instance_id = instance_id
        self.name = name
        self.date = date
        self.state = state
        self.players = players

    @staticmethod
    def _update_cache():
        if Game._cache is None or not Game._cache.is_valid():
            logging.info("Getting newer data from server")
            json_data = API.get_games()
            Game._cache = Cache(Game, lambda game: game.instance_id, json_data)

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(json_data[Game.ID],
                   json_data[Game.NAME],
                   json_data[Game.DATE],
                   Game.State(json_data[Game.STATE]),
                   [Player.from_json(data)
                    for data in json_data[Game.PLAYERS]])

    @classmethod
    def by_id(cls, instance_id: int):
        Game._update_cache()
        game_data = Game._cache.get(instance_id)
        return Game.from_json(game_data)

    @staticmethod
    def get_all():
        Game._update_cache()
        return Game._cache.get_all()

    @staticmethod
    def filter(filtering_function):
        Game._update_cache()
        return Game._cache.filter(filtering_function)

    @staticmethod
    def create(name, date):
        return Game.from_json(API.create_game(name, date))

    def join(self, player: Player):
        pass

    def __str__(self):
        return "{}".format(self.name)
