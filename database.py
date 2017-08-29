from typing import Iterable

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class Database:
    engine = create_engine('sqlite:///db.sqlite3', echo=True)
    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'

        id = Column(Integer, primary_key=True)
        frisbeer_id = Column(Integer, nullable=False)
        frisbeer_nick = Column(String, nullable=False)
        telegram_username = Column(String, unique=True, nullable=True)
        telegram_user_id = Column(Integer, unique=True, nullable=False)

        def __repr__(self):
            return "{} - {}".format(self.telegram_username if self.telegram_username else self.telegram_user_id,
                                    self.frisbeer_nick)

    class Game(Base):
        __tablename__ = 'games'

        id = Column(Integer, primary_key=True)
        name = Column(String)
        date = Column(DateTime)
        location = Column(Integer)

    class NotificationChannel(Base):
        __tablename__ = 'notification_channel'
        id = Column(Integer, primary_key=True)
        channel_id = Column(Integer, unique=True)

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    @staticmethod
    def create_game() -> Game:
        game = Database.Game()
        Database.session.add(game)
        Database.session.commit()
        return game

    @staticmethod
    def create_user(frisbeer_id: int, frisbeer_nick: str, telegram_user_id: int, telegram_username: str = None) -> User:
        user = Database.User(frisbeer_id=frisbeer_id, frisbeer_nick=frisbeer_nick,
                             telegram_user_id=telegram_user_id, telegram_username=telegram_username)
        Database.session.add(user)
        Database.session.commit()
        return user

    @staticmethod
    def game_by_id(identifier: int) -> Game:
        return Database.session.query(Database.Game).filter(Database.Game.id == identifier).first()

    @staticmethod
    def user_by_telegram_id(identifier: int) -> User:
        return Database.session.query(Database.User).filter(Database.User.telegram_user_id == identifier).first()

    @staticmethod
    def user_by_telegram_username(username: str) -> User:
        return Database.session.query(Database.User).filter(Database.User.telegram_username == username).first()

    @staticmethod
    def register_channel(channel_id: int) -> NotificationChannel:
        channel = Database.NotificationChannel()
        channel.channel_id = channel_id
        Database.session.add(channel)
        Database.session.commit()
        return channel

    @staticmethod
    def get_notification_channels() -> Iterable[NotificationChannel]:
        return list(Database.session.query(Database.NotificationChannel))

    @staticmethod
    def get_notification_channel_by_id(channel_id: int) -> NotificationChannel:
        return Database.session.query(Database.NotificationChannel) \
            .filter(Database.NotificationChannel.channel_id == channel_id).first()

    @staticmethod
    def save():
        Database.session.commit()

    @staticmethod
    def delete_channel(channel_id):
        Database.session.delete(Database.get_notification_channel_by_id(channel_id))
