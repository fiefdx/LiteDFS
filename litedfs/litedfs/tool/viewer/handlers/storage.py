# -*- coding: utf-8 -*-

import json
import time
import logging
from pathlib import Path

from tornado import web
from tornado import gen

from litedfs.tool.viewer.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.tool.viewer.utils.common import listdir, joinpath, splitpath, list_storage
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


class StorgeSocketHandler(BaseSocketHandler):
    socket_handlers = set()

    def open(self):
        home_path = str(Path.home())
        if self not in StorgeSocketHandler.socket_handlers:
            StorgeSocketHandler.socket_handlers.add(self)
            LOG.info("storage websocket len: %s", len(StorgeSocketHandler.socket_handlers))
        else:
            LOG.info("storage websocket len: %s", len(StorgeSocketHandler.socket_handlers))
        data = list_storage(home_path, home_path, sort_by = "name", desc = False)
        data["cmd"] = "init"
        send_msg(json.dumps(data), self)

    def on_close(self):
        StorgeSocketHandler.socket_handlers.remove(self)
        LOG.info("storage websocket len: %s", len(StorgeSocketHandler.socket_handlers))

    def on_message(self, msg):
        msg = json.loads(msg)
        LOG.debug("msg: %s", msg)
