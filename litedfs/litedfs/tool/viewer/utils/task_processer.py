# -*- coding: utf-8 -*-

import os
import time
import shutil
import logging
import threading
from threading import Thread
from queue import Queue, Empty

import tornado.ioloop
from tornado import gen

from litedfs.tool.viewer.handlers import storage
from litedfs.tool.viewer.utils.task_cache import TaskCache
from litedfs.tool.viewer.utils.common import joinpath, splitpath, listdir, Command
from litedfs.tool.viewer.config import CONFIG

LOG = logging.getLogger(__name__)

MessageQueue = Queue(0)


class MessageSender(object):
    _instance = None
    name = "message sender"

    def __new__(cls, interval = 0.1):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.interval = interval
            cls._instance.ioloop_service()
        return cls._instance

    @classmethod
    def instance(cls):
        return cls._instance

    def ioloop_service(self):
        self.periodic_message_sender = tornado.ioloop.PeriodicCallback(
            self.send_message, 
            self.interval * 1000
        )
        self.periodic_message_sender.start()

    @gen.coroutine
    def send_message(self):
        try:
            task = MessageQueue.get(block = False)
            handler, msg = task
            LOG.debug("send message: %s", msg)
            if isinstance(handler, str):
                if handler == "local":
                    storage.LocalSocketHandler.send_msgs(msg)
                elif handler == "remote":
                    storage.RemoteSocketHandler.send_msgs(msg)
            else:
                handler.write_message(msg)
        except Empty:
            pass
        except Exception as e:
            LOG.exception(e)

    def close(self):
        try:
            if self.periodic_message_sender:
                self.periodic_message_sender.stop()
            LOG.info("MessageSender close")
        except Exception as e:
            LOG.exception(e)


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
    items, _ = handler.client.listdir(source_path, sort_by = "name", desc = False)
    for item in items:
        if item["type"] == "Directory":
            download_directory(item, source_path, target_path, handler)
        else:
            msg = {"cmd": "info"}
            try:
                source_file_path = os.path.join(source_path, item["name"])
                target_file_path = os.path.join(target_path, item["name"])
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
            MessageQueue.put([handler, msg])
    msg = {"cmd": "info"}
    msg["info"] = "Download remote directory [%s] to [%s] success" % (source_path, target_path)
    LOG.info("Download remote directory [%s] to [%s] success", source_path, target_path)
    MessageQueue.put([handler, msg])


def upload_directory(dir, local_path, remote_path, handler, replica = 1):
    source_path = os.path.join(local_path, dir["name"])
    target_path = os.path.join(remote_path, dir["name"])
    handler.client.mkdir(target_path)
    items, _ = listdir(source_path)
    for item in items:
        if item["type"] == "Directory":
            upload_directory(item, source_path, target_path, handler, replica = replica)
        else:
            msg = {"cmd": "info"}
            try:
                source_file_path = os.path.join(source_path, item["name"])
                target_file_path = os.path.join(target_path, item["name"])
                if handler.client.upload_file(source_file_path, target_file_path, replica = replica):
                    msg["info"] = "Upload file [%s] to [%s] success" % (source_file_path, target_file_path)
                    LOG.info("Upload file [%s] to [%s] success", source_file_path, target_file_path)
                else:
                    msg["cmd"] = "error"
                    msg["info"] = "Upload file [%s] to [%s] failed" % (source_file_path, target_file_path)
                    LOG.info("Upload file [%s] to [%s] failed", source_file_path, target_file_path)
                time.sleep(0.1)
            except Exception as e:
                LOG.exception(e)
                msg["cmd"] = "error"
                msg["info"] = str(e)
            MessageQueue.put([handler, msg])
    msg = {"cmd": "info"}
    msg["info"] = "Upload directory [%s] to [%s] success" % (source_path, target_path)
    LOG.info("Upload directory [%s] to [%s] success", source_path, target_path)
    MessageQueue.put([handler, msg])


