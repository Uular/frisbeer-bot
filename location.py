from api import API
from cacheable import Cacheable


class Location(Cacheable):
    ID = "id"
    NAME = "name"
    LONGITUDE = "longitude"
    LATITUDE = "latitude"

    def __init__(self, id_: int, name: str, longitude: float, latitude: float):
        self.id = id_
        self.name = name
        self.longitude = longitude
        self.latitude = latitude

    @classmethod
    def from_json(cls, json_data):
        return cls(
            json_data[Location.ID],
            json_data[Location.NAME],
            json_data[Location.LONGITUDE],
            json_data[Location.LATITUDE],
        )

    @staticmethod
    def create(name: str, longitude: float = None, latitude: float = None) -> 'Location':
        return Location.from_json(API.create_location(name, longitude, latitude))

    def __str__(self):
        return self.name
