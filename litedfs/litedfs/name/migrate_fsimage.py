# -*- coding: utf-8 -*-

import os
import logging
import argparse

from litedfs.version import __version__
from litedfs.name.utils.fs_core import F, C
from litedfs.name.utils.append_log import AppendLogJson
from litedfs.name.config import CONFIG, load_config
from litedfs.name import logger

LOG = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog = 'migrate_fsimage.py')
    parser.add_argument("-c", "--config", required = True, help = "configuration file path")
    parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)
    args = parser.parse_args()
    if args.config:
        success = load_config(args.config)
        if success:
            logger.config_logging(file_name = "migrate_fsimage.log",
                                  log_level = CONFIG["log_level"],
                                  dir_name = CONFIG["log_path"],
                                  day_rotate = False,
                                  when = "D",
                                  interval = 1,
                                  max_size = 20,
                                  backup_count = 5,
                                  console = True)

            LOG.info("migrate start")
            
            fsimage_new = AppendLogJson(os.path.join(CONFIG["data_path"], "fsimage.new"))
            fsimage = AppendLogJson(os.path.join(CONFIG["data_path"], "fsimage"))
            for line in fsimage.iterlines():
                if line[F.cmd] == C.makedir:
                    line[F.cmd] = C.makedirs
                fsimage_new.writeline(line)
            fsimage_new.close()
            fsimage.close()

            editlog_new = AppendLogJson(os.path.join(CONFIG["data_path"], "editlog.new"))
            editlog = AppendLogJson(os.path.join(CONFIG["data_path"], "editlog"))
            for line in editlog.iterlines():
                if line[F.cmd] == C.makedir:
                    line[F.cmd] = C.makedirs
                editlog_new.writeline(line)
            editlog_new.close()
            editlog.close()

            LOG.info("migrate end")
        else:
            print("failed to load configuration: %s" % args.config)
    else:
        parser.print_help()