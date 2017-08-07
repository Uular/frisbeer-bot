import json


class Action:
    CREATE_GAME = 1
    INSPECT_GAME = 2
    INSPECT_PLAYER = 3
    LIST_GAMES = 4
    JOIN_GAME = 5

    _ACTION = "action"
    _PHASE = "phase"
    _DATA = "data"

    def __init__(self, action: int, phase: int = 0, data=None):
        if data is None:
            data = {}
        self.action = action
        self.phase = phase
        self.data = data

    @classmethod
    def create(cls):
        return cls(Action.CREATE_GAME)

    @classmethod
    def list(cls):
        return cls(Action.LIST_GAMES)

    @classmethod
    def inspect_game(cls, instance_id):
        return cls(Action.INSPECT_GAME, data=instance_id)

    @classmethod
    def parse(cls, json_data: str):
        j = json.loads(json_data)
        return Action(j[Action._ACTION], j[Action._PHASE], j.get(Action._DATA, None))

    def copy_with_data(self, data):
        return Action(self.action, self.phase, data)

    def __str__(self):
        d = {
            Action._ACTION: self.action,
            Action._PHASE: self.phase,
            Action._DATA: self.data
        }
        return json.dumps(d)
