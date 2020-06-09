# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.data.utils.common import disk_usage, size_pretty
from litedfs.data import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_disk_usage.log",
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
        s = time.time()
        r = disk_usage("/home/breeze")
        ss = time.time()
        LOG.debug("%s, use %ss", r, ss - s)
        LOG.debug("free: %s", size_pretty(r["free"]))
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