def update_directory(dir, remote_path, handler, replica):
    dir_path = os.path.join(remote_path, dir["name"])
    items, _ = handler.client.listdir(dir_path, sort_by = "name", desc = False)
    for item in items:
        if item["type"] == "Directory":
            update_directory(item, dir_path, handler, replica = replica)
        else:
            msg = {"cmd": "info"}
            try:
                f_path = os.path.join(dir_path, item["name"])
                if handler.client.update_file(f_path, replica = replica):
                    msg["info"] = "Update remote file [%s] success" % f_path
                    LOG.info("Update remote file [%s] success", f_path)
                else:
                    msg["cmd"] = "error"
                    msg["info"] = "Update remote file [%s] failed" % f_path
                    LOG.info("Update remote file [%s] failed", f_path)
                time.sleep(0.1)
            except Exception as e:
                LOG.exception(e)
                msg["cmd"] = "error"
                msg["info"] = str(e)
            MessageQueue.put([handler, msg])
    msg = {"cmd": "info"}
    msg["info"] = "Update remote directory [%s] success" % dir_path
    LOG.info("Update remote directory [%s] success", dir_path)
    MessageQueue.put([handler, msg])


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
                                        MessageQueue.put([task["socket_handler"], msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": dir_path}
                                    MessageQueue.put(["local", msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": dir_path}
                                    MessageQueue.put(["local", msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": dir_path}
                                    MessageQueue.put(["remote", msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": dir_path}
                                    MessageQueue.put(["remote", msg])
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
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": local_path}
                                    MessageQueue.put(["local", msg])
                                elif task["cmd"] == Command.upload:
                                    local_path = task["local_path"]
                                    remote_path = task["remote_path"]
                                    dirs = task["dirs"]
                                    files = task["files"]
                                    replica = task["replica"] if "replica" in task else 1
                                    for d in dirs:
                                        upload_directory(d, local_path, remote_path, task["socket_handler"], replica = replica)
                                    for f in files:
                                        msg = {"cmd": "info"}
                                        try:
                                            source_path = os.path.join(local_path, f["name"])
                                            target_path = os.path.join(remote_path, f["name"])
                                            if task["socket_handler"].client.upload_file(source_path, target_path, replica = replica):
                                                msg["info"] = "Upload file [%s] to [%s] success" % (source_path, target_path)
                                                LOG.info("Upload file [%s] to [%s] success", source_path, target_path)
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Upload file [%s] to [%s] failed" % (source_path, target_path)
                                                LOG.info("Upload file [%s] to [%s] failed", source_path, target_path)
                                            time.sleep(0.1)
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": remote_path}
                                    MessageQueue.put(["remote", msg])
                                elif task["cmd"] == Command.update:
                                    dir_path = joinpath(task["dir_path"])
                                    dirs = task["dirs"]
                                    files = task["files"]
                                    replica = task["replica"]
                                    for d in dirs:
                                        update_directory(d, dir_path, task["socket_handler"], replica = replica)
                                    for f in files:
                                        msg = {"cmd": "info"}
                                        try:
                                            f_path = os.path.join(dir_path, f["name"])
                                            if task["socket_handler"].client.update_file(f_path, replica = replica):
                                                msg["info"] = "Update remote file [%s] success" % f_path
                                                LOG.info("Update remote file [%s] success", f_path)
                                            else:
                                                msg["cmd"] = "error"
                                                msg["info"] = "Update remote file [%s] failed" % f_path
                                                LOG.info("Update remote file [%s] failed", f_path)
                                            time.sleep(0.1)
                                        except Exception as e:
                                            LOG.exception(e)
                                            msg["cmd"] = "error"
                                            msg["info"] = str(e)
                                        MessageQueue.put([task["socket_handler"], msg])
                                    msg = {"cmd": Command.need_refresh, "dir_path": dir_path}
                                    MessageQueue.put(["remote", msg])
                                elif task["cmd"] == Command.preview:
                                    dir_path = joinpath(task["dir_path"])
                                    file = task["file"]
                                    file_type = file["type"].lower()
                                    file_path = os.path.join(dir_path, file["name"])
                                    msg = {}
                                    if file_type == ".zip":
                                        namelist = task["socket_handler"].client.preview_zip_file(file_path)
                                        if namelist:
                                            msg["cmd"] = Command.preview
                                            msg["file_path"] = file_path
                                            msg["data"] = namelist
                                            msg["type"] = file_type
                                        else:
                                            msg["cmd"] = "error"
                                            msg["info"] = "preview file [%s] failed" % file_path
                                    elif file["name"].lower() == ".gitignore" or file_type in [".txt", ".log", ".yml", ".json", ".md", ".py", ".c", ".xml", ".go", ".sh", ".html"]:
                                        content = task["socket_handler"].client.preview_text_file(file_path)
                                        if content:
                                            msg["cmd"] = Command.preview
                                            msg["file_path"] = file_path
                                            msg["data"] = content
                                            msg["type"] = file_type
                                        else:
                                            msg["cmd"] = "error"
                                            msg["info"] = "preview file [%s] failed" % file_path
                                    else:
                                        msg["cmd"] = "error"
                                        msg["info"] = "preview does not support this type of file"
                                    MessageQueue.put([task["socket_handler"], msg])
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
