# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.name.utils.fs_core import FileSystemTree
from litedfs.name.config import CONFIG
from litedfs.name import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.config_logging(file_name = "test_file_system_tree.log",
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
        CONFIG["data_path"] = "."

        fs = FileSystemTree()
        # fs.create("/a/b/c/d/e/f/g.txt", {"size": 100})
        # fs.create("/a/b/c/d/e/f.txt", {"size": 100})
        # fs.makedirs("/a/b/c/d/e/f/g/h")
        # fs.move("/a/b/c/d/e/f.txt", "/a/b")
        # fs.delete("/a/b/f.txt")
        LOG.debug("%s", json.dumps(fs.cache, indent = 4))
        LOG.debug("%s", json.dumps(fs.get_info("/"), indent = 4))
        # LOG.debug("%s", json.dumps(fs.get_info("/a/b/c/d"), indent = 4))
        # LOG.debug("%s", json.dumps(fs.list_dir("/a/b/c/d/e", recursive = True), indent = 4))
    except Exception as e:
        LOG.exception(e)

    LOG.debug("test end")
