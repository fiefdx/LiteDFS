# -*- coding: utf-8 -*-

import logging
from uuid import uuid4

import tornado.tcpserver
from tornado import gen
from tornado.ioloop import IOLoop
from tornado_discovery.connection import BaseConnection
from tornado_discovery.listener import BaseListener
from tornado_discovery.common import crc32sum, Command, Status, Message

from litedfs.name.models.data_nodes import DataNodes
from litedfs.name.utils.common import OperationError

LOG = logging.getLogger(__name__)


class Connection(BaseConnection):
    clients_dict = {}
    id_compress = {}
    id_decompress = {}
    tasks = {}

    def __init__(self, stream, address):
        super(Connection, self).__init__(stream, address)

    @classmethod
    def push_task(cls, id, task):
        if id in cls.tasks:
            cls.tasks[id].append(task)
        else:
            cls.tasks[id] = [task]
        LOG.debug("push task, id: %s, task: %s", id, task)

    @classmethod
    def load_node_ids(cls):
        nodes_info = DataNodes.instance().list()
        for node in nodes_info["data_nodes"]:
            cls.id_compress[node["node_id"]] = node["id"]
            cls.id_decompress[node["id"]] = node["node_id"]
        LOG.debug("id_compress: %s, id_decompress: %s", cls.id_compress, cls.id_decompress)

    @classmethod
    def get_node_infos(cls, current = None, without_full_node = False):
        result = {}
        for node_id in cls.clients_dict:
            node = cls.clients_dict[node_id]
            if node is not current:
                if without_full_node:
                    if not node.info["storage_full"]:
                        result[node.id] = [node.info["http_host"], node.info["http_port"], node.info["storage_full"]]
                else:
                    result[node.id] = [node.info["http_host"], node.info["http_port"], node.info["storage_full"]]
        return result

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
                        success = DataNodes.instance().add(node_id, info = self.info)
                        if not success:
                            send_data = {
                                "command": Command.register,
                                "data": {
                                    "status": Status.failure,
                                    "message": "add data node into data_nodes database failed",
                                }
                            }
                        else:
                            node = DataNodes.instance().get(node_id)
                            self.id = node["id"]
                            Connection.id_decompress[self.id] = self.info["node_id"]
                            Connection.id_compress[self.info["node_id"]] = self.id
                            if self.info["node_id"] not in Connection.clients_dict:
                                Connection.clients_dict[self.info["node_id"]] = self
                            self._status = Status.registered
                    # register with node_id
                    else:
                        send_data = {
                            "command": Command.register,
                            "data": {
                                "status": Status.success,
                                "message": Status.success,
                                "node_id": self.info["node_id"],
                            }
                        }
                        node = DataNodes.instance().get(self.info["node_id"])
                        if node is False:
                            send_data = {
                                "command": Command.register,
                                "data": {
                                    "status": Status.failure,
                                    "message": "data node retrive from data_nodes database failed",
                                }
                            }
                        elif node is None:
                            send_data = {
                                "command": Command.register,
                                "data": {
                                    "status": Status.failure,
                                    "message": "data node not exists in data_nodes database",
                                }
                            }
                        else:
                            self.id = node["id"]
                            Connection.id_decompress[self.id] = self.info["node_id"]
                            Connection.id_compress[self.info["node_id"]] = self.id
                            DataNodes.instance().update(self.info["node_id"], {"info": self.info})
                            if self.info["node_id"] not in Connection.clients_dict:
                                Connection.clients_dict[self.info["node_id"]] = self
                            self._status = Status.registered
                elif "command" in data and data["command"] == Command.heartbeat:
                    self.info = data["data"]
                    if self.info["http_host"] == "0.0.0.0":
                        self.info["http_host"] = self._address[0]
                    if self._status == Status.registered:
                        send_data = {
                            "command": Command.heartbeat,
                            "data": {
                                "data_nodes": Connection.get_node_infos(current = self),
                                "status": Status.success,
                                "message": Status.success,
                            }
                        }
                        if self.id in Connection.tasks and Connection.tasks[self.id]:
                            if not self.info["task_queue_full"]:
                                task = Connection.tasks[self.id].pop(0)
                                send_data["data"]["task"] = task
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
        self._stream.close()
        LOG.warning("Client(%s) node_id: %s heartbeat_timeout", self._address, self.info["node_id"])

    def _refuse_connect(self):
        if self._heartbeat_timeout:
            IOLoop.instance().remove_timeout(self._heartbeat_timeout)
        if self in BaseConnection.clients:
            if "node_id" in self.info and self.info["node_id"] in Connection.clients_dict:
                del Connection.clients_dict[self.info["node_id"]]
            BaseConnection.clients.remove(self)
        self._stream.close()
        LOG.warning("Refuse(%s) node_id: %s connect", self._address, self.info["node_id"])

    def _on_close(self):
        if self._heartbeat_timeout:
            IOLoop.instance().remove_timeout(self._heartbeat_timeout)
        if self in BaseConnection.clients:
            if "node_id" in self.info and self.info["node_id"] in Connection.clients_dict:
                del Connection.clients_dict[self.info["node_id"]]
            BaseConnection.clients.remove(self)
        self._stream.close()
        LOG.info("Client(%s) closed", self._address)


class DiscoveryListener(BaseListener):
    def __init__(self, connection_cls, ssl_options = None, **kwargs):
        LOG.info("DiscoveryListener start")
        self.connection_cls = connection_cls
        self.connection_cls.load_node_ids()
        tornado.tcpserver.TCPServer.__init__(self, ssl_options = ssl_options, **kwargs)

    def handle_stream(self, stream, address):
        LOG.debug("Incoming connection from %r", address)
        self.connection_cls(stream, address)
