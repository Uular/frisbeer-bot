import datetime

import logging
from typing import ValuesView, List, Callable

from fuzzywuzzy import fuzz

from cacheable import Cacheable


class Cache:
    def __init__(self, cls, key_accessor, data, case_insensitive=False):
        self.data_store = {}
        self.case_insensitive = case_insensitive
        for entity in data:
            obj = cls.from_json(entity)
            key_val = key_accessor(obj)
            self.data_store[key_val] = obj
        self.timestamp = datetime.datetime.now()

    def get(self, key) -> Cacheable:
        if self.case_insensitive:
            return self.data_store[key.lower()]
        return self.data_store[key]

    def get_all(self) -> ValuesView[Cacheable]:
        return self.data_store.values()

    def fuzzy_get(self, key):
        try:
            return self.get(key)
        except KeyError:
            pass
        if self.case_insensitive:
            key_val = key.lower()
        else:
            key_val = key
        fuzzes = [(data_key, fuzz.partial_ratio(data_key, key_val)) for data_key in self.data_store.keys()]
        fuzzes = sorted(fuzzes, key=lambda key_ratio_pair: key_ratio_pair[1])
        logging.debug("Best match for {} was {} at level {}".format(key, fuzzes[-1][0], fuzzes[-1][1]))
        return self.data_store[fuzzes[-1][0]]

    def filter(self, filtering_function: Callable[[Cacheable], bool]) -> List[Cacheable]:
        return [instance for instance in self.data_store.values() if filtering_function(instance)]

    def is_valid(self):
        if (datetime.datetime.now() - self.timestamp).total_seconds() > 30:
            logging.debug("Cache is too old")
            return False
        logging.debug("Cache ok")
        return True
