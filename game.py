import dateutil.parser
from datetime import datetime
from enum import Enum
from typing import List

from api import API
from cacheable import Cacheable
from location import Location
from player import Player


class Rules:
    def __init__(self, id: int, name: str, min_players: int, max_players: int, min_rounds: int, max_rounds: int):
        self.id = id
        self.name = name
        self.min_players = min_players
        self.max_players = max_players
        self.min_rounds = min_rounds
        self.max_rounds = max_rounds

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)


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
    LOCATION = "location"
    LOCATION_REPR = "location_repr"
    TEAM_1_SCORE = "team1_score"
    TEAM_2_SCORE = "team2_score"
    RULES = "rules"

    def __init__(self, id_: int, name: str, date: datetime, state: State, players: List[Player], location: Location,
                 team1_score: int, team2_score: int, rules: Rules):
        self.id = id_
        self.name = name
        self.date = date
        self.state = state
        self.players = players
        self.location = location
        self.team1_score = team1_score
        self.team2_score = team2_score
        self.rules = rules

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(json_data[Game.ID],
                   json_data[Game.NAME],
                   dateutil.parser.parse(json_data[Game.DATE]),
                   Game.State(json_data[Game.STATE]),
                   [Player.from_json(data)
                    for data in json_data[Game.PLAYERS]],
                   Location.from_json(json_data[Game.LOCATION_REPR]) if json_data[Game.LOCATION] is not None else None,
                   json_data[Game.TEAM_1_SCORE],
                   json_data[Game.TEAM_2_SCORE],
                   Rules.from_json(json_data[Game.RULES])
                   )

    @staticmethod
    def create(name: str, date: datetime, location: int):
        """
        Create a game in frisbeer backend
        :param name: Name of the game
        :param date: Data and time of the game
        :param location: id of the location
        :return: Game object representing the game
        """
        return Game.from_json(API.create_game(name, date, location))

    def delete(self):
        API.delete_game(self.id)

    def join(self, player: Player):
        return self.from_json(API.join_game(self.id, player.id))

    def leave(self, player: Player):
        return self.from_json(API.leave_game(self.id, player.id))

    def is_in_game(self, player: Player):
        for p in self.players:
            if p.id == player.id:
                return True
        return False

    def is_full(self):
        return len(self.players) >= self.rules.max_players

    def create_teams(self):
        return self.from_json(API.create_teams(self.id))

    def __str__(self):
        return "{}".format(self.name)

    @property
    def max_players_str(self):
        if self.rules.max_players == self.rules.min_players:
            return f"{self.rules.max_players}"
        else:
            return f"{self.rules.min_players}-{self.rules.max_players}"

    def long_str(self):
        return "{}\n{}\n{}\n{}/{}\n{}".format(self.name, self.date, self.location,
                                             len(self.players) if self.players else 0,
                                             self.max_players_str,
                                             ", ".join([p.nick for p in self.players]))

    @property
    def team1(self):
        return [player for player in self.players if player.team == 1]

    @property
    def team2(self):
        return [player for player in self.players if player.team == 2]

    def submit_score(self, team1_score, team2_score) -> 'Game':
        return self.from_json(API.submit_score(self.id, team1_score, team2_score))
