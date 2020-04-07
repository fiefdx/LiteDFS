# -*- coding: utf-8 -*-

import json
import time
import logging

from tornado import web
from tornado import gen

from litedfs.name.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.name.utils.common import Errors
from litedfs.version import __version__
from litedfs.name.config import CONFIG

LOG = logging.getLogger("__name__")


class AboutHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"message": "LiteDFS name service"}
        self.write(result)
        self.finish()
