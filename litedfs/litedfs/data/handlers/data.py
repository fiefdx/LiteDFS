# -*- coding: utf-8 -*-

import os
import json
import time
import logging
from io import BytesIO

from tornado import web
from tornado import gen

from litedfs.data.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.data.utils.registrant import Registrant
from litedfs.data.utils.common import file_sha1sum, file_md5sum, bytes_md5sum, Errors, splitall
from litedfs.data.config import CONFIG

LOG = logging.getLogger("__name__")


def parse_node_ids(ids_str):
    node_ids = []
    node_ids_tmp = ids_str.split(",")
    for i in node_ids_tmp:
        if i:
            node_ids.append(i)
    return node_ids


class CreateBlockHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        result = {"result": Errors.OK}
        try:
            file_name = self.get_argument("name", "")
            block_id = self.get_argument("block", "")
            node_ids = parse_node_ids(self.get_argument("ids", ""))
            file_body = self.request.files['up_file'][0]["body"]
            if file_name and block_id:
                dir_path = os.path.join(CONFIG["data_path"], "files", file_name[:2], file_name[2:4])
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                file_path = os.path.join(dir_path, "%s_%s.blk" % (file_name, block_id))
                tmp_file_path = os.path.join(dir_path, "%s_%s.blk.tmp" % (file_name, block_id))
                fp = open(tmp_file_path, "wb")
                fp.write(file_body)
                fp.close()
                os.rename(tmp_file_path, file_path)
                file_path = os.path.join(dir_path, "%s_%s.chk" % (file_name, block_id))
                fp = open(file_path, "w")
                block_md5 = bytes_md5sum(file_body)
                fp.write(block_md5)
                fp.close()
                result["md5"] = block_md5
                Registrant.instance().replicate_block_async(file_name, BytesIO(file_body), block_id, node_ids)
            else:
                LOG.warning("invalid arguments")
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(result)
        self.finish()


class RangeReadHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_name = self.get_argument("name", "")
            block_id = self.get_argument("block", "")
            offset = int(self.get_argument("offset", -1))
            size = int(self.get_argument("size", -1))
            block_md5 = self.get_argument("md5", "")
            if file_name and block_id and offset >= 0 and size > 0 and block_md5:
                file_md5 = ""
                dir_path = os.path.join(CONFIG["data_path"], "files", file_name[:2], file_name[2:4])
                file_path = os.path.join(dir_path, "%s_%s.chk" % (file_name, block_id))
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    with open(file_path, 'r') as f:
                        file_md5 = f.read()
                if file_md5 == block_md5:
                    file_path = os.path.join(dir_path, "%s_%s.blk" % (file_name, block_id))
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        buf_size = 64 * 1024
                        self.set_header('Content-Type', 'application/octet-stream')
                        self.set_header('Content-Disposition', 'attachment; filename=%s_%s.blk.%s-%s.part' % (file_name, block_id, offset, size))
                        with open(file_path, 'rb') as f:
                            f.seek(offset)
                            while size > buf_size:
                                data = f.read(buf_size)
                                if not data:
                                    break
                                self.write(data)
                                self.flush()
                                yield gen.moment
                                size -= buf_size
                            if size > 0:
                                self.write(f.read(size))
                                self.flush()
                        self.finish()
                        return
                    else:
                        Errors.set_result_error("BlockNotExists", result)
                else:
                    Errors.set_result_error("ChecksumFailed", result)
            else:
                LOG.warning("invalid arguments")
                Errors.set_result_error("InvalidParameters", result)
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.set_status(400)
        self.write(result)
        self.finish()


class DownloadBlockHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK}
        try:
            file_name = self.get_argument("name", "")
            block_id = self.get_argument("block", "")
            if file_name and block_id:
                file_path = os.path.join(CONFIG["data_path"], "files", file_name[:2], file_name[2:4], "%s_%s.blk" % (file_name, block_id))
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    buf_size = 64 * 1024
                    self.set_header('Content-Type', 'application/octet-stream')
                    self.set_header('Content-Disposition', 'attachment; filename=%s_%s.blk' % (file_name, block_id))
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
        self.set_status(400)
        self.write(result)
        self.finish()
