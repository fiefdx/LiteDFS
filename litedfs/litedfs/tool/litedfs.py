#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import re
import sys
import json
import time
import argparse

import requests
from progress.spinner import Spinner

from litedfs.version import __version__

parser = argparse.ArgumentParser(prog = 'litedfs')

# common arguments
parser.add_argument("address", help = "name node address, host:port")
parser.add_argument("-v", "--version", action = 'version', version = '%(prog)s ' + __version__)

args = parser.parse_args()


def main():
    try:
        address = args.address
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
