from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class Database:
    engine = create_engine('sqlite:///db.sqlite3', echo=True)
    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'

        id = Column(Integer, primary_key=True)
        frisbeer_nick = Column(String)
        telegram_username = Column(String, unique=True)

        def __repr__(self):
            return "{} - {}".format(self.telegram_nick, self.frisbeer_nick)

    class Game(Base):
        __tablename__ = 'games'

        id = Column(Integer, primary_key=True)
        name = Column(String)
        date = Column(DateTime)

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    @staticmethod
    def create_game()->Game:
        game = Database.Game()
        Database.session.add(game)
        Database.session.commit()
        return game

    @staticmethod
    def game_by_id(identifier: int)->Game:
        return Database.session.query(Database.Game).filter(Database.Game.id == identifier).first()

    @staticmethod
    def save():
        Database.session.commit()

