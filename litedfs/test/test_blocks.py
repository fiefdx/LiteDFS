# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.name import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_blocks.log",
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
        file_size = 103
        replica = 1
        block_size = 100
        blocks = []
        block_id = 0
        while file_size > block_size:
            blocks.append((block_id, block_size))
            file_size -= block_size
            block_id += 1
        if file_size > 0:
            blocks.append((block_id, file_size))
        LOG.debug("blocks: %s", blocks)
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
