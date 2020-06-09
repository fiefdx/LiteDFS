# -*- coding: utf-8 -*-

import os
import json
import logging
from io import BytesIO

import requests
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.tcpclient import TCPClient
from tornado_discovery.registrant import BaseRegistrant
from tornado_discovery.common import Command, Status

from litedfs.data.utils.common import Errors, async_post, disk_usage, size_pretty
from litedfs.data.utils.task_cache import TaskCache
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
            cls._instance.registered = False
            cls._instance.data_nodes = {}
            cls._instance.async_client = AsyncHTTPClient()
        return cls._instance

    def __init__(self, host, port, config, retry_interval = 10, reconnect = True):
        pass

    @classmethod
    def instance(cls):
        return cls._instance

    def update_heartbeat_data(self, data = {}):
        self.heartbeat_data.update(data)

    @gen.coroutine
    def replicate_block_async(self, file_name, block_file, block_id, node_ids):
        result = False
        try:
            if node_ids:
                node_id = node_ids[0]
                if node_id in self.data_nodes:
                    data_node = self.data_nodes[node_id]
                    url = "http://%s:%s/block/create" % (data_node[0], data_node[1])
                    r = yield async_post(self.async_client, url, {"up_file": block_file}, {"name": file_name, "block": block_id, "ids": ",".join(node_ids[1:])})
                    if r.code == 200:
                        data = json.loads(r.body.decode("utf-8"))
                        if "result" in data and data["result"] == Errors.OK:
                            result = True
                            LOG.debug("replicate block to node: %s(%s:%s), result: %s", node_id, data_node[0], data_node[1], result)
                        else:
                            LOG.error("replicate block to node: %s(%s:%s) failed, result: %s", node_id, data_node[0], data_node[1], result)
                    else:
                        LOG.error("replicate block to node: %s(%s:%s) failed, response: %s", node_id, data_node[0], data_node[1], r)
            else:
                result = True
        except Exception as e:
            LOG.exception(e)
        return result

    def replicate_block(self, file_name, block_id, node_ids):
        result = False
        try:
            node_ids = [str(i) for i in node_ids]
            if node_ids:
                node_id = node_ids[0]
                if node_id in self.data_nodes:
                    data_node = self.data_nodes[node_id]
                    url = "http://%s:%s/block/create" % (data_node[0], data_node[1])

                    file_path = os.path.join(CONFIG["data_path"], "files", file_name[:2], file_name[2:4], "%s_%s.blk" % (file_name, block_id))
                    if os.path.exists(file_path):
                        fp = open(file_path, "rb")
                        block_content = BytesIO(fp.read())
                        fp.close()
                        files = {'up_file': ("up_file", block_content, b"text/plain")}
                        values = {"name": file_name, "block": block_id, "ids": ",".join(node_ids[1:])}
                        r = requests.post(url, files = files, data = values)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                result = True
                            else:
                                LOG.error("replicate block failed: %s", d)
                        else:
                            LOG.error("replicate block error:\ncode: %s\ncontent: %s", r.status_code, r.content)
                    else:
                        LOG.error("replicate block[%s] not exists", file_path)
                else:
                    LOG.error("replicate block failed, node_id: %s not exists", node_id)
            else:
                result = True
        except Exception as e:
            LOG.exception(e)
        return result

    @gen.coroutine
    def register_service(self):
        try:
            data = {"command": Command.register, "data": self.config.to_dict()}
            self.update_storage_info(data["data"])
            self.send_message(data)
            data = yield self.read_message()
            if data["command"] == Command.register:
                if data["data"]["status"] == Status.success:
                    self.registered = True
                    if not self.config.has_key("node_id"):
                        self.config.set("node_id", data["data"]["node_id"])
                        LOG.info("Received new node_id: %s", data["data"]["node_id"])
                    LOG.info("Client Register Received Message: %s", data)
                else:
                    LOG.error("Client Register Failed, Received Message: %s", data)
            else:
                LOG.error("Client Register Failed, Received Wrong Message: %s", data)
        except Exception as e:
            LOG.exception(e)

    def update_storage_info(self, data):
        usage = disk_usage()
        data.update({"storage_full": self.config.get("storage_preserve_space") > usage["free"]})
        data.update({"storage_preserve_space": size_pretty(self.config.get("storage_preserve_space"))})
        data.update({"storage_disk_total": size_pretty(usage["total"])})
        data.update({"storage_disk_used": size_pretty(usage["used"])})
        data.update({"storage_disk_free": size_pretty(usage["free"])})
        data.update({"storage_disk_percent": "%s%%" % usage["percent"]})

    @gen.coroutine
    def heartbeat_service(self):
        try:
            message_data = self.config.to_dict()
            message_data.update(self.heartbeat_data)
            message_data.update({"task_queue_full": TaskCache.full()})
            self.update_storage_info(message_data)
            data = {"command": Command.heartbeat, "data": message_data}
            self.send_message(data)
            data = yield self.read_message()
            if data["data"]["status"] == Status.success:
                if "data_nodes" in data["data"]:
                    self.data_nodes = data["data"]["data_nodes"]
                if "task" in data["data"]:
                    task = data["data"]["task"]
                    TaskCache.push(task)
                LOG.debug("Client Received Heartbeat Message: %s", data["data"])
            else:
                LOG.error("Client Received Heartbeat Message: %s", data["data"])
        except Exception as e:
            LOG.exception(e)
