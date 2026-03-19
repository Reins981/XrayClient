#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 14.03.2019

@author: reko8680
@Coding Guidelines: XrayClient methods, functions and variables shall be written in Lowercase separated by _
"""

import pathmagic
import json
import re
import inspect
from functools import wraps

with pathmagic.context("utils"):
    import XmlUtils
    from Logger import Logger
    from Shell import SshShell
    from Observer import Observer, Observable
    from Connector import JiraConnector, RequestException, InvalidResponse
    from TestExecutionContainer import TestExecution, TestNode, TestSet, TestPlan, Precondition, Bug
    from ProcessorBase import WorkerPool
    from DataStructUtils import ProcessingQueue, pretty_dict
    from ExceptionUtils import InvalidXrayClientMode, InvalidType, ImportFailure, ConnectionFailure, GeneralError, \
        AttributesError
    from DecoratorUtils import TimedFunc, measure_func_time, accepts, check_authorization, XrayClientUIPyQtSlot


# - Class Decorators -


def xray_get_request_threaded(func):
    """
        Function decorator which takes a list of urls from a function.
        Each url will be executed as GET request by a new thread.
        The number of threads is equal to the number of urls found
        @param func: function to be wrapped
        @return: python dictionary of json results in the form {thread_name1:json1,..}
        @return type: python dictionary (empty in case of input failures)
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        m_logger = Logger(func.__name__)

        if len(args) != 2:
            m_logger.print_log_line("Invalid number of args provided!")
            return {}

        self = args[0]
        url_list = args[1]

        if not isinstance(url_list, list):
            m_logger.print_log_line("Invalid type provided for url_list!")
            return {}

        return self.__start_thread_pool_send_get(func, len(url_list), url_list)

    return func_wrapper


