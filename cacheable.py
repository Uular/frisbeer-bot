class Cacheable:
    @classmethod
    def from_json(cls, json_data: dict):
        raise NotImplementedError("Implement in subclass")

