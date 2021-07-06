#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import signal
import logging
import argparse
from pathlib import Path

import tornado.ioloop
import tornado.httpserver
import tornado.web

from litedfs.version import __version__
from litedfs.name.handlers import info
from litedfs.name.handlers import data
from litedfs.name.utils.listener import Connection
from litedfs.name.utils.listener import DiscoveryListener
from litedfs.name.models.data_nodes import DataNodes
from litedfs.name.utils.fs_core import FileSystemTree
from litedfs.name.utils import common
from litedfs.name.config import CONFIG, load_config
from litedfs.name import logger

LOG = logging.getLogger(__name__)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", info.AboutHandler),
            (r"/cluster/info", info.ClusterInfoHandler),
            (r"/file/block/list", data.GenerateFileBlockListHandler),
            (r"/file/create", data.CreateFileHandler),
            (r"/file/delete", data.DeleteFileHandler),
            (r"/file/move", data.MoveFileDirectoryHandler),
            (r"/file/rename", data.RenameFileDirectoryHandler),
            (r"/file/update", data.UpdateFileHandler),
            (r"/file/lock/update", data.UpdateFileLockHandler),
            (r"/file/block/info", data.GetFileBlockInfoHandler),
            (r"/directory/create", data.CreateDirectoryHandler),
            (r"/directory/list", data.ListDirectoryHandler),
            (r"/directory/delete", data.DeleteDirectoryHandler),
            (r"/directory/move", data.MoveFileDirectoryHandler),
            (r"/directory/rename", data.RenameFileDirectoryHandler),
            (r"/path/info", data.PathInfoHandler),
        ]
        settings = dict(debug = False)
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    parser = argparse.ArgumentParser(prog = 'ldfsname')
    parser.add_argument("-g", "--generate-config", help = "generate configuration file & scripts into given path")
    parser.add_argument("-c", "--config", help = "run name node with configuration file")
    parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)
    args = parser.parse_args()

    if args.generate_config:
        output = args.generate_config
        cwd = os.path.split(os.path.realpath(__file__))[0]
        config_file = os.path.join(cwd, "./configuration.yml.temp")
        copy_files = [
            "install_systemd_service.sh",
            "uninstall_systemd_service.sh",
            "litedfs-name.service.temp",
            "name.sh",
            "README.md",
        ]
        if os.path.exists(output) and os.path.isdir(output):
            output = str(Path(output).resolve())
            log_path = os.path.join(output, "logs")
            data_path = os.path.join(output, "data")
            content = ""
            fp = open(config_file, "r")
            content = fp.read()
            fp.close()
            content = content.replace("log_path_string", log_path)
            content = content.replace("data_path_string", data_path)
            fp = open(os.path.join(output, "configuration.yml"), "w")
            fp.write(content)
            fp.close()
            for file_name in copy_files:
                file_path_source = os.path.join(cwd, file_name)
                with open(file_path_source, "r") as fs:
                    file_path_target = os.path.join(output, file_name)
                    with open(file_path_target, "w") as ft:
                        ft.write(fs.read())
                    if file_path_target.endswith(".sh"):
                        os.chmod(
                            file_path_target,
                            stat.S_IRUSR | stat.S_IWUSR | stat.S_IEXEC | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
                        )
        else:
            print("output(%s) not exists!", output)
    elif args.config:
        success = load_config(args.config)
        if success:
            common.init_storage()
            logger.config_logging(file_name = "name.log",
                                  log_level = CONFIG["log_level"],
                                  dir_name = CONFIG["log_path"],
                                  day_rotate = False,
                                  when = "D",
                                  interval = 1,
                                  max_size = 20,
                                  backup_count = 5,
                                  console = True)

            LOG.info("service start")

            try:
                data_nodes_db = DataNodes()
                http_server = tornado.httpserver.HTTPServer(Application())
                http_server.listen(CONFIG["http_port"], address = CONFIG["http_host"])
                # http_server.bind(CONFIG["http_port"], address = CONFIG["http_host"])
                listener = DiscoveryListener(Connection)
                listener.listen(CONFIG["tcp_port"], CONFIG["tcp_host"])
                file_system_tree = FileSystemTree()
                common.Servers.HTTP_SERVER = http_server
                common.Servers.SERVERS.append(data_nodes_db)
                common.Servers.SERVERS.append(file_system_tree)
                tornado.ioloop.IOLoop.instance().add_callback(file_system_tree.recover)
                signal.signal(signal.SIGTERM, common.sig_handler)
                signal.signal(signal.SIGINT, common.sig_handler)
                tornado.ioloop.IOLoop.instance().start()
            except Exception as e:
                LOG.exception(e)

            LOG.info("service end")
        else:
            print("failed to load configuration: %s" % args.config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
