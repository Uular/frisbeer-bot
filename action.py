import json
import logging
import uuid
from datetime import timedelta, date, datetime
from typing import Iterable, Callable

import redis
from random_words import RandomWords

from telegram import Update, Message, Bot, Chat

from actiontypes import ActionTypes
from cache import NotFoundError
from database import Database
from game import Game
from gamecache import GameCache
from helpers import get_player
from keyboard import Keyboard, BackButtonKeyboard, YesNoKeyboard, KeyboardButton
from locationcache import LocationCache
from player import Player
from playercache import PlayerCache
from texts import Texts


class Action:
    TYPE = ActionTypes.ACTION
    _BUILD_KEY_DATA = "data"
    _KEY_CALLBACK_DATA = "callback_data"

    def __init__(self, key, data=None):
        self.key = key
        if data is None:
            data = {}
        self._data = data

    @classmethod
    def from_json(cls, key: str, json_data: str) -> 'Action':
        return cls(key, json.loads(json_data)[Action._BUILD_KEY_DATA])

    def to_json(self) -> str:
        return json.dumps({
            self._BUILD_KEY_DATA: self._data
        })

    def _save(self):
        ActionBuilder.save(self)

    @staticmethod
    def _show_loading(message):
        keyboard = Keyboard()
        keyboard.add(Texts.BACK, ActionBuilder.action_as_callback_data(ActionTypes.GAME_MENU), 1, 1)
        message.edit_text("Loading...", reply_markup=keyboard.create())

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        self._show_loading(update.callback_query.message)

    def start(self, update: Update, game_cache: GameCache, player_cache: PlayerCache, location_cache: LocationCache):
        pass

    @property
    def callback_data(self):
        return self._data.get(Action._KEY_CALLBACK_DATA, None)

    @callback_data.setter
    def callback_data(self, value):
        self._data[Action._KEY_CALLBACK_DATA] = value

    @staticmethod
    def _send_notification(bot: Bot, message: str) -> None:
        for channel in Database.get_notification_channels():
            bot.send_message(chat_id=channel.channel_id, text=message)

    def _is_query_or_error(self, update, message):
        """
        Check if message came in query. Send notification if message was sent to a channel
        :return True if it was query, False otherwise
        """
        if update.effective_chat.type != Chat.PRIVATE:
            message.reply_text("I'm a bit shy. Please let's do that in private")
            return False
        return True


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
    """
    Action which stores game id
    """
    _GAME_ID = "game_id"

    @property
    def game_id(self) -> int:
        return self._data.get(GameAction._GAME_ID, None)

    @game_id.setter
    def game_id(self, id_: int):
        self._data[GameAction._GAME_ID] = id_

    def get_game_or_fail(self, message: Message, game_cache: GameCache, back_action: Action) -> Game:
        game_id = self.game_id
        keyboard = Keyboard()
        keyboard.add(Texts.BACK, ActionBuilder.to_callback_data(back_action), 1, 1)
        if not game_id:
            logging.warning("No game id in inspect action")
            message.edit_text(Texts.ERROR, reply_markup=keyboard.create())
            raise NotFoundError
        try:
            return game_cache.get(game_id)
        except NotFoundError as e:
            logging.warning("Game with id {} not found", game_id)
            message.edit_text(Texts.ERROR, reply_markup=keyboard.create())
            raise e


