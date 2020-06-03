# -*- coding: utf-8 -*-

import os
import time
import shutil
import logging
import threading
from threading import Thread

from litedfs.tool.viewer.utils.task_cache import TaskCache
from litedfs.tool.viewer.utils.common import joinpath, splitpath
from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger(__name__)


class Command(object):
    cd = "cd"
    refresh = "refresh"
    rename = "rename"
    mkdir = "mkdir"
    delete = "delete"


class StoppableThread(Thread):
    """
    Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition.
    """

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.isSet()


class TaskProcesser(StoppableThread):
    def __init__(self, pid):
        StoppableThread.__init__(self)
        Thread.__init__(self)
        self.pid = pid

    def run(self):
        LOG = logging.getLogger("task_processer")
        LOG.info("TaskProcesser(%03d) start", self.pid)
        try:
            while True:
                if not self.stopped():
                    try:
                        if not TaskCache.empty():
                            task = TaskCache.pop()
                            if task is not None:
                                if task["cmd"] == Command.delete:
                                    dir_path = joinpath(task["dir_path"])
                                    dirs = task["dirs"]
                                    files = task["files"]
                                    for d in dirs:
                                        try:
                                            d_path = os.path.join(dir_path, d["name"])
                                            shutil.rmtree(d_path)
                                            msg = {}
                                            msg["cmd"] = "info"
                                            msg["info"] = "Delete directory[%s] success" % d_path
                                            task["socket_handler"].write_message(msg)
                                        except Exception as e:
                                            LOG.exception(e)
                                    for f in files:
                                        try:
                                            f_path = os.path.join(dir_path, f["name"])
                                            os.remove(f_path)
                                            msg = {}
                                            msg["cmd"] = "info"
                                            msg["info"] = "Delete file[%s] success" % f_path
                                            task["socket_handler"].write_message(msg)
                                        except Exception as e:
                                            LOG.exception(e)
                            else:
                                time.sleep(0.5)
                            LOG.info("TaskProcesser(%03d) process task: %s", self.pid, task)
                        else:
                            time.sleep(0.5)
                    except Exception as e:
                        LOG.exception(e)
                else:
                    LOG.info("TaskProcesser(%03d) exit by siginal", self.pid)
                    break
        except Exception as e:
            LOG.exception(e)
        LOG.info("TaskProcesser(%03d) exit", self.pid)
