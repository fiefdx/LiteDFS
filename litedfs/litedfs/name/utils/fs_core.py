# -*- coding: utf-8 -*-

import os
import json
import logging

from litedfs.name.utils.common import file_sha1sum, file_md5sum, Errors, splitall, InvalidValueError
from litedfs.name.config import CONFIG

LOG = logging.getLogger(__name__)


class FileSystemTree(object):
    _instance = None
    name = "file_system_tree"

    def __new__(cls):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.cache = {"children": {}}
        return cls._instance

    @classmethod
    def instance(cls):
        return cls._instance

    def create_file(self, file_path, file_info):
        result = False
        dir_path, file_name = os.path.split(file_path)
        parent = self.makdirs(dir_path)
        if parent:
            parent["children"][file_name] = {"type": "file", "info": file_info}
            result = True
        return result

    def delete_file(self, file_path):
        result = True
        _, name = os.path.split(file_path)
        exists, file_type, _, parent = self.get_info(file_path)
        if exists:
            del parent["children"][name]
        return result

    def get_file_info(self, file_path):
        result = False
        exists, file_type, file, _ = self.get_info(file_path)
        if exists:
            result = file
        return result

    def rename_file(self, file_path, new_name):
        result = True
        _, name = os.path.split(file_path)
        exists, file_type, file, parent = self.get_info(file_path)
        if exists:
            if new_name not in parent["children"]:
                parent["children"][new_name] = file
                del parent["children"][name]
            else:
                raise InvalidValueError("same file name exists: %s" % new_name)
        else:
            raise InvalidValueError("file not exists: %s" % file_path)
        return result

    def move_file(self, source_path, target_path):
        result = False
        _, name = os.path.split(source_path)
        source_exists, _, source_file, source_parent = self.get_info(source_path)
        if source_exists:
            target_exists, target_type, target_file, _ = self.get_info(target_path)
            if target_exists:
                if target_type == "dir":
                    if name not in target_file["children"]:
                        target_file["children"][name] = source_file
                        del source_parent["children"][name]
                        result = True
                    else:
                        raise InvalidValueError("same file name exists: %s" % name)
                else:
                    raise InvalidValueError("target path must be directory: %s" % target_path)
            else:
                raise InvalidValueError("target path not exists: %s" % target_path)
        else:
            raise InvalidValueError("source path not exists: %s" % source_path)
        return result

    def copy_file(self, source_path, target_path):
        result = False
        _, name = os.path.split(source_path)
        source_exists, _, source_file, source_parent = self.get_info(source_path)
        if source_exists:
            target_exists, target_type, target_file, _ = self.get_info(target_path)
            if target_exists:
                if target_type == "dir":
                    if name not in target_file["children"]:
                        target_file["children"][name] = source_file
                        result = True
                    else:
                        raise InvalidValueError("same file name exists: %s" % name)
                else:
                    raise InvalidValueError("target path must be directory: %s" % target_path)
            else:
                raise InvalidValueError("target path not exists: %s" % target_path)
        else:
            raise InvalidValueError("source path not exists: %s" % source_path)
        return result

    def list_dir(self, directory_path, recursive = False):
        result = []
        exists, file_type, file, _ = self.get_info(directory_path)
        if exists and file_type == "dir":
            if recursive:
                result = file["children"]
            else:
                result = list(file["children"].keys())
        return result

    def exists(self, file_path):
        result, _, _, _ = self.get_info(directory_path)
        return result

    def makdirs(self, directory_path):
        result = False
        path_parts = splitall(directory_path)
        if path_parts[0] != "/":
            raise InvalidValueError("must be absolute path: %s" % directory_path)
        else:
            current_root = self.cache
            for dir_name in path_parts[1:]:
                if dir_name not in current_root["children"]:
                    current_root["children"][dir_name] = {"type": "dir", "children": {}}
                current_root = current_root["children"][dir_name]                    
            result = current_root
        return result

    def isdir(self, directory_path):
        result = False
        exists, file_type, _, _ = self.get_info(directory_path)
        if exists and file_type == "dir":
            result = True
        return result

    def isfile(self, file_path):
        result = False
        exists, file_type, _, _ = self.get_info(file_path)
        if exists and file_type == "file":
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
                if name not in current_root["children"]:
                    result[0] = False
                    break
                else:
                    parent = current_root
                    current_root = current_root["children"][name]
            if result[0]:
                result[1] = current_root["type"]
                result[2] = current_root
                result[3] = parent
        return result
