# -*- coding: utf-8 -*-

import logging

from tornado import gen
from tornado.tcpclient import TCPClient
from tornado_discovery.registrant import BaseRegistrant
from tornado_discovery.common import Command, Status

from litedfs.data.config import CONFIG

LOG = logging.getLogger(__name__)


class Registrant(BaseRegistrant):
    _instance = None

    def __new__(cls, host, port, config, retry_interval = 10, reconnect = True):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.host = host
            cls._instance.port = port
            cls._instance.config = config
            cls._instance.retry_interval = retry_interval
            cls._instance.heartbeat_interval = cls._instance.config.get("heartbeat_interval")
            cls._instance.heartbeat_timeout = cls._instance.config.get("heartbeat_timeout")
            cls._instance.reconnect = reconnect
            cls._instance.tcpclient = TCPClient()
            cls._instance.periodic_heartbeat = None
            cls._instance._stream = None
            cls._instance.heartbeat_data = {}
        return cls._instance

    def __init__(self, host, port, config, retry_interval = 10, reconnect = True):
        pass

    @classmethod
    def instance(cls):
        return cls._instance

    def update_heartbeat_data(self, data = {}):
        self.heartbeat_data.update(data)

    @gen.coroutine
    def heartbeat_service(self):
        try:
            message_data = self.config.to_dict()
            message_data.update(self.heartbeat_data)
            data = {"command": Command.heartbeat, "data": message_data}
            self.send_message(data)
            data = yield self.read_message()
            if data["data"]["status"] == Status.success:
                LOG.info("Client Received Heartbeat Message: %s", data["data"])
            else:
                LOG.error("Client Received Heartbeat Message: %s", data["data"])
        except Exception as e:
            LOG.exception(e)
