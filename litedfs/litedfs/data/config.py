# -*- coding: utf-8 -*-
'''
Created on 2013-10-26 21:29
@summary:  import yaml configuration
@author: YangHaitao
''' 
try:
    import yaml
except ImportError:
    raise ImportError("Config module requires pyYAML package, please check if pyYAML is installed!")

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import os

cwd = os.path.split(os.path.realpath(__file__))[0]

CONFIG = {}

def load_config(config_file_path):
    result = False
    try:
        if config_file_path and os.path.exists(config_file_path) and os.path.isfile(config_file_path):
            s = open(config_file_path, "r")
            local_config = load(stream = s, Loader = Loader)
            CONFIG.update(local_config)
            s.close()
            if "app_path" not in CONFIG:
                CONFIG["app_path"] = cwd
            result = True
    except Exception as e:
        print(e)
    return result

if __name__ == "__main__":
    print ("CONFIG: %s" % CONFIG)
