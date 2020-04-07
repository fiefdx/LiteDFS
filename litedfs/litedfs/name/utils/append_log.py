# -*- coding: utf-8 -*-

import os
import json
import logging

from litedfs.name.config import CONFIG

LOG = logging.getLogger(__name__)


class AppendLog(object):
    def __init__(self, log_path):
        self.log_path = log_path
        self.log_file = open(self.log_path, "a")

    def writeline(self, line):
        result = False
        try:
            line += "\n"
            self.log_file.write(line)
            self.log_file.flush()
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    def iterlines(self):
        fp = open(self.log_path, "r")
        line = fp.readline().strip()
        while line:
            yield line
            line = fp.readline().strip()
        fp.close()

    def close(self):
        try:
            if self.log_file:
                self.log_file.close()
        except Exception as e:
            LOG.exception(e)


class AppendLogJson(AppendLog):
    def writeline(self, data = {}):
        result = False
        try:
            line = json.dumps(data, separators = (",", ":")) + "\n"
            self.log_file.write(line)
            self.log_file.flush()
            result = True
        except Exception as e:
            LOG.exception(e)
        return result

    def iterlines(self):
        fp = open(self.log_path, "r")
        line = fp.readline().strip()
        while line:
            yield json.loads(line)
            line = fp.readline().strip()
        fp.close()
