#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 03.3.2019

@param author: reko8680
@Coding Guidelines: Synchronization methods, functions and variables shall be written in Lowercase separated by _
"""

import threading


def synchronized(method):
    """
        Synchronize a method
    """
    def f(*args):
        self = args[0]
        self.mutex.acquire()
        try:
            return method(*args)
        finally:
            self.mutex.release()
    return f


def synchronize(m_class, names=None):
    """
        Synchronize methods in the given class
        @param m_class: class to be synchronized
        @param type m_class: class
        @param names:  Only synchronize the methods whose names are given, or all methods if names=None.
        @param type names: string or list
    """
    if isinstance(names, str): names = names.split()
    for (name, val) in m_class.__dict__.items():
        if callable(val) and name != '__init__' and \
                (names is None or name in names):
                    setattr(m_class, name, synchronized(val))


class Synchronization:
    """
        Create your own self.mutex or inherit from this class
    """
    def __init__(self):
        self.mutex = threading.RLock()
