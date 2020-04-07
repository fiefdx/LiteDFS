# -*- coding: utf-8 -*-

import logging
from uuid import uuid4

import tornado.tcpserver
from tornado import gen
from tornado.ioloop import IOLoop
from tornado_discovery.connection import BaseConnection
from tornado_discovery.listener import BaseListener
from tornado_discovery.common import crc32sum, Command, Status, Message

LOG = logging.getLogger(__name__)


class Connection(BaseConnection):
    clients_dict = {}
    total_action_slots = 0

    def __init__(self, stream, address):
        super(Connection, self).__init__(stream, address)

    @gen.coroutine
    def _on_connect(self):
        try:
            while True:
                refuse_connect_flag = False
                data = yield self.read_message()
                send_data = {}
                # register
                if "command" in data and data["command"] == Command.register:
                    self.info = data["data"]
                    if self.info["http_host"] == "0.0.0.0":
                        self.info["http_host"] = self._address[0]
                    # no node_id
                    if "node_id" not in self.info or self.info["node_id"] == None:
                        node_id = str(uuid4())
                        send_data = {
                            "command": Command.register,
                            "data": {
                                "status": Status.success,
                                "message": Status.success,
                                "node_id": node_id,
                            }
                        }
                        self.info["node_id"] = node_id
                        self._status = Status.registered
                        if self.info["node_id"] not in Connection.clients_dict:
                            Connection.clients_dict[self.info["node_id"]] = self
                    # register with node_id
                    else:
                        if self.info["node_id"] not in Connection.clients_dict:
                            Connection.clients_dict[self.info["node_id"]] = self
                        send_data = {
                            "command": Command.register,
                            "data": {
                                "status": Status.success,
                                "message": Status.success,
                                "node_id": self.info["node_id"],
                            }
                        }
                        self._status = Status.registered
                    if "action_slots" in self.info:
                        Connection.total_action_slots += self.info["action_slots"]
                elif "command" in data and data["command"] == Command.heartbeat:
                    self.info = data["data"]
                    if self.info["http_host"] == "0.0.0.0":
                        self.info["http_host"] = self._address[0]
                    if self._status == Status.registered:
                        send_data = {
                            "command": Command.heartbeat,
                            "data": {
                                "status": Status.success,
                                "message": Status.success,
                            }
                        }
                        if self._heartbeat_timeout:
                            IOLoop.instance().remove_timeout(self._heartbeat_timeout)
                        self._heartbeat_timeout = IOLoop.instance().add_timeout(
                            IOLoop.time(IOLoop.instance()) + self.info["heartbeat_timeout"],
                            self._remove_connection
                        )
                    else:
                        send_data = {
                            "command": Command.heartbeat,
                            "data": {
                                "status": Status.failure,
                                "message": "invalid node_id: %s" % self.info["node_id"],
                            }
                        }
                        refuse_connect_flag = True
                else:
                    LOG.error("Client(%s) invaild message error: %s", self._address, data)
                    send_data = {
                        "command": Command.error,
                        "data": {
                            "status": Status.failure,
                            "message": "Unknown Command!",
                        }
                    }
                self.send_message(send_data, refuse_connect_flag = refuse_connect_flag)
        except tornado.iostream.StreamClosedError:
            LOG.info("Closed: %s", self._address)
        except Exception as e:
            LOG.exception(e)

    def _remove_connection(self):
        if self in BaseConnection.clients:
            if "node_id" in self.info and self.info["node_id"] in Connection.clients_dict:
                del Connection.clients_dict[self.info["node_id"]]
            BaseConnection.clients.remove(self)
        if "action_slots" in self.info:
            Connection.total_action_slots -= self.info["action_slots"]
        self._stream.close()
        LOG.warning("Client(%s) node_id: %s heartbeat_timeout", self._address, self.info["node_id"])

    def _refuse_connect(self):
        if self._heartbeat_timeout:
            IOLoop.instance().remove_timeout(self._heartbeat_timeout)
        if self in BaseConnection.clients:
            if "node_id" in self.info and self.info["node_id"] in Connection.clients_dict:
                del Connection.clients_dict[self.info["node_id"]]
            BaseConnection.clients.remove(self)
        if "action_slots" in self.info:
            Connection.total_action_slots -= self.info["action_slots"]
        self._stream.close()
        LOG.warning("Refuse(%s) node_id: %s connect", self._address, self.info["node_id"])

    def _on_close(self):
        if self._heartbeat_timeout:
            IOLoop.instance().remove_timeout(self._heartbeat_timeout)
        if self in BaseConnection.clients:
            if "node_id" in self.info and self.info["node_id"] in Connection.clients_dict:
                del Connection.clients_dict[self.info["node_id"]]
            BaseConnection.clients.remove(self)
        if "action_slots" in self.info:
            Connection.total_action_slots -= self.info["action_slots"]
        self._stream.close()
        LOG.info("Client(%s) closed", self._address)


class DiscoveryListener(BaseListener):
    def __init__(self, connection_cls, ssl_options = None, **kwargs):
        LOG.info("DiscoveryListener start")
        self.connection_cls = connection_cls
        tornado.tcpserver.TCPServer.__init__(self, ssl_options = ssl_options, **kwargs)

    def handle_stream(self, stream, address):
        LOG.debug("Incoming connection from %r", address)
        self.connection_cls(stream, address)
