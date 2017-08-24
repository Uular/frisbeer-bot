import json
import uuid
from enum import Enum
from typing import Union


class ActionTypes(Enum):
    ACTION = 0
    CREATE_GAME = 1
    LIST_GAMES = 3
    JOIN_GAME = 4
    GAME_MENU = 5
    DELETE_GAME = 6


class Action:
    _KEY_UUID = "u"
    _KEY_CALLBACK_DATA = "c"

    _TYPE = ActionTypes.ACTION

    _ongoing = {}

    def __init__(self, type_: ActionTypes = None, key=None, data=None, callback_data=None):
        if key is None:
            key = uuid.uuid4().int
        if type_ is None:
            type_ = self.__class__._TYPE
        if data is None:
            data = {}
        self._data = data
        self.type = type_
        self.key = key
        self.callback_data = callback_data
        Action._ongoing[key] = self

    @classmethod
    def from_json(cls, json_data: str):
        j = json.loads(json_data)
        uid = j[Action._KEY_UUID]
        action = Action._ongoing.get(uid, None)
        if action is None:
            return cls(key=j[Action._KEY_UUID], callback_data=j[Action._KEY_CALLBACK_DATA])
        else:
            return action.with_callback_data(j[Action._KEY_CALLBACK_DATA])

    @classmethod
    def from_action(cls, action):
        return cls(action.type, action.key, data=action._data, callback_data=action.callback_data)

    def __str__(self):
        d = {
            Action._KEY_UUID: self.key,
            Action._KEY_CALLBACK_DATA: self.callback_data
        }
        return json.dumps(d)

    def copy_with_callback_data(self, data: Union[str, int, bool]):
        copied = self.__class__.from_action(self)
        copied.callback_data = data
        return copied

    def with_callback_data(self, data: Union[str, int, bool]):
        self.callback_data = data
        return self


class PhasedAction(Action):
    """
    Action which stores next phases
    """
    _PHASE = "phase"

    def increase_phase(self):
        """
        Increase phase and return new phase
        
        :return: new phase
        """
        phases = self._data.get(PhasedAction._PHASE, [1])
        p = phases.pop(0)
        if not phases:
            phases = [p + 1]
        self._data[PhasedAction._PHASE] = phases
        return phases[0]

    def get_phase(self):
        return self._data.get(PhasedAction._PHASE, [1])[0]

    def add_phase(self, phase: int):
        phases = self._data.get(PhasedAction._PHASE, [])
        phases.append(phase)
        self._data[PhasedAction._PHASE] = phases

    def set_phases(self, phases):
        self._data[PhasedAction._PHASE] = phases
        return self


class GameAction(Action):
    _TYPE = 1
    """
    Action which stores game id
    """
    _GAME_ID = "game_id"

    def get_game_id(self) -> int:
        return self._data.get(GameAction._GAME_ID, None)

    def set_game_id(self, id_: int):
        self._data[GameAction._GAME_ID] = id_
        return self


class CreateGameAction(GameAction, PhasedAction):
    _TYPE = ActionTypes.CREATE_GAME
    _UNFINISHED_GAME_ID = "unfinished_game_id"

    def get_unfinished_game_id(self):
        return self._data.get(CreateGameAction._UNFINISHED_GAME_ID, None)

    def set_unfinished_game_id(self, id_:int):
        self._data[CreateGameAction._UNFINISHED_GAME_ID] = id_


class InspectGameAction(GameAction, PhasedAction):
    _TYPE = ActionTypes.JOIN_GAME


class ListGamesAction(Action):
    _TYPE = ActionTypes.LIST_GAMES


class GameMenuAction(Action):
    _TYPE = ActionTypes.GAME_MENU


class DeleteGameAction(GameAction, PhasedAction):
    _TYPE = ActionTypes.DELETE_GAME

