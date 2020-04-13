# -*- coding: utf-8 -*-

import time
import logging
import threading
from threading import Thread

from litedfs.data.utils.common import delete_file
from litedfs.data.config import CONFIG

LOG = logging.getLogger(__name__)


class TaskCache(object):
    cache = []
    max_size = 10

    @classmethod
    def set_max_size(cls, size):
        cls.max_size = size

    @classmethod
    def push(cls, task):
        cls.cache.append(task)

    @classmethod
    def pop(cls):
        result = None
        try:
            result = cls.cache.pop(0)
        except IndexError:
            pass
        except Exception as e:
            LOG.exception(e)
        return result

    @classmethod
    def empty(cls):
        return len(cls.cache) == 0

    @classmethod
    def full(cls):
        return len(cls.cache) >= cls.max_size

    @classmethod
    def size(cls):
        return len(cls.cache)


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
                                    delete_file(task["name"])
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
