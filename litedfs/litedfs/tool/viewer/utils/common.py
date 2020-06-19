# -*- coding: utf-8 -*-

import os
import time
import json
import hashlib
import logging
import datetime

from tornado import ioloop
from tornado import gen
import psutil

from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger(__name__)

BUF_SIZE = 65536


class Servers(object):
    HTTP_SERVER = None
    SERVERS = []
    TORNADO_INSTANCE = None


async def shutdown():
    LOG.info("Stopping Service(%s:%s)", CONFIG["http_host"], CONFIG["http_port"])
    if Servers.HTTP_SERVER:
        Servers.HTTP_SERVER.stop()
        LOG.info("Stop http server!")
    for s in Servers.SERVERS:
        if hasattr(s, "close"):
            s.close()
        elif hasattr(s, "stop"):
            s.stop()
        if hasattr(s, "name"):
            LOG.info("Stop %s server!", s.name)
        else:
            LOG.info("Stop nameless server!")
    await gen.sleep(1)
    LOG.info("Will shutdown ...")
    ioloop.IOLoop.current().stop()


def sig_handler(sig, frame):
    LOG.warning("sig_handler Caught signal: %s", sig)
    ioloop.IOLoop.current().add_callback_from_signal(shutdown)


class Errors(object):
    OK = "ok"
    errors = {
        "ServerException": {"name": "ServerException", "message": "server exception"},
        "InvalidParameters": {"name": "InvalidParameters", "message": "invalid parameters"},
        "OperationFailed": {"name": "OperationFailed", "message": "operation failed"},
        "AppNotExists": {"name": "AppNotExists", "message": "application not exists"},
        "TaskNotExists": {"name": "TaskNotExists", "message": "task not exists"},
        "OperationRunning": {"name": "OperationRunning", "message": "operation running"},
        "WorkspaceNotExists": {"name": "WorkspaceNotExists", "message": "workspace not exists"},
        "WorkspaceNotPacked": {"name": "WorkspaceNotPacked", "message": "workspace not packed"},
    }

    @classmethod
    def set_result_error(cls, error_name, result, message = ""):
        if error_name in cls.errors:
            result["result"] = error_name
            if message == "":
                result["message"] = cls.errors[error_name]["message"]
            else:
                result["message"] = message
        else:
            result["result"] = "UnknownError"
            result["message"] = "unknown error"


class Stage(object):
    pending = "pending"
    running = "running"
    finished = "finished"


class Status(object):
    fail = "fail"
    success = "success"
    kill = "kill"
    cancel = "cancel"
    terminate = "terminate"


class Signal(object):
    kill = -9
    terminate = -15
    stop = -15
    cancel = -50


class JSONLoadError(Exception):
    def __init__(self, message):
        self.message = message


class MetaNotDictError(Exception):
    def __init__(self, message):
        self.message = message


def sha1sum(content):
    sha1 = hashlib.sha1()
    sha1.update(content.encode("utf-8"))
    return sha1.hexdigest()


