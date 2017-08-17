import json
from typing import List

import copy


class Action:
    CREATE_GAME = 1
    INSPECT_GAME = 2
    INSPECT_PLAYER = 3
    LIST_GAMES = 4
    JOIN_GAME = 5
    GAME_MENU = 6

    _ACTION = "a"
    _RETURN_ACTION = "ra"
    _PHASE = "p"
    _NEXT_PHASE = "np"
    _ID = "i"
    _DATA = "d"

    def __init__(self, action: int, phase: int = 1, next_phases: List[int] = None, id_=0, data="",
                 ready_action=GAME_MENU):
        if not next_phases:
            next_phases = []
        self.action = action
        self.return_action = ready_action
        self.phase = phase
        self.next_phases = next_phases
        self.id = id_
        self._data = data

    @classmethod
    def game_menu(cls):
        return cls(Action.GAME_MENU)

    @classmethod
    def create_game(cls):
        return cls(Action.CREATE_GAME)

    @classmethod
    def list_games(cls):
        return cls(Action.LIST_GAMES)

    @classmethod
    def inspect_game(cls, instance_id):
        return cls(Action.INSPECT_GAME, id_=instance_id)

    @classmethod
    def join_game(cls, instance_id):
        return cls(Action.JOIN_GAME, id_=instance_id)

    @classmethod
    def parse(cls, json_data: str):
        j = json.loads(json_data)
        return Action(j[Action._ACTION],
                      j[Action._PHASE],
                      j[Action._NEXT_PHASE],
                      j[Action._ID],
                      j.get(Action._DATA, None))

    def copy(self):
        return Action(self.action, self.phase, copy.copy(self.next_phases), self.id, copy.copy(self._data))

    def set_data(self, data: str):
        """Add data with key to data store and returns self"""
        self._data = data
        return self

    def get_data(self):
        return self._data

    def increase_phase(self):
        if self.next_phases:
            self.phase = self.next_phases.pop(0)
        else:
            self.phase += 1
        return self

    def add_phase(self, phase: int):
        self.next_phases.append(phase)

    def __str__(self):
        d = {
            Action._ACTION: self.action,
            Action._PHASE: self.phase,
            Action._NEXT_PHASE: self.next_phases,
            Action._ID: self.id,
            Action._DATA: self._data
        }
        return json.dumps(d)
