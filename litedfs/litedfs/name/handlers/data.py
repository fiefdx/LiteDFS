# -*- coding: utf-8 -*-

import os
import json
import time
import random
import logging
from uuid import uuid4

from tornado import web
from tornado import gen

from litedfs.name.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.name.utils.listener import Connection
from litedfs.name.utils.common import file_sha1sum, file_md5sum, Errors, splitall
from litedfs.name.config import CONFIG

LOG = logging.getLogger("__name__")


class GenerateFileBlockListHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_size = int(self.get_argument("size", "0"))
            replica = int(self.get_argument("replica", "1"))
            block_size = CONFIG["block_size"]
            data_nodes = Connection.get_node_infos()
            if len(data_nodes) > 0:
                data_node_ids = list(data_nodes.keys())
                blocks = []
                block_id = 0
                if replica < 1:
                    replica = 1
                if replica > len(data_nodes):
                    replica = len(data_nodes)
                while file_size > block_size:
                    blocks.append((block_id, block_size, random.sample(data_node_ids, replica)))
                    file_size -= block_size
                    block_id += 1
                if file_size > 0:
                    blocks.append((block_id, file_size, random.sample(data_node_ids, replica)))
                result["data_nodes"] = data_nodes
                result["blocks"] = blocks
                result["file_id"] = str(uuid4())
            else:
                Errors.set_result_error("AllDataNodeOffline", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class CreateFileHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        result = {"result": Errors.OK}
        try:
            self.json_data = json.loads(self.request.body.decode("utf-8"))
            file_path = self.get_json_argument("path", "")
            file_type = self.get_json_argument("type", "")
            file_id = self.get_json_argument("file_id", "")
            replica = int(self.get_json_argument("replica", "1"))
            blocks = self.get_json_argument("blocks", [])
            if replica < 1:
                replica = 1

        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class GetFileBlockInfoHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            pass
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()
