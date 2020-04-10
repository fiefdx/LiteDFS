#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import re
import sys
import json
import time
import argparse
import logging
from io import BytesIO

import requests
from progress.spinner import Spinner

from litedfs.version import __version__

parser = argparse.ArgumentParser(prog = 'litedfs')

# common arguments
parser.add_argument("address", help = "name node address, host:port")
parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)
subparsers = parser.add_subparsers(dest = "object", help = 'sub-command help')

# operate with application
parser_file = subparsers.add_parser("file", help = "operate with file API")
subparsers_file = parser_file.add_subparsers(dest = "operation", help = 'sub-command file help')

parser_file_create = subparsers_file.add_parser("create", help = "create file")
parser_file_create.add_argument("-f", "--file", required = True, help = "local file path", default = "")
parser_file_create.add_argument("-p", "--path", required = True, help = "remote file path", default = "")
parser_file_create.add_argument("-r", "--replica", help = "replica count", type = int, default = 1)

parser_file_download = subparsers_file.add_parser("download", help = "download file")
parser_file_download.add_argument("-p", "--path", required = True, help = "remote file path", default = "")

args = parser.parse_args()


def main():
    try:
        address = args.address
        object = args.object
        operation = args.operation
        url = "http://%s/%s/%s" % (address, object, operation)
        if address:
            if object == "file":
                if operation == "create":
                    if os.path.exists(args.file) and os.path.isfile(args.file):
                        success = True
                        file_size = os.stat(args.file).st_size
                        block_list_url = "http://%s/file/block/list?size=%s&replica=%s" % (address, file_size, args.replica)
                        r = requests.get(block_list_url)
                        if r.status_code == 200:
                            data = r.json()
                            if "result" in data and data["result"] == "ok":
                                # print(json.dumps(data, indent = 4))
                                data_nodes = data["data_nodes"]
                                fp = open(args.file, "rb")
                                for block in data["blocks"]:
                                    block_id = block[0]
                                    block_size = block[1]
                                    block_content = BytesIO()
                                    block_content.write(fp.read(block_size))
                                    for node_id in block[2]:
                                        data_node = data_nodes[str(node_id)]
                                        block_create_url = "http://%s:%s/block/create" % (data_node[0], data_node[1])
                                        block_content.seek(0)
                                        files = {'up_file': ("up_file", block_content, b"text/plain")}
                                        values = {"name": data["file_id"], "block": block_id}
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
                                        "path": args.path,
                                        "file_id": data["file_id"],
                                        "replica": args.replica,
                                        "blocks": data["blocks"],
                                    }
                                    r = requests.post(url, json = json_data)
                                    if r.status_code == 200:
                                        d = r.json()
                                        if "result" in d and d["result"] == "ok":
                                            print("create file[%s] success" % args.path)
                                        else:
                                            print("create file[%s] failed: %s" % (args.path, d["result"]))
                                    else:
                                        print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                                else:
                                    print("create file[%s] failed")
                        else:
                            print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
                    else:
                        print("file[%s] not exists" % args.file)
    except Exception as e:
        logging.error(logging.traceback.format_exc())


if __name__ == "__main__":
    main()
