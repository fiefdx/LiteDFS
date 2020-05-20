# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from io import BytesIO

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.tool.litedfs import strings_md5sum, file_md5sum, bytes_io_md5sum
from litedfs.name import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_md5_methods.log",
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
        LOG.debug("%s", strings_md5sum(["1", "2", "3"]))
        LOG.debug("%s", file_md5sum("./test_md5_methods.py"))

        fp = open("./test_md5_methods.py", "rb")
        content = BytesIO()
        content.write(fp.read())
        content.seek(0)
        LOG.debug("%s", bytes_io_md5sum(content))

    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
