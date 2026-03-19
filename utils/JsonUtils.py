#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 10.04.2019

@author: reko8680
@Coding Guidelines: JsonUtils methods, functions and variables shall be written in Lowercase separated by _
"""

from DecoratorUtils import accepts

'''
    Get the attribute of a JSON object
    @param data: JSON data
    @param type data: JSON
    @param attribute: attribute key
    @param type attribute: string OR int
    @param default_value: The default value if attribute is not found
    @param type default_value: None OR string or int
    @return: The value of attribute OR default_value if attribute is not found
'''


@accepts((str, dict), (str, int), (None, str, int))
def get_attribute(data, attribute, default_value):
    return data.get(attribute) or default_value


