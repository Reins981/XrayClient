#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 14.03.2019

@author: reko8680
@Coding Guidelines: ExceptionUtils methods, functions and variables shall be written in Lowercase separated by _
"""


class ImportFailure(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class ConnectionFailure(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class GeneralError(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class LengthLimitReached(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class InvalidHandlerMode(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class InvalidXrayClientMode(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class InvalidFrameworkConfigLocation(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class InvalidFrameworkString(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class InvalidType(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class NoneTypeObject(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class AttributesError(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class FileError(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class RequestException(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class InvalidResponse(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)


class AuthenticationException(Exception):
    """
        Exception class
    """

    def __init__(self, message, *args):
        super().__init__(message, *args)
