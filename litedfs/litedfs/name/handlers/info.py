# -*- coding: utf-8 -*-

import json
import time
import logging

from tornado import web
from tornado import gen

from litedfs.name.handlers.base import BaseHandler, BaseSocketHandler
from litedfs.name.models.data_nodes import DataNodes
from litedfs.name.utils.listener import Connection
from litedfs.name.utils.common import Errors, list_sort
from litedfs.version import __version__
from litedfs.name.config import CONFIG

LOG = logging.getLogger("__name__")


class AboutHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"message": "LiteDFS name service"}
        self.write(result)
        self.finish()


class ClusterInfoHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        result = {"result": Errors.OK, "version": __version__}
        try:
            info = {
                "number_of_nodes": 0,
                "number_of_online_nodes": 0,
                "number_of_offline_nodes": 0,
                "online_nodes": [],
                "offline_nodes": [],
            }
            for node in Connection.clients:
                node.info["id"] = Connection.id_compress[node.info["node_id"]]
                info["online_nodes"].append(node.info)
                info["number_of_nodes"] += 1
                info["number_of_online_nodes"] += 1
            info["online_nodes"] = list_sort(info["online_nodes"], "id")
            nodes_info = DataNodes.instance().list()
            for node in nodes_info["data_nodes"]:
                if node["node_id"] not in Connection.clients_dict:
                    node["info"]["id"] = node["id"]
                    info["offline_nodes"].append(node["info"])
                    info["number_of_offline_nodes"] += 1
            info["offline_nodes"] = list_sort(info["offline_nodes"], "id")
            result["info"] = info
        except Exception as e:
            LOG.exception(e)
            Errors.set_result_error("ServerException", result)
        self.write(json.dumps(result, sort_keys = True))
        self.finish()
