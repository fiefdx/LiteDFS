# -*- coding: utf-8 -*-

import json
import time
import logging

from tornado import web
from tornado import gen

from litedfs.data.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.data.config import CONFIG

LOG = logging.getLogger("__name__")


class AboutHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"message": "LiteDFS data service"}
        self.write(result)
        self.finish()
