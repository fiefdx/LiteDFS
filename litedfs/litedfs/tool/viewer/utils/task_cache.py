# -*- coding: utf-8 -*-

import logging

LOG = logging.getLogger(__name__)


class TaskCache(object):
    cache = []
    max_size = 10

    @classmethod
    def set_max_size(cls, size):
        cls.max_size = size

    @classmethod
    def push(cls, task):
        cls.cache.append(task)

    @classmethod
    def pop(cls):
        result = None
        try:
            result = cls.cache.pop(0)
        except IndexError:
            pass
        except Exception as e:
            LOG.exception(e)
        return result

    @classmethod
    def empty(cls):
        return len(cls.cache) == 0

    @classmethod
    def full(cls):
        return len(cls.cache) >= cls.max_size

    @classmethod
    def size(cls):
        return len(cls.cache)