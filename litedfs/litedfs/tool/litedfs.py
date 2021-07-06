#!/usr/bin/env python3
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
from io import BytesIO

import requests

from litedfs.version import __version__
from litedfs_client.client import LiteDFSClient


BUF_SIZE = 65536


def print_table_result(data, fields, args):
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


def main():
    parser = argparse.ArgumentParser(prog = 'ldfs')

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
    parser_directory_list.add_argument("-o", "--offset", help = "list offset", type = int, default = 0)
    parser_directory_list.add_argument("-l", "--limit", help = "list limit", type = int, default = 0)
    parser_directory_list.add_argument("-f", "--exclude-file", help = "exclude file", action = "store_false")
    parser_directory_list.add_argument("-d", "--exclude-directory", help = "exclude directory", action = "store_false")

    # operate with cluster
    parser_cluster = subparsers.add_parser("cluster", help = "operate with cluster API")
    subparsers_cluster = parser_cluster.add_subparsers(dest = "operation", help = 'sub-command cluster help')

    parser_cluster_info = subparsers_cluster.add_parser("info", help = "cluster's info")
    parser_cluster_info.add_argument("-r", "--raw", help = "display raw json data", action = "store_true")

    # operate with path(file or directory)
    parser_path = subparsers.add_parser("path", help = "operate with path API")
    subparsers_path = parser_path.add_subparsers(dest = "operation", help = 'sub-command path help')

    parser_path_info = subparsers_path.add_parser("info", help = "get path's info")
    parser_path_info.add_argument("-r", "--remote-path", required = True, help = "remote file/directory path", default = "")

    args = parser.parse_args()

    try:
        address = args.address
        object = args.object
        operation = args.operation
        url = "http://%s/%s/%s" % (address, object, operation)
        if address:
            host, port = address.split(":")
            ldfs = LiteDFSClient(host, port)
            if object == "file":
                if operation == "create":
                    try:
                        r = ldfs.create_file(args.local_path, args.remote_path, replica = args.replica)
                        if r:
                            print("create file[%s] success" % args.remote_path)
                        else:
                            print("create file[%s] failed" % args.remote_path)
                    except Exception as e:
                        print(e)
                elif operation == "delete":
                    if args.remote_path:
                        try:
                            r = ldfs.delete_file(args.remote_path)
                            if r:
                                print("delete file[%s] success" % args.remote_path)
                            else:
                                print("delete file[%s] failed" % args.remote_path)
                        except Exception as e:
                            print(e)
                elif operation == "move":
                    if args.source_path and args.target_path:
                        try:
                            r = ldfs.move_file(args.source_path, args.target_path)
                            if r:
                                print("move file[%s] to %s success" % (args.source_path, args.target_path))
                            else:
                                print("move file[%s] to %s failed" % (args.source_path, args.target_path))
                        except Exception as e:
                            print(e)
                elif operation == "rename":
                    if args.remote_path and args.new_name:
                        try:
                            r = ldfs.rename_file(args.remote_path, args.new_name)
                            if r:
                                print("rename file[%s] to %s success" % (args.remote_path, args.new_name))
                            else:
                                print("rename file[%s] to %s failed" % (args.remote_path, args.new_name))
                        except Exception as e:
                            print(e)
                elif operation == "update":
                    if args.remote_path and args.replica:
                        try:
                            r = ldfs.update_file(args.remote_path, args.replica)
                            if r:
                                print("update file[%s] success" % args.remote_path)
                            else:
                                print("update file[%s] failed" % args.remote_path)
                        except Exception as e:
                            print(e)
                elif operation == "download":
                    try:
                        r = ldfs.download_file(args.remote_path, args.local_path)
                        if r:
                            print("download file[%s => %s] success" % (args.remote_path, args.local_path))
                        else:
                            print("download file[%s => %s] failed" % (args.remote_path, args.local_path))
                    except Exception as e:
                        print(e)
                elif operation == "info":
                    if args.remote_path:
                        try:
                            r = ldfs.info_file(args.remote_path)
                            if r:
                                print(json.dumps(r, indent = 4, sort_keys = True))
                            else:
                                print("get file[%s]'s info failed" % args.remote_path)
                        except Exception as e:
                            print(e)
            elif object == "directory":
                if operation == "create":
                    if args.remote_path:
                        try:
                            r = ldfs.create_directory(args.remote_path)
                            if r:
                                print("create directory[%s] success" % args.remote_path)
                            else:
                                print("create directory[%s] failed" % args.remote_path)
                        except Exception as e:
                            print(e)
                elif operation == "delete":
                    if args.remote_path:
                        try:
                            r = ldfs.delete_directory(args.remote_path)
                            if r:
                                print("delete directory[%s] success" % args.remote_path)
                            else:
                                print("delete directory[%s] failed" % args.remote_path)
                        except Exception as e:
                            print(e)
                elif operation == "move":
                    if args.source_path and args.target_path:
                        try:
                            r = ldfs.move_directory(args.source_path, args.target_path)
                            if r:
                                print("move directory[%s] to %s success" % (args.source_path, args.target_path))
                            else:
                                print("move directory[%s] to %s failed" % (args.source_path, args.target_path))
                        except Exception as e:
                            print(e)
                elif operation == "rename":
                    if args.remote_path and args.new_name:
                        try:
                            r = ldfs.rename_directory(args.remote_path, args.new_name)
                            if r:
                                print("rename directory[%s] to %s success" % (args.remote_path, args.new_name))
                            else:
                                print("rename directory[%s] to %s failed" % (args.remote_path, args.new_name))
                        except Exception as e:
                            print(e)
                elif operation == "list":
                    if args.remote_path:
                        try:
                            r = ldfs.list_directory(args.remote_path, offset = args.offset, limit = args.limit, include_file = args.exclude_file, include_directory = args.exclude_directory)
                            if r:
                                print_table_result(
                                    r["children"],
                                    ["id", "type", "size", "name"],
                                    args
                                )
                            else:
                                print("list directory[%s] failed" % args.remote_path)
                        except Exception as e:
                            print(e)
            if object == "path":
                if operation == "info":
                    if args.remote_path:
                        try:
                            r = ldfs.info_path(args.remote_path)
                            if r:
                                print(json.dumps(r, indent = 4, sort_keys = True))
                            else:
                                print("get file[%s]'s info failed" % args.remote_path)
                        except Exception as e:
                            print(e)
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
                                    ],
                                    args
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
                                    ],
                                    args
                                )
                            else:
                                print_table_result(
                                    [data],
                                    ["result", "message"],
                                    args
                                )
                    else:
                        print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                        
    except Exception as e:
        logging.error(logging.traceback.format_exc())


if __name__ == "__main__":
    main()
