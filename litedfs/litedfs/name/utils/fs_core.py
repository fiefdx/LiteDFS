# -*- coding: utf-8 -*-

import os
import json
import time
import random
import logging
from copy import deepcopy

from tornado import gen, ioloop

from litedfs.name.utils.append_log import AppendLogJson
from litedfs.name.utils.listener import Connection
from litedfs.name.utils.common import file_sha1sum, file_md5sum, Errors, splitall
from litedfs.name.config import CONFIG

LOG = logging.getLogger(__name__)


class F(object):
    children = "c"
    type = "t"
    file = "f"
    dir = "d"
    info = "i"
    cmd = "c"
    new_name = "n"
    path = "p"
    source_path = "s"
    target_path = "t"
    id = "id"
    replica = "r"


class C(object):
    create = "c"
    makedirs = "md"
    delete = "d"
    rename = "r"
    move = "m"
    copy = "cp"
    update_replica = "ur"
    update_file_info = "ufi"


class InvalidValueError(Exception):
    def __init__(self, message):
        self.message = message


class SameNameExistsError(Exception):
    def __init__(self, message):
        self.message = message


class SameNameFileExistsError(Exception):
    def __init__(self, message):
        self.message = message


class FileNotExistsError(Exception):
    def __init__(self, message):
        self.message = message


class TargetPathMustDirectoryError(Exception):
    def __init__(self, message):
        self.message = message


class SourcePathNotExistsError(Exception):
    def __init__(self, message):
        self.message = message


class TargetPathNotExistsError(Exception):
    def __init__(self, message):
        self.message = message


