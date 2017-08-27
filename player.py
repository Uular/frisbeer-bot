from cacheable import Cacheable
from rank import Rank


class Player(Cacheable):
    ID = "id"
    NICK = "name"
    RANK = "rank"
    SCORE = "score"

    def __init__(self, id_: int, nick: str, rank: Rank, score: int, team=None):
        self.id = id_
        self.nick = nick
        self.rank = rank
        self.score = score
        self.team = team

    @classmethod
    def from_json(cls, json_data):
        return cls(
            json_data[Player.ID],
            json_data[Player.NICK],
            Rank.from_json(json_data[Player.RANK]),
            json_data[Player.SCORE],
            json_data.get("team", None)
        )

    def __str__(self):
        if self.rank:
            return "{}: rank {}, score {}".format(self.nick, self.rank, self.score)
        else:
            return "{}: score {}".format(self.nick, self.score)
