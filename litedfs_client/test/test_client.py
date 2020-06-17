# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs_client.client import LiteDFSClient, RemoteFile
from litedfs_client import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_client.log",
                          log_level = "DEBUG",
                          dir_name = os.path.join(cwd, "logs"),
                          day_rotate = False,
                          when = "D",
                          interval = 1,
                          max_size = 20,
                          backup_count = 5,
                          console = True)

    LOG.debug("test start")
    
    try:
        c = LiteDFSClient("127.0.0.1", 9000)

        # LOG.debug("update file: %s", c.update_file("/replica_test.tar.gz", 1))
        # LOG.debug("create file: %s", c.create_file("./test.log", "/test.log"))
        # LOG.debug("rename file: %s", c.rename_file("/test.log", "test.rename.log"))
        # LOG.debug("move file: %s", c.move_file("/test.rename.log", "/test"))
        # LOG.debug("download file: %s", c.download_file("/test/test.rename.log", "./test.rename.log"))
        # LOG.debug("info file: %s", c.info_file("/test/test.rename.log"))
        # LOG.debug("delete file: %s", c.delete_file("/test/test.rename.log"))

        # LOG.debug("create directory: %s", c.create_directory("/new_dir"))
        # LOG.debug("rename directory: %s", c.rename_directory("/new_dir", "new_dir_name"))
        # LOG.debug("move directory: %s", c.move_directory("/new_dir_name", "/test"))
        # LOG.debug("list directory: %s", c.list_directory("/test"))
        # LOG.debug("delete directory: %s", c.delete_directory("/test/new_dir_name"))

        # file_info = {
        #     "data_nodes": {
        #         "1": [
        #             "localhost",
        #             8002,
        #             False
        #         ],
        #         "2": [
        #             "localhost",
        #             8003,
        #             False
        #         ],
        #         "3": [
        #             "localhost",
        #             8004,
        #             False
        #         ]
        #     },
        #     "file_info": {
        #         "blocks": [
        #             [
        #                 0,
        #                 67108864,
        #                 [
        #                     1
        #                 ],
        #                 "1e16cd4360fd9772a3bc9d09647ac765"
        #             ],
        #             [
        #                 1,
        #                 64091659,
        #                 [
        #                     3
        #                 ],
        #                 "076b226552b58a4ef39f7648da27507f"
        #             ]
        #         ],
        #         "checksum": "535c73c8ce4d601db0805b224f647f0c",
        #         "ctime": 1591680858,
        #         "current_replica": 1,
        #         "id": "dde3752d-0b8f-473d-a24f-897afa127d31",
        #         "mtime": 1591680858,
        #         "replica": 1,
        #         "size": 131200523
        #     },
        #     "block_size": 67108864,
        #     "result": "ok"
        # }

        # rf = RemoteFile("localhost", "9000", "/t.txt", file_info)
        # rf.seek(10)
        # r = rf.read(67108864)
        # LOG.debug("read remote file: %s", r)

        rf = c.open_remote_file("/build.sh")
        # rf.seek(67108864 - 10)
        LOG.debug("remote file content: %s", rf.read().decode())

    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
