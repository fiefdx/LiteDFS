#!/usr/bin/env python3
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

from litedfs.version import __version__

parser = argparse.ArgumentParser(prog = 'litedfs')

# common arguments
parser.add_argument("address", help = "name node address, host:port")
parser.add_argument("-w", "--column_width", help = "column max width", type = int, default = 0)
parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)
subparsers = parser.add_subparsers(dest = "object", help = 'sub-command help')

# operate with file
parser_file = subparsers.add_parser("file", help = "operate with file API")
subparsers_file = parser_file.add_subparsers(dest = "operation", help = 'sub-command file help')

parser_file_create = subparsers_file.add_parser("create", help = "create file")
parser_file_create.add_argument("-l", "--local-path", required = True, help = "local file path", default = "")
parser_file_create.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
parser_file_create.add_argument("-R", "--replica", help = "replica count", type = int, default = 1)

parser_file_delete = subparsers_file.add_parser("delete", help = "delete file")
parser_file_delete.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")

parser_file_move = subparsers_file.add_parser("move", help = "move file")
parser_file_move.add_argument("-s", "--source-path", required = True, help = "source file path", default = "")
parser_file_move.add_argument("-t", "--target-path", required = True, help = "target directory path", default = "")

parser_file_rename = subparsers_file.add_parser("rename", help = "rename file")
parser_file_rename.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
parser_file_rename.add_argument("-n", "--new-name", required = True, help = "new file name", default = "")

parser_file_update = subparsers_file.add_parser("update", help = "update file")
parser_file_update.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
parser_file_update.add_argument("-R", "--replica", required = True, help = "replica count", type = int, default = 1)

parser_file_download = subparsers_file.add_parser("download", help = "download file")
parser_file_download.add_argument("-l", "--local-path", required = True, help = "local file path", default = "")
parser_file_download.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")

parser_file_info = subparsers_file.add_parser("info", help = "get file's info")
parser_file_info.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")

# operate with directory
parser_directory = subparsers.add_parser("directory", help = "operate with directory API")
subparsers_directory = parser_directory.add_subparsers(dest = "operation", help = 'sub-command file help')

parser_directory_create = subparsers_directory.add_parser("create", help = "create directory")
parser_directory_create.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")

parser_directory_delete = subparsers_directory.add_parser("delete", help = "delete directory")
parser_directory_delete.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")

parser_directory_move = subparsers_directory.add_parser("move", help = "move directory")
parser_directory_move.add_argument("-s", "--source-path", required = True, help = "source directory path", default = "")
parser_directory_move.add_argument("-t", "--target-path", required = True, help = "target directory path", default = "")

parser_directory_rename = subparsers_directory.add_parser("rename", help = "rename directory")
parser_directory_rename.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")
parser_directory_rename.add_argument("-n", "--new-name", required = True, help = "new directory name", default = "")

parser_directory_list = subparsers_directory.add_parser("list", help = "list directory's children")
parser_directory_list.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")

# operate with cluster
parser_cluster = subparsers.add_parser("cluster", help = "operate with cluster API")
subparsers_cluster = parser_cluster.add_subparsers(dest = "operation", help = 'sub-command cluster help')

parser_cluster_info = subparsers_cluster.add_parser("info", help = "cluster's info")
parser_cluster_info.add_argument("-r", "--raw", help = "display raw json data", action = "store_true")

args = parser.parse_args()


def print_table_result(data, fields):
    fields.insert(0, "#")
    field_length_map = {}
    lines = []
    num = 1
    column_max_width = args.column_width
    for field in fields:
        field_length_map[field] = len(field)
    for item in data:
        line = []
        for field in fields:
            if field == "#":
                line.append(str(num))
            else:
                v = str(item[field]) if field in item else ""
                v_len = len(v)
                if column_max_width > 0 and v_len > column_max_width:
                    v_len = column_max_width
                    v = v[:v_len]
                if v_len > field_length_map[field]:
                    field_length_map[field] = v_len
                line.append(v)
        lines.append(tuple(line))
        num += 1
    field_length_map["#"] = len(str(num))
    format_str = ""
    for field in fields:
        field_len = field_length_map[field]
        if field == "#":
            format_str += "%" + " %s" % field_len + "s | "
        else:
            format_str += "%" + "-%s" % field_len + "s | "
    format_str = format_str[:-3]
    print(format_str % tuple(fields))
    for line in lines:
        print(format_str % line)