class CreateGameAction(GameAction, PhasedAction):
    TYPE = ActionTypes.CREATE_GAME
    _UNFINISHED_GAME_ID = "unfinished_game_id"

    def _create_name(self):
        rw = RandomWords()
        return "#" + "".join([word.title() for word in rw.random_words(count=3)])

    def get_unfinished_game_id(self):
        return self._data.get(CreateGameAction._UNFINISHED_GAME_ID, None)

    def set_unfinished_game_id(self, id_: int):
        self._data[CreateGameAction._UNFINISHED_GAME_ID] = id_

    def start(self, update: Update, game_cache: GameCache, player_cache: PlayerCache, location_cache: LocationCache):
        if not self._is_query_or_error(update, update.message):
            return
        try:
            name = update.message.text.split(" ", 1)[1]
        except IndexError:
            name = self._create_name()
        keyboard = Keyboard()
        self.callback_data = name
        keyboard.add(Texts.CREATE_GAME, ActionBuilder.to_callback_data(self), 1, 1)
        keyboard.add(Texts.CANCEL, ActionBuilder.action_as_callback_data(ActionTypes.GAME_MENU), 2, 1)
        update.message.reply_text(name, reply_markup=keyboard.create())

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        message = update.callback_query.message
        old_action = ActionBuilder.copy_action(self)
        old_phase = self.get_phase()
        if old_phase == 1:
            # Create the game
            name = self.callback_data if self.callback_data else self._create_name()
            game = Database.create_game()
            self.set_unfinished_game_id(game.id)
            game.name = name
            Database.save()
        game = Database.game_by_id(self.get_unfinished_game_id())
        if not game:
            return
        if old_phase == 2:
            # Save the date
            now = date.today() + timedelta(days=self.callback_data)
            game.date = now
            Database.save()
        elif old_phase == 3:
            # Save hour
            game.date += timedelta(hours=self.callback_data)
            Database.save()
        elif old_phase == 4:
            # Save minutes
            game.date += timedelta(minutes=self.callback_data)
            Database.save()
        elif old_phase == 5:
            game.location = self.callback_data
            Database.save()
        elif old_phase == 6:
            created_game = Game.create(game.name, game.date, game.location)
            game_cache.update_instance(created_game)
            action = ActionBuilder.create(ActionTypes.INSPECT_GAME)
            action.game_id = created_game.id
            self._send_notification(bot, "A new upcoming game {} {} @{}"
                                    .format(created_game.name, created_game.date.strftime("%a %d. %b %H:%M"),
                                            created_game.location.name))
            ActionBuilder.redirect(action, bot, update, game_cache, player_cache, location_cache)
            return

        new_phase = self.increase_phase()
        keyboard = BackButtonKeyboard(ActionBuilder.action_as_callback_data(ActionTypes.GAME_MENU), Texts.CANCEL)

        if new_phase == 2:
            # Query a date
            days = ["Today", "Tomorrow", "+2", "+3", "+4", "+5"]
            for i in range(len(days)):
                action = ActionBuilder.copy_action(self)
                action.callback_data = i
                keyboard.add(days[i], ActionBuilder.to_callback_data(action), 1, i)
            text = Texts.ENTER_DATE
        elif new_phase == 3:
            # Query hour
            start = datetime.now().hour if game.date.date() == date.today() else 0
            for time in range(start, 24):
                action = ActionBuilder.copy_action(self)
                action.callback_data = time
                keyboard.add(str(time), ActionBuilder.to_callback_data(action), int(time / 8) + 1, time % 8 + 1)
            text = Texts.ENTER_TIME
        elif new_phase == 4:
            # Query minutes
            for time in range(4):
                hours = self.callback_data
                action = ActionBuilder.copy_action(self)
                action.callback_data = time * 15
                keyboard.add("{}:{}".format(str(hours).zfill(2), str(time * 15).zfill(2)),
                             ActionBuilder.to_callback_data(action), 1, time)
            text = Texts.ENTER_TIME
        elif new_phase == 5:
            i = 0
            for location in location_cache.get_all():
                action = ActionBuilder.copy_action(self)
                action.callback_data = location.id
                keyboard.add("{}".format(location.name), ActionBuilder.to_callback_data(action), i, 1)
                i += 1
            keyboard.add_refresh(ActionBuilder.to_callback_data(old_action))
            text = Texts.ENTER_LOCATION
        elif new_phase == 6:
            # Confirm creation
            action = ActionBuilder.copy_action(self)
            keyboard.add(Texts.CREATE_GAME, ActionBuilder.to_callback_data(action), 1, 1)
            action = ActionBuilder.create(ActionTypes.CREATE_GAME)
            action.callback_data = game.name
            keyboard.add(Texts.EDIT_GAME, ActionBuilder.to_callback_data(action), 2, 1)
            text = "{} {}".format(game.date, location_cache.get(game.location))
        else:
            logging.error("Unknown phase")
            message.edit_text(Texts.ERROR,
                              BackButtonKeyboard(ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_GAMES))
                              .create())
            return
        message.edit_text(game.name + " " + text, reply_markup=keyboard.create())


