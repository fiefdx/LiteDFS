# -*- coding: utf-8 -*-

import os
import time
import json
import hashlib
import logging

from tornado import ioloop
from tornado import gen

from litedfs.name.config import CONFIG

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
        s.close()
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
        "NodeNotExists": {"name": "NodeNotExists", "message": "node not exists"},
        "AllDataNodeOffline": {"name": "AllDataNodeOffline", "message": "all data node offline"},
        "NoUsableDataNode": {"name": "NoUsableDataNode", "message": "no usable data node"},
        "FileNotExists": {"name": "FileNotExists", "message": "file not exists"},
        "SetFileLockFailed": {"name": "SetFileLockFailed", "message": "set file lock failed"},
        "SameNameExists": {"name": "SameNameExists", "message": "same name exists"},
        "SameNameFileExists": {"name": "SameNameFileExists", "message": "same name file exists"},
        "TargetPathMustDirectory": {"name": "TargetPathMustDirectory", "message": "target path must directory"},
        "TargetPathNotExists": {"name": "TargetPathNotExists", "message": "target path not exists"},
        "SourcePathNotExists": {"name": "SourcePathNotExists", "message": "source path not exists"},
        "ServiceNotReadyYet": {"name": "ServiceNotReadyYet", "message": "service not ready yet"},
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
    stopping = "stopping"
    recovering = "recovering"


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


class Event(object):
    events = ["fail", "success"]
    fail = "fail"
    success = "success"


class JSONLoadError(Exception):
    def __init__(self, message):
        self.message = message


class MetaNotDictError(Exception):
    def __init__(self, message):
        self.message = message


class OperationError(Exception):
    def __init__(self, message):
        self.message = message


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


def bytes_md5sum(b):
    md5 = hashlib.md5()
    md5.update(b)
    return md5.hexdigest()


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
            if parts[1]:
                allparts.insert(0, parts[1])
    return allparts


def init_storage():
    directories = [
        os.path.join(CONFIG["data_path"], "tmp"),
    ]
    for d in directories:
        if not os.path.exists(d) or not os.path.isdir(d):
            os.makedirs(d)


def makekey(c):
    if isinstance(c, int):
        return c
    elif isinstance(c, str):
        return c.lower()


def list_sort(l, sort_by, desc = False):
    l_keys = []
    l_mapping = {}
    l_sorted = []
    for c in l:
        l_keys.append(c[sort_by])
        if c[sort_by] in l_mapping:
            l_mapping[c[sort_by]].append(c)
        else:
            l_mapping[c[sort_by]] = [c]
    l_keys = list(set(l_keys))
    l_keys.sort(key = makekey, reverse = desc)
    for k in l_keys:
        for c in l_mapping[k]:
            l_sorted.append(c)
    return l_sorted
