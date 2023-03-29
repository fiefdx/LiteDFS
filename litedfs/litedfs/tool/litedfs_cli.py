#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import re
import sys
import cmd
import json
import time
import hashlib
import argparse
import logging
import random
from io import BytesIO
from getpass import getpass
from base64 import b64encode, b64decode

import requests
from tea_encrypt import EncryptStr, DecryptStr

from litedfs.version import __version__
from litedfs_client.client import LiteDFSClient


BUF_SIZE = 65536


def print_table_result(data, fields, column_width):
    fields.insert(0, "#")
    field_length_map = {}
    lines = []
    num = 1
    column_max_width = column_width
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


class NonExitArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.already_print_help = False

    def print_help(self, file = None):
        self.already_print_help = True
        if file is None:
            file = sys.stdout
        self._print_message(self.format_help(), file)

    def exit(self, status = 0, message = None):
        pass

    def error(self, message):
        if self.already_print_help:
            self.already_print_help = False
        else:
            self.print_usage(sys.stderr)


class LDFSShell(cmd.Cmd):
    def __init__(self, host, port, user = None, password = None, column_width = 0):
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.column_width = column_width
        self.ldfs = LiteDFSClient(self.host, self.port, user = self.user, password = self.password)
        self.intro = ("LiteDFS Client %s\n" % __version__ +
                      "Connect to Service<%s:%s>\n" % (self.host, self.port) +
                      "Type 'help' or '?' to list commands, Type 'exit' to exit.\n")
        self.prompt = '> '

    def precmd(self, line):
        line = line.lower()
        return line

    def do_about(self, arg):
        "about"
        r = requests.get("http://%s:%s/" % (self.host, self.port))
        print(r.json())

    def do_ls(self, arg):
        "remote list directory: ls -r /path -o 0 -l 10 -f -d"
        try:
            p = NonExitArgumentParser(prog = "ls", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")
            p.add_argument("-o", "--offset", help = "list offset", type = int, default = 0)
            p.add_argument("-l", "--limit", help = "list limit", type = int, default = 0)
            p.add_argument("-f", "--exclude-file", help = "exclude file", action = "store_false")
            p.add_argument("-d", "--exclude-directory", help = "exclude directory", action = "store_false")
            args = p.parse_args(arg.split())
            if args.remote_path:
                try:
                    r = self.ldfs.list_directory(args.remote_path, offset = args.offset, limit = args.limit, include_file = args.exclude_file, include_directory = args.exclude_directory)
                    if r:
                        print_table_result(
                            r["children"],
                            ["id", "type", "size", "name"],
                            self.column_width
                        )
                    else:
                        print("list directory[%s] failed" % args.remote_path)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_mkdir(self, arg):
        "remote create directory: mkdir -r /path"
        try:
            p = NonExitArgumentParser(prog = "mkdir", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")
            args = p.parse_args(arg.split())
            if args.remote_path:
                try:
                    r = self.ldfs.create_directory(args.remote_path)
                    if r:
                        print("create directory[%s] success" % args.remote_path)
                    else:
                        print("create directory[%s] failed" % args.remote_path)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_rm(self, arg):
        "remote delete directory or file: rm -r /path"
        try:
            p = NonExitArgumentParser(prog = "rm", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote directory or file path", default = "")
            args = p.parse_args(arg.split())
            if args.remote_path:
                try:
                    info = self.ldfs.info_path(args.remote_path)
                    if "info" in info and info["info"]["exists"]:
                        if info["info"]["type"] == "directory":
                            r = self.ldfs.delete_directory(args.remote_path)
                            if r:
                                print("delete directory[%s] success" % args.remote_path)
                            else:
                                print("delete directory[%s] failed" % args.remote_path)
                        elif info["info"]["type"] == "file":
                            r = self.ldfs.delete_file(args.remote_path)
                            if r:
                                print("delete file[%s] success" % args.remote_path)
                            else:
                                print("delete file[%s] failed" % args.remote_path)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_mv(self, arg):
        "remote create directory or file: mv -s /path -t /path"
        try:
            p = NonExitArgumentParser(prog = "mv", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-s", "--source-path", required = True, help = "source directory path", default = "")
            p.add_argument("-t", "--target-path", required = True, help = "target directory path", default = "")
            args = p.parse_args(arg.split())
            if args.source_path and args.target_path:
                try:
                    info = self.ldfs.info_path(args.source_path)
                    if "info" in info and info["info"]["exists"]:
                        if info["info"]["type"] == "directory":
                            r = self.ldfs.move_directory(args.source_path, args.target_path)
                            if r:
                                print("move directory[%s] to %s success" % (args.source_path, args.target_path))
                            else:
                                print("move directory[%s] to %s failed" % (args.source_path, args.target_path))
                        elif info["info"]["type"] == "file":
                            r = self.ldfs.move_file(args.source_path, args.target_path)
                            if r:
                                print("move file[%s] to %s success" % (args.source_path, args.target_path))
                            else:
                                print("move file[%s] to %s failed" % (args.source_path, args.target_path))
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_rename(self, arg):
        "remote create directory or file: rename -r /path -n name"
        try:
            p = NonExitArgumentParser(prog = "rename", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote directory path", default = "")
            p.add_argument("-n", "--new-name", required = True, help = "new directory name", default = "")
            args = p.parse_args(arg.split())
            if args.remote_path and args.new_name:
                try:
                    info = self.ldfs.info_path(args.remote_path)
                    if "info" in info and info["info"]["exists"]:
                        if info["info"]["type"] == "directory":
                            r = self.ldfs.rename_directory(args.remote_path, args.new_name)
                            if r:
                                print("rename directory[%s] to %s success" % (args.remote_path, args.new_name))
                            else:
                                print("rename directory[%s] to %s failed" % (args.remote_path, args.new_name))
                        elif info["info"]["type"] == "file":
                            r = self.ldfs.rename_file(args.remote_path, args.new_name)
                            if r:
                                print("rename file[%s] to %s success" % (args.remote_path, args.new_name))
                            else:
                                print("rename file[%s] to %s failed" % (args.remote_path, args.new_name))
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_upload(self, arg):
        "remote upload file: upload -r /path -l /path -L 120 -R 1"
        try:
            p = NonExitArgumentParser(prog = "upload", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-l", "--local-path", required = True, help = "local file path", default = "")
            p.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
            p.add_argument("-L", "--lock-ttl", help = "lock ttl/seconds, default: 60", type = int, default = 60)
            p.add_argument("-R", "--replica", help = "replica count", type = int, default = 1)
            args = p.parse_args(arg.split())
            try:
                r = self.ldfs.create_file(args.local_path, args.remote_path, replica = args.replica, lock_ttl = args.lock_ttl, progress_callback = print)
                if r:
                    print("create file[%s] success" % args.remote_path)
                else:
                    print("create file[%s] failed" % args.remote_path)
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)

    def do_update(self, arg):
        "remote update file: update -r /path -R 1"
        try:
            p = NonExitArgumentParser(prog = "update", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
            p.add_argument("-R", "--replica", required = True, help = "replica count", type = int, default = 1)
            args = p.parse_args(arg.split())
            if args.remote_path and args.replica:
                try:
                    r = self.ldfs.update_file(args.remote_path, args.replica)
                    if r:
                        print("update file[%s] success" % args.remote_path)
                    else:
                        print("update file[%s] failed" % args.remote_path)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_download(self, arg):
        "remote download file: download -r /path -l /path"
        try:
            p = NonExitArgumentParser(prog = "download", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-l", "--local-path", required = True, help = "local file path", default = "")
            p.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
            args = p.parse_args(arg.split())
            r = self.ldfs.download_file(args.remote_path, args.local_path, progress_callback = print)
            if r:
                print("download file[%s => %s] success" % (args.remote_path, args.local_path))
            else:
                print("download file[%s => %s] failed" % (args.remote_path, args.local_path))
        except Exception as e:
            print(e)

    def do_info(self, arg):
        "remote info file: info -r /path"
        try:
            p = NonExitArgumentParser(prog = "info", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote file path", default = "")
            args = p.parse_args(arg.split())
            if args.remote_path:
                try:
                    r = self.ldfs.info_file(args.remote_path)
                    if r:
                        print(json.dumps(r, indent = 4, sort_keys = True))
                    else:
                        print("get file[%s]'s info failed" % args.remote_path)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_cluster(self, arg):
        "cluster info: cluster -r"
        try:
            p = NonExitArgumentParser(prog = "cluster", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--raw", help = "display raw json data", action = "store_true")
            args = p.parse_args(arg.split())
            url = "http://%s:%s/cluster/info" % (self.host, self.port)
            r = requests.get(url, headers = self.ldfs.headers)
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
                            self.column_width
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
                            self.column_width
                        )
                    else:
                        print_table_result(
                            [data],
                            ["result", "message"],
                            self.column_width
                        )
            else:
                print("error:\ncode: %s\ncontent: %s" % (r.status_code, r.content))
        except Exception as e:
            print(e)

    def do_path(self, arg):
        "remote path info: path -r /path"
        try:
            p = NonExitArgumentParser(prog = "path", add_help = False, exit_on_error = False)
            p.add_argument("-h", "--help", help = "", action = "help")
            p.add_argument("-r", "--remote-path", required = True, help = "remote file/directory path", default = "")
            args = p.parse_args(arg.split())
            if args.remote_path:
                try:
                    r = self.ldfs.info_path(args.remote_path)
                    if r:
                        print(json.dumps(r, indent = 4, sort_keys = True))
                    else:
                        print("get file/directory[%s]'s info failed" % args.remote_path)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    def do_exit(self, arg):
        "exit"
        return True


def main():
    parser = argparse.ArgumentParser(prog = 'ldfs', add_help = False)

    # common arguments
    parser.add_argument("address", help = "name node address, host:port")
    parser.add_argument("-w", "--column_width", help = "column max width", type = int, default = 0)
    parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)
    parser.add_argument("-u", "--user", help = "user name", default = "")
    parser.add_argument("-p", "--password", help = "with password", action = "store_true", default = False)
    args = parser.parse_args()


    try:
        address = args.address
        if address:
            host, port = address.split(":")
            password = None
            if args.password:
                password = getpass("password: ")
            
            shell = LDFSShell(host, port, args.user, password, column_width = args.column_width)
            shell.cmdloop()
    except Exception as e:
        logging.error(logging.traceback.format_exc())


if __name__ == "__main__":
    main()