class InspectGameAction(GameAction, PhasedAction):
    TYPE = ActionTypes.INSPECT_GAME

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        logging.info("Inspecting game {}".format(self.game_id))
        message = update.callback_query.message
        self._show_loading(message)
        keyboard = Keyboard()
        keyboard.add(Texts.BACK, ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_GAMES), 10, 1)
        try:
            game = self.get_game_or_fail(message, game_cache, ActionBuilder.create(ActionTypes.LIST_PENDING_GAMES))
        except NotFoundError:
            return
        player = get_player(player_cache, update)

        if len(game.players) < 6:
            self._inspect_undermanned_game(update, game, player, keyboard, game_cache, player_cache, location_cache)

        elif len(game.players) == 6 and game.state == Game.State.PENDING:
            self._inspect_full_pending_game(update, game, player, keyboard, game_cache, player_cache, location_cache)

        elif game.state == Game.State.READY:
            self._inspect_ready_game(update, game, player, keyboard, game_cache, player_cache, location_cache)

        elif game.state == Game.State.PLAYED:
            self._inspect_played_game(update, game, player, keyboard, game_cache, player_cache, location_cache)

    def _inspect_undermanned_game(self, update, game, player, keyboard, game_cache, player_cache, location_cache):
        logging.info("Inspecting undermanned game")
        message = update.callback_query.message

        if not player:
            logging.info("User not registered")
            update.callback_query.message.reply_text("Please register first using /register <frisbeer nick>")
            update.callback_query.answer()
            return

        if not game.is_in_game(player):
            action = ActionBuilder.copy_action(self, ActionTypes.JOIN_GAME)
            keyboard.add(Texts.WANT_TO_JOIN, ActionBuilder.to_callback_data(action), 2, 1)
            if not game.players:
                action = ActionBuilder.copy_action(self, ActionTypes.DELETE_GAME)
                keyboard.add(Texts.DELETE_GAME, ActionBuilder.to_callback_data(action), 3, 1)
        else:
            action = ActionBuilder.copy_action(self, ActionTypes.LEAVE_GAME)
            keyboard.add(Texts.LEAVE_GAME, ActionBuilder.to_callback_data(action), 2, 1)
        message.edit_text(game.long_str(), reply_markup=keyboard.create())

    def _inspect_full_pending_game(self, update, game, player, keyboard, game_cache, player_cache, location_cache):
        logging.info("Inspecting full pending game")
        message = update.callback_query.message
        if game.is_in_game(player):
            keyboard.add(Texts.CREATE_TEAMS,
                         ActionBuilder.to_callback_data(ActionBuilder.copy_action(self, ActionTypes.CREATE_TEAMS)),
                         1, 1)
        message.edit_text(game.long_str(), reply_markup=keyboard.create())

    def _scoring_keyboard(self, game, keyboard: Keyboard) -> Keyboard:
        t1_scores = [2, 2, 1, 0]
        t2_scores = [0, 1, 2, 2]
        for i in range(4):
            action = ActionBuilder.create(ActionTypes.SUBMIT_SCORE)
            action.game_id = game.id
            action.callback_data = {"t1": t1_scores[i], "t2": t2_scores[i]}
            keyboard.add("{} - {}".format(t1_scores[i], t2_scores[i]), ActionBuilder.to_callback_data(action), 1, i)
        return keyboard

    def _inspect_ready_game(self, update, game, player, keyboard, game_cache, player_cache, location_cache):
        logging.info("Inspecting full game")
        message = update.callback_query.message
        self._show_loading(message)

        keyboard = BackButtonKeyboard(ActionBuilder.action_as_callback_data(ActionTypes.LIST_READY_GAMES))
        keyboard = self._scoring_keyboard(game, keyboard)
        message.edit_text(
            Texts.ENTER_SCORE + ": \n{} - \n{}\n{}\n{}".format(", ".join([player.nick for player in game.team1]),
                                                               ", ".join([player.nick for player in game.team2]),
                                                               game.date.strftime("%a %d. %b %H:%M"),
                                                               game.location.name
                                                               ),
            reply_markup=keyboard.create())

    def _inspect_played_game(self, update: Update, game: Game, player: Player, keyboard: Keyboard,
                             game_cache: GameCache, player_cache: PlayerCache, location_cache: LocationCache):
        logging.info("Inspecting full game")
        message = update.callback_query.message
        self._show_loading(message)
        keyboard = BackButtonKeyboard(ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_ACCEPTING_GAMES))
        keyboard = self._scoring_keyboard(game, keyboard)
        message.edit_text(Texts.ENTER_SCORE + ": \n{} {} - {} \n{}".format(
            ", ".join([player.nick for player in game.team1]),
            game.team1_score,
            game.team2_score,
            ", ".join([player.nick for player in game.team2])),
                          reply_markup=keyboard.create())


