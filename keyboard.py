from typing import Union

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from action import Action


class Keyboard:
    def __init__(self):
        self._content = {}

    def add(self, text: str, callback_data: Action, row: int, col: int) -> None:
        self._content.setdefault(row, {})[col] = [text, callback_data]

    def create(self) -> InlineKeyboardMarkup:
        rows = self._content.keys()
        keyboard = []
        rows = sorted(rows)
        for key in rows:
            row = []
            cols = self._content[key]
            col_keys = cols.keys()
            col_keys = sorted(col_keys)
            for col_key in col_keys:
                data = cols[col_key]
                row.append(InlineKeyboardButton(data[0], callback_data=str(data[1])))
            keyboard.append(row)
        return InlineKeyboardMarkup(keyboard)


class YesNoKeyboard(Keyboard):
    def __init__(self, callback_data: Action, answer_key: Union[str, int]):
        super().__init__()
        self.add("Yes", callback_data.copy().add_data(answer_key, True), 1, 1)
        self.add("No", callback_data.copy().add_data(answer_key, False), 1, 2)
