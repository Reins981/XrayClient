#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 14.03.2019

@author: reko8680
@Coding Guidelines: DecoratorUtils methods, functions and variables shall be written in Lowercase separated by _ or Uppercase
"""

import os
import datetime
import inspect
import types
import traceback
from functools import wraps
from PyQt5.QtCore import pyqtSlot
from Logger import Logger
from ExceptionUtils import InvalidFrameworkString


class TimedFunc(Logger):
    """
        Context Manager for measuring function or method execution times
    """

    def __init__(self, func_name):
        super().__init__(self.__class__.__name__)
        self.__func_name = func_name

    def __enter__(self):
        self.print_log_line("Started: %s" % self.__func_name)
        self.start_time = datetime.datetime.now()
        return self

    def __exit__(self, *args):
        self.print_log_line(
            "Finished: %s in %s seconds" % (self.__func_name, datetime.datetime.now() - self.start_time), color="BLUE")


# ---- Decorators ----


def measure_func_time(func):
    """
        Function decorator which calls the TimedFunc context manager measuring the exec time
        @param func: function to be wrapped
        @return: time measured function
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        with TimedFunc(func.__name__):
            return func(*args, **kwargs)
    return func_wrapper


def check_authorization(framework):
    """
        Function decorator which checks the function or method membership based on a given framework string and the
        currently used framework. If the framework in use differs with the input string, an InvalidFrameworkString
            exception is raised
        @param func: function to be wrapped
        @return: func
    """
    def framework_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            if framework != args[0].get_framework_string():
                raise InvalidFrameworkString("%s is only supported in %s" % (func.__name__, framework), "ERROR")
            return func(*args, **kwargs)
        return func_wrapper
    return framework_decorator


def add_tags_as_suffix_to_path(tags):
    """
        Function decorator to construct paths from a general path and a suffix. The suffix is represented as tags
        The tags are passed as one string separated by whitespaces "tag1 tag2 .."
        For each suffix a path is constructed
        @param func: function to be wrapped
        @return: list of constructed paths (list)
    """

    def path_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            return [(tag, os.path.join(func(*args, **kwargs), tag))
                    for tag in tags.split()]
        return func_wrapper
    return path_decorator


def accepts(*types):
    """
        Function decorator which performs function or method argument checks before a function is called
        @param func: function to be wrapped
        @return: Raises Assertion in case of invalid arguments
    """
    def check_accepts(func):
        class_method = False
        args = inspect.getfullargspec(func)
        arg_list = args.args
        if arg_list[0] == 'self':
            class_method = True
            arg_list.pop(0)
        assert len(types) == len(arg_list)

        @wraps(func)
        def function_wrapper(*args, **kwargs):
            f_args = list(args)
            if class_method:
                f_args.pop(0)
            for (a, t) in zip(f_args, types):
                type_list = []
                if isinstance(t, tuple) or isinstance(t, list):
                    for m_type in t:
                        type_list.append(m_type)
                else:
                    type_list.append(t)

                if 'IGNORE' in type_list:
                    continue

                r = False
                if None in type_list:
                    if a is None:
                        r = True
                    else:
                        none_index = type_list.index(None)
                        type_list.pop(none_index)
                        res = filter(lambda x: isinstance(a, x), type_list)
                        r = bool((sum(1 for _ in res)))
                else:
                    res = filter(lambda x: isinstance(a, x), type_list)
                    r = bool((sum(1 for _ in res)))
                assert r, \
                    "arg %s does not match %s" % (a, ' '.join(str(x) for x in type_list))
            return func(*args, **kwargs)

        function_wrapper.func_name = func.__name__
        return function_wrapper

    return check_accepts


def XrayClientUIPyQtSlot(*args):
    if len(args) == 0 or isinstance(args[0], types.FunctionType):
        args = []

    """
        Function decorator which assigns functions or methods to slots
        Slots are needed in case the XrayClients user interface is executed. 
        Whenever an exception in the function occurs, the user interfaces is informed
        @param func: function to be wrapped
        @return: A function assigned to a slot
    """
    @pyqtSlot(*args)
    def slotDecorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(e)
                traceback.print_exc()
        return wrapper

    return slotDecorator

