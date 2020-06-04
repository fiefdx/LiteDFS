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
    remote_delete = "remote_delete"
    remote_paste = "remote_paste"
    download = "download"
    upload = "upload"


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


def download_directory(dir, remote_path, local_path, handler):
    source_path = os.path.join(remote_path, dir["name"])
    target_path = os.path.join(local_path, dir["name"])
    if not os.path.exists(target_path):
        os.mkdir(target_path)
    dirs, files = handler.client.listdir(source_path)
    for d in dirs:
        download_directory(d, source_path, target_path, handler)
    for f in files:
        msg = {"cmd": "info"}
        try:
            source_file_path = os.path.join(source_path, f["name"])
            target_file_path = os.path.join(target_path, f["name"])
            if handler.client.download_file(source_file_path, target_file_path):
                msg["info"] = "Download remote file [%s] to [%s] success" % (source_file_path, target_file_path)
                LOG.info("Download remote file [%s] to [%s] success", source_file_path, target_file_path)
            else:
                msg["cmd"] = "error"
                msg["info"] = "Download remote file [%s] to [%s] failed" % (source_file_path, target_file_path)
                LOG.info("Download remote file [%s] to [%s] failed", source_file_path, target_file_path)
            time.sleep(0.1)
        except Exception as e:
            LOG.exception(e)
            msg["cmd"] = "error"
            msg["info"] = str(e)
        handler.write_message(msg)
    msg = {"cmd": "info"}
    msg["info"] = "Download remote directory [%s] to [%s] success" % (source_path, target_path)
    LOG.info("Download remote directory [%s] to [%s] success", source_path, target_path)
    handler.write_message(msg)


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
                                            msg["info"] = "Delete directory [%s] success" % d_path
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
                                            msg["info"] = "Delete file [%s] success" % f_path
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
                                elif task["cmd"] == Command.remote_delete:
                                    dir_path = joinpath(task["dir_path"])
                                    dirs = task["dirs"]
                                    files = task["files"]
                                    for d in dirs:
                                        msg = {}
                                        try:
                                            d_path = os.path.join(dir_path, d["name"])
                                            if task["socket_handler"].client.delete_directory(d_path):
                                                msg["cmd"] = "info"
                                                msg["info"] = "Delete remote directory [%s] success" % d_path
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Delete remote directory [%s] failed" % d_path
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                    for f in files:
                                        msg = {}
                                        try:
                                            f_path = os.path.join(dir_path, f["name"])
                                            if task["socket_handler"].client.delete_directory(f_path):
                                                msg["cmd"] = "info"
                                                msg["info"] = "Delete remote file [%s] success" % f_path
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Delete remote file [%s] failed" % f_path
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                elif task["cmd"] == Command.remote_paste:
                                    dir_path = joinpath(task["dir_path"])
                                    clipboard = task["clipboard"]
                                    dirs = clipboard["dirs"]
                                    files = clipboard["files"]
                                    for d in dirs:
                                        msg = {"cmd": "info"}
                                        try:
                                            source_path = os.path.join(clipboard["dir_path"], d["name"])
                                            target_path = dir_path
                                            if task["socket_handler"].client.move_directory(source_path, target_path):
                                                msg["info"] = "Cut remote directory [%s] to [%s] success" % (source_path, target_path)
                                                LOG.info("Cut remote directory [%s] to [%s] success", source_path, target_path)
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Cut remote directory [%s] to [%s] failed" % (source_path, target_path)
                                                LOG.info("Cut remote directory [%s] to [%s] failed", source_path, target_path)
                                            time.sleep(0.1)
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                    for f in files:
                                        msg = {"cmd": "info"}
                                        try:
                                            source_path = os.path.join(clipboard["dir_path"], f["name"])
                                            target_path = dir_path
                                            if task["socket_handler"].client.move_file(source_path, target_path):
                                                msg["info"] = "Cut remote file [%s] to [%s] success" % (source_path, target_path)
                                                LOG.info("Cut remote file [%s] to [%s] success", source_path, target_path)
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Cut remote file [%s] to [%s] failed" % (source_path, target_path)
                                                LOG.info("Cut remote file [%s] to [%s] failed", source_path, target_path)
                                            time.sleep(0.1)
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        task["socket_handler"].write_message(msg)
                                elif task["cmd"] == Command.download:
                                    local_path = task["local_path"]
                                    remote_path = task["remote_path"]
                                    dirs = task["dirs"]
                                    files = task["files"]
                                    for d in dirs:
                                        download_directory(d, remote_path, local_path, task["socket_handler"])
                                    for f in files:
                                        msg = {"cmd": "info"}
                                        try:
                                            source_path = os.path.join(remote_path, f["name"])
                                            target_path = os.path.join(local_path, f["name"])
                                            if task["socket_handler"].client.download_file(source_path, target_path):
                                                msg["info"] = "Download remote file [%s] to [%s] success" % (source_path, target_path)
                                                LOG.info("Download remote file [%s] to [%s] success", source_path, target_path)
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Download remote file [%s] to [%s] failed" % (source_path, target_path)
                                                LOG.info("Download remote file [%s] to [%s] failed", source_path, target_path)
                                            time.sleep(0.1)
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
