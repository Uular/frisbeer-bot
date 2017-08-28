from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from texts import Texts


class KeyboardButton:
    def __init__(self, text, callback_data):
        self.text = text
        self.callback_data = callback_data


class Keyboard:
    def __init__(self):
        self._content = {}

    def add(self, text: str, callback_data: str, row: int, col: int) -> None:
        self._content.setdefault(row, {})[col] = KeyboardButton(text, callback_data)

    def add_button(self, button: KeyboardButton, row: int, col: int) -> None:
        self.add(button.text, button.callback_data, row, col)

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
                button = cols[col_key]
                row.append(InlineKeyboardButton(button.text, callback_data=button.callback_data))
            keyboard.append(row)
        return InlineKeyboardMarkup(keyboard)


class YesNoKeyboard(Keyboard):
    def __init__(self, callback_yes: str, callback_no: str):
        super().__init__()
        self.add("Yes", callback_yes, 1, 1)
        self.add("No", callback_no, 1, 2)


class BackButtonKeyboard(Keyboard):
    def __init__(self, callback_data: str, text=Texts.BACK):
        super().__init__()
        self.add(text, callback_data, 100, 1)
