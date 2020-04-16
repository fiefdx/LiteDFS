# -*- coding: UTF-8 -*-

import os
import re
import sys
import json
import time
import argparse
import logging
import random
from io import BytesIO

import requests

LOG = logging.getLogger(__name__)


class LiteDFSClient(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_url = "http://%s:%s" % (self.host, self.port)

    def create_file(self, local_path, remote_path, replica = 1):
        result = False
        try:
            if os.path.exists(local_path) and os.path.isfile(local_path):
                success = True
                file_size = os.stat(local_path).st_size
                block_list_url = "%s/file/block/list?size=%s&replica=%s" % (self.base_url, file_size, replica)
                r = requests.get(block_list_url)
                if r.status_code == 200:
                    data = r.json()
                    if "result" in data and data["result"] == "ok":
                        data_nodes = data["data_nodes"]
                        fp = open(local_path, "rb")
                        for block in data["blocks"]:
                            block_id = block[0]
                            block_size = block[1]
                            block_content = BytesIO()
                            block_content.write(fp.read(block_size))
                            node_id = block[2][0]
                            node_ids = ",".join([str(b) for b in block[2][1:]])
                            data_node = data_nodes[str(node_id)]
                            block_create_url = "http://%s:%s/block/create" % (data_node[0], data_node[1])
                            block_content.seek(0)
                            files = {'up_file': ("up_file", block_content, b"text/plain")}
                            values = {"name": data["id"], "block": block_id, "ids": node_ids}
                            r = requests.post(block_create_url, files = files, data = values)
                            if r.status_code == 200:
                                d = r.json()
                                if "result" in d and d["result"] != "ok":
                                    LOG.error("create block failed: %s", d)
                                    success = False
                                    break
                            if not success:
                                break
                        fp.close()
                        if success:
                            json_data = {
                                "size": file_size,
                                "path": remote_path,
                                "id": data["id"],
                                "replica": replica,
                                "blocks": data["blocks"],
                            }
                            r = requests.post("%s/file/create" % self.base_url, json = json_data)
                            if r.status_code == 200:
                                d = r.json()
                                if "result" in d and d["result"] == "ok":
                                    result = True
                                else:
                                    LOG.error("create file[%s] failed: %s", remote_path, d["result"])
                            else:
                                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
                        else:
                            LOG.error("create file[%s] failed", remote_path)
                    else:
                        LOG.error("create file[%s] failed: %s", remote_path, data["result"])
                else:
                    LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
            else:
                LOG.error("file[%s] not exists", local_path)
        except Exception as e:
            LOG.exception(e)
        return result

    def delete_file(self, remote_path):
        result = False
        try:
            url = "%s/file/delete?path=%s" % (self.base_url, remote_path)
            r = requests.delete(url)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("delete file[%s] failed: %s", remote_path, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def move_file(self, source_path, target_path):
        result = False
        try:
            url = "%s/file/move" % self.base_url
            json_data = {"source_path": source_path, "target_path": target_path}
            r = requests.put(url, json = json_data)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("move file[%s] to %s failed: %s", source_path, target_path, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def rename_file(self, remote_path, new_name):
        result = False
        try:
            url = "%s/file/rename" % self.base_url
            json_data = {"path": remote_path, "new_name": new_name}
            r = requests.put(url, json = json_data)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("rename file[%s] to %s failed: %s", remote_path, new_name, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def update_file(self, remote_path, replica):
        result = False
        try:
            url = "%s/file/update" % self.base_url
            json_data = {"path": remote_path, "replica": replica}
            r = requests.put(url, json = json_data)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("update file[%s] replica to %s failed: %s", remote_path, replica, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def download_file(self, remote_path, local_path):
        result = False
        try:
            if not os.path.exists(local_path):
                success = True
                block_info_url = "%s/file/block/info?path=%s" % (self.base_url, remote_path)
                r = requests.get(block_info_url)
                if r.status_code == 200:
                    data = r.json()
                    if "result" in data and data["result"] == "ok":
                        data_nodes = {}
                        for node_id in data["data_nodes"]:
                            data_nodes[int(node_id)] = data["data_nodes"][node_id]
                        file_info = data["file_info"]
                        fp = open(local_path, "wb")
                        for block in file_info["blocks"]:
                            block_id = block[0]
                            block_size = block[1]
                            node_ids = block[2]
                            exists_ids = list(set(node_ids).intersection(set(data_nodes.keys())))
                            if exists_ids:
                                node_id = random.choice(exists_ids)
                                data_node = data_nodes[node_id]
                                block_download_url = "http://%s:%s/block/download?name=%s&block=%s" % (data_node[0], data_node[1], file_info["id"], block_id)
                                r = requests.get(block_download_url)
                                if r.status_code == 200:
                                    fp.write(r.content)
                                else:
                                    LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
                                    success = False
                                    break
                            else:
                                LOG.error("not enough data nodes online")
                                success = False
                                break
                        fp.close()
                        if success:
                            result = True
                        else:
                            LOG.error("download file[%s => %s] failed", remote_path, local_path)
                    else:
                        LOG.error("download file[%s] failed: %s", remote_path, data["result"])
                else:
                    LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
            else:
                LOG.error("local file[%s] already exists", local_path)
        except Exception as e:
            LOG.exception(e)
        return result

    def info_file(self, remote_path):
        result = False
        try:
            block_info_url = "%s/file/block/info?path=%s" % (self.base_url, remote_path)
            r = requests.get(block_info_url)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = data
                else:
                    LOG.error("get file[%s]'s info failed: %s", remote_path, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def create_directory(self, remote_path):
        result = False
        try:
            url = "%s/directory/create" % self.base_url
            json_data = {"path": remote_path}
            r = requests.post(url, json = json_data)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("create directory[%s] failed: %s", remote_path, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def delete_directory(self, remote_path):
        result = False
        try:
            url = "%s/directory/delete?path=%s" % (self.base_url, remote_path)
            r = requests.delete(url)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("delete directory[%s] failed: %s", remote_path, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def move_directory(self, source_path, target_path):
        result = False
        try:
            url = "%s/directory/move" % self.base_url
            json_data = {"source_path": source_path, "target_path": target_path}
            r = requests.put(url, json = json_data)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("move directory[%s] to %s failed: %s", source_path, target_path, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def rename_directory(self, remote_path, new_name):
        result = False
        try:
            url = "%s/directory/rename" % self.base_url
            json_data = {"path": remote_path, "new_name": new_name}
            r = requests.put(url, json = json_data)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = True
                else:
                    LOG.error("rename directory[%s] to %s failed: %s", remote_path, new_name, data["result"])
            else:
                LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
        except Exception as e:
            LOG.exception(e)
        return result

    def list_directory(self, remote_path):
        result = False
        try:
            url = "%s/directory/list?path=%s" % (self.base_url, remote_path)
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    result = data
                else:
                    print("list directory[%s] failed: %s" % (remote_path, data["result"]))
            else:
                print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        except Exception as e:
            LOG.exception(e)
        return result
