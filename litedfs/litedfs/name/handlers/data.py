# -*- coding: utf-8 -*-

import os
import json
import time
import random
import urllib
import logging
from uuid import uuid4

from tornado import web
from tornado import gen

from litedfs.name.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.name.utils.fs_core import FileSystemTree, InvalidValueError, SameNameExistsError, TargetPathMustDirectoryError, TargetPathNotExistsError, SourcePathNotExistsError, FileNotExistsError
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
            for i in data_nodes:
                data_node = data_nodes[i]
                if data_node[0] == "127.0.0.1":
                    host_parts = urllib.parse.urlsplit("//" + self.request.host)
                    data_node[0] = host_parts.hostname
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
                result["id"] = str(uuid4())
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
            file_size = int(self.get_json_argument("size", "0"))
            file_path = self.get_json_argument("path", "")
            file_id = self.get_json_argument("id", "")
            replica = int(self.get_json_argument("replica", "1"))
            blocks = self.get_json_argument("blocks", [])
            if file_path and file_id and replica:
                success = FileSystemTree.instance().create(file_path, {"size": file_size, "id": file_id, "replica": replica, "blocks": blocks})
                if not success:
                    Errors.set_result_error("OperationFailed", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class MoveFileDirectoryHandler(BaseHandler):
    @gen.coroutine
    def put(self):
        result = {"result": Errors.OK}
        try:
            self.json_data = json.loads(self.request.body.decode("utf-8"))
            source_path = self.get_json_argument("source_path", "")
            target_path = self.get_json_argument("target_path", "")
            if source_path and target_path:
                success = FileSystemTree.instance().move(source_path, target_path)
                if not success:
                    Errors.set_result_error("OperationFailed", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except SameNameExistsError as e:
            LOG.error(e)
            Errors.set_result_error("SameNameExists", result)
        except TargetPathMustDirectoryError as e:
            LOG.error(e)
            Errors.set_result_error("TargetPathMustDirectory", result)
        except TargetPathNotExistsError as e:
            LOG.error(e)
            Errors.set_result_error("TargetPathNotExists", result)
        except SourcePathNotExistsError as e:
            LOG.error(e)
            Errors.set_result_error("SourcePathNotExists", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class RenameFileDirectoryHandler(BaseHandler):
    @gen.coroutine
    def put(self):
        result = {"result": Errors.OK}
        try:
            self.json_data = json.loads(self.request.body.decode("utf-8"))
            file_path = self.get_json_argument("path", "")
            new_name = self.get_json_argument("new_name", "")
            if file_path and new_name:
                success = FileSystemTree.instance().rename(file_path, new_name)
                if not success:
                    Errors.set_result_error("OperationFailed", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except SameNameExistsError as e:
            LOG.error(e)
            Errors.set_result_error("SameNameExists", result)
        except FileNotExistsError as e:
            LOG.error(e)
            Errors.set_result_error("FileNotExists", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class DeleteFileHandler(BaseHandler):
    @gen.coroutine
    def delete(self):
        result = {"result": Errors.OK}
        try:
            file_path = self.get_argument("path", "")
            if file_path:
                success = FileSystemTree.instance().delete(file_path)
                if not success:
                    Errors.set_result_error("OperationFailed", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class CreateDirectoryHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        result = {"result": Errors.OK}
        try:
            self.json_data = json.loads(self.request.body.decode("utf-8"))
            dir_path = self.get_json_argument("path", "")
            if dir_path:
                success = FileSystemTree.instance().makedirs(dir_path)
                if not success:
                    Errors.set_result_error("OperationFailed", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class DeleteDirectoryHandler(BaseHandler):
    @gen.coroutine
    def delete(self):
        result = {"result": Errors.OK}
        try:
            dir_path = self.get_argument("path", "")
            if dir_path:
                success = FileSystemTree.instance().delete(dir_path)
                if not success:
                    Errors.set_result_error("OperationFailed", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class ListDirectoryHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            dir_path = self.get_argument("path", "")
            if dir_path:
                result["children"] = FileSystemTree.instance().list_dir(dir_path)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
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
            file_path = self.get_argument("path", "")
            data_nodes = Connection.get_node_infos()
            for i in data_nodes:
                data_node = data_nodes[i]
                if data_node[0] == "127.0.0.1":
                    host_parts = urllib.parse.urlsplit("//" + self.request.host)
                    data_node[0] = host_parts.hostname
            if file_path:
                file_info = FileSystemTree.instance().get_file_info(file_path)
                if file_info:
                    result["file_info"] = file_info
                    result["data_nodes"] = data_nodes
                else:
                    Errors.set_result_error("FileNotExists", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()
