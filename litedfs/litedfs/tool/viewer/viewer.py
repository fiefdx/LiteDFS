#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import stat
import signal
import logging
import argparse
from pathlib import Path

import tornado.ioloop
import tornado.httpserver
import tornado.web

from litedfs.version import __version__
from litedfs.tool.viewer.handlers import info, cluster, storage
from litedfs.tool.viewer.utils import common
from litedfs.tool.viewer.utils.task_processer import MessageSender, TaskProcesser
from litedfs.tool.viewer.config import CONFIG, load_config
from litedfs.tool.viewer import logger

LOG = logging.getLogger(__name__)

cwd = os.path.split(os.path.realpath(__file__))[0]


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", info.RedirectHandler),
            (r"/cluster", cluster.ClusterHandler),
            (r"/storage", storage.StorageHandler),
            (r"/websocket/local", storage.LocalSocketHandler),
            (r"/websocket/remote", storage.RemoteSocketHandler),
        ]
        settings = dict(
            debug = False,
            template_path = os.path.join(cwd, "templates"),
            static_path = os.path.join(cwd, "static")
        )
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    parser = argparse.ArgumentParser(prog = 'ldfsviewer')
    parser.add_argument("-g", "--generate-config", help = "generate configuration file & scripts into given path")
    parser.add_argument("-c", "--config", help = "run litedfs viewer with configuration file")
    parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)
    args = parser.parse_args()

    if args.generate_config:
        output = args.generate_config
        cwd = os.path.split(os.path.realpath(__file__))[0]
        config_file = os.path.join(cwd, "./configuration.yml.temp")
        copy_files = [
            "install_systemd_service.sh",
            "uninstall_systemd_service.sh",
            "litedfs-viewer.service.temp",
            "viewer.sh",
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
            logger.config_logging(file_name = "viewer.log",
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
                message_sender = MessageSender(0.1)
                task_processer = TaskProcesser(0)
                task_processer.start()
                http_server = tornado.httpserver.HTTPServer(Application())
                http_server.listen(CONFIG["http_port"], address = CONFIG["http_host"])
                # http_server.bind(CONFIG["http_port"], address = CONFIG["http_host"])
                common.Servers.HTTP_SERVER = http_server
                common.Servers.SERVERS.append(message_sender)
                common.Servers.SERVERS.append(task_processer)
                signal.signal(signal.SIGTERM, common.sig_handler)
                signal.signal(signal.SIGINT, common.sig_handler)
                tornado.ioloop.IOLoop.instance().start()
                task_processer.join()
            except Exception as e:
                LOG.exception(e)

            LOG.info("service end")
        else:
            print("failed to load configuration: %s" % args.config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