class FileSystemTree(object):
    _instance = None
    name = "file_system_tree"

    def __new__(cls, interval = 10):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.tree = {F.children: {}, F.type: "root"}
            cls._instance.files = {}
            cls._instance.editlog = None
            cls._instance.status = "booting"
            cls._instance.locks = {}
            cls._instance.interval = interval
            cls._instance.ioloop_service()
        return cls._instance

    @classmethod
    def instance(cls):
        if cls._instance and cls._instance.status == "ready":
            return cls._instance
        else:
            return None

    def ioloop_service(self):
        self.periodic_lock_service = ioloop.PeriodicCallback(
            self.check_file_lock, 
            self.interval * 1000
        )
        self.periodic_lock_service.start()

    @gen.coroutine
    def recover(self):
        self.status = "recovering"
        yield self.load_fsimage()
        yield self.load_editlog()
        yield self.dump_fsimage()
        self.editlog = AppendLogJson(os.path.join(CONFIG["data_path"], "editlog"))
        # TODO: synchronize between name node and data nodes
        self.status = "ready"

    def set_file_lock(self, file_path, ttl = 60):
        result = False
        if file_path not in self.locks:
            self.locks[file_path] = time.time() + ttl
            result = True
        return result

    def unset_file_lock(self, file_path):
        try:
            if file_path in self.locks:
                del self.locks[file_path]
        except Exception as e:
            LOG.exception(e)

    def update_file_lock(self, file_path, ttl = 60):
        result = False
        if file_path in self.locks:
            self.locks[file_path] = time.time() + ttl
            result = True
        return result

    @gen.coroutine
    def check_file_lock(self):
        try:
            now = time.time()
            files = list(self.locks.keys())
            for f in files:
                if self.locks[f] < now:
                    del self.locks[f]
                    LOG.info("release write file lock: %s", f)
        except Exception as e:
            LOG.exception(e)

    def create(self, file_path, file_info):
        result = False
        dir_path, file_name = os.path.split(file_path)
        parent = self.makedirs(dir_path)
        if parent:
            file_id = file_info["id"]
            if file_name in parent[F.children]:
                raise SameNameExistsError("same file name exists: %s" % file_name)
            elif file_name == "":
                raise InvalidValueError("file name can't be empty string: %s" % file_name)
            else:
                parent[F.children][file_name] = {F.type: F.file, F.id: file_id}
                self.files[file_id] = file_info            
            if self.editlog:
                self.editlog.writeline({F.cmd: C.create, F.path: file_path, F.info: file_info})
            result = True
        return result

    def delete(self, file_path):
        result = True
        _, name = os.path.split(file_path)
        exists, file_type, file, parent = self.get_info(file_path)
        if exists:
            del parent[F.children][name]
            if file[F.type] == F.file:
                file_id = file[F.id]
                del self.files[file_id]
                task = {"command": "delete", "name": file_id}
                for i in Connection.id_decompress:
                    Connection.push_task(i, task)
            elif file[F.type] == F.dir:
                self.delete_files(file)
            if self.editlog:
                self.editlog.writeline({F.cmd: C.delete, F.path: file_path})
        return result

    @gen.coroutine
    def delete_files(self, file):
        if F.children in file and file[F.children]:
            for name in file[F.children]:
                child = file[F.children][name]
                yield self.delete_files(child)
        else:
            if file[F.type] == F.file:
                file_id = file[F.id]
                del self.files[file_id]
                task = {"command": "delete", "name": file_id}
                for i in Connection.id_decompress:
                    Connection.push_task(i, task)
                LOG.debug("delete file: %s", file)
                yield gen.moment

    def get_file_info(self, file_path):
        result = False
        exists, file_type, file, _ = self.get_info(file_path)
        if exists:
            file_id = file[F.id]
            result = self.files[file_id]
        return result

    def rename(self, file_path, new_name):
        result = True
        if self.is_valid_name(new_name):
            _, name = os.path.split(file_path)
            exists, file_type, file, parent = self.get_info(file_path)
            if exists:
                if new_name not in parent[F.children]:
                    parent[F.children][new_name] = file
                    del parent[F.children][name]
                    if self.editlog:
                        self.editlog.writeline({F.cmd: C.rename, F.path: file_path, F.new_name: new_name})
                else:
                    raise SameNameExistsError("same file name exists: %s" % new_name)
            else:
                raise FileNotExistsError("file not exists: %s" % file_path)
        else:
            raise InvalidValueError("invailed file name: %s" % new_name)
        return result

    def update_file_info(self, file_path, file_info):
        result = False
        exists, file_type, file, parent = self.get_info(file_path)
        if exists:
            if file_type == F.file:
                file_id = file[F.id]
                self.files[file_id] = file_info
                result = True
            else:
                raise InvalidValueError("must by file not directory: %s" % file_path)
        else:
            raise FileNotExistsError("file not exists: %s" % file_path)
        return result

    @gen.coroutine
    def update_replica(self, file_path, replica):
        result = False
        exists, file_type, file, parent = self.get_info(file_path)
        if exists:
            if file_type == F.file:
                file_id = file[F.id]
                file_info = self.files[file_id]
                file_info["replica"] = replica
                data_nodes = Connection.get_node_infos()
                data_node_ids = list(data_nodes.keys())
                if (
                        (file_info["replica"] > file_info["current_replica"] and len(data_nodes) >= file_info["current_replica"]) or
                        (file_info["replica"] < file_info["current_replica"] and len(data_nodes) >= file_info["replica"])
                    ):
                    for block in file_info["blocks"]:
                        old_node_ids = []
                        new_node_ids = []
                        for node_id in data_node_ids:
                            if node_id not in block[2]:
                                if not data_nodes[node_id][2]:
                                    new_node_ids.append(node_id)
                            else:
                                old_node_ids.append(node_id)
                        if old_node_ids:
                            delta = file_info["replica"] - len(old_node_ids)
                            block[2] = []
                            block[2].extend(old_node_ids)
                            if delta > 0: # increase block replica
                                if new_node_ids:
                                    if len(new_node_ids) <= delta:
                                        block[2].extend(new_node_ids)
                                    else:
                                        new_node_ids = random.sample(new_node_ids, delta)
                                        block[2].extend(new_node_ids)
                                    source_node_id = random.choice(old_node_ids)
                                    task = {"command": "replicate", "name": file_id, "block": block[0], "ids": new_node_ids}
                                    Connection.push_task(source_node_id, task)
                                else:
                                    LOG.warning("can not increase block replica, no usable data node")
                            elif delta < 0: # decrease block replica
                                delta = -delta
                                if len(block[2]) > delta:
                                    delete_node_ids = random.sample(block[2], delta)
                                    block[2] = [i for i in block[2] if i not in delete_node_ids]
                                    for delete_node_id in delete_node_ids:
                                        task = {"command": "delete", "name": file_id, "block": block[0]}
                                        Connection.push_task(delete_node_id, task)
                        yield gen.moment
                    file_info["current_replica"] = replica
                    for block in file_info["blocks"]:
                        if len(block[2]) < file_info["current_replica"]:
                            file_info["current_replica"] = len(block[2])
                result = True
                if self.editlog:
                    self.editlog.writeline({F.cmd: C.update_file_info, F.path: file_path, F.info: file_info})
            else:
                raise InvalidValueError("must by file not directory: %s" % file_path)
        else:
            raise FileNotExistsError("file not exists: %s" % file_path)
        return result

    def is_valid_name(self, name):
        result = True
        if "/" in name:
            result = False
        return result

    def move(self, source_path, target_path):
        result = False
        _, name = os.path.split(source_path)
        source_exists, _, source_file, source_parent = self.get_info(source_path)
        if source_exists:
            target_exists, target_type, target_file, _ = self.get_info(target_path)
            if target_exists:
                if target_type in (F.dir, "root"):
                    if name not in target_file[F.children]:
                        target_file[F.children][name] = source_file
                        del source_parent[F.children][name]
                        if self.editlog:
                            self.editlog.writeline({F.cmd: C.move, F.source_path: source_path, F.target_path: target_path})
                        result = True
                    else:
                        raise SameNameExistsError("same file name exists: %s" % name)
                else:
                    raise TargetPathMustDirectoryError("target path must be directory: %s" % target_path)
            else:
                raise TargetPathNotExistsError("target path not exists: %s" % target_path)
        else:
            raise SourcePathNotExistsError("source path not exists: %s" % source_path)
        return result

    def copy(self, source_path, target_path):
        result = False
        _, name = os.path.split(source_path)
        source_exists, _, source_file, source_parent = self.get_info(source_path)
        if source_exists:
            target_exists, target_type, target_file, _ = self.get_info(target_path)
            if target_exists:
                if target_type == F.dir:
                    if name not in target_file[F.children]:
                        target_file[F.children][name] = source_file
                        if self.editlog:
                            self.editlog.writeline({F.cmd: C.copy, F.source_path: source_path, F.target_path: target_path})
                        result = True
                    else:
                        raise SameNameExistsError("same file name exists: %s" % name)
                else:
                    raise TargetPathMustDirectoryError("target path must be directory: %s" % target_path)
            else:
                raise TargetPathNotExistsError("target path not exists: %s" % target_path)
        else:
            raise SourcePathNotExistsError("source path not exists: %s" % source_path)
        return result

    def list_dir(self, directory_path, offset = 0, limit = 0, recursive = False, include_file = True, include_directory = True):
        result = {"files": []}
        if offset < 0:
            offset = 0
        if limit < 0:
            limit = 0
        result["offset"] = offset
        result["limit"] = limit
        files = []
        dirs = []
        exists, file_type, file, _ = self.get_info(directory_path)
        if exists and file_type in (F.dir, "root"):
            if recursive:
                result = file[F.children]
            else:
                names = list(file[F.children].keys())
                names.sort()
                for name in names:
                    file_type = file[F.children][name][F.type]
                    child = {
                        "name": name,
                    }
                    if include_file and file_type == F.file:
                        file_id = file[F.children][name][F.id]
                        file_info = self.files[file_id]
                        child["type"] = "file"
                        child["size"] = file_info["size"]
                        child["id"] = file_id
                        if "ctime" in file_info:
                            child["ctime"] = file_info["ctime"]
                        if "mtime" in file_info:
                            child["mtime"] = file_info["mtime"]
                        if "current_replica" in file_info:
                            child["current_replica"] = file_info["current_replica"]
                        if "replica" in file_info:
                            child["replica"] = file_info["replica"]
                        files.append(child)
                    elif include_directory and file_type == F.dir:
                        child["type"] = "directory"
                        child["size"] = 0
                        child["id"] = ""
                        dirs.append(child)
                result["files"].extend(dirs)
                result["files"].extend(files)
                result["total"] = len(result["files"])
                if offset > 0 and limit > 0:
                    result["files"] = result["files"][offset:offset + limit]
                elif offset > 0:
                    result["files"] = result["files"][offset:]
                elif limit > 0:
                    result["files"] = result["files"][:limit]
            LOG.debug("list_dir: %s", result)
        return result

    def exists(self, file_path):
        result, _, _, _ = self.get_info(file_path)
        return result

    def makedirs(self, directory_path):
        result = False
        path_parts = splitall(directory_path)
        if path_parts[0] != "/":
            raise InvalidValueError("must be absolute path: %s" % directory_path)
        else:
            current_root = self.tree
            for dir_name in path_parts[1:]:
                if dir_name not in current_root[F.children]:
                    current_root[F.children][dir_name] = {F.type: F.dir, F.children: {}}
                else:
                    child = current_root[F.children][dir_name]
                    if child[F.type] == F.file:
                        raise SameNameFileExistsError("same file name exists: %s" % dir_name)
                current_root = current_root[F.children][dir_name]
            if self.editlog:
                self.editlog.writeline({F.cmd: C.makedirs, F.path: directory_path})
            result = current_root
        return result

    def isdir(self, directory_path):
        result = False
        exists, file_type, _, _ = self.get_info(directory_path)
        if exists and file_type == F.dir:
            result = True
        return result

    def isfile(self, file_path):
        result = False
        exists, file_type, _, _ = self.get_info(file_path)
        if exists and file_type == F.file:
            result = True
        return result

    def get_info(self, file_path):
        result = [True, "", {}, None]
        path_parts = splitall(file_path)
        if path_parts[0] != "/":
            raise InvalidValueError("must be absolute path: %s" % file_path)
        else:
            parent = None
            current_root = self.tree
            for name in path_parts[1:]:
                if name not in current_root[F.children]:
                    result[0] = False
                    break
                else:
                    parent = current_root
                    current_root = current_root[F.children][name]
            if result[0]:
                result[1] = current_root[F.type]
                result[2] = current_root
                result[3] = parent
        return result

    @gen.coroutine
    def load_fsimage(self):
        result = False
        try:
            LOG.info("loading fsimage ...")
            fsimage_path = os.path.join(CONFIG["data_path"], "fsimage")
            fsimage = AppendLogJson(fsimage_path)
            n = 0
            for line in fsimage.iterlines():
                if n >= 100:
                    n = 0
                    yield gen.moment
                if line[F.cmd] == C.create:
                    self.create(line[F.path], line[F.info])
                elif line[F.cmd] == C.makedirs:
                    self.makedirs(line[F.path])
                n += 1
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    @gen.coroutine
    def load_editlog(self):
        result = False
        try:
            LOG.info("loading editlog ...")
            editlog_path = os.path.join(CONFIG["data_path"], "editlog")
            editlog = AppendLogJson(editlog_path)
            n = 0
            for line in editlog.iterlines():
                if n >= 100:
                    n = 0
                    yield gen.moment
                if line[F.cmd] == C.create:
                    self.create(line[F.path], line[F.info])
                elif line[F.cmd] == C.makedirs:
                    self.makedirs(line[F.path])
                elif line[F.cmd] == C.rename:
                    self.rename(line[F.path], line[F.new_name])
                elif line[F.cmd] == C.delete:
                    self.delete(line[F.path])
                elif line[F.cmd] == C.move:
                    self.move(line[F.source_path], line[F.target_path])
                elif line[F.cmd] == C.copy:
                    self.copy(line[F.source_path], line[F.target_path])
                elif line[F.cmd] == C.update_file_info:
                    self.update_file_info(line[F.path], line[F.info])
                n += 1
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    @gen.coroutine
    def dump_fsimage(self):
        result = False
        try:
            LOG.info("dumping fsimage ...")
            new_fsimage_path = os.path.join(CONFIG["data_path"], "fsimage.new")
            fsimage_path = os.path.join(CONFIG["data_path"], "fsimage")
            old_fsimage_path = os.path.join(CONFIG["data_path"], "fsimage.old")
            editlog_path = os.path.join(CONFIG["data_path"], "editlog")
            LOG.debug("new fsimage: %s", new_fsimage_path)
            self.new_fsimage = AppendLogJson(new_fsimage_path)
            yield self.dump_files("/", self.tree)
            if os.path.exists(old_fsimage_path):
                os.remove(old_fsimage_path)
            if os.path.exists(fsimage_path):
                os.rename(fsimage_path, old_fsimage_path)
            if os.path.exists(new_fsimage_path):
                os.rename(new_fsimage_path, fsimage_path)
            if os.path.exists(editlog_path):
                os.remove(editlog_path)
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    @gen.coroutine
    def dump_files(self, file_path, file):
        if F.children in file and file[F.children]:
            for name in file[F.children]:
                child = file[F.children][name]
                yield self.dump_files(os.path.join(file_path, name), child)
        else:
            if file[F.type] == F.file:
                file_id = file[F.id]
                file_info = self.files[file_id]
                LOG.debug("find file[%s]: %s", file_path, file)
                self.new_fsimage.writeline({F.cmd: C.create, F.path: file_path, F.info: file_info})
            elif file[F.type] == F.dir:
                LOG.debug("find directory[%s]: %s", file_path, file)
                self.new_fsimage.writeline({F.cmd: C.makedirs, F.path: file_path})

    def close(self):
        pass
