# -*- coding: utf-8 -*-

import json
import datetime
import logging
from uuid import uuid4

from litedfs.name.db.sqlite_interface import DataNodesTable, NoResultFound
from litedfs.name.config import CONFIG

LOG = logging.getLogger(__name__)


class DataNodes(object):
    _instance = None
    name = "data_nodes"

    def __new__(cls):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.table = DataNodesTable
            engine, session = DataNodesTable.init_engine_and_session()
            cls._instance.table.metadata.create_all(engine)
            cls._instance.session = session(autoflush = False, autocommit = False)
        return cls._instance

    @classmethod
    def instance(cls):
        return cls._instance

    def _new_id(self):
        return str(uuid4())

    def add(self, node_id, info = {}):
        result = False
        now = datetime.datetime.now()
        item = {
            "node_id": node_id,
            "info": json.dumps(info),
            "create_at": now,
            "update_at": now,
        }

        row = self.table()
        row.parse_dict(item)
        try:
            self.session.add(row)
            self.session.commit()
            result = node_id
            LOG.debug("add data node: %s", row)
        except Exception as e:
            LOG.exception(e)
            self.session.rollback()
        return result

    def update(self, node_id, data):
        result = False
        try:
            now = datetime.datetime.now()
            if "info" in data:
                data["info"] = json.dumps(data["info"])
            data["update_at"] = now
            self.session.query(self.table).filter_by(node_id = node_id).update(data)
            self.session.commit()
            result = True
            LOG.debug("update data node: %s, %s", node_id, data)
        except Exception as e:
            LOG.exception(e)
            self.session.rollback()
        return result

    def delete(self, node_id):
        result = False
        try:
            row = self.session.query(self.table).filter_by(node_id = node_id).one()
            self.session.delete(row)
            self.session.commit()
            result = True
            LOG.debug("delete data node: %s", row)
        except Exception as e:
            LOG.exception(e)
        return result

    def delete_by_id(self, db_id):
        result = False
        try:
            row = self.session.query(self.table).filter_by(id = db_id).one()
            self.session.delete(row)
            self.session.commit()
            result = True
            LOG.debug("delete data node by id: %s", row)
        except Exception as e:
            LOG.exception(e)
        return result

    def get(self, node_id):
        result = False
        try:
            row = self.session.query(self.table).filter_by(node_id = node_id).one()
            result = row.to_dict()
        except NoResultFound:
            result = None
        except Exception as e:
            LOG.exception(e)
        return result

    def list(self, offset = 0, limit = 0):
        result = {"data_nodes": [], "total": 0}
        try:
            offset = 0 if offset < 0 else offset
            limit = 0 if limit < 0 else limit
            result["total"] = self.count()
            if limit:
                rows = self.session.query(self.table).order_by(self.table.create_at.desc()).offset(offset).limit(limit)
            elif offset:
                rows = self.session.query(self.table).order_by(self.table.create_at.desc()).offset(offset)
            else:
                rows = self.session.query(self.table).order_by(self.table.create_at.desc())
            for row in rows:
                result["data_nodes"].append(row.to_dict())
        except Exception as e:
            LOG.exception(e)
        return result

    def count(self):
        result = 0
        try:
            result = self.session.query(self.table).count()
        except Exception as e:
            LOG.exception(e)
        return result

    def close(self):
        self.session.close()
