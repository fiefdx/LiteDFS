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
from litedfs.name.utils.fs_core import FileSystemTree, InvalidValueError, SameNameExistsError, TargetPathMustDirectoryError, TargetPathNotExistsError, SourcePathNotExistsError, FileNotExistsError, SameNameFileExistsError
from litedfs.name.utils.listener import Connection
from litedfs.name.utils.common import file_sha1sum, file_md5sum, Errors, splitall
from litedfs.name.config import CONFIG

LOG = logging.getLogger("__name__")


class GenerateFileBlockListHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_path = self.get_argument("path", "")
            file_size = int(self.get_argument("size", "0"))
            replica = int(self.get_argument("replica", "1"))
            lock_ttl = int(self.get_argument("lock_ttl", "60"))
            block_size = CONFIG["block_size"]
            if file_path:
                fs = FileSystemTree.instance()
                if fs:
                    if not fs.exists(file_path):
                        lock_success = fs.set_file_lock(file_path, ttl = lock_ttl)
                        if lock_success:
                            data_nodes = Connection.get_node_infos(without_full_node = True)
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
                                Errors.set_result_error("NoUsableDataNode", result)
                        else:
                            Errors.set_result_error("SetFileLockFailed", result)
                    else:
                        Errors.set_result_error("SameNameExists", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class UpdateFileLockHandler(BaseHandler):
    @gen.coroutine
    def put(self):
        result = {"result": Errors.OK}
        try:
            self.json_data = json.loads(self.request.body.decode("utf-8"))
            file_path = self.get_json_argument("path", "")
            lock_ttl = self.get_json_argument("lock_ttl", 60)
            if file_path and lock_ttl:
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.update_file_lock(file_path, ttl = lock_ttl)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
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
            checksum = self.get_json_argument("checksum", "")
            current_replica = replica
            for block in blocks:
                if current_replica > len(block[2]):
                    current_replica = len(block[2])
            if file_path and file_id and replica:
                fs = FileSystemTree.instance()
                if fs:
                    if not fs.exists(file_path):
                        now = int(time.time())
                        success = fs.create(
                            file_path,
                            {
                                "size": file_size,
                                "id": file_id,
                                "replica": replica,
                                "current_replica": current_replica,
                                "blocks": blocks,
                                "checksum": checksum,
                                "ctime": now,
                                "mtime": now,
                            }
                        )
                        if success:
                            fs.unset_file_lock(file_path)
                        else:
                            Errors.set_result_error("OperationFailed", result)
                    else:
                        Errors.set_result_error("SameNameExists", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except SameNameExistsError as e:
            LOG.error(e)
            Errors.set_result_error("SameNameExists", result)
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
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.move(source_path, target_path)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.rename(file_path, new_name)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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


class UpdateFileHandler(BaseHandler):
    @gen.coroutine
    def put(self):
        result = {"result": Errors.OK}
        try:
            self.json_data = json.loads(self.request.body.decode("utf-8"))
            file_path = self.get_json_argument("path", "")
            replica = self.get_json_argument("replica", 1)
            if replica < 1:
                replica = 1
            if file_path and replica:
                fs = FileSystemTree.instance()
                if fs:
                    success = yield fs.update_replica(file_path, replica)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
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
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.delete(file_path)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.makedirs(dir_path)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except InvalidValueError as e:
            LOG.error(e)
            Errors.set_result_error("InvalidParameters", result)
        except SameNameFileExistsError as e:
            LOG.error(e)
            Errors.set_result_error("SameNameFileExists", result)
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
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.delete(dir_path)
                    if not success:
                        Errors.set_result_error("OperationFailed", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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
            include_file = True if self.get_argument("include_file", "true") == "true" else False
            include_directory = True if self.get_argument("include_directory", "true") == "true" else False
            offset = int(self.get_argument("offset", 0))
            limit = int(self.get_argument("limit", 0))
            if dir_path:
                fs = FileSystemTree.instance()
                if fs:
                    r = fs.list_dir(dir_path, offset = offset, limit = limit, recursive = False, include_file = include_file, include_directory = include_directory)
                    result["children"] = r["files"]
                    result["offset"] = r["offset"]
                    result["limit"] = r["limit"]
                    result["total"] = r["total"]
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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
                fs = FileSystemTree.instance()
                if fs:
                    if fs.isfile(file_path):
                        file_info = fs.get_file_info(file_path)
                        if file_info:
                            result["file_info"] = file_info
                            result["data_nodes"] = data_nodes
                            result["block_size"] = CONFIG["block_size"]
                        else:
                            Errors.set_result_error("FileNotExists", result)
                    else:
                        Errors.set_result_error("InvalidParameters", result)
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
            else:
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class IsFileHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_path = self.get_argument("path", "")
            if file_path:
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.isfile(file_path)
                    if success:
                        result["file"] = True
                    else:
                        result["file"] = False
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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


class IsDirectoryHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_path = self.get_argument("path", "")
            if file_path:
                fs = FileSystemTree.instance()
                if fs:
                    success = fs.isdir(file_path)
                    if success:
                        result["directory"] = True
                    else:
                        result["directory"] = False
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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


class PathInfoHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_path = self.get_argument("path", "")
            if file_path:
                fs = FileSystemTree.instance()
                if fs:
                    r = fs.get_info(file_path)
                    result["info"] = {}
                    result["info"]["exists"] = r[0]
                    result["info"]["type"] = "file"
                    if r[1] == "d":
                        result["info"]["type"] = "directory"
                else:
                    Errors.set_result_error("ServiceNotReadyYet", result)
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