def file_sha1sum(file_path):
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def file_md5sum(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as fp:
        while True:
            data = fp.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


class Command(object):
    cd = "cd"
    refresh = "refresh"
    rename = "rename"
    mkdir = "mkdir"
    delete = "delete"
    copy = "copy"
    cut = "cut"
    paste = "paste"
    remote_delete = "remote_delete"
    remote_paste = "remote_paste"
    download = "download"
    upload = "upload"
    need_refresh = "need_refresh"
    update = "update"
    preview = "preview"
    change_page = "change_page"


def splitall(path):
    allparts = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def get_workspace_path(create_at, task_id = None, action_name = None):
    result = ""
    date_create_at = datetime.datetime.strptime(create_at, "%Y-%m-%d %H:%M:%S.%f")
    date_directory_name = date_create_at.strftime("%Y-%m-%d")
    if task_id and action_name:
        result = os.path.join(CONFIG["data_path"], "tmp", "workspace", date_directory_name, task_id[:2], task_id[2:4], task_id, action_name)
    elif task_id:
        result = os.path.join(CONFIG["data_path"], "tmp", "workspace", date_directory_name, task_id[:2], task_id[2:4], task_id)
    else:
        result = os.path.join(CONFIG["data_path"], "tmp", "workspace", date_directory_name)
    return result


def init_storage():
    directories = [
        os.path.join(CONFIG["data_path"], "applications"),
        os.path.join(CONFIG["data_path"], "tmp", "workspace"),
        os.path.join(CONFIG["data_path"], "tmp", "download"),
    ]
    for d in directories:
        if not os.path.exists(d) or not os.path.isdir(d):
            os.makedirs(d)


def get_file_size(size):
    result = ""
    try:
        if size > 1024*1014*1024:
            result = "%.3f G"%(size/1024.0/1024.0/1024.0)
        elif size > 1024*1024:
            result = "%.3f M"%(size/1024.0/1024.0)
        elif size > 1024:
            result = "%.3f K"%(size/1024.0)
        else:
            result = "%d B"%size
    except Exception as e:
        LOG.exception(e)
        result = "0 B"
    return result


def makekey(c):
    if isinstance(c, int):
        return c
    elif isinstance(c, str):
        return c.lower()


def listsort(dirs, files, sort_by = "name", desc = False, offset = 0, limit = -1):
    dirs_keys = []
    dirs_tree = {}
    dirs_sort = []
    files_keys = []
    files_tree = {}
    files_sort = []
    result = []
    for d in dirs:
        dirs_keys.append(d[sort_by])
        if d[sort_by] in dirs_tree:
            dirs_tree[d[sort_by]].append(d)
        else:
            dirs_tree[d[sort_by]] = []
            dirs_tree[d[sort_by]].append(d)
    dirs_keys = list(set(dirs_keys))
    dirs_keys.sort(key = makekey, reverse = desc)
    # LOG.info("Dirs_keys: %s", dirs_keys)
    n = 1
    for k in dirs_keys:
        for d in dirs_tree[k]:
            d["num"] = n
            d["size"] = get_file_size(d["size"])
            dirs_sort.append(d)
            n += 1
    for f in files:
        files_keys.append(f[sort_by])
        if f[sort_by] in files_tree:
            files_tree[f[sort_by]].append(f)
        else:
            files_tree[f[sort_by]] = []
            files_tree[f[sort_by]].append(f)
    files_keys = list(set(files_keys))
    files_keys.sort(key = makekey, reverse = desc)
    # LOG.info("Files_keys: %s", files_keys)
    for k in files_keys:
        for f in files_tree[k]:
            f["num"] = n
            f["size"] = get_file_size(f["size"])
            files_sort.append(f)
            n += 1
    items = []
    items.extend(dirs_sort)
    items.extend(files_sort)
    total_len = len(items)
    if limit == -1:
        result = items
    else:
        result = items[offset:offset + limit]

    return (result, total_len)


def listdir(dir_path = ".", sort_by = "name", desc = False, offset = 0, limit = -1):
    dirs = []
    files = []
    try:
        dirs_list = [d for d in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, d))]
        files_list = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        dirs_list.sort()
        files_list.sort()
        n = 1
        for d in dirs_list:
            d_path = os.path.join(dir_path, d)
            dirs.append({
                "num":n,
                "name":d,
                "sha1":sha1sum(d_path),
                "type":"Directory",
                "size":os.path.getsize(d_path),
                "ctime":time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(d_path))),
                "mtime":time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(d_path)))
            })
            n += 1
        for f in files_list:
            f_path = os.path.join(dir_path, f)
            files.append({
                "num":n,
                "name":f,
                "sha1":sha1sum(f_path),
                "type":os.path.splitext(f)[-1],
                "size":os.path.getsize(f_path),
                "ctime":time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(f_path))),
                "mtime":time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(f_path)))
            })
            n += 1
    except Exception as e:
        LOG.exception(e)
    return listsort(dirs, files, sort_by = sort_by, desc = desc, offset = offset, limit = limit)


def joinpath(dir_list):
    dir_path = dir_list[0]
    dir_list = dir_list[1:]
    for d in dir_list:
        dir_path = os.path.join(dir_path, d)
    return dir_path


def splitpath(dir_path):
    dir_list = []
    dir_path, dir_last = os.path.split(dir_path)
    while dir_last != "":
        dir_list.append(dir_last)
        dir_path, dir_last = os.path.split(dir_path)
    dir_list.append(dir_path)
    dir_list.reverse()
    return dir_list


def list_storage(home_path, dir_path, sort_by = "name", desc = False, offset = 0, limit = -1):
    disk_usage = psutil.disk_usage(dir_path)
    disk_partitions = psutil.disk_partitions()
    data = {}
    items, total = listdir(dir_path = dir_path, sort_by = sort_by, desc = desc, offset = offset, limit = limit)
    data["items"] = items
    data["offset"] = offset
    data["limit"] = limit
    data["total"] = total
    data["sort"] = {"name":sort_by, "desc":desc}
    data["dir_path"] = splitpath(dir_path)
    data["home_path"] = splitpath(home_path)
    data["home_path_string"] = home_path
    data["disk_usage"] = {
        "total":get_file_size(disk_usage.total),
        "used":get_file_size(disk_usage.used),
        "free":get_file_size(disk_usage.free),
        "percent":disk_usage.percent
    }
    data["disk_partitions"] = [{"mountpoint":splitpath(p.mountpoint), "device":p.device} for p in disk_partitions]
    p_mountpoint_length = 0
    for n, p in enumerate(data["disk_partitions"]):
        mountpoint_path = joinpath(p["mountpoint"])
        if mountpoint_path in dir_path and len(mountpoint_path) > p_mountpoint_length:
            p_mountpoint_length = len(mountpoint_path)
            data["current_partition"] = n
    return data
