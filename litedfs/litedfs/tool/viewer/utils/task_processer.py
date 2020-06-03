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
    copy = "copy"
    cut = "cut"
    paste = "paste"


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
                                        msg = {}
                                        try:
                                            d_path = os.path.join(dir_path, d["name"])
                                            shutil.rmtree(d_path)
                                            msg["cmd"] = "info"
                                            msg["info"] = "Delete directory[%s] success" % d_path
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                    for f in files:
                                        msg = {}
                                        try:
                                            f_path = os.path.join(dir_path, f["name"])
                                            os.remove(f_path)
                                            msg["cmd"] = "info"
                                            msg["info"] = "Delete file[%s] success" % f_path
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                elif task["cmd"] == Command.paste:
                                    dir_path = joinpath(task["dir_path"])
                                    clipboard = task["clipboard"]
                                    dirs = clipboard["dirs"]
                                    files = clipboard["files"]
                                    for d in dirs:
                                        msg = {"cmd": "info"}
                                        try:
                                            source_path = os.path.join(clipboard["dir_path"], d["name"])
                                            target_path = os.path.join(dir_path, d["name"])
                                            if os.path.exists(target_path):
                                                msg["cmd"] = "warning"
                                                msg["info"] = "Directory [%s] already exists!" % target_path
                                                LOG.warning("Directory [%s] already exists!", target_path)
                                            elif not os.path.exists(source_path) or not os.path.isdir(source_path):
                                                msg["cmd"] = "warning"
                                                msg["info"] = "Directory [%s] doesn't exist!" % source_path
                                                LOG.warning("Directory [%s] doesn't exist!", source_path)
                                            else:
                                                if clipboard["type"] == Command.cut:
                                                    shutil.move(source_path, target_path)
                                                    msg["info"] = "Cut directory [%s] to [%s] success" % (source_path, target_path)
                                                    LOG.info("Cut directory [%s] to [%s] success", source_path, target_path)
                                                elif clipboard["type"] == Command.copy:
                                                    shutil.copytree(source_path, target_path)
                                                    msg["info"] = "Copy directory [%s] to [%s] success"%(source_path, target_path)
                                                    LOG.info("Copy directory [%s] to [%s] success", source_path, target_path)
                                                time.sleep(0.1)
                                                LOG.info("Paste directory from [%s] to [%s]", source_path, target_path)
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                    for f in files:
                                        msg = {"cmd": "info"}
                                        try:
                                            source_path = os.path.join(clipboard["dir_path"], f["name"])
                                            target_path = os.path.join(dir_path, f["name"])
                                            if os.path.exists(target_path):
                                                msg["cmd"] = "warning"
                                                msg["info"] = "File [%s] already exists!" % target_path
                                                LOG.warning("File [%s] already exists!", target_path)
                                            elif not os.path.exists(source_path) or not os.path.isfile(source_path):
                                                msg["cmd"] = "warning"
                                                msg["info"] = "File [%s] doesn't exists!" % source_path
                                                LOG.warning("File [%s] doesn't exists!", source_path)
                                            else:
                                                if clipboard["type"] == Command.cut:
                                                    shutil.move(source_path, target_path)
                                                    msg["info"] = "Cut file [%s] to [%s] success" % (source_path, target_path)
                                                    LOG.info("Cut file [%s] to [%s] success", source_path, target_path)
                                                elif clipboard["type"] == Command.copy:
                                                    shutil.copy(source_path, target_path)
                                                    msg["info"] = "Copy file [%s] to [%s] success" % (source_path, target_path)
                                                    LOG.info("Copy file [%s] to [%s] success", source_path, target_path)
                                                time.sleep(0.1)
                                                LOG.info("Paste file [%s] to [%s]", source_path, target_path)
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
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