class SubmitScoresAction(GameAction):
    TYPE = ActionTypes.SUBMIT_SCORE

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        logging.info("Submitting scores")
        message = update.callback_query.message
        self._show_loading(message)
        try:
            game = self.get_game_or_fail(message, game_cache, ActionBuilder.copy_action(self, ActionTypes.INSPECT_GAME))
        except NotFoundError:
            return
        game = game.submit_score(self.callback_data["t1"], self.callback_data["t2"])
        game_cache.update(game)
        self._send_notification(bot, "Game {} - {} ended {}-{}"
                                .format(", ".join([player.nick for player in game.team1]),
                                        ", ".join([player.nick for player in game.team2]),
                                        game.team1_score, game.team2_score))
        action = ActionBuilder.copy_action(self, ActionTypes.INSPECT_GAME)
        ActionBuilder.redirect(action, bot, update, game_cache, player_cache, location_cache)


class ListGamesAction(Action):
    title_text = None
    title_text_no_games = None

    @staticmethod
    def _filter(game: Game) -> bool:
        raise NotImplemented()

    @staticmethod
    def _game_str(game: Game) -> str:
        raise NotImplemented()

    @staticmethod
    def _additional_buttons(game: Game, player: Player) -> Iterable[KeyboardButton]:
        return []

    def run_callback(self, bot: Bot, update: Update,
                     game_cache: GameCache,
                     player_cache: PlayerCache,
                     location_cache: LocationCache):
        message = update.callback_query.message
        self._show_loading(message)
        games = game_cache.filter(self._filter)
        games = sorted(games, key=lambda game: game.date)
        keyboard = Keyboard()
        text = self.title_text if games else self.title_text_no_games
        player = get_player(player_cache, update)
        for i in range(len(games)):
            game = games[i]
            action = ActionBuilder.create(ActionTypes.INSPECT_GAME)
            action.game_id = game.id
            keyboard.add(self._game_str(game), ActionBuilder.to_callback_data(action), i, 1)
            c = 2
            for button in self._additional_buttons(game, player):
                keyboard.add_button(button, i, c)

        keyboard.add(Texts.CREATE_GAME, ActionBuilder.action_as_callback_data(ActionTypes.CREATE_GAME), 100, 1)
        keyboard.add(Texts.BACK, ActionBuilder.action_as_callback_data(ActionTypes.GAME_MENU), 100, 2)
        keyboard.add_refresh(ActionBuilder.to_callback_data(ActionBuilder.copy_action(self)))
        update.callback_query.message.edit_text(text, reply_markup=keyboard.create())


class ListPendingGamesAction(ListGamesAction):
    TYPE = ActionTypes.LIST_PENDING_GAMES

    title_text = Texts.OPEN_GAMES
    title_text_no_games = Texts.NO_UPCOMING_GAMES

    @staticmethod
    def _game_str(game: Game):
        return "{} {}/6 {}".format(game.date.strftime("%a %d. %b %H:%M"), len(game.players), game.name)

    @staticmethod
    def _additional_buttons(game: Game, player: Player) -> Iterable[KeyboardButton]:
        if not player:
            return []
        if not game.is_in_game(player) and not game.is_full():
            action = ActionBuilder.create(ActionTypes.JOIN_GAME)
            action.game_id = game.id
            return [KeyboardButton(Texts.WANT_TO_JOIN, ActionBuilder.to_callback_data(action))]
        if game.is_in_game(player):
            action = ActionBuilder.create(ActionTypes.LEAVE_GAME)
            action.game_id = game.id
            return [KeyboardButton(Texts.LEAVE_GAME, ActionBuilder.to_callback_data(action))]
        return []

    @staticmethod
    def _filter(game):
        return game.state in [Game.State.PENDING]


