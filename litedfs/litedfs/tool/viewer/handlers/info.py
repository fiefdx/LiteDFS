# -*- coding: utf-8 -*-

import json
import time
import logging

from tornado import web
from tornado import gen

from litedfs.tool.viewer.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger("__name__")


class AboutHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"message": "LiteDFS viewer service"}
        self.write(result)
        self.finish()


class RedirectHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        self.redirect("/")
