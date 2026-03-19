#!/usr/bin/python
# ! _+_ coding: utf-8 _*_

import os
import uuid
import requests
import inspect
from ProcessorBase import WorkerPool
from Logger import Logger
from Connector import JiraConnector
from TestExecutionContainer import TestExecution
from lxml import etree

class B:
    def __init__(self, name):
        self.name = name


def f_accepts(*types):
    def check_accepts(func):
        class_method = False
        args = inspect.getfullargspec(func)
        arg_list = args.args
        if arg_list[0] == 'self':
            class_method = True
            arg_list.pop(0)
        assert len(types) == len(arg_list)

        def function_wrapper(*args, **kwds):
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
                    "arg %s does not match %s" % (a, str(type_list))
            return func(*args, **kwds)

        function_wrapper.func_name = func.__name__
        return function_wrapper

    return check_accepts


def thread_decorator_send_get(func):
    def func_wrapper(*args, **kwargs):
        self = args[0]
        url_list = args[1]
        return self.start_thread_pool_send_get(func, len(url_list), url_list)

    return func_wrapper


class A(Logger):
    @f_accepts(str, str)
    def __init__(self, name, surname):
        super().__init__(self)
        self.name = name
        self.surname = surname

    '''
        Start a series of worker threads executing I/O tasks (GET requests)
        @param func: task to execute (GET request)
        @param type func: function or method
        @param worker_threads: number of threads to start (int)
        @param url_list: list of urls a request is generated from
        @return: False in case of wrong inputs or dictionary of json responses for each thread
        @return type: False or python dictionary of JSON objects
    '''

    def start_thread_pool_send_get(self, func, worker_threads=0, url_list=None):
        if url_list is None:
            url_list = []

        num_urls = len(url_list)

        if worker_threads != num_urls:
            self.print_log_line("Start of worker threads ignored -> "
                                "Num worker threads (%d) does not match url_list length (%d)" % (worker_threads,
                                                                                                 num_urls))
            return False

        pool = WorkerPool(num_workers=worker_threads, job_type='Thread')
        for i in range(0, num_urls):
            pool.add_task_threads(func, self, url_list[i])

        pool.wait_completion()
        return pool.get_thread_results()

    def update_test_status_of_all_tests_in_xray(self, test_status='Execute'):
        url_list = ["http://www.googgwegwegwegewle.de", "http://www.heise.de", "http://www.bmw.de"]
        results = self.send_get(url_list)
        print(results)

    @thread_decorator_send_get
    def send_get(self, url):
        allow_redirects = True
        r = requests.get(url,
                         allow_redirects=allow_redirects,
                         timeout=3,
                         verify=False
                         )
        return r

    @f_accepts((None, B), int, str)
    def input_check(self, client=None, worker_threads=0, url_list="test"):
        pass


def parse_xml():

    tree = etree.parse(os.path.dirname(__file__) + '/../test_configs/Pytefw/testconfig.xml')
    root = tree.getroot()
    print(type(root))
    #num_test_sests = len(root)
    #test_sets = {}
    '''for child in root:
        attributes = child.attrib
        if "id" not in attributes.keys():
            # generate random id
            m_id = uuid.uuid4().hex[:6].upper()
        else:
            m_id = attributes["id"]
            del attributes["id"]
        test_sets[m_id] = {}
        for key, val in attributes.items():
            test_sets[m_id][key] = val
        expr = './/' + child.tyyag + '/Data'
        for data in root.xpath(expr):
            attributes = data.attrib
            for key, val in attributes.items():
                pass
    print(test_sets)'''

    expr = './/TestSuite[starts-with(@class,"suites")]'
    preconditions = []
    for test_suite in root.xpath(expr):
        precondition = {}
        for key, value in test_suite.attrib.items():
            precondition[key] = value
        expr = ".//TestSuite[@class = $name]/Data[@param]"
        precondition['params'] = {}
        for data in root.xpath(expr, name=test_suite.attrib['class']):
            for key, value in data.attrib.items():
                precondition['params'][value] = data.text
        preconditions.append(precondition)

    print(preconditions)


def pretty(d, indent=0):
   for key, value in d.items():
      print('\t' * indent + str(key))
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
         print('\t' * (indent+1) + str(value))

if __name__ == '__main__':
    pretty({'param': {'OutputFile': 'output\\\\identdata.log'}})
    #parse_xml()

    '''item = {"xrayclient": [TestExecution(1, 1), TestExecution(2, 2), dict()], "aaa": [1,2,3, TestExecution(5, 7)]}
    item_values = list(item.values())
    item_keys = list(item.keys())

    for i in range(0, len(item_values)):
        item_value = item_values[i]
        item_key = item_keys[i]
        results = list(filter(lambda x: isinstance(x, TestExecution), item_value))
        if results:
            item[item_key] = results
        else:
            item.pop(item_key, None)

    print(item)
    #item = {"xrayclient": "test"}'''

    #a = A("Franz", 2)
    #a.input_check(B("Franz"), 1, "test")
    # a.update_test_status_of_all_tests_in_xray()

    pretty({'name': {'themes': 'Diag'}})