class ListReadyGamesAction(ListGamesAction):
    TYPE = ActionTypes.LIST_READY_GAMES

    title_text = Texts.READY_GAMES
    title_text_no_games = Texts.NO_READY_GAMES

    @staticmethod
    def _game_str(game: Game) -> str:
        return "{}\n{} - {}\n{}\n{}".format(
            game.name,
            ", ".join([player.nick for player in game.team1]),
            ", ".join([player.nick for player in game.team2]),
            game.date.strftime("%a %d. %b %H:%M"),
            game.location.name)

    @staticmethod
    def _filter(game: Game) -> bool:
        return game.state == Game.State.READY


class ListPendingAcceptingGamesAction(ListGamesAction):
    TYPE = ActionTypes.LIST_PENDING_ACCEPTING_GAMES

    title_text = Texts.GAMES_WAITING_APPROVAL
    title_text_no_games = Texts.NO_GAMES_WAITING_APPROVAL

    @staticmethod
    def _filter(game: Game) -> bool:
        return game.state == Game.State.PLAYED

    @staticmethod
    def _game_str(game: Game) -> str:
        return "id: {}\n{}".format(game.id, game.name)


class JoinGameAction(GameAction):
    TYPE = ActionTypes.JOIN_GAME

    def run_callback(self,
                     bot: Bot,
                     update: Update,
                     game_cache: GameCache,
                     player_cache: PlayerCache,
                     location_cache: LocationCache):
        keyboard = Keyboard()
        keyboard.add(Texts.BACK, ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_GAMES), 100, 1)
        message = update.callback_query.message
        player = get_player(player_cache, update)
        if player is None:
            logging.warning("Player {} tried to join without registering", update.effective_user.id)
            message.edit_text(Texts.PLEASE_REGISTER, reply_markup=keyboard.create())
            return
        try:
            game = game_cache.get(self.game_id)
        except NotFoundError as e:
            logging.warning("Game not found with id {}", self.game_id)
            message.edit_text(Texts.GAME_NOT_FOUND, reply_markup=keyboard.create())
            return
        if game.is_in_game(player):
            logging.debug("Player {} tried to join again", player.nick)
            message.edit_text(Texts.ALREADY_IN_GAME, reply_markup=keyboard.create())
            return
        game = game.join(player)
        if not game.is_in_game(player):
            message.edit_text(Texts.JOIN_FAILED, reply_markup=keyboard.create())
            return
        game_cache.update(game)
        self._send_notification(bot, "{} joined game {}".format(player.nick, game.name))
        ActionBuilder.redirect(ActionBuilder.copy_action(self, ActionTypes.INSPECT_GAME), bot, update,
                               game_cache, player_cache, location_cache)


class LeaveGameAction(GameAction):
    TYPE = ActionTypes.LEAVE_GAME

    def run_callback(self,
                     bot: Bot,
                     update: Update,
                     game_cache: GameCache,
                     player_cache: PlayerCache,
                     location_cache: LocationCache):
        keyboard = Keyboard()
        keyboard.add(Texts.BACK, ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_GAMES), 100, 1)
        message = update.callback_query.message
        player = get_player(player_cache, update)
        if player is None:
            logging.warning("Player {} tried to leave without registering", update.effective_user.id)
            message.edit_text(Texts.PLEASE_REGISTER, reply_markup=keyboard.create())
            return
        try:
            game = game_cache.get(self.game_id)
        except NotFoundError as e:
            logging.warning("Game not found with id {}", self.game_id)
            message.edit_text(Texts.GAME_NOT_FOUND, reply_markup=keyboard.create())
            return
        if not game.is_in_game(player):
            logging.debug("Player {} tried to leave a game they're not in {}", player.nick, game.id)
            message.edit_text(Texts.ALREADY_IN_GAME, reply_markup=keyboard.create())
            return
        game = game.leave(player)
        if game.is_in_game(player):
            message.edit_text(Texts.LEAVE_FAILED, reply_markup=keyboard.create())
            return

        game_cache.update(game)
        self._send_notification(bot, "{} left game {}".format(player.nick, game.name))
        ActionBuilder.redirect(ActionBuilder.copy_action(self, ActionTypes.INSPECT_GAME), bot, update,
                               game_cache, player_cache, location_cache)


