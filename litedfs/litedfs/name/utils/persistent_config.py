# -*- coding: utf-8 -*-

import logging

from tinydb import TinyDB
from tinydb.operations import delete

from tornado_discovery.config import BaseConfig

LOG = logging.getLogger(__name__)


class PersistentConfig(BaseConfig):
    def __init__(self, db_path):
        self.db_path = db_path
        self.db = TinyDB(self.db_path)
        self.doc_id = 1
        if len(self.db.all()) == 0:
            self.db.insert({})

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def has_key(self, key):
        result = False
        try:
            result = key in self.db.all()[0]
        except Exception as e:
            LOG.exception(e)
        return result

    def get(self, key):
        result = None
        try:
            result = self.db.all()[0][key]
        except Exception as e:
            LOG.exception(e)
        return result

    def set(self, key, value):
        result = False
        try:
            self.db.update({key: value}, doc_ids = [self.doc_id])
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    def update(self, key, value):
        return self.set(key, value)

    def delete(self, key):
        result = False
        try:
            self.db.update(delete(key), doc_ids = [self.doc_id])
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    def to_dict(self):
        result = {}
        try:
            result = self.db.all()[0]
        except Exception as e:
            LOG.exception(e)
        return result

    def from_dict(self, data):
        result = False
        try:
            self.db.update(data, doc_ids = [self.doc_id])
            result = True
        except Exception as e:
            LOG.exception(e)
        return result