def xray_post_request_threaded(func):
    """
        Function decorator which takes a dictionary of {url:data,..} pairs from a function.
        The data itself must be a python dictionary
        Each url:data pair will be executed as POST request by a new thread.
        The number of threads is equal to the number of pairs found
        @param func: function to be wrapped
        @return: python dictionary of json results in the form {thread_name1:json1,..}
        @return type: python dictionary (empty in case of input failures)
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        m_logger = Logger(func.__name__)

        if len(args) != 2:
            m_logger.print_log_line("Invalid number of args provided!")
            return {}

        self = args[0]
        url_data_dict = args[1]

        if not isinstance(url_data_dict, dict):
            m_logger.print_log_line("Invalid type provided for url_data_dict!")
            return {}

        return self.__start_thread_pool_send_post(func, len(url_data_dict), url_data_dict)

    return func_wrapper


class XrayClient(Logger):
    """
        Create a XrayClient instance which imports or exports data from or to Xray.
        The XrayClient communicates with a XmlHandler which either generates test input configurations
        for a given framework or passes test results to the client for making updates in Xray
        An initial Import or Export ist started. If desired other im/exports can be fired afterwards
        @param mode: XrayClient mode "Import" or "Export"
            if mode == "Export": fetch data from the xml handler and export them to Xray
            if mode == "Import": Import data from Xray and notify the xml handler for further processing (default)
        @param type mode: string
        @param import_mode_test_execution: import tests by issue type test execution
        @param type import_mode_test_execution: bool
        @param import_mode_test_plan: import tests by issue type test plan
        @param type import_mode_test_plan: bool
        @param issue_type_key: Depending on the import mode, specify the key of the issue type. If no key is provided
            all test executions OR test plans are imported
        @param framework: choose the framework
            can be: "Pytefw" or "Ita"
        @param type framework: string
        @param framework_config_location: choose where the framework config resides: 'Remote' or 'Local'
        @param type framework_config_location: str
        @param framework_config_dir: framework specific local configuration directory
        @param remote_host: framework specific local configuration directory (str)
        @param ssh_conn_timeout: ssh connection timeout in seconds (int)
        @param remote_user: framework specific local configuration directory (str)
        @param remote_password: framework specific local configuration directory (str)
        @param framework_remote_config_dir: framework specific remote configuration directory (str)
        @param type framework_config_dir: string
        @param xray_rest_api_endpoint: base url of Xray REST API
        @param type xray_rest_api_endpoint: string
        @param use_threads: Use threading for I/O operations like GET and POST
        @param type use_threads: boolean
        @return: None or (InvalidHandlerMode, InvalidType) exception is raised
        @param auth: choose between "Basic" and "OAuth1" authentication (string)
        @param user: username [if Basic Auth] (string)
        @param password: password [if Basic Auth] (string)
        @param timeout: abort JIRA connection attempt if timeout has exceeded (int)
        @param connection_attempts: Try to reconnect to the JIRA endpoint this amount of times in case
            the first connection attempt failed
        @param type connection_attempts: int
        @param verify_ssl_certs: enable or disable server certificate verification (boolean)
        @param verbose: enable or disable debug log output (boolean)
        @param print_data_containers: print internal data structure containers for further analysis (boolean)
    """

    @XrayClientUIPyQtSlot()
    @accepts(str, bool, bool, (None, str), str, str, str, str, int, str, str, str, str, bool, str,
             str, str, int, int, bool, bool, bool)
    def __init__(self,
                 mode=None,
                 import_mode_test_execution=False,
                 import_mode_test_plan=False,
                 issue_type_key=None,
                 framework="Pytefw",
                 framework_config_location="",
                 framework_config_dir="",
                 remote_host="",
                 ssh_conn_timeout=1,
                 remote_user="",
                 remote_password="",
                 framework_remote_config_dir="",
                 xray_rest_api_endpoint="",
                 use_threads=False,
                 auth="Basic",
                 user="",
                 password="",
                 timeout=5,
                 connection_attempts=5,
                 verify_ssl_certs=False,
                 verbose=False,
                 print_data_containers=False):
        super().__init__(self.__class__.__name__)

        self.__mode = mode
        self.__import_mode_test_execution = import_mode_test_execution
        self.__import_mode_test_plan = import_mode_test_plan
        self.__issue_type_key = issue_type_key
        self.__framework = framework
        self.__framework_config_location = framework_config_location
        self.__framework_config_dir = framework_config_dir
        self.__remote_host = remote_host
        self.__ssh_conn_timeout = ssh_conn_timeout
        self.__remote_user = remote_user
        self.__remote_password = remote_password
        self.__framework_remote_config_dir = framework_remote_config_dir
        self.__xray_rest_api_base_url = xray_rest_api_endpoint
        self.__use_threads = use_threads
        self.__auth = auth
        self.__user = user
        self.__password = password
        self.__timeout = timeout
        self.__connection_attempts = connection_attempts
        self.__verify_ssl_certs = verify_ssl_certs
        self.__verbose = verbose
        self.__print_data_containers = print_data_containers

        # list of test executions
        self.__test_executions = []
        # create queue object (public accessible)
        self.processing_queue = ProcessingQueue()

        # create observer or notifier instance, add all observers
        if verbose:
            self.print_log_line("Run for framework (%s)" % framework, log_level="DEBUG")
        if mode == "Import":
            if verbose:
                self.print_log_line("Starting with mode (%s/XrayClient.XmlHandlerNotifier)" % mode, log_level="DEBUG")
            if import_mode_test_execution and import_mode_test_plan:
                raise GeneralError("Choose either import_tests_from_test_execution OR import_tests_from_test_plan", "ERROR")

            if not import_mode_test_execution and not import_mode_test_plan:
                self.print_log_line("No Import mode was selected, setting default -> import_mode_test_execution",
                                    log_level="WARNING", color="YELLOW")
                self.__import_mode_test_execution = True

            self.xml_handler_notifier = XrayClient.XmlHandlerNotifier(verbose=verbose)
            self.__xml_handler = XmlUtils.XmlHandler(mode="XrayClientObserver",
                                                     framework=framework,
                                                     framework_config_location=framework_config_location,
                                                     framework_config_dir=framework_config_dir,
                                                     remote_host=remote_host,
                                                     ssh_conn_timeout=ssh_conn_timeout,
                                                     remote_user=remote_user,
                                                     remote_password=remote_password,
                                                     framework_remote_config_dir=framework_remote_config_dir,
                                                     xray_client_instance=self,
                                                     processing_queue=self.processing_queue,
                                                     verbose=verbose,
                                                     print_data_containers=print_data_containers
                                                     )
            if self.__xml_handler.constructor_raised_exception():
                return
            self.xml_handler_notifier.add_observer(self.__xml_handler.xray_client_observer)

            # test the server connection first
            if not self._connect_to_xray_api():
                raise ConnectionFailure("Connection to Xray Server failed!", "ERROR")

            # start the Initial Import/class XmlHandler
            self.start_import()

        elif mode == "Export":
            if verbose:
                self.print_log_line("Starting with mode (%s/XrayClient.XmlHandlerObserver)" % mode, log_level="DEBUG")
            self.xml_handler_observer = XrayClient.XmlHandlerObserver(self, verbose=verbose)
            self.__xml_handler = XmlUtils.XmlHandler(mode="XrayClientNotifier",
                                                     framework=framework,
                                                     framework_config_location=framework_config_location,
                                                     framework_config_dir=framework_config_dir,
                                                     remote_host=remote_host,
                                                     ssh_conn_timeout=ssh_conn_timeout,
                                                     remote_user=remote_user,
                                                     remote_password=remote_password,
                                                     framework_remote_config_dir=framework_remote_config_dir,
                                                     xray_client_instance=self,
                                                     processing_queue=self.processing_queue,
                                                     verbose=verbose,
                                                     print_data_containers=print_data_containers
                                                     )
            if self.__xml_handler.constructor_raised_exception():
                return
            # pool = WorkerPool(num_workers=1, job_type='Thread')
            # pool.add_task_threads(self.start_export)

            # start the Initial Export
            self.start_export()
        else:
            raise InvalidXrayClientMode("XrayClient mode %s is invalid! - "
                                        "supported modes ['Import','Export']" % mode, "ERROR")

    class XmlHandlerNotifier(Observable):
        """
            define a notifier class which notifies observers when results have been generated
        """

        def __init__(self, verbose=False):
            super().__init__()
            self.__verbose = verbose

        '''
            notify all registered observers
            @return: None
        '''

        def notify_observers(self):
            self.set_changed()
            super().notify_observers(self)

    class XmlHandlerObserver(Observer, Logger):
        """
            define an observer class which fetches results from an observable class in form of an update
        """

        def __init__(self, xray_client, verbose=False):
            Logger.__init__(self, self.__class__.__name__)
            self.__xray_client = xray_client
            self.__verbose = verbose

        '''
            Overridden method from Observer class which is called when updates are available
            The update itself is fetched from a queueing structure
            @return: None or specific exception (AttributesError, InvalidType) is raised in case of errors
        '''

        @XrayClientUIPyQtSlot()
        def update(self, observable, arg):
            self.print_log_line("Got update from %s" % observable)

            # test the server connection first
            '''if not self.__xray_client._connect_to_xray_api():
                raise ConnectionFailure("Connection to Xray Server failed!", "ERROR")'''

            if not self.__xray_client.processing_queue.consume():
                self.print_log_line("No update received from %s!" % observable, log_level="ERROR", color="RED")
                return

            # test executions are filled by the XmlHandler which uses the xray client interfaces
            test_executions = self.__xray_client.get_current_test_executions()
            if not test_executions:
                self.print_log_line("Ignoring update from %s, no TestExecutions received!" % observable,
                                    log_level="ERROR", color="RED")
                return

    # -  PROTECTED -
    '''
        Try to connect to the Xray REST API Endpoint
        @return: True or False (boolean)
    '''

    def _connect_to_xray_api(self):
        self.jira_connector = JiraConnector(base_url=self.__xray_rest_api_base_url,
                                            auth=self.__auth,
                                            user=self.__user,
                                            password=self.__password,
                                            timeout=self.__timeout,
                                            verify_ssl_certs=self.__verify_ssl_certs,
                                            verbose=self.__verbose)
        self.jira_connector.set_retry_sequence(self.__connection_attempts)
        if not self.jira_connector.is_xray_api_connected() and not self.jira_connector.reconnect():
            return False
        return True

    '''
        Delete all test execution instances from memory and clear the list of test executions afterwards
        @return: None
    '''

    def _clear_test_execution_container(self):
        self.print_log_line("Clearing test execution container..")
        for test_exec in self.__test_executions:
            del test_exec
        self.__test_executions.clear()

    # -  PRIVATE -

    '''
        Add the test execution to the list of available test executions
        @param test_execution: test execution 
        @param type test_execution: instance
        @return: None
    '''

    @accepts(TestExecution)
    def __add_test_execution_to_current_test_executions(self, test_execution):
        if list(filter(lambda test_exec: id(test_exec) is id(test_exec), self.__test_executions)) \
                or list(filter(lambda test_exec:
                               test_exec.get_id() == test_execution.get_id(),
                               self.__test_executions)):
            if self.__verbose:
                self.print_log_line("Could not add test execution with id %s to current test executions, "
                                    "id is duplicate" % (test_execution.get_id()), log_level="ERROR", color="RED")
            return

        self.__test_executions.append(test_execution)

    '''
        Check if the provided item can be deserialized as json
        @param json_item: json string
        @return: True or False (boolean)
    '''

    def __is_json(self, json_item):
        try:
            json.loads(json_item)
        except ValueError:
            return False
        return True

    '''
        Start a series of worker threads executing I/O tasks (GET requests)
        @param func: task to execute (GET request)
        @param type func: function or method
        @param worker_threads: number of threads to start (int)
        @param url_list: list of urls a request is generated from
        @return: False in case of wrong inputs or dictionary of json responses for each thread
        @return type: False or python dictionary of JSON objects
    '''

    def __start_thread_pool_send_get(self, func, worker_threads=0, url_list=None):
        if url_list is None:
            url_list = []

        num_tasks = len(url_list)

        if worker_threads != num_tasks:
            self.print_log_line("Start of worker threads ignored -> "
                                "Num worker threads (%d) does not match url_list length (%d)" % (worker_threads,
                                                                                                 num_tasks),
                                log_level="ERROR", color="RED")
            return False

        if num_tasks <= 100:

            pool = WorkerPool(num_workers=worker_threads, job_type='Thread')
            for i in range(0, num_tasks):
                pool.add_task_threads(func, self, url_list[i])

            pool.wait_completion()
            return pool.get_thread_results()
        else:
            final_results = {}
            chunk_size = 10
            if self.__verbose:
                self.print_log_line("More than (%d) tasks detected, starting of worker threads in chunks of (%d)"
                                    % (num_tasks, chunk_size), log_level="DEBUG")

            rest_tasks = num_tasks % chunk_size
            start_index = 0
            while num_tasks > 0:
                if num_tasks == rest_tasks:
                    num_tasks -= rest_tasks
                    chunk_size = rest_tasks
                else:
                    num_tasks -= chunk_size

                end_index = start_index + chunk_size

                pool = WorkerPool(num_workers=chunk_size, job_type='Thread')
                for i in range(start_index, end_index):
                    pool.add_task_threads(func, self, url_list[i])

                start_index = end_index

                pool.wait_completion()
                final_results = {**final_results, **pool.get_thread_results()}

            return final_results

    '''
        Start a series of worker threads executing I/O tasks (POST requests)
        @param func: task to execute (POST request)
        @param type func: function or method
        @param worker_threads: number of threads to start (int)
        @param url_data_dict: dictionary of url:data pairs where url is the url to request, data is the data to post
            Example: {url1:data1,url2:data2,..}
        @param type url_data_dict: {string:dictionary}
        @return: False in case of wrong inputs or dictionary of json responses for each thread
        @return type: False or python dictionary of JSON objects
    '''

    def __start_thread_pool_send_post(self, func, worker_threads=0, url_data_dict=None):
        if url_data_dict is None:
            url_data_dict = {}

        num_tasks = len(url_data_dict)

        if worker_threads != num_tasks:
            self.print_log_line("Start of worker threads ignored -> "
                                "Num worker threads (%d) does not match url_data_dict length (%d)" % (worker_threads,
                                                                                                      num_tasks),
                                log_level="ERROR", color="RED")
            return False

        if num_tasks <= 100:
            pool = WorkerPool(num_workers=worker_threads, job_type='Thread')
            for key, val in url_data_dict.items():
                pool.add_task_threads(func, self, key, val)

            pool.wait_completion()
            return pool.get_thread_results()
        else:
            thread_results = {}
            chunk_size = 10
            if self.__verbose:
                self.print_log_line("More than %d tasks detected, starting of worker threads in chunks of (%d)"
                                    % (num_tasks, chunk_size), log_level="DEBUG")

            # convert dict to list of pairs [(url1,data1), (url2,data2), ..]
            url_data_list = [(key, val) for key, val in url_data_dict.items()]

            rest_tasks = num_tasks % chunk_size
            start_index = 0
            while num_tasks > 0:
                if num_tasks == rest_tasks:
                    num_tasks -= rest_tasks
                    chunk_size = rest_tasks
                else:
                    num_tasks -= chunk_size

                end_index = start_index + chunk_size

                pool = WorkerPool(num_workers=chunk_size, job_type='Thread')
                for i in range(start_index, end_index):
                    pool.add_task_threads(func, self, url_data_list[i][0], url_data_list[i][1])

                start_index = end_index

                pool.wait_completion()
                thread_results = {**thread_results, **pool.get_thread_results()}

            return thread_results

    # - Public -

    ''' 
        Return the currently in use framework string
        @return: framework
        @return type: string
    '''

    def get_framework_string(self):
        return self.__framework

    '''
        Override settings for the issue type being selected
        @return: None
    '''

    def set_import_mode_test_execution(self):
        self.__import_mode_test_execution = True

    def set_import_mode_test_plan(self):
        self.__import_mode_test_plan = True

    '''
        Override the issue type key
        @param key: issue type key
        @return: None
    '''

    @accepts(str)
    def set_issue_type_key(self, key=None):
        self.__issue_type_key = key

    '''
        Override and reset the issue type key to None (= ALL issue type keys are considered)
        @return: None
    '''

    def reset_issue_type_key(self):
        self.__issue_type_key = None

    '''
        Print members of all or specific test execution(s)
        @param test_execution_key: test execution key or None, if None is passed members of all test executions 
        are printed
        @param type test_execution_key: None or string
        @return: None
    '''

    def print_test_execution_container(self, test_execution_key=None):
        m_logger = Logger(self.__class__.__name__)
        """
        Do not pretty print pointer references IF reference is an instance
        Those instances will be pretty printed anyways
        """
        pointers = ["prev", "next", "parent", "__head", "__tail"]

        test_exec_gen = self.test_exec_iter(test_execution_key)
        test_exec_orig = None
        for test_exec, test_node in test_exec_gen:
            if id(test_exec_orig) != id(test_exec):
                self.print_log_line("%s:" % test_exec, color="GREEN")
                for name, value in test_exec.__dict__.items():
                    # filter out public attributes
                    if name.startswith("__") or name.startswith("_"):
                        if isinstance(value, list):
                            self.print_log_line("   %s: %s" % (name, value))
                            for m_obj in value:
                                self.print_log_line("   %s:" % m_obj)
                                for p_name, p_value in m_obj.__dict__.items():
                                    self.print_log_line("       %s: %s" % (p_name, p_value))
                        else:
                            self.print_log_line("   %s: %s" % (name, value))
                            # __module__ magic attribute of class instance
                            if not list(filter(lambda x: x in name, pointers)) and inspect.getmodule(value):
                                self.print_log_line("       %s:" % value, color="YELLOW")
                                for m_name, m_value in value.__dict__.items():
                                    self.print_log_line("           %s: %s" % (m_name, m_value))
            self.print_log_line("   %s:" % test_node, color="LIGHTGREEN")
            for n_name, n_value in test_node.__dict__.items():
                if isinstance(n_value, list):
                    self.print_log_line("       %s: %s" % (n_name, n_value))
                    for m_obj in n_value:
                        if isinstance(m_obj, dict):
                            pretty_dict(m_logger, m_obj, indent=8)
                        # __module__ magic attribute of class instance
                        elif not list(filter(lambda x: x in n_name, pointers)) and inspect.getmodule(m_obj):
                            self.print_log_line("           %s:" % m_obj, color="PURPLE")
                            for t_name, t_value in m_obj.__dict__.items():
                                self.print_log_line("               %s: %s" % (t_name, t_value))
                        else:
                            self.print_log_line("           %s" % m_obj)
                else:
                    self.print_log_line("       %s: %s" % (n_name, n_value))
                    # __module__ magic attribute of class instance
                    if not list(filter(lambda x: x in n_name, pointers)) and inspect.getmodule(n_value):
                        self.print_log_line("           %s:" % n_value, color="YELLOW")
                        for c_name, c_value in n_value.__dict__.items():
                            self.print_log_line("               %s: %s" % (c_name, c_value))
                            if isinstance(c_value, dict):
                                pretty_dict(m_logger, c_value, indent=6)
                            elif isinstance(c_value, list):
                                for c_obj in c_value:
                                    if not list(filter(lambda x: x in c_name, pointers)) and inspect.getmodule(c_obj):
                                        self.print_log_line("                       %s:" % c_obj, color="BOLD")
                                        for cc_name, cc_value in c_obj.__dict__.items():
                                            self.print_log_line("                           %s: %s" % (cc_name, cc_value))
                                            if isinstance(cc_value, dict):
                                                pretty_dict(m_logger, cc_value, indent=8)
            test_exec_orig = test_exec

    '''
        Iterate through all or a specific test execution(s) and return a (test_execution, test_node) pair
        @param test_execution_key: test execution key or None, if None then all test executions are considered
        @param type test_execution_key: None or string
        @return: (test_execution, test_nodes) pair
        @return type: tuple( TestExecution, TestNode)
    '''

    def test_exec_iter(self, test_execution_key=None):
        test_executions = self.get_current_test_executions(test_execution_key)

        for test_exec in test_executions:
            test_exec_iter = iter(test_exec)
            while True:
                try:
                    yield (test_exec, next(test_exec_iter))
                except StopIteration:
                    break

    '''
        Return a list of all currently available test executions or a specific test execution specified by 
        test_execution_key 
        @param test_execution_key: test execution key , if None is passed all test executions are returned 
        @param type test_execution_key: None or string
        @return: list of test executions with test nodes
        @return type: list
    '''

    def get_current_test_executions(self, test_execution_key=None):
        if test_execution_key:
            return [test_exec for test_exec in self.__test_executions if
                    test_exec.get_key() == test_execution_key]
        return self.__test_executions

    '''
        Read out each test from all stored test executions and update each test in xray with the given 
        status. Before xray is updated, the changes are mirrored into the local test execution structure
        @param test_status: the test status to use ['Execute','FAIL','PASS']
        @param type test_status: string
        @return: dictionary of server responses or GeneralError exception is raised in case of a failure
    '''

    @XrayClientUIPyQtSlot()
    @measure_func_time
    @accepts(str)
    def update_test_status_of_all_tests_in_xray(self, test_status='Execute'):
        test_exec_gen = self.test_exec_iter()

        url_data_dict = {}

        for test_exec, test_node in test_exec_gen:
            if test_node.has_key() \
                    and test_node.has_status():
                test_node_key = test_node.get_key()
                # TODO: Create url string and data dict
                url = "blabla" + test_node_key
                data = {
                    'key_xxx': test_status
                }
                url_data_dict[url] = data

                self.print_log_line("Update local test node structure with attribute: test_status")
                test_node.set_status(test_status)
            else:
                if self.__verbose:
                    if not test_node.has_key():
                        self.print_log_line("TestNode (id %s) in TestExecution (id %s) has no key attribute" %
                                            (test_node.get_id(),
                                             test_exec.get_id()), log_level="ERROR", color="RED")
                    if not test_node.has_status():
                        self.print_log_line("TestNode (id %s) in TestExecution (id %s) has no status attribute" %
                                            (test_node.get_id(),
                                             test_exec.get_id()), log_level="ERROR", color="RED")

        if self.__use_threads:
            # Perform the update in a threaded way
            return self.send_post(url_data_dict)
        else:
            results = {}
            for key, value in url_data_dict.items():
                success, message = self.create_xray_request(key, value)

                if not success:
                    raise GeneralError("Update test status failed for URL (%s) with error: (%s)" % (key, message), "ERROR")

                if self.__is_json(message):
                    results[key] = json.loads(message)
                else:
                    if self.__verbose:
                        self.print_log_line("Could not add response to result dictionary, "
                                            "response is not in JSON format", log_level="ERROR", color="RED")
            return results

    '''
        Return the total number of tests from all test executions
        @return: total number of tests (int)
    '''

    def total_number_of_tests(self):
        return sum([test_exec.__len__() for test_exec in self.get_current_test_executions()])

    '''
        Create a TestExecution and add it to the list of test executions with the following properties:
        TestExecution properties:
        @param test_exec_id: the unique id of the test execution - Non optional
        @param type test_exec_id: int or string
        @param test_exec_key: the key of the test execution
        @param type test_exec_key: string or None
        @param summary: the summary of the test execution (string)
        @param m_description: the description of the test execution (string)
        @param sort_by_rank: sort tests by rank for this test execution (boolean)
        @param test_plan_ids: optional dictionary consisting of key value pairs in the form {id:test_plan_key, ..}
        @return: None
    '''

    @accepts((int, str), (None, str), str, str, bool)
    def create_test_execution(self, test_exec_id, test_exec_key=None, summary="", m_description="", sort_by_rank=False):
        self.__add_test_execution_to_current_test_executions(TestExecution(test_exec_id,
                                                                           test_exec_key,
                                                                           summary,
                                                                           m_description,
                                                                           sort_by_rank
                                                                           ))

    '''
        Create a new TestNode with properties
        properties:
        @param m_id: unique id (int or string) - Not optional
        @param test_key: test case key (string or None)
        @param rank: ordering of test case in the test execution
        @param type rank: int or None
        @param m_self: test case link representing the testcase URL (string)
        @param reporter: reporter (string)
        @param assignee: assignee (string)
        @param description: description (string)
        @param summary: summary (string)
        @param m_type: type of test (Automated[Generic], Manual,..)
        @param type m_type: string
        @param status: test status (FAIL, PASS, ...)
        @parm type status: (string)
        @param definition: List of test steps in the form {steps:[{key,value,..},{key,value}]} or as a String
        @param type definition: python dictionary or String
        @return: the newly created test_node
        @return type: TestNode
    '''

    def create_test_node(self, **kwargs):
        args = {
            'm_id': None,
            'test_key': None,
            'rank': None,
            'm_self': "",
            'reporter': "",
            'assignee': "",
            'description': "",
            'summary': "",
            'm_type': "",
            'status': "",
            'definition': None,
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            self.print_log_line("Ignoring Test Node Creation - Invalid args: %s" % str(tuple(diff)),
                                log_level="ERROR", color="RED")
            return

        args.update(kwargs)
        # add default pointers to previous and next TestNode
        args.update({'prev': None, 'm_next': None})

        new_test_node = TestNode(args['m_id'],
                                 args['test_key'],
                                 args['rank'],
                                 args['m_self'],
                                 args['reporter'],
                                 args['assignee'],
                                 args['description'],
                                 args['summary'],
                                 args['m_type'],
                                 args['status'],
                                 args['definition'],
                                 args['prev'],
                                 args['m_next'])

        return new_test_node

    '''
        Create a new TestSet with properties
        properties:
        @param m_id: unique id (int or string) - Not optional
        @param test_set_key: test set key (string or None)
        @param description: description (string)
        @return type: TestSet
    '''

    def create_test_set(self, **kwargs):
        args = {
            'm_id': None,
            'test_set_key': None,
            'description': "",
            'summary': "",
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            self.print_log_line("Ignoring Test Set Creation - Invalid args: %s" % str(tuple(diff)),
                                log_level="ERROR", color="RED")
            return

        args.update(kwargs)

        new_test_set = TestSet(args['m_id'],
                               args['test_set_key'],
                               args['description'],
                               args['summary'])

        return new_test_set

    '''
        Create a new Precondition with properties
        properties:
        @param m_id: unique id (int or string) - Not optional
        @param precondition_key: precondition key (string or None)
        @param description: description (string)
        @param summary: sumamry (string)
        @return type: Precondition instance
    '''

    def create_precondition(self, **kwargs):
        args = {
            'm_id': None,
            'precondition_key': None,
            'description': "",
            'summary': ""
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            self.print_log_line("Ignoring Precondition Creation - Invalid args: %s" % str(tuple(diff)),
                                log_level="ERROR", color="RED")
            return

        args.update(kwargs)

        new_precondition = Precondition(args['m_id'],
                                        args['precondition_key'],
                                        args['description'],
                                        args['summary'])

        return new_precondition

    '''
        Create a new Bug with properties
        properties:
        @param m_id: unique id (int or string) - Not optional
        @param bug_key: precondition key (string or None)
        @param description: description (string)
        @param summary: sumamry (string)
        @return type: Bug instance
    '''

    def create_bug(self, **kwargs):
        args = {
            'm_id': None,
            'bug_key': None,
            'description': "",
            'summary': "",
            'attachments': None
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            self.print_log_line("Ignoring Bug Creation - Invalid args: %s" % str(tuple(diff)),
                                log_level="ERROR", color="RED")
            return

        args.update(kwargs)

        new_bug = Bug(args['m_id'],
                      args['bug_key'],
                      args['description'],
                      args['summary'],
                      args['attachments'])

        return new_bug

    '''
        Create a new TestPlan with properties
        properties:
        @param m_id: unique id (int or string) - Not optional
        @param test_plan_key: test plan key (string or None)
        @return type: TestPlan instance
    '''

    def create_test_plan(self, **kwargs):
        args = {
            'm_id': None,
            'test_plan_key': None,
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            self.print_log_line("Ignoring Test Plan Creation - Invalid args: %s" % str(tuple(diff)),
                                log_level="ERROR", color="RED")
            return

        args.update(kwargs)

        new_test_plan = TestPlan(args['m_id'],
                                 args['test_plan_key'])

        return new_test_plan

    # ---- methods decorated ----

    '''
            Add an attachment to a given bug
            A bug might have more than one attachment
            @param bug: the bug instance for which the attachment is added
            @param type bug: Bug
            @param attachment: the absolute path to the attachment (including attachment file name)
            @param type attachment: str
            @return: None
    '''

    @accepts(Bug, str)
    def add_attachment_to_bug(self, bug, attachment):
        bug.add_attachment(attachment)

    '''
        Set a summary for a TestExecution with given key
        @param test_execution_key: the test execution with this key will be used
        @param type test_execution_key: string
        @param summary: summary (str)
        @return: None
    '''

    @accepts(str, str)
    def add_summary_to_test_execution_with_key(self, test_execution_key, summary):
        test_execution = list(filter(lambda test_exec: test_exec.get_key() == test_execution_key,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Could not find test execution with key %s in list of test executions" %
                    test_execution_key,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Multiple test executions with the same key %s detected!" % test_execution_key,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]
        test_execution.set_summary(summary)

    '''
        Set a summary for a TestExecution with given id
        @param test_execution_id: the test execution with this id will be used
        @param type test_execution_id: string or int
        @param summary: summary (str)
        @return: None
    '''

    @accepts((str, int), str)
    def add_summary_to_test_execution_with_id(self, test_execution_id, summary):
        test_execution = list(filter(lambda test_exec: test_exec.get_id() == test_execution_id,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Could not find test execution with id %s in list of test executions" %
                    test_execution_id,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Multiple test executions with the same id %s detected!" % test_execution_id,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]
        test_execution.set_summary(summary)

    '''
        Set a description for a TestExecution with given key
        @param test_execution_key: the test execution with this key will be used
        @param type test_execution_key: string
        @param description: description (str)
        @return: None
    '''

    @accepts(str, str)
    def add_description_to_test_execution_with_key(self, test_execution_key, description):
        test_execution = list(filter(lambda test_exec: test_exec.get_key() == test_execution_key,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Could not find test execution with key %s in list of test executions" %
                    test_execution_key,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Multiple test executions with the same key %s detected!" % test_execution_key,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]
        test_execution.set_description(description)

    '''
        Set a description for a TestExecution with given id
        @param test_execution_id: the test execution with this id will be used
        @param type test_execution_id: string or int
        @param description: description (str)
        @return: None  
    '''

    @accepts((str, int), str)
    def add_description_to_test_execution_with_id(self, test_execution_id, description):
        test_execution = list(filter(lambda test_exec: test_exec.get_id() == test_execution_id,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Could not find test execution with id %s in list of test executions" %
                    test_execution_id,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding summary - Multiple test executions with the same id %s detected!" % test_execution_id,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]
        test_execution.set_description(description)

    '''
        Set the MasterData for a TestExecution with given key
        @param test_execution_key: the test execution with this key will be used
        @param type test_execution_key: string
        @param master_data_instance: the MasterData instance
        @param type master_data_instance: instance
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts(str, "IGNORE")
    def add_master_data_to_test_execution_with_key(self, test_execution_key, master_data_instance):
        test_execution = list(filter(lambda test_exec: test_exec.get_key() == test_execution_key,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding MasterData - Could not find test execution with key %s in list of test executions" %
                    test_execution_key,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding MasterData - Multiple test executions with the same key %s detected!" % test_execution_key,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]
        test_execution.set_master_data(master_data_instance)

    '''
        Add the MasterData for a TestExecution with given id
        @param test_execution_id: the test execution with this id will be used
        @param type test_execution_id: string or int
        @param master_data_instance: the MasterData instance
        @param type master_data_instance: instance
        @return: None  
    '''

    @check_authorization("Pytefw")
    @accepts((str, int), "IGNORE")
    def add_master_data_to_test_execution_with_id(self, test_execution_id, master_data_instance):
        test_execution = list(filter(lambda test_exec: test_exec.get_id() == test_execution_id,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding MasterData - Could not find test execution with id %s in list of test executions" %
                    test_execution_id,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding MasterData - Multiple test executions with the same id %s detected!" % test_execution_id,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]
        test_execution.set_master_data(master_data_instance)

    '''
        Add a test with defined properties to a given test execution
            The test can either be newly created using the properties given 
            or a test node instance can be passed as argument
        @param test_execution_key: the test execution with this key will be used
        @param type test_execution_key: string
        @param test_node_instance: test_node instance to be used
        @param type test_node_instance: None or TestNode
        
        Test properties **kwargs:
        @param m_id: unique id (int or string) - Non optional
        @param test_key: test case key (string or None)
        @param rank: ordering of test case in the test execution
        @param type rank: int or None
        @param m_self: test case link representing the testcase URL (string)
        @param reporter: reporter (string)
        @param assignee: assignee (string)
        @param description: description (string)
        @param summary: summary (string)
        @param m_type: type of test (Automated[Generic], Manual,..)
        @param type m_type: string
        @param status: test status (FAIL, PASS, ...)
        @parm type status: (string)
        @param definition: List of test steps in the form {steps:[{key,value,..},{key,value}]} or as a String
        @param type definition: python dictionary or String
        @return: None
    '''

    @accepts(str, (None, TestNode))
    def add_test_node_to_test_execution_with_key(self,
                                                 test_execution_key,
                                                 test_node_instance=None,
                                                 **kwargs):
        args = {
            'm_id': None,
            'test_key': None,
            'rank': None,
            'm_self': "",
            'reporter': "",
            'assignee': "",
            'description': "",
            'summary': "",
            'm_type': "",
            'status': "",
            'definition': None,
        }
        args.update(kwargs)

        test_execution = list(filter(lambda test_exec: test_exec.get_key() == test_execution_key,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Test - Could not find test execution with key %s in list of test executions" %
                    test_execution_key,
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Test - Multiple test executions with the same key %s detected!" % test_execution_key,
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]

        test_execution.append_test_node(test_node_instance, **args)

    '''
         Add a test with defined properties to a given test execution
            The test can either be newly created using the properties given 
            or a test node instance can be passed as argument
        @param test_execution_id: the test execution with this unique id will be used
        @param type test_execution_id: int or string
        @param test_node_instance: test_node instance to be used
        @param type test_node_instance: None or TestNode
        
        Test properties **kwargs:
        @param m_id: unique id (int or string) - Non optional
        @param test_key: test case key (string or None)
        @param rank: ordering of test case in the test execution
        @param type rank: int or None
        @param m_self: test case link representing the testcase URL (string)
        @param reporter: reporter (string)
        @param assignee: assignee (string)
        @param description: description (string)
        @param summary: summary (string)
        @param m_type: type of test (Automated[Generic], Manual,..)
        @param type m_type: string
        @param status: test status (FAIL, PASS, ...)
        @parm type status: (string)
        @param definition: List of test steps in the form {steps:[{key,value,..},{key,value}]} or as a String
        @param type definition: python dictionary or String
        @return: None
    '''

    @accepts((str, int), (None, TestNode))
    def add_test_node_to_test_execution_with_id(self,
                                                test_execution_id,
                                                test_node_instance=None,
                                                **kwargs):
        args = {
            'm_id': None,
            'test_key': None,
            'rank': None,
            'm_self': "",
            'reporter': "",
            'assignee': "",
            'description': "",
            'summary': "",
            'm_type': "",
            'status': "",
            'definition': None,
        }
        args.update(kwargs)

        test_execution = list(filter(lambda test_exec: test_exec.get_id() == test_execution_id,
                                     self.get_current_test_executions()))

        if not test_execution:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Test - Could not find test execution with id %s in list of test executions" %
                    str(test_execution_id),
                    log_level="ERROR", color="RED")
            return

        if len(test_execution) > 1:
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Test - Multiple test executions with the same id %s detected!" % str(test_execution_id),
                    log_level="ERROR", color="RED")
                return

        test_execution = test_execution[0]

        if (test_node_instance and test_node_instance.get_id() in test_execution) or args['m_id'] in test_execution:
            if test_node_instance:
                test_node_id = test_node_instance.get_id()
            else:
                test_node_id = args['m_id']
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Test - TestNode with id %s already exists in TestExecution with id %s!"
                    % (str(test_node_id), str(test_execution_id)), log_level="ERROR", color="RED")
            return

        test_execution.append_test_node(test_node_instance, **args)

    '''
        Add a test plan with defined properties to a given test execution
            The test plan can either be newly created using the properties given 
            or a test plan instance can be passed as argument
        A test execution might be part of more than one test plan
        @param test_exec_key: the test execution identified by key for which the test plan is created
        @param type test_exec_key: string
        @param test_plan_instance: test_plan instance to be used
        @param type test_pan_instance: None or TestPlan
        test plan properties:
        @param m_id: unique id of the test plan (int or string) - Non optional
        @param test_plan_key: key of the test plan (string or None)
        @return: None or AttributesError exception in case no m_id was provided
    '''

    @accepts(str, (None, TestPlan))
    def add_test_plan_to_test_execution_with_key(self,
                                                 test_exec_key,
                                                 test_plan_instance=None,
                                                 **kwargs):
        args = {
            'm_id': None,
            'test_plan_key': None,
        }
        args.update(kwargs)

        success = False
        for test_execution in self.get_current_test_executions():
            if test_execution.get_key() == test_exec_key:
                test_execution.append_test_plan(test_plan_instance, **args)
                success = True
                break

        if not success:
            if self.__verbose:
                self.print_log_line(
                    "Could not add Test Plan to Test Execution "
                    "- Could not find test execution with key %s in list of test executions" %
                    test_exec_key,
                    log_level="ERROR", color="RED")
            return

    '''
        Add a test plan with defined properties to a given test execution
            The test plan can either be newly created using the properties given 
            or a test plan instance can be passed as argument
        A test execution might be part of more than one test plan
        @param test_exec_id: the test execution identified by the unique id for which the test plan is created 
        @param type test_exec_id: int or string
        @param test_plan_instance: test_plan instance to be used
        @param type test_pan_instance: None or TestPlan
        test plan properties:
        @param m_id: unique id of the test plan (int or string) - Non optional
        @param test_plan_key: key of the test plan (string or None)
        @return: None or AttributesError exception in case no m_id was provided
    '''

    @accepts(str, (None, TestPlan))
    def add_test_plan_to_test_execution_with_id(self,
                                                test_exec_id,
                                                test_plan_instance=None,
                                                **kwargs):
        args = {
            'm_id': None,
            'test_plan_key': None,
        }
        args.update(kwargs)

        success = False
        default_error_msg = "Could not add Test Plan to Test Execution " \
                            "- Could not find test execution with id %s in list of test executions" % test_exec_id
        for test_execution in self.get_current_test_executions():
            if test_execution.get_id() == test_exec_id:
                if (test_plan_instance and test_plan_instance.get_id() in test_execution) or args['m_id'] in test_execution:
                    if test_plan_instance:
                        test_plan_id = test_plan_instance.get_id()
                    else:
                        test_plan_id = args['m_id']
                    default_error_msg = "Ignore adding TestPlan - TestPlan with id %s already exists in " \
                                        "TestExecution with id %s!" \
                                        % (str(test_plan_id), str(test_exec_id))
                    break
                test_execution.append_test_plan(test_plan_instance, **args)
                success = True
                break

        if not success:
            if self.__verbose:
                self.print_log_line(default_error_msg, log_level="ERROR", color="RED")
            return

    '''
        Add a test set with defined properties to a given test node
            The test set can either be newly created using the properties given 
            or a test set instance can be passed as argument
        A test node might be part of more than one test set
        @param test_node: the test node identified by the instance
        @param type test_node: TestNode
        @param test_set_instance: test_set instance to be used
        @param type test_set_instance: None or TestSet
        test set properties:
        @param m_id: unique id of the test set (int or string) - Non optional
        @param test_set_key: key of the test set (string or None)
        @param description: description (string)
        @return: None
    '''

    @accepts(TestNode, (None, TestSet))
    def add_test_set_to_test_node(self, test_node, test_set_instance=None, **kwargs):
        args = {
            'm_id': None,
            'test_set_key': None,
            'description': "",
            'summary': "",
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            if self.__verbose:
                self.print_log_line("Ignore adding Test Set - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
            return
        args.update(kwargs)

        if test_set_instance:
            test_set_id = test_set_instance.get_id()
        else:
            test_set_id = args['m_id']

        if list(filter(lambda test_set: test_set.get_id() == test_set_id, test_node.get_test_sets())):
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding TestSet - TestSet with id %s already exists for TestNode with id %s!"
                    % (str(test_set_id), str(test_node.get_id())), log_level="ERROR", color="RED")
            return

        test_node.append_test_set(test_set_instance, **args)

    '''
        Add a precondition with defined properties to a given test node
            The precondition can either be newly created using the properties given 
            or a precondition instance can be passed as argument
        A test node might have more than one precondition
        @param test_node: the test node identified by the instance
        @param type test_node: TestNode
        @param precondition_instance: precondition instance to be used
        @param type precondition_instance: None or Precondition
        precondition properties:
        @param m_id: unique id of the precondition (int or string) - Non optional
        @param precondition_key: key of the precondition (string or None)
        @param description: description (string)
        @param summary: summary (string)
        @return: None
    '''

    @accepts(TestNode, (None, Precondition))
    def add_precondition_to_test_node(self, test_node, precondition_instance=None, **kwargs):
        args = {
            'm_id': None,
            'precondition_key': None,
            'description': "",
            'summary': ""
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            if self.__verbose:
                self.print_log_line("Ignore adding Precondition - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
            return
        args.update(kwargs)

        if precondition_instance:
            precondition_id = precondition_instance.get_id()
        else:
            precondition_id = args['m_id']

        if list(filter(lambda precondition: precondition.get_id() == precondition_id, test_node.get_preconditions())):
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Precondition - Precondition with id %s already exists for TestNode with id %s!"
                    % (str(precondition_id), str(test_node.get_id())), log_level="ERROR", color="RED")
            return

        test_node.append_precondition(precondition_instance, **args)

    '''
        Add a bug with defined properties to a given test node
            The bug can either be newly created using the properties given 
            or a bug instance can be passed as argument
        A test node might have more than one bug
        @param test_node: the test node identified by the instance
        @param type test_node: TestNode
        @param bug_instance: bug instance to be used
        @param type bug_instance: None or Bug
        bug properties:
        @param m_id: unique id of the bug (int or string) - Non optional
        @param precondition_key: key of the bug (string or None)
        @param description: description (string)
        @param summary: summary (string)
        @return: None
    '''

    @accepts(TestNode, (None, Bug))
    def add_bug_to_test_node(self, test_node, bug_instance=None, **kwargs):
        args = {
            'm_id': None,
            'bug_key': None,
            'description': "",
            'summary': ""
        }

        diff = set(kwargs.keys()) - set(args.keys())
        if diff:
            if self.__verbose:
                self.print_log_line("Ignore adding Bug - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
            return
        args.update(kwargs)

        if bug_instance:
            bug_id = bug_instance.get_id()
        else:
            bug_id = args['m_id']

        if list(filter(lambda bug: bug.get_id() == bug_id, test_node.get_bugs())):
            if self.__verbose:
                self.print_log_line(
                    "Ignore adding Bug - Bug with id %s already exists for TestNode with id %s!"
                    % (str(bug_id), str(test_node.get_id())), log_level="ERROR", color="RED")
            return

        test_node.append_bug(bug_instance, **args)

    '''
        Add a requirement string to a given test node
        @param test_node: the test node identified by the instance
        @param type test_node: TestNode
        @param requirement: the requirement which is added to the list of requirements
        @param type requirement: str
        @return: None
    '''

    @accepts(TestNode, str)
    def add_requirement_to_test_node(self, test_node, requirement):
        test_node.append_requirement(requirement)

    '''
        Set the TestClass which runs the TestNode as testcase
        @param test_node: the test node for which the test class is set
        @param type test_node: TestNode
        @param test_class_instance: the test class instance (Pytefw support only)
        @param type test_class_instance: instance of type TestClass
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts(TestNode, 'IGNORE')
    def set_test_class_for_test_node(self, test_node, test_class_instance):
        test_node.set_test_class(test_class_instance)

    '''
        Export test results to Xray
        Before the results are exported to Xray the XmlHandler creates the test execution container structure 
        from xml results
    '''

    @measure_func_time
    def start_export(self):
        # The export itself will be handled in XmlHandlerObserver.update()
        self.__xml_handler.create_test_execution_container_from_xml()
        if self.__print_data_containers:
            self.print_test_execution_container()

        # process data
        # .....

        # clear test execution container after export is finished
        # self._clear_test_execution_container()

    '''
        Import tests from Xray based on a given issue type and issue type key (can be None)
        In case several imports are started after the Initial Import, override the issue type and issue type key
        to specify which type is going to be imported
    '''

    @XrayClientUIPyQtSlot
    @measure_func_time
    def start_import(self):
        url = "..."
        success, message = self.create_xray_request(url)
        if not success:
            raise ImportFailure("Import from Xray Server failed with message %s" % message, "ERROR")
        else:
            json_data = message

        # TODO parse xray response, fetch executions and tests
        # for data in json_data..
        # self.create_test_execution('...)
        # self.add_test_to_test_execution_with_key(..)
        self.print_log_line("Adding update to processing queue..")
        self.processing_queue.produce("XrayClient update")
        self.print_log_line("Notify XMLGenerator..")
        self.xml_handler_notifier.notify_observers()

    '''
        Create a xray request (GET or POST) non threaded and return the result 
        @param url: resource requested including the issue type
        @param type url: string
        @param data: data to be linked if the request is of type POST (default GET)
        @param type data: python dictionary
        @return: If success: True and json data, if not success: False and error message
        @return type: If success: boolean and json, if not success: boolean and error string   
    '''

    @accepts(str, (None, dict))
    def create_xray_request(self, url, data=None):
        if not data:
            try:
                json_data = self.jira_connector.send_get(url)
            except (InvalidResponse, RequestException) as e:
                return False, e
        else:
            try:
                json_data = self.jira_connector.send_post(url, data)
            except (InvalidResponse, RequestException) as e:
                return False, e

        return True, json_data

    '''
        Execute the xray request (GET) in a Thread and return the result 
        @param url: resource requested including the issue type
        @param type url: string
        @return: If success: json data, if not success: error message
        @return type: If success: json, if not success: string   
    '''

    @xray_get_request_threaded
    def send_get(self, url):
        try:
            json_data = self.jira_connector.send_get(url)
        except (InvalidResponse, RequestException) as e:
            return e

        return json_data

    '''
        Execute the xray request (POST) in a Thread and return the result 
        @param url: resource requested including the issue type
        @param type url: string
        @param data: data to be linked if the request is of type POST (default GET)
        @param type data: python dictionary
        @return: If success: json data, if not success: error message
        @return type: If success: json, if not success: string   
    '''

    @xray_post_request_threaded
    def send_post(self, url, data=None):
        try:
            json_data = self.jira_connector.send_post(url, data)
        except (InvalidResponse, RequestException) as e:
            return e

        return json_data


'''
    Check for mandatory arguments
    @param o_parser: the option parser instance
    @param type o_parser: OptionParser
    @return: None or parser exception is thrown
'''


def check_required_arguments(o_parser):
    missing_options = []
    for option in o_parser.option_list:
        if re.match(r'^\[REQUIRED\]', option.help) and not option.default:
            missing_options.append(option._long_opts)
    if len(missing_options) > 0:
        o_parser.error('Missing REQUIRED parameters: ' + str(missing_options))


if __name__ == '__main__':
    from optparse import OptionParser

    logger = Logger("__main__")


    class OptParser(OptionParser):
        def format_description(self, formatter):
            return self.description


    description = "usage: %prog [options] arg1 arg2"
    parser = OptParser(description="""Note: String Options MODE, FRAMEWORK, FRAMEWORK_CONFIG_LOCATION are CASE SENSITIVE""")
    parser.add_option("-m", "--mode", dest="mode", default="Import", type="str",
                      help="Run the Xray Client either in 'Import' OR 'Export' mode"
                           "[default: %default] ")
    parser.add_option("-b", "--import_mode_test_execution", action="store_true",
                      dest="import_mode_test_execution", default=False,
                      help="Import tests by issue type test execution ( use with option -m ) [default: %default]")
    parser.add_option("-c", "--import_mode_test_plan", action="store_true",
                      dest="import_mode_test_plan", default=False,
                      help="Import tests by issue type test plan ( use with option -m ) [default: %default]")
    parser.add_option("-k", "--key", dest="key", default=None, type="str",
                      help="Depending on the import mode, specify the issue type key. "
                           "If no key is provided all test executions OR test plans are imported "
                           "( use with option combo -m -b OR -m -c) [default: %default] ")
    parser.add_option("-f", "--framework", dest="framework", default="Pytefw", type="str",
                      help="Use one of two supported frameworks ['Pytefw', 'Ita'] to generate xml output or results "
                           "[default: %default]")
    parser.add_option("-g", "--framework_config_location", dest="framework_config_location", default="Local", type="str",
                      help="Choose where the framework config resides: 'Remote' OR 'Local' "
                           "[default: %default]")
    parser.add_option("-d", "--framework_config_dir", dest="framework_config_dir", default="/", type="str",
                      help="framework specific local configuration directory [default: %default]")
    parser.add_option("-e", "--remote_host", dest="remote_host", default="myserver.com", type="str",
                      help="Remote server"
                           "[default: %default]")
    parser.add_option("-w", "--ssh_conn_timeout", dest="ssh_conn_timeout", default=1, type="int",
                      help="Remote server connection timeout"
                           "[default: %default second(s)]")
    parser.add_option("-i", "--remote_user", dest="remote_user", default="root", type="str",
                      help="Username for remote server"
                           "[default: %default]")
    parser.add_option("-j", "--remote_password", dest="remote_password", default="root", type="str",
                      help="Password for Remote Server"
                           "[default: %default]")
    parser.add_option("-o", "--remote_config_dir", dest="remote_config_dir", default="/path/to/config", type="str",
                      help="Remote server configuration directory"
                           "[default: %default]")
    parser.add_option("-r", "--rest_api_endpoint", dest="rest_api_endpoint",
                      default="https://mbition.atlassian.net/rest/raven/1.0/api", type="str",
                      help="[REQUIRED] Base URL of Xray REST API, URL ending similar to '/rest/raven/1.0/api' "
                           "[default: %default]")
    parser.add_option("-t", "--connection_timeout", dest="connection_timeout", default=5, type="int",
                      help="Abort JIRA connection attempt if timeout has exceeded [default: %default seconds]")
    parser.add_option("-n", "--connection_attempts", dest="connection_attempts", default=5, type="int",
                      help="Try to reconnect to the JIRA endpoint this amount of times in case the first connection "
                           "attempt failed [default: %default]")
    parser.add_option("-x", "--use_threads", action="store_true", dest="use_threads", default=False,
                      help="Use threading for I/O operations like GET and POST [default: %default]")
    parser.add_option("-a", "--auth", dest="auth", default="Basic", type="str",
                      help="Choose between 'Basic' and 'OAuth1' Authentication [default: %default]")
    parser.add_option("-u", "--user", dest="user", default="root",
                      help="username for Basic Authentication [default: %default]")
    parser.add_option("-p", "--password", dest="password", default="root",
                      help="password for Basic Authentication [default: %default]")
    parser.add_option("-s", "--verify_ssl_certs", action="store_true", dest="verify_ssl_certs", default=False,
                      help="Enable server certificate verification when using HTTPS [default: %default]")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Enable debug logs for analysis [default: %default]")
    parser.add_option("-z", "--data_containers", action="store_true", dest="data_containers", default=False,
                      help="Print internal data structure containers for further analysis [default: %default]")

    (options, args) = parser.parse_args()
    check_required_arguments(parser)

    xray_client = XrayClient(
        options.mode,
        options.import_mode_test_execution,
        options.import_mode_test_plan,
        options.key,
        options.framework,
        options.framework_config_location,
        options.framework_config_dir,
        options.remote_host,
        options.ssh_conn_timeout,
        options.remote_user,
        options.remote_password,
        options.remote_config_dir,
        options.rest_api_endpoint,
        options.use_threads,
        options.auth,
        options.user,
        options.password,
        options.connection_timeout,
        options.connection_attempts,
        options.verify_ssl_certs,
        options.verbose,
        options.data_containers
    )
