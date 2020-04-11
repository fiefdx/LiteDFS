# -*- coding: utf-8 -*-

import os
import json
import logging

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


class C(object):
    create = "c"
    makedirs = "md"
    delete = "d"
    rename = "r"
    move = "m"
    copy = "cp"


class InvalidValueError(Exception):
    def __init__(self, message):
        self.message = message


class SameNameExistsError(Exception):
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

    def __new__(cls):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.cache = {F.children: {}, F.type: "root"}
            cls._instance.editlog = None
            cls._instance.load_fsimage()
            cls._instance.load_editlog()
            cls._instance.dump_fsimage()
            cls._instance.editlog = AppendLogJson(os.path.join(CONFIG["data_path"], "editlog"))
        return cls._instance

    @classmethod
    def instance(cls):
        return cls._instance

    def create(self, file_path, file_info):
        result = False
        dir_path, file_name = os.path.split(file_path)
        parent = self.makedirs(dir_path)
        if parent:
            parent[F.children][file_name] = {F.type: F.file, F.info: file_info}
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
                file_id = file[F.info]["id"]
                task = {"command": "delete", "name": file_id}
                for i in Connection.id_decompress:
                    if i not in Connection.tasks:
                        Connection.tasks[i] = [task]
                    else:
                        Connection.tasks[i].append(task)
            elif file[F.type] == F.dir:
                self.delete_files(file)
            if self.editlog:
                self.editlog.writeline({F.cmd: C.delete, F.path: file_path})
        return result

    def delete_files(self, file):
        if F.children in file and file[F.children]:
            for name in file[F.children]:
                child = file[F.children][name]
                self.delete_files(child)
        else:
            if file[F.type] == F.file:
                file_id = file[F.info]["id"]
                task = {"command": "delete", "name": file_id}
                for i in Connection.id_decompress:
                    if i not in Connection.tasks:
                        Connection.tasks[i] = [task]
                    else:
                        Connection.tasks[i].append(task)
                LOG.debug("delete file: %s", file)

    def get_file_info(self, file_path):
        result = False
        exists, file_type, file, _ = self.get_info(file_path)
        if exists:
            result = file[F.info]
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

    def list_dir(self, directory_path, recursive = False):
        result = []
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
                    if file_type == F.file:
                        child["type"] = "file"
                        child["size"] = file[F.children][name][F.info]["size"]
                        child["id"] = file[F.children][name][F.info]["id"]
                    elif file_type == F.dir:
                        child["type"] = "directory"
                        child["size"] = 0
                        child["id"] = ""
                    result.append(child)
            LOG.debug("list_dir: %s", result)
        return result

    def exists(self, file_path):
        result, _, _, _ = self.get_info(directory_path)
        return result

    def makedirs(self, directory_path):
        result = False
        path_parts = splitall(directory_path)
        if path_parts[0] != "/":
            raise InvalidValueError("must be absolute path: %s" % directory_path)
        else:
            current_root = self.cache
            for dir_name in path_parts[1:]:
                if dir_name not in current_root[F.children]:
                    current_root[F.children][dir_name] = {F.type: F.dir, F.children: {}}
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
            current_root = self.cache
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

    def load_fsimage(self):
        result = False
        try:
            LOG.info("loading fsimage ...")
            fsimage_path = os.path.join(CONFIG["data_path"], "fsimage")
            fsimage = AppendLogJson(fsimage_path)
            for line in fsimage.iterlines():
                if line[F.cmd] == C.create:
                    self.create(line[F.path], line[F.info])
                elif line[F.cmd] == C.makedirs:
                    self.makedirs(line[F.path])
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    def load_editlog(self):
        result = False
        try:
            LOG.info("loading editlog ...")
            editlog_path = os.path.join(CONFIG["data_path"], "editlog")
            editlog = AppendLogJson(editlog_path)
            for line in editlog.iterlines():
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
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

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
            self.dump_files("/", self.cache)
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

    def dump_files(self, file_path, file):
        if F.children in file and file[F.children]:
            for name in file[F.children]:
                child = file[F.children][name]
                self.dump_files(os.path.join(file_path, name), child)
        else:
            if file[F.type] == F.file:
                LOG.debug("find file[%s]: %s", file_path, file)
                self.new_fsimage.writeline({F.cmd: C.create, F.path: file_path, F.info: file[F.info]})
            elif file[F.type] == F.dir:
                LOG.debug("find directory[%s]: %s", file_path, file)
                self.new_fsimage.writeline({F.cmd: C.makedirs, F.path: file_path})

    def close(self):
        pass
