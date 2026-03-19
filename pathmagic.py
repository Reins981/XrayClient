#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 21.03.2019

@author: reko8680
"""

import os
import sys


class context:
    """
        pathmagic class to be used for module imports residing in the libs_directory
        @param libs_directory: append modules from this path to the system path
        @param type libs_directory: string
    """
    def __init__(self, libs_directory):
        self.__libs_dir = libs_directory

    def __enter__(self):
        if self.__libs_dir == "..":
            mod_path = ".."
        else:
            abspath = os.path.realpath('.').split(os.sep)
            mod_path = os.sep.join(abspath + [self.__libs_dir])
        sys.path.append(mod_path)

    def __exit__(self, *args):
        pass
