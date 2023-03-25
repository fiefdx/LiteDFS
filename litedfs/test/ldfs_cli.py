#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys

cwd = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.split(cwd)[0])

from litedfs.tool.litedfs_cli import main


if __name__ == "__main__":
    main()
