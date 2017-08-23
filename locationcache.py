from api import API
from cache import Cache
from location import Location


class LocationCache(Cache):
    def __init__(self):
        super().__init__(Location, lambda location: location.id)

    def update(self, force=False):
        if not force and self.is_valid():
            return False
        self.set_data(API.get_locations())
