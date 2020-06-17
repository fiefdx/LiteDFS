# -*- coding: utf-8 -*-
'''
LiteDFS: distributed file system
'''

from setuptools import setup

from litedfs.version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name = "litedfs",
    version = __version__,
    description = "LiteDFS: distributed file system",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/fiefdx/LiteDFS",
    author = "fiefdx",
    author_email = "fiefdx@163.com",
    packages = [
        'litedfs',
        'litedfs.tool',
        'litedfs.tool.viewer',
        'litedfs.tool.viewer.handlers',
        'litedfs.tool.viewer.modules',
        'litedfs.tool.viewer.utils',
        'litedfs.name',
        'litedfs.name.db',
        'litedfs.name.handlers',
        'litedfs.name.models',
        'litedfs.name.utils',
        'litedfs.data',
        'litedfs.data.handlers',
        'litedfs.data.utils',
    ],
    entry_points = {
        'console_scripts': [
            'ldfs = litedfs.tool.litedfs:main',
            'ldfsviewer = litedfs.tool.viewer.viewer:main',
            'ldfsname = litedfs.name.name:main',
            'ldfsdata = litedfs.data.data:main',
        ],
    },
    install_requires = [
        "requests >= 2.22.0",
        "tornado",
        "pyYAML",
        "tinydb",
        "sqlalchemy",
        "tornado_discovery",
        "psutil",
        "litedfs_client",
    ],
    include_package_data = True,
    license = "MIT",
    classifiers = [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ]
)
