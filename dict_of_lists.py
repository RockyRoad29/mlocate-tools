import collections
import logging

logger = logging.getLogger(__name__)


class DictOfLists (collections.OrderedDict):
    """
    Deriving it from OrderedDict basically for easier testing

    >>> coll = DictOfLists()
    >>> coll['a']
    []
    >>> coll.add_to('a','b'); coll
    DictOfLists([('a', ['b'])])
    >>> coll.add_to('a','c'); coll
    DictOfLists([('a', ['b', 'c'])])
    >>> coll['e']
    []
    >>> coll.add_to('d','b'); coll == {'d': ['b'], 'a': ['b', 'c']}
    True
    """
    def add_to(self, key, value):
        if key in self:
            self[key].append(value)
        else:
            self[key] = [value]
    def __getitem__(self, key):
        if key not in self:
            return []
        return dict.__getitem__(self,key)