class CreateTeamsAction(GameAction, PhasedAction):
    TYPE = ActionTypes.CREATE_TEAMS

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        logging.info("Creating teams")
        message = update.callback_query.message
        back_action = ActionBuilder.create(ActionTypes.LIST_PENDING_GAMES)
        try:
            game = self.get_game_or_fail(message, game_cache, back_action)
        except NotFoundError:
            return
        logging.debug("Creating teams for game {}", game.id)

        if self.get_phase() == 1:
            action = ActionBuilder.create(ActionTypes.CREATE_TEAMS)
            action.game_id = game.id
            action.increase_phase()
            yes = ActionBuilder.copy_action(action)
            yes.callback_data = True
            no = ActionBuilder.copy_action(action)
            no.callback_data = False
            keyboard = YesNoKeyboard(ActionBuilder.to_callback_data(yes), ActionBuilder.to_callback_data(no))
            message.edit_text(Texts.CREATE_TEAMS, reply_markup=keyboard.create())
        elif self.get_phase() == 2:
            if self.callback_data:
                game = game.create_teams()
                game_cache.update(game)
            action = ActionBuilder.create(ActionTypes.INSPECT_GAME)
            action.game_id = game.id
            self._send_notification(bot, "Teams for {} are {} - {}".format(game.name,
                                                                           ", ".join(
                                                                               player.nick for player in game.team1),
                                                                           ", ".join(
                                                                               player.nick for player in game.team2),
                                                                           ))
            ActionBuilder.redirect(action, bot, update, game_cache, player_cache, location_cache)


class GameMenuAction(Action):
    TYPE = ActionTypes.GAME_MENU

    def _show_menu(self, show_text: Callable):
        game_keyboard = Keyboard()
        game_keyboard.add(Texts.LIST_PENDING_GAMES,
                          ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_GAMES), 2, 1)
        game_keyboard.add(Texts.LIST_READY_GAMES,
                          ActionBuilder.action_as_callback_data(ActionTypes.LIST_READY_GAMES), 3, 1)
        game_keyboard.add(Texts.LIST_PENDING_ACCEPTING_GAMES,
                          ActionBuilder.action_as_callback_data(ActionTypes.LIST_PENDING_ACCEPTING_GAMES), 4, 1)

        game_keyboard.add(Texts.CREATE_A_GAME, ActionBuilder.action_as_callback_data(ActionTypes.CREATE_GAME), 5, 1)
        game_keyboard.add(Texts.CLOSE, ActionBuilder.action_as_callback_data(ActionTypes.CLOSE), 5, 2)

        show_text(Texts.CHOOSE_ACTION, reply_markup=game_keyboard.create())

    def start(self, update: Update, game_cache: GameCache, player_cache: PlayerCache, location_cache: LocationCache):
        if not self._is_query_or_error(update, update.message):
            return
        message = update.message
        self._show_menu(message.reply_text)

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        message = update.callback_query.message
        self._show_menu(message.edit_text)


