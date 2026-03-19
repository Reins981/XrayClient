#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 14.03.2019

@author: reko8680
@Coding Guidelines: DataStructUtils methods, functions and variables shall be written in Lowercase separated by _
"""

import sys
from collections import deque
from Logger import Logger
from DecoratorUtils import accepts
from TestExecutionContainer import TestExecution


class ProcessingQueue(Logger):
    """
        Create a queue handling any kind of data except object instances
    """

    def __init__(self):
        super().__init__(self.__class__.__name__)
        self.PROCESSINGQUEUE = deque()

    '''
        Check if an item is available
        @return: True or False
    '''

    def __an_item_is_available(self):
        return bool(self.PROCESSINGQUEUE)

    '''
        Add an item to the queue
        @param item: item to add (any type)
        @return: None
    '''

    def __make_an_item_available(self, item):
        self.PROCESSINGQUEUE.append(item)

    '''
        Get the first item found from the queue
        @return: item
    '''

    def __get_an_available_item(self):
        return self.PROCESSINGQUEUE.pop()

    '''
        Clea the content of the queue
        @return: None
    '''

    def clear_queue(self):
        self.PROCESSINGQUEUE.clear()

    '''
        Consume an item from the queue
        @return: None in case the queue is empty, item in case of success
    '''

    def consume(self):
        if not self.__an_item_is_available():
            return None
        return self.__get_an_available_item()

    '''
        Add an item to the queue
        @param item: item to add (any type)
    '''

    def produce(self, item):
        self.__make_an_item_available(item)


'''
    Filter out unwanted items not of type TestExecution from a given list
    @param item_list: item list to filter
    @param type item: list
    @return: TestExecution items, results might be an empty list in case no TestExecution items were found
    @return type: list 
'''


@accepts(list)
def filter_items_of_type_test_execution(item_list):
    logger = Logger("filter_items_of_type_test_execution")

    results = list(filter(lambda x: isinstance(x, TestExecution), item_list))

    len_filtered_results = len(results)
    len_original_results = len(item_list)
    if len_filtered_results != len_original_results:
        logger.print_log_line("Filtered number of test executions (%s items), "
                              "Original number of test executions (%s items)" %
                              (len_filtered_results, len_original_results), log_level="ERROR", color="WARNING")

    return results


'''
    Pretty print a nested python dictionary
    @param logger: The Logger for printing the dictionary
    @param type logger: Logger instance
    @param d: python dictionary
    @param type d: dictionary
    @param indent: indentation (int)
    @return: None
'''


@accepts(Logger, dict, int)
def pretty_dict(logger, d, indent=0):
    for key, value in d.items():
        logger.print_log_line('\t' * indent + str(key) + ': ')
        if isinstance(value, dict):
            pretty_dict(logger, value, indent + 1)
        else:
            logger.print_log_line('\t' * (indent + 1) + str(value))
