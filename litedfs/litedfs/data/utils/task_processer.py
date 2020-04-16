# -*- coding: utf-8 -*-

import time
import logging
import threading
from threading import Thread

from litedfs.data.utils.task_cache import TaskCache
from litedfs.data.utils.registrant import Registrant
from litedfs.data.utils.common import delete_file, delete_block
from litedfs.data.config import CONFIG

LOG = logging.getLogger(__name__)


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
                                if task["command"] == "delete":
                                    if "block" not in task:
                                        delete_file(task["name"])
                                    else:
                                        delete_block(task["name"], task["block"])
                                elif task["command"] == "replicate":
                                    Registrant.instance().replicate_block(task["name"], task["block"], task["ids"])
                            else:
                                time.sleep(0.5)
                            LOG.info("TaskProcesser(%03d) process task: %s", self.pid, task)
                        else:
                            time.sleep(5)
                    except Exception as e:
                        LOG.exception(e)
                else:
                    LOG.info("TaskProcesser(%03d) exit by siginal", self.pid)
                    break
        except Exception as e:
            LOG.exception(e)
        LOG.info("TaskProcesser(%03d) exit", self.pid)
