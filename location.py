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

    def __str__(self):
        return self.name
