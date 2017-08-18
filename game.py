from datetime import datetime
from enum import Enum
from typing import List

from api import API
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

    def __init__(self, id_: int, name: str, date: datetime, state: State, players: List[Player]):
        self.id = id_
        self.name = name
        self.date = date
        self.state = state
        self.players = players

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(json_data[Game.ID],
                   json_data[Game.NAME],
                   json_data[Game.DATE],
                   Game.State(json_data[Game.STATE]),
                   [Player.from_json(data)
                    for data in json_data[Game.PLAYERS]])

    @staticmethod
    def create(name: str, date: datetime):
        """
        Create a game in frisbeer backend
        :param name: Name of the game
        :param date: Data and time of the game
        :return: Game object representing the game
        """
        return Game.from_json(API.create_game(name, date))

    def join(self, player: Player):
        return self.from_json(API.join_game(self.id, player.id))

    def leave(self, player: Player):
        return self.from_json(API.leave_game(self.id, player.id))

    def is_in_game(self, player: Player):
        for p in self.players:
            if p.id == player.id:
                return True
        return False

    def __str__(self):
        return "{}".format(self.name)

    def long_str(self):
        return "{}\n{}\n{}/6\n{}".format(self.name, self.date,
                                         len(self.players) if self.players else 0,
                                         ", ".join([p.nick for p in self.players]))