class DeleteGameAction(GameAction, PhasedAction):
    TYPE = ActionTypes.DELETE_GAME

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        message = update.callback_query.message
        self._show_loading(message)
        try:
            game = self.get_game_or_fail(message, game_cache, ActionBuilder.create(ActionTypes.LIST_PENDING_GAMES))
        except NotFoundError:
            return

        if self.get_phase() == 1:
            action = ActionBuilder.create(ActionTypes.DELETE_GAME)
            action.increase_phase()
            action.game_id = game.id
            action.callback_data = True
            yes = ActionBuilder.to_callback_data(ActionBuilder.copy_action(action))
            action.callback_data = False
            no = ActionBuilder.to_callback_data(action)
            keyboard = YesNoKeyboard(yes, no)
            message.edit_text(Texts.DELETE_GAME + " {}".format(game.name), reply_markup=keyboard.create())
        elif self.get_phase() == 2:
            if self.callback_data:
                game.delete()
                game_cache.delete_instance(game)
                self._send_notification(bot, "{} was cancelled".format(game.name))
            ActionBuilder.redirect(ActionBuilder.create(ActionTypes.LIST_PENDING_GAMES), bot,
                                   update, game_cache, player_cache, location_cache)


class CloseAction(Action):
    TYPE = ActionTypes.CLOSE

    def run_callback(self, bot: Bot, update: Update, game_cache: GameCache, player_cache: PlayerCache,
                     location_cache: LocationCache):
        update.callback_query.message.delete()


class ActionBuilder:
    _KEY_UUID = "u"
    _KEY_TYPE = "t"

    _r = None

    _action_mapping = {
        ActionTypes.CREATE_GAME: CreateGameAction,
        ActionTypes.LIST_PENDING_GAMES: ListPendingGamesAction,
        ActionTypes.LIST_READY_GAMES: ListReadyGamesAction,
        ActionTypes.LIST_PENDING_ACCEPTING_GAMES: ListPendingAcceptingGamesAction,
        ActionTypes.INSPECT_GAME: InspectGameAction,
        ActionTypes.GAME_MENU: GameMenuAction,
        ActionTypes.DELETE_GAME: DeleteGameAction,
        ActionTypes.JOIN_GAME: JoinGameAction,
        ActionTypes.LEAVE_GAME: LeaveGameAction,
        ActionTypes.CREATE_TEAMS: CreateTeamsAction,
        ActionTypes.SUBMIT_SCORE: SubmitScoresAction,
        ActionTypes.CLOSE: CloseAction,
    }

    @staticmethod
    def setup(redis_host, redis_port):
        ActionBuilder._r = redis.StrictRedis(host=redis_host, port=redis_port, db=0)

    @staticmethod
    def from_callback_data(json_data: str) -> Action:
        j = json.loads(json_data)
        uid = j[ActionBuilder._KEY_UUID]
        action_type = j[ActionBuilder._KEY_TYPE]
        data = bytes.decode(ActionBuilder._r.get(uid))
        if data is None:
            return ActionBuilder.create(ActionTypes.ACTION)
        else:
            return ActionBuilder._action_mapping.get(ActionTypes(action_type)).from_json(uid, data)

    @staticmethod
    def redirect(action: Action,
                 bot: Bot,
                 update: Update,
                 game_cache: GameCache,
                 player_cache: PlayerCache,
                 location_cache: LocationCache):
        action.run_callback(bot, update, game_cache, player_cache, location_cache)

    @staticmethod
    def start(action: Action,
              update: Update,
              game_cache: GameCache,
              player_cache: PlayerCache,
              location_cache: LocationCache):
        action.start(update, game_cache, player_cache, location_cache)

    @staticmethod
    def save(action: Action) -> Action:
        ActionBuilder._r.set(action.key, action.to_json())
        return action

    @staticmethod
    def create(type_: ActionTypes):
        a = ActionBuilder._action_mapping[type_](key=uuid.uuid4())
        ActionBuilder.save(a)
        return a

    @staticmethod
    def copy_action(action: Action, action_type: ActionTypes = None):
        if action_type is None:
            return action.from_json(key=uuid.uuid4(), json_data=action.to_json())
        return ActionBuilder._action_mapping[action_type].from_json(key=uuid.uuid4(), json_data=action.to_json())

    @staticmethod
    def to_callback_data(action: Action):
        ActionBuilder.save(action)
        return json.dumps({
            ActionBuilder._KEY_UUID: str(action.key),
            ActionBuilder._KEY_TYPE: action.TYPE.value,
        })

    @staticmethod
    def action_as_callback_data(type_: ActionTypes):
        a = ActionBuilder.create(type_)
        return ActionBuilder.to_callback_data(a)
