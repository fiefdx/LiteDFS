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
        self.lines_pos = {}

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

    def iterlines(self, start = 1):
        fp = open(self.log_path, "r")
        if start in self.lines_pos:
            pos = self.lines_pos[start]
            fp.seek(pos)
        line = fp.readline().strip()
        while line:
            yield line
            line = fp.readline().strip()
        fp.close()

    def indexlines(self):
        n = 1
        fp = open(self.log_path, "r")
        pos = fp.tell()
        line = fp.readline().strip()
        while line:
            self.lines_pos[n] = pos
            pos = fp.tell()
            line = fp.readline().strip()
            n += 1
        fp.close()

    def lines(self):
        return len(self.lines_pos)

    def readline(self, line = 1):
        result = False
        try:
            fp = open(self.log_path, "r")
            if line in self.lines_pos:
                pos = self.lines_pos[line]
                fp.seek(pos)
                result = fp.readline().strip()
            else:
                result = None
            fp.close()
        except Exception as e:
            LOG.exception(e)
        return result

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

    def iterlines(self, start = 1):
        fp = open(self.log_path, "r")
        if start in self.lines_pos:
            pos = self.lines_pos[start]
            fp.seek(pos)
        line = fp.readline().strip()
        while line:
            yield json.loads(line)
            line = fp.readline().strip()
        fp.close()

    def readline(self, line = 1):
        result = False
        try:
            fp = open(self.log_path, "r")
            if line in self.lines_pos:
                pos = self.lines_pos[line]
                fp.seek(pos)
                result = json.loads(fp.readline().strip())
            else:
                result = None
            fp.close()
        except Exception as e:
            LOG.exception(e)
        return result
