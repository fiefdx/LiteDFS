# -*- coding: utf-8 -*-

import json
import time
import logging

from tornado import web
from tornado import gen

from litedfs.tool.viewer.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger("__name__")


class ClusterHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        self.render(
            "cluster/cluster.html",
            current_nav = "cluster",
            manager_host = "%s:%s" % (
                CONFIG["name_http_host"],
                CONFIG["name_http_port"])
        )
