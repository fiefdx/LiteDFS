# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import zipfile

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs_client.client import LiteDFSClient, RemoteFile
from litedfs_client import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_remote_zip_file.log",
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
        rf = c.open_remote_file("/lightpipeline_docs.zip")
        z = zipfile.ZipFile(rf)
        LOG.debug("namelist: %s", json.dumps(z.namelist(), indent = 4))
        z.extractall("./")
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
