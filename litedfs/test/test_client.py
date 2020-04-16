# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.tool.client import LiteDFSClient
from litedfs.name import logger

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
        LOG.debug("update file: %s", c.update_file("/replica_test.tar.gz", 1))
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
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
