from api import API


class Player:
    NICK = "name"
    RANK = "rank"
    SCORE = "score"

    def __init__(self, nick, rank, score):
        self.nick = nick
        self.rank = rank
        self.score = score

    @classmethod
    def by_nick(cls, nick):
        json_data = API.get_players()
        player_data = None
        for p in json_data:
            if p[Player.NICK] == nick:
                player_data = p
                break
        return cls(player_data[Player.NICK], player_data[Player.RANK], player_data[Player.SCORE])

    def __str__(self):
        if len(self.rank):
            return "{}: rank {}, score {}".format(self.nick, self.rank, self.score)
        else:
            return "{}: score {}".format(self.nick, self.score)
