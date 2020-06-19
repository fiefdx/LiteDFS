# -*- coding: utf-8 -*-

import os
import json
import time
import shutil
import logging
from pathlib import Path

from tornado import web
from tornado import gen

from litedfs.tool.viewer.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.tool.viewer.utils.common import listdir, joinpath, splitpath, list_storage, Command
from litedfs.tool.viewer.utils.task_cache import TaskCache
from litedfs.tool.viewer.utils.remote_storage import RemoteStorage
from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger("__name__")


class StorageHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        self.render(
            "storage/storage.html",
            current_nav = "storage",
            manager_host = "%s:%s" % (
                CONFIG["name_http_host"],
                CONFIG["name_http_port"])
        )


def send_msg(msg, handler):
    try:
        handler.write_message(msg)
    except Exception as e:
        LOG.exception(e)


def send_msgs(msg, handlers):
    try:
        for handler in handlers:
            handler.write_message(msg)
    except Exception as e:
        LOG.exception(e)


class LocalSocketHandler(BaseSocketHandler):
    socket_handlers = set()

    @classmethod
    def send_msgs(cls, msg):
        try:
            for handler in cls.socket_handlers:
                handler.write_message(msg)
        except Exception as e:
            LOG.exception(e)

    def open(self):
        self.home_path = str(Path.home())
        self.client = RemoteStorage(CONFIG["name_http_host"], CONFIG["name_http_port"])
        self.clipboard = {}
        if self not in LocalSocketHandler.socket_handlers:
            LocalSocketHandler.socket_handlers.add(self)
            LOG.info("storage websocket len: %s", len(LocalSocketHandler.socket_handlers))
        else:
            LOG.info("storage websocket len: %s", len(LocalSocketHandler.socket_handlers))
        data = list_storage(self.home_path, self.home_path, sort_by = "name", desc = False, offset = 0, limit = 100)
        data["cmd"] = "init"
        send_msg(json.dumps(data), self)

    def on_close(self):
        LocalSocketHandler.socket_handlers.remove(self)
        LOG.info("storage websocket len: %s", len(LocalSocketHandler.socket_handlers))

    def on_message(self, msg):
        msg = json.loads(msg)
        LOG.debug("msg: %s", msg)
        data = {}
        try:
            if msg["cmd"] == Command.cd:
                cd_path = joinpath(msg["dir_path"])
                data = list_storage(self.home_path, cd_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                data["cmd"] = "init"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.refresh:
                dir_path = joinpath(msg["dir_path"])
                data = list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                data["cmd"] = "init"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.change_page:
                dir_path = joinpath(msg["dir_path"])
                data = list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                data["cmd"] = "init"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.rename:
                dir_path = joinpath(msg["dir_path"])
                old_name = msg["old_name"]
                new_name = msg["new_name"]
                if new_name != "" and new_name != old_name:
                    old_path = os.path.join(dir_path, old_name)
                    new_path = os.path.join(dir_path, new_name)
                    if os.path.exists(new_path):
                        data["cmd"] = "warning"
                        data["info"] = "File [%s] already exists!" % new_path
                    else:
                        os.rename(old_path, new_path)
                        data = list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                        data["cmd"] = "init"
                    send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.mkdir:
                dir_path = joinpath(msg["dir_path"])
                dir_name = msg["name"]
                if dir_name != "":
                    new_path = os.path.join(dir_path, dir_name)
                    if os.path.exists(new_path):
                        data["cmd"] = "warning"
                        data["info"] = "Directory [%s] already exists!" % new_path
                    else:
                        os.mkdir(new_path)
                        data = list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                        data["cmd"] = "init"
                    send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.delete:
                msg["socket_handler"] = self
                TaskCache.push(msg)
            elif msg["cmd"] == Command.copy:
                dir_path = joinpath(msg["dir_path"])
                files = msg["files"]
                dirs = msg["dirs"]
                self.clipboard["type"] = Command.copy
                self.clipboard["dir_path"] = dir_path
                self.clipboard["files"] = files
                self.clipboard["dirs"] = dirs
                data["cmd"] = "paste"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.cut:
                dir_path = joinpath(msg["dir_path"])
                files = msg["files"]
                dirs = msg["dirs"]
                self.clipboard["type"] = Command.cut
                self.clipboard["dir_path"] = dir_path
                self.clipboard["files"] = files
                self.clipboard["dirs"] = dirs
                data["cmd"] = "paste"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.paste:
                msg["socket_handler"] = self
                msg["clipboard"] = self.clipboard
                TaskCache.push(msg)
            elif msg["cmd"] == Command.upload:
                msg["socket_handler"] = self
                TaskCache.push(msg)
        except Exception as e:
            LOG.exception(e)
            data["cmd"] = "error"
            data["info"] = str(e)
            send_msg(json.dumps(data), self)


class RemoteSocketHandler(BaseSocketHandler):
    socket_handlers = set()

    @classmethod
    def send_msgs(cls, msg):
        try:
            for handler in cls.socket_handlers:
                handler.write_message(msg)
        except Exception as e:
            LOG.exception(e)

    def open(self):
        self.home_path = "/"
        self.client = RemoteStorage(CONFIG["name_http_host"], CONFIG["name_http_port"])
        self.clipboard = {}
        if self not in RemoteSocketHandler.socket_handlers:
            RemoteSocketHandler.socket_handlers.add(self)
            LOG.info("remote storage websocket len: %s", len(RemoteSocketHandler.socket_handlers))
        else:
            LOG.info("remote storage websocket len: %s", len(RemoteSocketHandler.socket_handlers))
        data = self.client.list_storage(self.home_path, self.home_path, sort_by = "name", desc = False, offset = 0, limit = 100)
        if data:
            data["cmd"] = "init"
        else:
            data["cmd"] = "error"
            data["info"] = "Remote storage is offline"
        send_msg(json.dumps(data), self)

    def on_close(self):
        RemoteSocketHandler.socket_handlers.remove(self)
        LOG.info("remote storage websocket len: %s", len(RemoteSocketHandler.socket_handlers))

    def on_message(self, msg):
        msg = json.loads(msg)
        LOG.debug("msg: %s", msg)
        data = {}
        try:
            if msg["cmd"] == Command.cd:
                cd_path = joinpath(msg["dir_path"])
                data = self.client.list_storage(self.home_path, cd_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                if data:
                    data["cmd"] = "init"
                else:
                    data["cmd"] = "error"
                    data["info"] = "Remote storage is offline"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.refresh:
                dir_path = joinpath(msg["dir_path"])
                data = self.client.list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                if data:
                    data["cmd"] = "init"
                else:
                    data["cmd"] = "error"
                    data["info"] = "Remote storage is offline"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.change_page:
                dir_path = joinpath(msg["dir_path"])
                data = self.client.list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                if data:
                    data["cmd"] = "init"
                else:
                    data["cmd"] = "error"
                    data["info"] = "Remote storage is offline"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.rename:
                dir_path = joinpath(msg["dir_path"])
                old_name = msg["old_name"]
                new_name = msg["new_name"]
                if new_name != "" and new_name != old_name:
                    old_path = os.path.join(dir_path, old_name)
                    self.client.rename(old_path, new_name)
                    data = self.client.list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                    if data:
                        data["cmd"] = "init"
                    else:
                        data["cmd"] = "error"
                        data["info"] = "Remote storage is offline"
                    send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.mkdir:
                dir_path = joinpath(msg["dir_path"])
                dir_name = msg["name"]
                if dir_name != "":
                    new_path = os.path.join(dir_path, dir_name)
                    self.client.mkdir(new_path)
                    data = self.client.list_storage(self.home_path, dir_path, sort_by = "name", desc = False, offset = msg["offset"], limit = msg["limit"])
                    if data:
                        data["cmd"] = "init"
                    else:
                        data["cmd"] = "error"
                        data["info"] = "Remote storage is offline"
                    send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.delete:
                msg["socket_handler"] = self
                msg["cmd"] = Command.remote_delete
                TaskCache.push(msg)
            elif msg["cmd"] == Command.cut:
                dir_path = joinpath(msg["dir_path"])
                files = msg["files"]
                dirs = msg["dirs"]
                self.clipboard["type"] = Command.cut
                self.clipboard["dir_path"] = dir_path
                self.clipboard["files"] = files
                self.clipboard["dirs"] = dirs
                data["cmd"] = "paste"
                send_msg(json.dumps(data), self)
            elif msg["cmd"] == Command.paste:
                msg["socket_handler"] = self
                msg["clipboard"] = self.clipboard
                msg["cmd"] = Command.remote_paste
                TaskCache.push(msg)
            elif msg["cmd"] == Command.download:
                msg["socket_handler"] = self
                TaskCache.push(msg)
            elif msg["cmd"] == Command.update:
                msg["socket_handler"] = self
                TaskCache.push(msg)
            elif msg["cmd"] == Command.preview:
                msg["socket_handler"] = self
                TaskCache.push(msg)
        except Exception as e:
            LOG.exception(e)
            data["cmd"] = "error"
            data["info"] = str(e)
            send_msg(json.dumps(data), self)
