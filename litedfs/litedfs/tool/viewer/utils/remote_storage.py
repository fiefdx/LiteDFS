# -*- coding: utf-8 -*-

import os
import time
import json
import logging
import datetime

from litedfs.tool.client import LiteDFSClient
from litedfs.tool.viewer.utils.common import joinpath, splitpath, listsort, sha1sum
from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger(__name__)


class RemoteStorage(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client = LiteDFSClient(self.host, self.port)

    def listdir(self, dir_path, sort_by = "name", desc = False):
        dirs = []
        files = []
        r = self.client.list_directory(dir_path)
        if r:
            if "result" in r and r["result"] == "ok":
                n = 1
                for c in r["children"]:
                    if c["type"] == "directory":
                        d_path = os.path.join(dir_path, c["name"])
                        dirs.append({
                            "num": n,
                            "name": c["name"],
                            "sha1": sha1sum(d_path),
                            "type": "Directory",
                            "size": c["size"],
                            "ctime": "",
                            "mtime": ""
                        })
                    elif c["type"] == "file":
                        f_path = os.path.join(dir_path, c["name"])
                        f = {
                            "num": n,
                            "name": c["name"],
                            "sha1": sha1sum(f_path),
                            "type": os.path.splitext(c["name"])[-1],
                            "size": c["size"],
                            "ctime": "",
                            "mtime": ""
                        }
                        if "current_replica" in c:
                            f["current_replica"] = c["current_replica"]
                        if "replica" in c:
                            f["replica"] = c["replica"]
                        files.append(f)
                    n += 1
                dirs, files = listsort(dirs, files, sort_by = sort_by, desc = desc)
        return dirs, files

    def list_storage(self, home_path, dir_path, sort_by = "name", desc = False):
        data = {}
        r = self.client.list_directory(dir_path)
        if r:
            if "result" in r and r["result"] == "ok":
                dirs = []
                files = []
                n = 1
                for c in r["children"]:
                    if c["type"] == "directory":
                        d_path = os.path.join(dir_path, c["name"])
                        dirs.append({
                            "num": n,
                            "name": c["name"],
                            "sha1": sha1sum(d_path),
                            "type": "Directory",
                            "size": c["size"],
                            "ctime": datetime.datetime.fromtimestamp(c["ctime"]).strftime("%Y-%m-%d %H:%M:%S") if "ctime" in c and c["ctime"] else "",
                            "mtime": datetime.datetime.fromtimestamp(c["mtime"]).strftime("%Y-%m-%d %H:%M:%S") if "mtime" in c and c["mtime"] else ""
                        })
                    elif c["type"] == "file":
                        f_path = os.path.join(dir_path, c["name"])
                        f = {
                            "num": n,
                            "name": c["name"],
                            "sha1": sha1sum(f_path),
                            "type": os.path.splitext(c["name"])[-1],
                            "size": c["size"],
                            "ctime": datetime.datetime.fromtimestamp(c["ctime"]).strftime("%Y-%m-%d %H:%M:%S") if "ctime" in c and c["ctime"] else "",
                            "mtime": datetime.datetime.fromtimestamp(c["mtime"]).strftime("%Y-%m-%d %H:%M:%S") if "mtime" in c and c["mtime"] else ""
                        }
                        if "current_replica" in c:
                            f["current_replica"] = c["current_replica"]
                        if "replica" in c:
                            f["replica"] = c["replica"]
                        files.append(f)
                    n += 1
                dirs, files = listsort(dirs, files, sort_by = sort_by, desc = desc)
                data["dirs"] = dirs
                data["files"] = files
                data["sort"] = {"name": sort_by, "desc": desc}
                data["dir_path"] = splitpath(dir_path)
                data["home_path"] = splitpath(home_path)
                data["home_path_string"] = home_path
        return data

    def rename(self, dir_path, new_name):
        return self.client.rename_file(dir_path, new_name)

    def mkdir(self, dir_path):
        return self.client.create_directory(dir_path)

    def delete_file(self, file_path):
        return self.client.delete_file(file_path)

    def delete_directory(self, dir_path):
        return self.client.delete_directory(dir_path)

    def move_file(self, source_path, target_path):
        return self.client.move_file(source_path, target_path)

    def move_directory(self, source_path, target_path):
        return self.client.move_directory(source_path, target_path)

    def download_file(self, source_path, target_path):
        return self.client.download_file(source_path, target_path)

    def upload_file(self, source_path, target_path, replica = 1):
        return self.client.create_file(source_path, target_path, replica = replica)

    def update_file(self, file_path, replica = 1):
        return self.client.update_file(file_path, replica)
