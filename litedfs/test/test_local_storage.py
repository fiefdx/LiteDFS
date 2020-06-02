# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.tool.viewer.utils.common import makekey, listsort, listdir, joinpath, splitpath, list_storage
from litedfs.name import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_local_storage.log",
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
        LOG.debug(json.dumps(listdir("/home/breeze"), indent = 4))
        LOG.debug(json.dumps(list_storage("/home/breeze", "/home/breeze"), indent = 4))
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
