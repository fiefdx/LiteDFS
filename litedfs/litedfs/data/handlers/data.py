# -*- coding: utf-8 -*-

import os
import json
import time
import logging

from tornado import web
from tornado import gen

from litedfs.data.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.data.utils.common import file_sha1sum, file_md5sum, Errors, splitall
from litedfs.data.config import CONFIG

LOG = logging.getLogger("__name__")


class CreateBlockHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        result = {"result": Errors.OK}
        try:
            file_name = self.get_argument("name", "")
            block_number = self.get_argument("block", "")
            file_body = self.request.files['up_file'][0]["body"]
            if file_name and block_number:
                dir_path = os.path.join(CONFIG["data_path"], "files", file_name[:2], file_name[2:4])
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                file_path = os.path.join(dir_path, "%s_%s.blk" % (file_name, block_number))
                fp = open(file_path, "wb")
                fp.write(file_body)
                fp.close()
            else:
                LOG.warning("invalid arguments")
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class DownloadBlockHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_name = self.get_argument("name", "")
            block_number = self.get_argument("block", "")
            if file_name and block_number:
                file_path = os.path.join(CONFIG["data_path"], "files", file_name[:2], file_name[2:4], "%s_%s.blk" % (file_name, block_number))
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    buf_size = 64 * 1024
                    self.set_header('Content-Type', 'application/octet-stream')
                    self.set_header('Content-Disposition', 'attachment; filename=%s_%s.blk' % (file_name, block_number))
                    with open(file_path, 'rb') as f:
                        while True:
                            data = f.read(buf_size)
                            if not data:
                                break
                            self.write(data)
                            self.flush()
                            yield gen.moment
                    self.finish()
                    return
                else:
                    Errors.set_result_error("BlockNotExists", result)
            else:
                LOG.warning("invalid arguments")
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()
