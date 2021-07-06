# -*- coding: UTF-8 -*-

import os
import re
import sys
import json
import time
import hashlib
import argparse
import logging
import random
import urllib.parse
from io import BytesIO

import requests

from litedfs_client.version import __version__

LOG = logging.getLogger(__name__)

BUF_SIZE = 65536

USER_AGENT = "python-litedfs-client"


class OperationFailedError(Exception):
    def __init__(self, message):
        self.message = message


def file_md5sum(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as fp:
        while True:
            data = fp.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def bytes_io_md5sum(fp):
    md5 = hashlib.md5()
    while True:
        data = fp.read(BUF_SIZE)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()


def bytes_md5sum(b):
    md5 = hashlib.md5()
    md5.update(b)
    return md5.hexdigest()


def strings_md5sum(l):
    md5 = hashlib.md5()
    for s in l:
        if s:
            md5.update(s.encode("utf-8"))
    return md5.hexdigest()


class RemoteFile(object):
    def __init__(self, host, port, remote_path, file_info):
        self.host = host
        self.port = port
        self.remote_path = remote_path
        self.base_url = "http://%s:%s" % (self.host, self.port)
        self.headers = {"user-agent": "%s/%s" % (USER_AGENT, __version__)}
        self.file_info = file_info["file_info"]
        self.data_nodes = {}
        for key in file_info["data_nodes"]:
            self.data_nodes[int(key)] = file_info["data_nodes"][key]
        self.file_size = self.file_info["size"]
        self.blocks = self.file_info["blocks"]
        self.file_id = self.file_info["id"]
        self.block_size = file_info["block_size"]
        self.pos = 0
        self.closed = False

    def read(self, size = -1):
        result = b""
        if size != -1:
            if size <= 0:
                return result
            elif size > 0 and self.pos + size < self.file_size:
                blocks = self.blocks_range(self.pos, size)
                for block in blocks:
                    r = self.block_range_read(block[0], block[1], block[2])
                    if r:
                        result += r
                    else:
                        raise
                self.pos = self.pos + size
            else:
                blocks = self.blocks_range(self.pos, self.file_size - self.pos)
                for block in blocks:
                    r = self.block_range_read(block[0], block[1], block[2])
                    if r:
                        result += r
                    else:
                        raise
                self.pos = self.file_size
        else:
            blocks = self.blocks_range(self.pos, self.file_size - self.pos)
            for block in blocks:
                r = self.block_range_read(block[0], block[1], block[2])
                if r:
                    result += r
                else:
                    raise
            self.pos = self.file_size
        return result

    def readall(self):
        return self.read()

    def block_range_read(self, block_id, offset, size):
        result = False
        block = self.blocks[block_id]

        node_ids = block[2]
        block_md5 = block[3]

        exists_ids = list(set(node_ids).intersection(set(self.data_nodes.keys())))
        if exists_ids:
            exists_ids_random = random.sample(exists_ids, len(exists_ids))
            block_success = False
            for node_id in exists_ids_random:
                data_node = self.data_nodes[node_id]
                block_read_url = "http://%s:%s/block/read?name=%s&block=%s&offset=%s&size=%s&md5=%s" % (data_node[0], data_node[1], self.file_id, block_id, offset, size, block_md5)
                r = requests.get(block_read_url, headers = self.headers)
                if r.status_code == 200:
                    result = r.content
                    block_success = True
                    break
                elif r.status_code == 400:
                    data = r.json()
                    LOG.error("error: %s", data["result"])
                    continue
                else:
                    LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
                    block_success = False
                    continue
            if not block_success:
                raise OperationFailedError("read block failed from: %s" % exists_ids_random)
        else:
            raise OperationFailedError("not enough data nodes online")
        return result

    def blocks_range(self, offset, size):
        result = []
        start_index = offset // self.block_size
        start_offset = offset % self.block_size
        while size > 0:
            block_read_size = size
            if start_offset + block_read_size > self.block_size:
                block_read_size = self.block_size - start_offset
            result.append([start_index, start_offset, block_read_size])
            start_index += 1
            size -= block_read_size
            start_offset = 0
        return result

    def seek(self, offset, whence = 0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        elif whence == 2:
            self.pos = self.file_size + offset
        if self.pos < 0:
            self.pos = 0
        if self.pos > self.file_size:
            self.pos = self.file_size

    def readinto(self, b):
        content = self.read(len(b))
        b[:len(content)] = content
        return len(content)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def flush(self):
        pass

    def close(self):
        self.closed = True


class LiteDFSClient(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_url = "http://%s:%s" % (self.host, self.port)
        self.headers = {"user-agent": "%s/%s" % (USER_AGENT, __version__)}

    def create_file(self, local_path, remote_path, replica = 1, lock_ttl = 60):
        result = False
        if os.path.exists(local_path) and os.path.isfile(local_path):
            success = True
            file_size = os.stat(local_path).st_size
            block_list_url = "%s/file/block/list?size=%s&replica=%s&path=%s&lock_ttl=%s" % (self.base_url, file_size, replica, urllib.parse.quote(remote_path), lock_ttl)
            r = requests.get(block_list_url, headers = self.headers)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    data_nodes = data["data_nodes"]
                    fp = open(local_path, "rb")
                    blocks_md5 = []
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
                        block_md5 = bytes_io_md5sum(block_content)
                        block.append(block_md5)
                        blocks_md5.append(block_md5)
                        block_content.seek(0)
                        files = {'up_file': ("up_file", block_content, b"text/plain")}
                        values = {"name": data["id"], "block": block_id, "ids": node_ids}
                        r = requests.post(block_create_url, headers = self.headers, files = files, data = values)
                        if r.status_code == 200:
                            update_file_lock_url = "%s/file/lock/update" % self.base_url
                            json_data = {"path": remote_path, "lock_ttl": lock_ttl}
                            rr = requests.put(update_file_lock_url, headers = self.headers, json = json_data)
                            if rr.status_code == 200:
                                dd = rr.json()
                                if "result" not in dd or dd["result"] != "ok":
                                    raise OperationFailedError("update file[%s] lock ttl[%s] failed: %s" % (remote_path, lock_ttl, dd["result"]))
                            else:
                                raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (rr.status_code, rr.content))

                            d = r.json()
                            if "result" in d and d["result"] != "ok":
                                LOG.error("create block failed: %s", d)
                                success = False
                                break
                            elif "md5" in d and d["md5"] != block_md5:
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
                            "checksum": strings_md5sum(blocks_md5),
                        }
                        r = requests.post("%s/file/create" % self.base_url, headers = self.headers, json = json_data)
                        if r.status_code == 200:
                            d = r.json()
                            if "result" in d and d["result"] == "ok":
                                result = True
                            else:
                                raise OperationFailedError("create file[%s] failed: %s" % (remote_path, d["result"]))
                        else:
                            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                    else:
                        raise OperationFailedError("create file[%s] failed" % remote_path)
                else:
                    raise OperationFailedError("create file[%s] failed: %s" % (remote_path, data["result"]))
            else:
                raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        else:
            raise OperationFailedError("file[%s] not exists" % local_path)
        return result

    def create_file_by_content(self, content, remote_path, replica = 1, lock_ttl = 60):
        result = False
        fp = None
        if isinstance(content, bytes):
            fp = BytesIO(content)
        elif isinstance(content, str):
            fp = BytesIO(content.encode("utf-8"))
        elif hasattr(content, "read"):
            fp = content
        if fp:
            success = True
            fp.seek(0, 2)
            file_size = fp.tell()
            fp.seek(0)
            block_list_url = "%s/file/block/list?size=%s&replica=%s&path=%s&lock_ttl=%s" % (self.base_url, file_size, replica, urllib.parse.quote(remote_path), lock_ttl)
            r = requests.get(block_list_url, headers = self.headers)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    data_nodes = data["data_nodes"]
                    blocks_md5 = []
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
                        block_md5 = bytes_io_md5sum(block_content)
                        block.append(block_md5)
                        blocks_md5.append(block_md5)
                        block_content.seek(0)
                        files = {'up_file': ("up_file", block_content, b"text/plain")}
                        values = {"name": data["id"], "block": block_id, "ids": node_ids}
                        r = requests.post(block_create_url, headers = self.headers, files = files, data = values)
                        if r.status_code == 200:
                            update_file_lock_url = "%s/file/lock/update" % self.base_url
                            json_data = {"path": remote_path, "lock_ttl": lock_ttl}
                            rr = requests.put(update_file_lock_url, headers = self.headers, json = json_data)
                            if rr.status_code == 200:
                                dd = rr.json()
                                if "result" not in dd or dd["result"] != "ok":
                                    raise OperationFailedError("update file[%s] lock ttl[%s] failed: %s" % (remote_path, lock_ttl, dd["result"]))
                            else:
                                raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (rr.status_code, rr.content))

                            d = r.json()
                            if "result" in d and d["result"] != "ok":
                                LOG.error("create block failed: %s", d)
                                success = False
                                break
                            elif "md5" in d and d["md5"] != block_md5:
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
                            "checksum": strings_md5sum(blocks_md5),
                        }
                        r = requests.post("%s/file/create" % self.base_url, headers = self.headers, json = json_data)
                        if r.status_code == 200:
                            d = r.json()
                            if "result" in d and d["result"] == "ok":
                                result = True
                            else:
                                raise OperationFailedError("create file[%s] failed: %s" % (remote_path, d["result"]))
                        else:
                            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                    else:
                        raise OperationFailedError("create file[%s] failed" % remote_path)
                else:
                    raise OperationFailedError("create file[%s] failed: %s" % (remote_path, data["result"]))
            else:
                raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        else:
            raise OperationFailedError("not support content parameter: %s" % content)
        return result

    def delete_file(self, remote_path):
        result = False
        url = "%s/file/delete?path=%s" % (self.base_url, urllib.parse.quote(remote_path))
        r = requests.delete(url, headers = self.headers)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("delete file[%s] failed: %s" % (remote_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def move_file(self, source_path, target_path):
        result = False
        url = "%s/file/move" % self.base_url
        json_data = {"source_path": source_path, "target_path": target_path}
        r = requests.put(url, headers = self.headers, json = json_data)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("move file[%s] to %s failed: %s" % (source_path, target_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def rename_file(self, remote_path, new_name):
        result = False
        url = "%s/file/rename" % self.base_url
        json_data = {"path": remote_path, "new_name": new_name}
        r = requests.put(url, headers = self.headers, json = json_data)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("rename file[%s] to %s failed: %s" % (remote_path, new_name, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def update_file(self, remote_path, replica):
        result = False
        url = "%s/file/update" % self.base_url
        json_data = {"path": remote_path, "replica": replica}
        r = requests.put(url, headers = self.headers, json = json_data)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("update file[%s] replica to %s failed: %s" % (remote_path, replica, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def download_file(self, remote_path, local_path):
        result = False
        if not os.path.exists(local_path):
            success = True
            block_info_url = "%s/file/block/info?path=%s" % (self.base_url, urllib.parse.quote(remote_path))
            r = requests.get(block_info_url, headers = self.headers)
            if r.status_code == 200:
                data = r.json()
                if "result" in data and data["result"] == "ok":
                    data_nodes = {}
                    for node_id in data["data_nodes"]:
                        data_nodes[int(node_id)] = data["data_nodes"][node_id]
                    file_info = data["file_info"]
                    fp = open(local_path, "wb")
                    blocks_md5 = []
                    for block in file_info["blocks"]:
                        block_id = block[0]
                        block_size = block[1]
                        node_ids = block[2]
                        block_md5 = block[3]
                        exists_ids = list(set(node_ids).intersection(set(data_nodes.keys())))
                        if exists_ids:
                            exists_ids_random = random.sample(exists_ids, len(exists_ids))
                            block_success = False
                            for node_id in exists_ids_random:
                                data_node = data_nodes[node_id]
                                block_download_url = "http://%s:%s/block/download?name=%s&block=%s" % (data_node[0], data_node[1], file_info["id"], block_id)
                                r = requests.get(block_download_url, headers = self.headers)
                                if r.status_code == 200:
                                    response_md5 = bytes_md5sum(r.content)
                                    if response_md5 == block_md5:
                                        blocks_md5.append(response_md5)
                                        fp.write(r.content)
                                        block_success = True
                                        break
                                    else:
                                        LOG.error("checksum not equal, need %s, get %s", block_md5, response_md5)
                                        block_success = False
                                        continue
                                else:
                                    LOG.error("error:\ncode: %s\ncontent: %s", r.status_code, r.content)
                                    block_success = False
                                    continue
                            if not block_success:
                                raise OperationFailedError("read block failed from: %s" % exists_ids_random)
                                success = False
                                break
                        else:
                            raise OperationFailedError("not enough data nodes online")
                            success = False
                            break
                    if success:
                        fp.close()
                        checksum = strings_md5sum(blocks_md5)
                        if file_info["checksum"] == checksum:
                            result = True
                        else:
                            raise OperationFailedError("download file[%s => %s] failed, checksum not equal: %s" % (remote_path, local_path, checksum))
                    else:
                        raise OperationFailedError("download file[%s => %s] failed" % (remote_path, local_path))
                else:
                    raise OperationFailedError("download file[%s] failed: %s" % (remote_path, data["result"]))
            else:
                raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        else:
            raise OperationFailedError("local file[%s] already exists" % local_path)
        return result

    def open_remote_file(self, remote_path):
        result = False
        info = self.info_file(remote_path)
        if info:
            result = RemoteFile(self.host, self.port, remote_path, info)
        return result

    def info_file(self, remote_path):
        result = False
        block_info_url = "%s/file/block/info?path=%s" % (self.base_url, urllib.parse.quote(remote_path))
        r = requests.get(block_info_url, headers = self.headers)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = data
            else:
                raise OperationFailedError("get file[%s]'s info failed: %s" % (remote_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def create_directory(self, remote_path):
        result = False
        url = "%s/directory/create" % self.base_url
        json_data = {"path": remote_path}
        r = requests.post(url, headers = self.headers, json = json_data)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("create directory[%s] failed: %s" % (remote_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def delete_directory(self, remote_path):
        result = False
        url = "%s/directory/delete?path=%s" % (self.base_url, urllib.parse.quote(remote_path))
        r = requests.delete(url, headers = self.headers)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("delete directory[%s] failed: %s" % (remote_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def move_directory(self, source_path, target_path):
        result = False
        url = "%s/directory/move" % self.base_url
        json_data = {"source_path": source_path, "target_path": target_path}
        r = requests.put(url, headers = self.headers, json = json_data)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("move directory[%s] to %s failed: %s" % (source_path, target_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def rename_directory(self, remote_path, new_name):
        result = False
        url = "%s/directory/rename" % self.base_url
        json_data = {"path": remote_path, "new_name": new_name}
        r = requests.put(url, headers = self.headers, json = json_data)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = True
            else:
                raise OperationFailedError("rename directory[%s] to %s failed: %s" % (remote_path, new_name, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result

    def list_directory(self, remote_path, offset = 0, limit = 0, include_file = True, include_directory = True):
        result = False
        url = "%s/directory/list?path=%s&offset=%s&limit=%s" % (self.base_url, urllib.parse.quote(remote_path), offset, limit)
        url += "&include_file=%s" % ("true" if include_file else "false")
        url += "&include_directory=%s" % ("true" if include_directory else "false")
        r = requests.get(url, headers = self.headers)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = data
            else:
                raise OperationFailedError("list directory[%s] failed: %s" % (remote_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result


    def info_path(self, remote_path):
        result = False
        url = "%s/path/info?path=%s" % (self.base_url, urllib.parse.quote(remote_path))
        r = requests.get(url, headers = self.headers)
        if r.status_code == 200:
            data = r.json()
            if "result" in data and data["result"] == "ok":
                result = data
            else:
                raise OperationFailedError("info path[%s] failed: %s" % (remote_path, data["result"]))
        else:
            raise OperationFailedError("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        return result
