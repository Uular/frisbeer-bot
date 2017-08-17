from cacheable import Cacheable


class Rank(Cacheable):
    NAME = "name"
    IMAGE_URL = "image_url"

    def __init__(self, name, image_url):
        self.name = name
        self.image_url = image_url

    @classmethod
    def from_json(cls, json_data: dict):
        try:
            return cls(json_data[Rank.NAME], json_data[Rank.IMAGE_URL])
        except:
            return None

