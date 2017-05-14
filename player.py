import logging

from api import API
from cache import Cache


class Player:
    NICK = "name"
    RANK = "rank"
    SCORE = "score"
    _cache = None

    def __init__(self, nick, rank, score):
        self.nick = nick
        self.rank = rank
        self.score = score

    @classmethod
    def by_nick(cls, nick):
        if Player._cache is None or not Player._cache.is_valid():
            logging.info("Getting newer data from server")
            json_data = API.get_players()
            Player._cache = Cache(Player.NICK, json_data)
        player_data = Player._cache.fuzzy_get(nick)
        return cls(player_data[Player.NICK], player_data[Player.RANK], player_data[Player.SCORE])

    def __str__(self):
        if len(self.rank):
            return "{}: rank {}, score {}".format(self.nick, self.rank, self.score)
        else:
            return "{}: score {}".format(self.nick, self.score)
