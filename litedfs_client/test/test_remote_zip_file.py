# -*- coding: utf-8 -*-

import os
import io
import sys
import json
import time
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
        t = time.time()
        # c = LiteDFSClient("127.0.0.1", 9000)
        c = LiteDFSClient("10.0.169.238", 9000)
        rf = c.open_remote_file("/front_camera_jpg.zip")
        # rf = c.open_remote_file("/front_camera_jpg.zip_annotation/front_camera_jpg/1535428898382744.jpg.json")
        # rf = c.open_remote_file("/lightpipeline_docs.zip")
        # reader = io.BufferedReader(rf, buffer_size = 1024 * 1024)
        # for i in range(5):
        #     LOG.debug("line: %s", reader.readline())
        z = zipfile.ZipFile(rf)
        file = z.open("front_camera_jpg/1535428898682621.jpg")
        content = file.read()
        # LOG.debug("namelist: %s", json.dumps(z.namelist(), indent = 4))
        # for info in z.infolist():
        #     LOG.debug("info: %s, %s, %s, %s, %s", info.filename, info.file_size, info.is_dir(), info.orig_filename, info.date_time)
        # print(dir(info))
        # z.extractall("./")
        tt = time.time()
        LOG.info("use: %ss", tt - t)
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
