import datetime

import logging
from typing import ValuesView, List, Callable, Union, Type, TypeVar, Generic

from fuzzywuzzy import fuzz

from cacheable import Cacheable


class NotFoundError(Exception):
    pass


C = TypeVar('C', bound=Cacheable, covariant=True)
K = TypeVar('K', str, int)


class Cache(Generic[C]):
    def __init__(self):
        self.data_store = {}
        self.timestamp = None

    def set_data(self, cls: Type[C], key_accessor: Callable[[C], K], data: List[dict]):
        """
        (re)build cache data from given input
        
        :param cls: subclass of Cacheable
        :param key_accessor: Callable which accesses key from Cacheable
        :param data: List of Dictionaries from which to build cache (ie. response.json() from API)
        :return: None
        """
        for entity in data:
            obj = cls.from_json(entity)
            key_val = key_accessor(obj)
            self.data_store[key_val] = obj
        self.timestamp = datetime.datetime.now()

    def get(self, key: K) -> C:
        updated = self.update()
        try:
            return self.data_store[key]
        except KeyError:
            if not updated:
                self.update(force=True)
            else:
                raise NotFoundError()
        try:
            return self.data_store[key]
        except KeyError:
            raise NotFoundError()

    def get_all(self) -> ValuesView[C]:
        """
        Update cache if needed and return all objects
        :return: a list of cached objects
        """
        self.update()
        return self.data_store.values()

    def fuzzy_get(self, key: K) -> C:
        self.update()
        try:
            return self.get(key)
        except NotFoundError:
            pass
        fuzzes = [(data_key, fuzz.partial_ratio(data_key, key)) for data_key in self.data_store.keys()]
        fuzzes = sorted(fuzzes, key=lambda key_ratio_pair: key_ratio_pair[1])
        logging.debug("Best match for {} was {} at level {}".format(key, fuzzes[-1][0], fuzzes[-1][1]))
        return self.data_store[fuzzes[-1][0]]

    def filter(self, filtering_function: Callable[[C], bool]) -> List[C]:
        """
        Return list of cached objects matching filter
        :param filtering_function: function taking cached object and returning bool whether 
        it should be included in returned list
        :return: List of objects matching filter
        """
        self.update()
        return [instance for instance in self.data_store.values() if filtering_function(instance)]

    def is_valid(self) -> bool:
        """
        Check if cache needs updating
        :return: bool indicating if cache is valid
        """
        if not self.timestamp or (datetime.datetime.now() - self.timestamp).total_seconds() > 30:
            logging.debug("Cache is too old")
            return False
        logging.debug("Cache ok")
        return True

    def update(self, force=False) -> bool:
        """
        Update cache if it's past its validity period or update is forced
        :param force: force update regardless of timestamp
        :return: whether cache actually updated
        """
        raise NotImplemented("Implement in subclass")
