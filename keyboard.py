from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from texts import Texts


class Keyboard:
    def __init__(self):
        self._content = {}

    def add(self, text: str, callback_data: str, row: int, col: int) -> None:
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
                row.append(InlineKeyboardButton(data[0], callback_data=data[1]))
            keyboard.append(row)
        return InlineKeyboardMarkup(keyboard)


class YesNoKeyboard(Keyboard):
    def __init__(self, callback_yes: str, callback_no: str):
        super().__init__()
        self.add("Yes", callback_yes, 1, 1)
        self.add("No", callback_no, 1, 2)


class BackButtonKeyboard(Keyboard):
    def __init__(self, callback_data: str):
        super().__init__()
        self.add(Texts.BACK, callback_data, 100, 1)
