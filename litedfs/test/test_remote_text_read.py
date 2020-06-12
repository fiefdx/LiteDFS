# -*- coding: utf-8 -*-

import os
import io
import sys
import json
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.tool.client import LiteDFSClient, RemoteFile
from litedfs.name import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_remote_text_read.log",
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
        rf = c.open_remote_file("/test_r_n.txt")
        fp = io.BufferedReader(rf)
        # print(rf.read(10))
        for i in range(20):
          LOG.debug("line-%03d: %s", i, fp.readline())
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
