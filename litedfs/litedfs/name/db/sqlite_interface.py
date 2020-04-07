# -*- coding: utf-8 -*-

import os
import json
import logging

import sqlalchemy
from sqlalchemy import func, exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, Date, DateTime, Numeric
from sqlalchemy.orm.exc import NoResultFound

from litedfs.name.utils import common
from litedfs.name.config import CONFIG

LOG = logging.getLogger(__name__)


BaseDataNodes = declarative_base()

class DataNodesTable(BaseDataNodes):
    __tablename__ = "data_nodes"

    id = Column(Integer, primary_key = True, autoincrement = True)
    node_id = Column(Text, unique = True, nullable = False, index = True)
    info = Column(Text, nullable = False)
    create_at = Column(DateTime, nullable = False, index = True)
    update_at = Column(DateTime, nullable = False, index = True)

    @classmethod
    def init_engine_and_session(cls):
        cls.engine = create_engine('sqlite:///' + os.path.join(CONFIG["data_path"], "data_nodes.db"), echo = False)
        cls.session = sessionmaker(bind = cls.engine)
        return cls.engine, cls.session

    def to_dict(self):
        return {
            "id": self.id,
            "node_id": self.node_id,
            "info": json.loads(self.info),
            "create_at": str(self.create_at), # "%Y-%m-%d %H:%M:%S.%f")
            "update_at": str(self.update_at),
        }

    def parse_dict(self, source):
        result = False

        attrs = [
            "node_id",
            "info",
            "create_at",
            "update_at",
        ]

        if hasattr(source, "__getitem__"):
            for attr in attrs:
                try:
                    setattr(self, attr, source[attr])
                except:
                    LOG.debug("some exception occured when extract %s attribute to object, i will discard it",
                        attr)
                    continue
            result = True
        else:
            LOG.debug("input param source does not have dict-like method, so i will do nothing at all!")
        return result

    def __repr__(self):
        return "application: %s" % self.to_dict()