def main():
    try:
        address = args.address
        object = args.object
        operation = args.operation
        url = "http://%s/%s/%s" % (address, object, operation)
        if address:
            if object == "file":
                if operation == "create":
                    if os.path.exists(args.local_path) and os.path.isfile(args.local_path):
                        success = True
                        file_size = os.stat(args.local_path).st_size
                        block_list_url = "http://%s/file/block/list?size=%s&replica=%s" % (address, file_size, args.replica)
                        r = requests.get(block_list_url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                data_nodes = data["data_nodes"]
                                fp = open(args.local_path, "rb")
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
                                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                                            success = False
                                            break
                                    if not success:
                                        break
                                fp.close()
                                if success:
                                    json_data = {
                                        "size": file_size,
                                        "path": args.remote_path,
                                        "id": data["id"],
                                        "replica": args.replica,
                                        "blocks": data["blocks"],
                                    }
                                    r = requests.post(url, json = json_data)
                                    if r.status_code == 200:
                                        d = r.json()
                                        if "result" in d and d["result"] == "ok":
                                            print("create file[%s] success" % args.remote_path)
                                        else:
                                            print("create file[%s] failed: %s" % (args.remote_path, d["result"]))
                                    else:
                                        print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                                else:
                                    print("create file[%s] failed" % args.remote_path)
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                    else:
                        print("file[%s] not exists" % args.local_path)
                elif operation == "delete":
                    if args.remote_path:
                        url += "?path=%s" % args.remote_path
                        r = requests.delete(url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("delete file[%s] success" % args.remote_path)
                            else:
                                print("delete file[%s] failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "move":
                    if args.source_path and args.target_path:
                        json_data = {"source_path": args.source_path, "target_path": args.target_path}
                        r = requests.put(url, json = json_data)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("move file[%s] to %s success" % (args.source_path, args.target_path))
                            else:
                                print("move file[%s] to %s failed: %s" % (args.source_path, args.target_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "rename":
                    if args.remote_path and args.new_name:
                        json_data = {"path": args.remote_path, "new_name": args.new_name}
                        r = requests.put(url, json = json_data)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("rename file[%s] to %s success" % (args.remote_path, args.new_name))
                            else:
                                print("rename file[%s] to %s failed: %s" % (args.remote_path, args.new_name, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "update":
                    if args.remote_path and args.replica:
                        json_data = {"path": args.remote_path, "replica": args.replica}
                        r = requests.put(url, json = json_data)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("update file[%s] success" % args.remote_path)
                            else:
                                print("update file[%s] failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "download":
                    if not os.path.exists(args.local_path):
                        success = True
                        block_info_url = "http://%s/file/block/info?path=%s" % (address, args.remote_path)
                        r = requests.get(block_info_url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                data_nodes = {}
                                for node_id in data["data_nodes"]:
                                    data_nodes[int(node_id)] = data["data_nodes"][node_id]
                                file_info = data["file_info"]
                                fp = open(args.local_path, "wb")
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
                                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                                            success = False
                                            break
                                    else:
                                        print("not enough data nodes online")
                                        success = False
                                        break
                                if success:
                                    fp.close()
                                    print("download file[%s => %s] success" % (args.remote_path, args.local_path))
                                else:
                                    print("download file[%s => %s] failed" % (args.remote_path, args.local_path))
                            else:
                                print("download file[%s] failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                    else:
                        print("local file[%s] already exists" % args.local_path)
                elif operation == "info":
                    if args.remote_path:
                        block_info_url = "http://%s/file/block/info?path=%s" % (address, args.remote_path)
                        r = requests.get(block_info_url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print(json.dumps(data, indent = 4, sort_keys = True))
                            else:
                                print("get file[%s]'s info failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
            elif object == "directory":
                if operation == "create":
                    if args.remote_path:
                        json_data = {"path": args.remote_path}
                        r = requests.post(url, json = json_data)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("create directory[%s] success" % args.remote_path)
                            else:
                                print("create directory[%s] failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "delete":
                    if args.remote_path:
                        url += "?path=%s" % args.remote_path
                        r = requests.delete(url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("delete directory[%s] success" % args.remote_path)
                            else:
                                print("delete directory[%s] failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "move":
                    if args.source_path and args.target_path:
                        json_data = {"source_path": args.source_path, "target_path": args.target_path}
                        r = requests.put(url, json = json_data)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("move directory[%s] to %s success" % (args.source_path, args.target_path))
                            else:
                                print("move directory[%s] to %s failed: %s" % (args.source_path, args.target_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "rename":
                    if args.remote_path and args.new_name:
                        json_data = {"path": args.remote_path, "new_name": args.new_name}
                        r = requests.put(url, json = json_data)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print("rename directory[%s] to %s success" % (args.remote_path, args.new_name))
                            else:
                                print("rename directory[%s] to %s failed: %s" % (args.remote_path, args.new_name, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                elif operation == "list":
                    if args.remote_path:
                        url += "?path=%s" % args.remote_path
                        r = requests.get(url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                print_table_result(
                                    data["children"],
                                    ["id", "type", "size", "name"]
                                )
                            else:
                                print("list directory[%s] failed: %s" % (args.remote_path, data["result"]))
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
            elif object == "cluster":
                if operation == "info":
                    r = requests.get(url)
                    if r.status_code == 200:
                        data = r.json()
                        if args.raw:
                            print(json.dumps(data, indent = 4, sort_keys = True))
                        else:
                            if data["result"] == "ok":
                                print("online nodes:")
                                print_table_result(
                                    data["info"]["online_nodes"],
                                    [
                                        "id",
                                        "node_id",
                                        "http_host",
                                        "http_port",
                                        "data_path",
                                    ]
                                )
                                print("\noffline nodes:")
                                print_table_result(
                                    data["info"]["offline_nodes"],
                                    [
                                        "id",
                                        "node_id",
                                        "http_host",
                                        "http_port",
                                        "data_path",
                                    ]
                                )
                            else:
                                print_table_result(
                                    [data],
                                    ["result", "message"]
                                )
                    else:
                        print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                        
    except Exception as e:
        logging.error(logging.traceback.format_exc())


if __name__ == "__main__":
    main()
