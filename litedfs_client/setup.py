# -*- coding: utf-8 -*-
'''
LiteDFS Client: distributed file system python client
'''

from setuptools import setup

from litedfs_client.version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name = "litedfs_client",
    version = __version__,
    description = "LiteDFS Client: distributed file system python client",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/fiefdx/LiteDFS",
    author = "fiefdx",
    author_email = "fiefdx@163.com",
    packages = [
        'litedfs_client',
    ],
    install_requires = [
        "requests >= 2.22.0",
    ],
    include_package_data = True,
    license = "MIT",
    classifiers = [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ]
)
