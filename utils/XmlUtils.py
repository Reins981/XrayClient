#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 14.03.2019

@author: reko8680
@Coding Guidelines: XmlUtils methods, functions and variables shall be written in Lowercase separated by _
"""

import os
import sys
import inspect
import copy
import shutil
import fnmatch
import XrayClientCs
from lxml import etree
from pathlib import Path
from Logger import Logger
from Shell import SshShell
from TestExecutionContainer import Bug, TestNode
from DataStructUtils import ProcessingQueue, pretty_dict
from DecoratorUtils import TimedFunc, measure_func_time, accepts, add_tags_as_suffix_to_path, check_authorization, \
    XrayClientUIPyQtSlot
from Observer import Observer, Observable
from ExceptionUtils import InvalidHandlerMode, InvalidType, AttributesError, InvalidFrameworkString, GeneralError, \
    InvalidFrameworkConfigLocation, FileError

# globals

'''
 Consecutively test case counter defining the rank of a test case according to the position in the xml config file
'''

test_case_rank = 0

# -- Helper functions --

'''
    Constructor for TestClass, TestSuite, MasterData
    @param data: A dictionary containing key, value pairs for member initialization
    @return: None
'''


@accepts(dict)
def init_data(self, data):
    for key, value in data.items():
        if key == "class":
            key = "m_class"
        if key == "id":
            key = "m_id"
        setattr(self, key, value)


'''
    Create a member attribute represented by a key and a value
    @param key: The name of the member attribute (string)
    @param data: The value of the member attribute, can be any type
    @return: None
'''


def set_data(self, key, data):
    if key == "class":
        key = "m_class"
    if key == "id":
        key = "m_id"
    setattr(self, key, data)


'''
    Add data to a given list member attribute represented by a key
    @param key: The name of the member attribute (string)
    @param data: The value to be added to the list member attribute if it exists, can be any type
    @return: None
'''


def append_data(self, key, data):
    value = getattr(self, key, None)
    if value is not None and isinstance(value, list):
        value.append(data)

    # -- Etree Helpers ---


'''
    Get the attribute of etree._Element
    @param elem: etree element
    @param type elem: etree._Element
    @param attribute: attribute key
    @param type attribute: string OR int
    @param default_value: The default value if attribute is not found
    @param type default_value: None OR string or int
    @return: The value of attribute OR default_value if attribute is not found
'''


@accepts(etree._Element, (str, int), (None, str, int))
def get_attribute(elem, attribute, default_value=None):
    return elem.get(attribute) or default_value


'''
    Check if an etree._Element has a certain value
    @param elem: etree element
    @param type elem: etree._Element
    @param attribute_value: attribute value
    @param type attribute_value: string
    @return: True or False (boolean)
'''


@accepts(etree._Element, str)
def has_attribute_value(elem, attribute_value):
    return attribute_value in elem.values()


'''
    Check if an etree._Element has a certain tag
    @param elem: etree element
    @param type elem: etree._Element
    @param tag: tag
    @param type tag: string
    @return: True or False (boolean)
'''


@accepts(etree._Element, str)
def has_tag(elem, tag):
    return tag == elem.tag


'''
    Get the text of an etree._Element
    @param elem: etree element
    @param type elem: etree._Element
    @param default_text: The default text if no text is provided
    @param type default_text: None OR string
    @return: The text of the etree element OR default_text if no text was found
'''


@accepts(etree._Element, (str, None))
def get_text(elem, default_text):
    return elem.text or default_text


'''
    TestSuites represents a sorted linked list which consists of TestSuite instances.
'''


class TestSuites(Logger):
    """
        A TestSuites linked list has a unique Id
        @param m_id: unique id
        @param type m_id: int or string
    """

    @accepts((int, str))
    def __init__(self, m_id):
        Logger.__init__(self, self.__class__.__name__)
        self.__id = m_id
        self.__head = None
        self.__tail = None
        self.__max_test_suites = 0

        '''
        The TestClasses which are initialized and executed. If nested TestSuites exist, 
        all of them together form one parameterized TestClass 
        '''
        self.__executed_test_classes = []

        # Master data from testresult.xml
        self.__master_data = None

    '''
        Get the length of this TestSuites instance
        @return: number of TestSuites (int)
    '''

    def __len__(self):
        return self.__max_test_suites

    '''
        destructor
    '''

    def __del__(self):
        del self

    '''
        create a TestSuites iterator
    '''

    def __iter__(self):
        self.test_suite_number = 0
        self.start = True
        self.current_test_suite = self.__head
        return self

    '''
        get next TestSuite from TestSuites
    '''

    def __next__(self):
        if self.test_suite_number < self.__max_test_suites:
            self.test_suite_number += 1
            if self.start:
                self.start = False
                return self.current_test_suite
            else:
                current_suite = self.__get_next_test_suite(self.current_test_suite)
                self.current_test_suite = current_suite
                return current_suite
        else:
            raise StopIteration

    # -- PRIVATE --

    '''
        Get TestSuite by id from the TestSuites Linked List
        @param test_suite_id: unique id
        @param type test_suite_id: str, int
        @return: TestSuite
        @return type TestSuite: TestSuite instance
    '''

    @XrayClientUIPyQtSlot()
    def __getitem__(self, test_suite_id):
        return self.__get_test_suite_by_id(test_suite_id)

    '''
        Check if TestSuites contains a TestSuite with the given id
        @param test_suite_id: unique id
        @param type test_suite_id: str, int
        @return: True or False (boolean) 
    '''

    def __contains__(self, test_suite_id):
        if self.__get_test_suite_by_id(test_suite_id):
            return True
        return False

    '''
        Get TestSuite by test_suite_id
        @param test_suite_id: unique id
        @param type test_suite_id: str, int
        @return: TestSuite or None
        @return type TestSuite: TestSuite instance or None
    '''

    def __get_test_suite_by_id(self, test_suite_id):
        current_suite = self.__head

        while current_suite is not None:
            if current_suite.get_id() == test_suite_id:
                return current_suite
            current_suite = self.__get_next_test_suite(current_suite)
        return None

    '''
        Check if TestSuite has a successor 
        @param current_suite: the TestSuite to be checked
        @param type current_suite: TestSuite instance
        @return: True or False (boolean)
    '''

    def __has_next_test_suite(self, current_suite):
        if current_suite.next is not None:
            return True
        return False

    '''
        Check the successor of the TestSuite
        @param current_suite: the TestSuite for which the successor is returned
        @param type current_suite: TestSuite instance
        @return: successor TestSuite
        @return type: TestSuite
    '''

    def __get_next_test_suite(self, current_suite):
        if not self.__has_next_test_suite(current_suite):
            return None
        return current_suite.next

    # -- PUBLIC --

    '''
        Add the TestClasses which are executed by the TestSuites
        @param test_class: TestClass
        @param type test_class: TestClass instance
        @return: None
    '''

    def add_test_class(self, test_class):
        self.__executed_test_classes.append(test_class)

    '''
        Set the MasterData
        @param master_data: MasterData
        @param type master_data: MasterData instance
        @return: None
    '''

    def set_master_data(self, master_data):
        self.__master_data = master_data

    '''
        Get the TestClasses which are executed by the TestSuites
        @return: list of TestClass instances
        @return type: list
    '''

    def get_test_classes(self):
        return self.__executed_test_classes

    '''
        Get the MasterData
        @return: MasterData
        @return type: MasterData instance
    '''

    def get_master_data(self):
        return self.__master_data

    '''
        Get the unique Id of the TestSuites Linked List
        @return: unique Id
        @return type: str or int
    '''

    def get_id(self):
        return self.__id

    '''
        Get a reference to the FIRST TestSuite instance
        @return: TestSuite
        @return type: TestSuite instance
    '''

    def get_head(self):
        return self.__head

    '''
        Get a reference to the LAST TestSuite instance
        @return: TestSuite
        @return type: TestSuite instance
    '''

    def get_tail(self):
        return self.__tail

    '''
        Add a TestSuite with properties to the TestSuites LinkedList
        @param test_suite_instance: TestSuite instance to be used
        @param type test_suite_instance: TestSuite
        @return: None
    '''

    def append_test_suite(self,
                          test_suite_instance):

        if self.__head is None:
            self.__head = self.__tail = test_suite_instance
        else:
            test_suite_instance.prev = self.__tail
            test_suite_instance.next = None
            self.__tail.next = test_suite_instance
            self.__tail = test_suite_instance
        self.__max_test_suites += 1


class XmlHandler(Logger):
    """
        Create a Xml Handler instance which acts as XrayClientObserver or XrayClientNotifier
        @param mode: "XrayClientObserver" or "XrayClientNotifier"
            if mode == "XrayClientObserver": fetch xray client updates and data (default)
            if mode == "XrayClientNotifier": notify and send data to xray client
        @param type mode: string
        @param framework: choose for which framework the xml output or results will be generated
            can be: "Pytefw" or "Ita"
        @param type framework: string
        @param framework_config_location: choose where the framework config resides: 'Remote' or 'Local'
        @param type framework_config_location: str
        @param framework_config_dir: framework specific local configuration directory
        @param type framework_config_dir: string
        @param remote_host: framework specific local configuration directory (str)
        @param ssh_conn_timeout: ssh connection timeout in seconds (int)
        @param remote_user: framework specific local configuration directory (str)
        @param remote_password: framework specific local configuration directory (str)
        @param framework_remote_config_dir: framework specific remote configuration directory (str)
        @param xray_client_instance: xray client instance
            if mode == "XrayClientNotifier": this xray client instance will be added to the list of observers meaning
            that the xray client will be notified from the XmlHandler upon changes
        @param type xray_client_instance: None or XrayClient instance
        @param processing_queue: queue which stores results of type TestExecution, processing_queue will be created
            if mode == "XrayClientNotifier"
        @param type processing_queue: None or dequeue()
        @param verbose: enable or disable debug log output (boolean)
        @param print_data_containers: print internal data structure containers for further analysis (boolean)
        @return: None or (InvalidHandlerMode, InvalidType, AttributesError) exception is raised
    """

    __paths_to_test_configs = []

    @XrayClientUIPyQtSlot()
    @accepts(str, str, str, str, str, int, str, str, str, XrayClientCs, ProcessingQueue, bool, bool)
    def __init__(self,
                 mode="XrayClientObserver",
                 framework="Pytefw",
                 framework_config_location="",
                 framework_config_dir="",
                 remote_host="",
                 ssh_conn_timeout=1,
                 remote_user="",
                 remote_password="",
                 framework_remote_config_dir="",
                 xray_client_instance=None,
                 processing_queue=None,
                 verbose=False,
                 print_data_containers=False):
        super().__init__(self.__class__.__name__)

        # Special exception flag
        self.__contructor_exception_raised = False
        if framework != "Pytefw" and framework != "Ita":
            self.__contructor_exception_raised = True
            raise InvalidFrameworkString("Chosen Framework %s is invalid! - "
                                         "supported frameworks ['Pytefw, 'Ita']" % framework, "ERROR")

        self.__mode = mode
        self.__framework = framework
        self.__framework_config_location = framework_config_location
        self.__framework_config_dir = framework_config_dir
        self.__remote_host = remote_host
        self.__ssh_conn_timeout = ssh_conn_timeout
        self.__remote_user = remote_user
        self.__remote_password = remote_password
        self.__framework_remote_config_dir = framework_remote_config_dir
        self.__xray_client_instance = xray_client_instance
        self.__processing_queue = processing_queue
        self.__verbose = verbose
        self.__print_data_containers = print_data_containers

        # Pytefw structure for storing TestSuites Linked Lists
        self.__test_suites_pytefw = []
        # Ptefw structure for storing test suite parents which have been traversed already
        self.__traversed_parent_test_suites = []
        # the home directory of the framework, will be calculated on startup
        self.__framework_home_dir = None
        # the shell object which is created for remote connections
        self.__shell = None

        self.__framework_map = {
            "Pytefw": {
                "create_xml": self.__create_pytefw_xml_structure,
                "parse_xml": self.__parse_pytefw_xml_structure,
                "fetch_local_config": self.__fetch_pytefw_local_test_configuration,
                "fetch_remote_config": self.__fetch_pytefw_remote_test_configuration
            },
            "Ita": {
                "create_xml": self.__create_ita_xml_structure,
                "parse_xml": self.__parse_ita_xml_structure,
                "fetch_local_config": self.__fetch_ita_local_test_configuration,
                "fetch_remote_config": self.__fetch_ita_remote_test_configuration
            }
        }

        # create the observer or notifier instance, add all observers
        if verbose:
            self.print_log_line("Starting with mode (%s)" % mode, log_level="DEBUG")
        # Setup the paths to configuration files first
        self.__setup_test_config_paths()
        if self.__mode == "XrayClientObserver":
            self.xray_client_observer = XmlHandler.XrayClientObserver(self, verbose=verbose)
        elif self.__mode == "XrayClientNotifier":
            # first fetch the test configuration
            if self.__framework_config_location == 'Remote':
                self.__framework_map[self.__framework]["fetch_remote_config"]()
            elif self.__framework_config_location == 'Local':
                self.__framework_map[self.__framework]["fetch_local_config"]()
            else:
                self.__contructor_exception_raised = True
                raise InvalidFrameworkConfigLocation("FrameworkConfigLocation %s is invalid!"
                                                     " - supported ['Remote','Local']"
                                                     % self.__framework_config_location, "ERROR")
            self.xray_client_notifier = XmlHandler.XrayClientNotifier(verbose=verbose)
            self.xray_client_notifier.add_observer(xray_client_instance.xml_handler_observer)
        else:
            self.__contructor_exception_raised = True
            raise InvalidHandlerMode("XmlHandler mode %s is invalid! - "
                                     "supported modes ['XrayClientObserver','XrayClientNotifier']" % mode, "ERROR")

    # -- Public --

    '''
        If the Constructor itself raised an Exception return True to the caller otherwise False
        @return: True or False (boolean)
    '''

    def constructor_raised_exception(self):
        return self.__contructor_exception_raised

    '''
        Return a list of valid framework specific paths to test configuration files
        @return: list of absolute paths to test configs
        @return type: list
    '''

    def get_test_config_paths(self):
        return self.__paths_to_test_configs

    ''' 
        Return the currently in use framework string
        @return: framework
        @return type: string
    '''

    def get_framework_string(self):
        return self.__framework

    '''
        Print the TestSuites container and all its members
        @return: None
    '''

    @check_authorization("Pytefw")
    def print_test_suites_container(self):
        """
        Do not pretty print pointer references IF reference is an instance
        Those instances will be pretty printed anyways
        """
        pointers = ["prev", "next", "parent", "__tail", "__head"]
        logger = Logger(self.__class__.__name__)

        test_suites_gen = self.__test_suites_iter()
        test_suites_orig = None
        for test_suites, test_suite in test_suites_gen:
            if id(test_suites_orig) != id(test_suites):
                self.print_log_line("%s:" % test_suites, color="GREEN")
                for name, value in test_suites.__dict__.items():
                    # filter out public attributes
                    if name.startswith("__") or name.startswith("_"):
                        self.print_log_line("   %s: %s" % (name, value))
                        if not list(filter(lambda x: x in name, pointers)):
                            if isinstance(value, list):
                                for s_obj in value:
                                    # __module__ magic attribute of class instance
                                    if inspect.getmodule(s_obj):
                                        self.print_log_line("       %s:" % s_obj, color="YELLOW")
                                        for t_name, t_value in s_obj.__dict__.items():
                                            self.print_log_line("           %s: %s" % (t_name, t_value))
                                            if isinstance(t_value, dict):
                                                pretty_dict(logger, t_value, indent=4)
                                            if isinstance(t_value, list):
                                                num = 0
                                                for t_obj in t_value:
                                                    num += 1
                                                    if isinstance(t_obj, dict):
                                                        self.print_log_line('\t' * 4 + "-> Test Case %d:" % num, color="RED")
                                                        pretty_dict(logger, t_obj, indent=5)

                            else:
                                # __module__ magic attribute of class instance
                                if inspect.getmodule(value):
                                    self.print_log_line("       %s:" % value, color="YELLOW")
                                    for t_name, t_value in value.__dict__.items():
                                        self.print_log_line("           %s: %s" % (t_name, t_value))
                                        if isinstance(t_value, dict):
                                            pretty_dict(logger, t_value, indent=4)
                                        if isinstance(t_value, list):
                                            num = 0
                                            for t_obj in t_value:
                                                num += 1
                                                if isinstance(t_obj, dict):
                                                    self.print_log_line('\t' * 4 + "-> Test Case %d:" % num, color="RED")
                                                    pretty_dict(logger, t_obj, indent=5)
            self.print_log_line("   %s:" % test_suite, color="PURPLE")
            for n_name, n_value in test_suite.__dict__.items():
                if isinstance(n_value, list):
                    self.print_log_line("       %s: %s" % (n_name, n_value))
                    for m_obj in n_value:
                        if isinstance(m_obj, dict):
                            pretty_dict(logger, m_obj, indent=3)
                        # __module__ magic attribute of class instance
                        if inspect.getmodule(m_obj):
                            self.print_log_line("           %s:" % m_obj, color="BLUE")
                            for t_name, t_value in m_obj.__dict__.items():
                                self.print_log_line("               %s: %s" % (t_name, t_value))
                else:
                    self.print_log_line("       %s: %s" % (n_name, n_value))
                    if isinstance(n_value, dict):
                        pretty_dict(logger, n_value, indent=3)
                    # __module__ magic attribute of class instance
                    if not list(filter(lambda x: x in n_name, pointers)) and inspect.getmodule(n_value):
                        self.print_log_line("           %s:" % n_value, color="LIGHTGREEN")
                        for c_name, c_value in n_value.__dict__.items():
                            self.print_log_line("               %s: %s" % (c_name, c_value))
                            if isinstance(c_value, dict):
                                pretty_dict(logger, c_value, indent=5)
            test_suites_orig = test_suites

    '''
        Create a test execution result structure from a framework related xml result output
        @return: None
    '''

    def create_test_execution_container_from_xml(self):
        try:
            self.__framework_map[self.__framework]["parse_xml"]()
        except Exception as e:
            raise GeneralError("ParseXml failed: %s" % e, "ERROR")

        self.print_log_line("Adding update to processing queue..")
        self.__processing_queue.produce("XmlHandler update")
        # cleanup resources
        self.__cleanup()
        self.print_log_line("Notify XrayClient..")
        self.xray_client_notifier.notify_observers()

    # -- Private --

    '''
        Close any open file descriptors
        Close open connections
        Cleanup any unused resources
        @return: None
    '''

    def __cleanup(self):
        if self.__shell and isinstance(self.__shell, SshShell):
            self.__shell.close()

    '''
        Process test suite parent element in order to keep track of the hierarchy of test suites 
            If the test suite has a parent which is not yet available in the list of parents add it
            If the parent is already in the list (it was traversed already), 
                clear the list and initialize the list newly beginning with this parent
        @param parent_test_suite: the TestSuite parent instance
        @param type test_suite: instance
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts("IGNORE")
    def __add_parent_test_suite_to_traversed_test_suites(self, parent_test_suite):
        if parent_test_suite is not None:
            if parent_test_suite in self.__traversed_parent_test_suites:
                if self.__verbose:
                    self.print_log_line("TestSuite hierarchy changed -> traversed_parent_test_suites[] starts with parent %s"
                                        % parent_test_suite, log_level="DEBUG")
                self.__traversed_parent_test_suites.clear()
            self.__traversed_parent_test_suites.append(parent_test_suite)
        else:
            # reset list, we start from the top level
            if self.__verbose:
                self.print_log_line("Starting from top level hierarchy -> reset: traversed_parent_test_suites[]",
                                    log_level="DEBUG")
            if len(self.__traversed_parent_test_suites) > 0:
                self.__traversed_parent_test_suites.clear()

    '''
        Return the traversed test suites list
        @return: list of traversed test suites
        @return type: list
    '''

    @check_authorization("Pytefw")
    def __get_traversed_test_suites(self):
        return self.__traversed_parent_test_suites

    '''
        Fetch the Pytefw test configuration files from a remote server
        @return: None
    '''

    @XrayClientUIPyQtSlot()
    def __fetch_pytefw_remote_test_configuration(self):
        def progress(filename, size, sent):
            self.print_log_line("Downloading %s - %s - %s" % (filename, size, sent))

        self.__shell = SshShell(self.__remote_host,
                                self.__remote_user,
                                self.__remote_password,
                                self.__ssh_conn_timeout,
                                self.__verbose)
        self.__shell.set_retry_sequence(3)
        self.__shell.open()
        if not self.__shell.is_host_connected() and not self.__shell.reconnect():
            self.__contructor_exception_raised = True
            raise GeneralError("Could not fetch test config from %s" % self.__remote_host)
        scp = self.__shell.open_scp(progress=progress)
        scp.get(self.__framework_remote_config_dir, self.get_test_config_paths()[self.__framework])

    '''
        Fetch the Ita test configuration files from a remote server
        @return: None
    '''

    @XrayClientUIPyQtSlot()
    def __fetch_ita_remote_test_configuration(self):
        # TODO
        pass

    '''
        Fetch the Pytefw test configuration files from a local directory
        The testconfig.xml can reside in sub directories depending on the TestType!
        @return: None
    '''

    @XrayClientUIPyQtSlot()
    def __fetch_pytefw_local_test_configuration(self):
        # calculate the framework home directory
        parent_first_level = Path(self.__framework_config_dir).parent
        parent_second_level = Path(parent_first_level).parent
        if os.path.isdir(os.path.join(parent_first_level, "output")):
            parent_folder = parent_first_level
        elif os.path.isdir(os.path.join(parent_second_level, "output")):
            parent_folder = parent_second_level
        else:
            self.__contructor_exception_raised = True
            raise GeneralError("Could not detect 'output' folder originating from (%s, %s)"
                               % (parent_first_level, parent_second_level), "ERROR")
        self.__framework_home_dir = parent_folder

        try:
            test_config = os.path.join(self.__framework_config_dir, "testconfig.xml")
            test_result = os.path.join(parent_folder, "output", "testresult.xml")
            testspec_raw = os.path.join(parent_folder, "output", "doc", "testspec_raw.xml")

            shutil.copy2(test_result, self.get_test_config_paths()[self.__framework])
            shutil.copy2(test_config, self.get_test_config_paths()[self.__framework])
            shutil.copy2(testspec_raw, self.get_test_config_paths()[self.__framework])
            if self.__verbose:
                self.print_log_line("Fetched local config successfully from %s" % self.__framework_config_dir,
                                    log_level="DEBUG")
        except FileNotFoundError as e:
            self.__contructor_exception_raised = True
            raise FileError("Fetch Test Configuration error %s" % e, "ERROR")

    '''
        Fetch the Ita test configuration files from a local directory
        @return: None
    '''

    @XrayClientUIPyQtSlot()
    def __fetch_ita_local_test_configuration(self):
        # TODO
        pass

    '''
        Construct test config paths for all supported test frameworks
        @return: a list of framework specific path tuples to the test config directory in the form 
            [("framework1":"path1"), ("framework2":"path2"), ..]
        @return type: list
    '''

    @add_tags_as_suffix_to_path("Pytefw Ita")
    def __test_config_paths(self):
        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application = os.path.basename(sys.executable)
            config_path = os.path.join(os.path.dirname(os.path.abspath(application)), "test_configs")
        else:
            application = __file__
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(application))), "test_configs")
        return config_path

    '''
        Create an lxml tree from a config file and return the root element
        @param config_file: the name of the config file which is loaded from the test config directory
        @return: the root element
        @return type: lxml.etree._Element or GeneralError exception is raised 
    '''

    def __get_root_element_from_tree(self, config_file):
        try:
            tree = etree.parse(os.path.join(self._test_config_Pytefw, config_file))
            return tree.getroot()
        except OSError:
            raise GeneralError("Error reading file %s" % os.path.join(self._test_config_Pytefw, config_file), "ERROR")

    '''
        Set the test config path per framework. Each constructed test config path MUST exist
        @return: None or raise a GeneralError exception if a path does not exist
    '''

    def __setup_test_config_paths(self):
        self.__paths_to_test_configs = {}
        test_config_dirs = self.__test_config_paths()
        for test_config in test_config_dirs:
            framework, path = test_config
            if not os.path.isdir(os.path.join(path)):
                raise GeneralError("Test config path [%s] for [%s] not found!" % (path, framework), "ERROR")
            setattr(self, "_test_config_" + framework, path)
            self.__paths_to_test_configs[framework] = path

    '''
        Create xml structure for Pytefw
        @param item: python dictionary of the form {"items_creator_string":[test_exec1, test_exec2, ..]}
        @return: None
    '''

    @measure_func_time
    def __create_pytefw_xml_structure(self, item):
        self.print_log_line("Creating xml structure for Pytefw")

        test_exec_gen = self.__xray_client_instance.test_exec_iter()
        for test_exec, test_node in test_exec_gen:
            pass

    '''
        Create xml structure for Tresos-ita
        @param item: python dictionary of the form {"items_creator_string":[test_exec1, test_exec2, ..]}
        @return: None
    '''

    @measure_func_time
    def __create_ita_xml_structure(self, item):
        self.print_log_line("Creating xml structure for Tresos-ita")

        test_exec_gen = self.__xray_client_instance.test_exec_iter()
        for test_exec, test_node in test_exec_gen:
            pass

    '''
        Add an attachment to a JiraIssue Type Bug 
        @param attachment: the attachment to add
        @param type attachment: any type
        @param bug_instance: the bug instance for which the attachment will be added
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts("IGNORE", Bug)
    def __add_attachment_to_bug(self, attachment, bug_instance):
        self.__xray_client_instance.add_attachment_to_bug(bug_instance, attachment)

    '''
            Try to create an attachment for a failed raw tests case 
                in the form of a test case log
                The test case log represents an absolute paths + test case log file name
                The stored test case log file name MUST be in the form test_class.m_class + test_node.id 
            @param test_case: the raw test case to retrieve information from
            @param type test_case: dict
            @param test_class: the test_class to retrieve information from
            @param type test_class: TestClass instance
            @return: None
        '''

    @check_authorization("Pytefw")
    @accepts(dict, "IGNORE")
    def __add_test_case_log_as_attachment_to_raw_test_case(self, test_case, test_class):
        pattern_1 = "TC_" + ".".join((test_case['m_id'], test_class.m_class, "log"))
        pattern_2 = "TC_" + ".".join((test_case['m_id'], test_class.m_class, "*", "asc"))
        lookup_mapping = {
            os.path.join(self.__framework_home_dir, "output", "logs"): pattern_1,
            os.path.join(self.__framework_home_dir, "output", "traces"): pattern_2
        }

        if self.__framework_config_location == 'Local':
            # collect test case logs and can traces
            for test_result_dir, pattern in lookup_mapping.items():
                results = [os.path.join(test_result_dir, n) for n in
                           fnmatch.filter(os.listdir(test_result_dir), pattern) if
                           os.path.isfile(os.path.join(test_result_dir, n))]

                # add all attachments to the test case
                for result in results:
                    self.__update_raw_test_case(test_case['bug'], 'attachments', result)
        else:
            for test_result_dir, pattern in lookup_mapping.items():
                cmd = "find " + test_result_dir + " -name " + pattern + " -type f"
                exit_status, stdout, stderr = self.__shell.run(cmd)
                for result in stdout.strip("\n"):
                    self.__update_raw_test_case(test_case['bug'], 'attachments', result)

    '''
        Update a raw test case attribute with a value
        @param test_case: the raw test case
        @param type test_case: dict
        @param attribute: the attribute which is updated (str)
        @param value: the value of the attribute (str)
    '''

    @check_authorization("Pytefw")
    @accepts(dict, str, "IGNORE")
    def __update_raw_test_case(self, test_case, attribute, value):
        if test_case.get(attribute) is not None:
            if isinstance(test_case.get(attribute), list):
                test_case[attribute].append(value)
            else:
                test_case[attribute] = value
        else:
            self.print_log_line("Could not update raw test case with id %s, attribute %s does not exist",
                                log_level="ERROR", color="RED")

    '''
        Retrieve the parent TestSuite from the etree element and match it against the XmlUtils.TestSuite instances 
            from the TestSuites Linked List. Return the matched XmlUtils.TestSuite instance 
                as new parent  
        @param etree_elem: The etree element
        @param type: etree._Element
        @param test_suite_linked_list: TestSuites Linked List
        @return: None (if no parent exits) OR the parent
        @return type: None, XmlUtils.TestSuite instance
    '''

    @check_authorization("Pytefw")
    @accepts(etree._Element, TestSuites)
    def __get_parent_test_suite(self, etree_elem, test_suite_linked_list):
        result = None
        parent = etree_elem.getparent()
        if has_tag(parent, "TestSuite"):
            test_suites_gen = self.__test_suites_iter(test_suite_linked_list.get_id())
            for _, test_suite in test_suites_gen:
                if parent.attrib['class'] == test_suite.m_class and parent.attrib['uniqueSuffix'] == test_suite.uniqueSuffix:
                    result = test_suite
                    break
            if result is None:
                raise GeneralError("Critical error occured during parent test suite lookup!", "ERROR")
        return result

    ''' 
        Create a sorted list of TestSuites with all available data
        The TestSuites are parsed in the order they are defined in the framework
        @param root: the root element of the tree
        @param type root: lxml.etree._Element
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts(etree._Element)
    def __create_test_suites(self, root):
        # Create a TestSuites Linked List with a unique string Id and add it to the list of TestSuites Linked Lists
        # There is a possibility to have more then one TestSuites Linked List stored (not used for Pytefw)
        test_suite_linked_list = TestSuites("0")
        self.__test_suites_pytefw.append(test_suite_linked_list)

        # Create TestSuites with parameters and add it to the Linked List
        for child in root.findall(".//TestSuite"):
            test_suite = {}
            for key, value in child.attrib.items():
                test_suite[key] = value

            test_suite['params'] = {}
            for params in child.getchildren():
                if has_tag(params, "Data"):
                    test_suite['params'][params.values()[0]] = get_text(params, "")

            TestSuite = type("TestSuite",
                             (),
                             {
                                 "__init__": init_data,
                                 "set_data": set_data,
                                 "append_data": append_data
                             })
            ts = TestSuite(test_suite)
            # create public parent_test_suite, prev and next pointers
            ts.set_data("prev", None)
            ts.set_data("next", None)
            ts.set_data("parent", None)
            test_suite_id = '/'.join([os.path.join(ts.m_class, ts.uniqueSuffix).replace('\\', '/')])
            ts.set_data("id", test_suite_id)
            # add the parent TestSuite to the current TestSuite as class member attribute
            result = self.__get_parent_test_suite(child, test_suite_linked_list)
            ts.set_data("parent", result)
            test_suite_linked_list.append_test_suite(ts)

    ''' 
        Create TestClasses with all available data derived from TestSuites
        All TestSuites from the TestSuites Linked List will be used as entry point for searching the TestClass
        The Id of the TestClass will be calculated as a sum of all TestSuite identifiers + the TestClass identifier
        A TestClass is parameterized by any number of test suites, this will be added as additional information 
            to the TestClass represented as a sum of all TestSuite identifiers
        @param root: the root element of the tree (testconfig.xml)
        @param type root: lxml.etree._Element
        @param test_suites_linked_list: TestSuites Linked List instance from which the unique TestClass ids are calculated
        @param type test_suites_linked_list: TestSuites instance
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts(etree._Element, TestSuites)
    def __create_test_classes_from_test_suites(self, root, test_suites_linked_list):
        test_suites_gen = self.__test_suites_iter(test_suites_linked_list.get_id())
        # Traverse the actual test suites and check its hierarchy
        for test_suites, test_suite in test_suites_gen:
            self.__add_parent_test_suite_to_traversed_test_suites(test_suite.parent)

            test_suite_suffix = test_suite.uniqueSuffix
            test_class_dict = {}
            # Create TestClass structure and collect TestClass data
            expr = './/TestSuite[@uniqueSuffix = $suffix1]/TestClass'
            for test_class in root.xpath(expr, suffix1=test_suite_suffix):
                for key, value in test_class.attrib.items():
                    test_class_dict[key] = value
                expr2 = expr + "[@uniqueSuffix = $suffix2]/ClassData/Data"
                test_class_dict['class_data'] = {}
                for class_data in root.xpath(expr2, suffix1=test_suite_suffix, suffix2=test_class.attrib['uniqueSuffix']):
                    for key, value in class_data.attrib.items():
                        if key not in test_class_dict['class_data'].keys():
                            test_class_dict['class_data'][key] = {}
                        test_class_dict['class_data'][key][value] = class_data.text
                expr3 = expr + "[@uniqueSuffix = $suffix2]/ClassVariable/Data"
                test_class_dict['class_variable'] = {}
                for class_data in root.xpath(expr3, suffix1=test_suite_suffix, suffix2=test_class.attrib['uniqueSuffix']):
                    for key, value in class_data.attrib.items():
                        if key not in test_class_dict['class_variable'].keys():
                            test_class_dict['class_variable'][key] = {}
                        test_class_dict['class_variable'][key][value] = class_data.text

                TestClass = type("TestClass",
                                 (),
                                 {
                                     "__init__": init_data,
                                     "set_data": set_data,
                                     "append_data": append_data
                                 })
                tc = TestClass(test_class_dict)
                # Create a default precondition attribute which will be filled later
                tc.set_data("precondition", None)

                '''
                Create a unique id for the TestClass consisting of the TestSuite(s) (class/uniqueSuffix) strings + 
                TestClass (class/uniqueSuffix) string
                NOTE: The uniqueSuffix is not a must and can be empty
                '''
                test_suite_ids = '/'.join([os.path.join(t_test_suite.m_class, t_test_suite.uniqueSuffix).replace('\\', '/')
                                           if t_test_suite.uniqueSuffix else t_test_suite.m_class
                                           for t_test_suite in self.__get_traversed_test_suites()])

                # Append the current active test_suite to the list of parent test suites
                m_delim = ""
                if test_suite_ids:
                    m_delim = '/'
                test_suite_ids = m_delim.join([
                    test_suite_ids, '/'.join([os.path.join(test_suite.m_class, test_suite.uniqueSuffix).replace('\\', '/')
                                              if test_suite.uniqueSuffix else test_suite.m_class])])
                tc.set_data('parameterized_by_test_suites', test_suite_ids)

                # - store the traversed TestSuites + the current TestSuite as separate entry for the TestClass -
                tc.set_data("traversed_test_suites", [])
                for t_test_suite in self.__get_traversed_test_suites():
                    tc.append_data("traversed_test_suites", t_test_suite)
                    # the current one is the last one in the list
                tc.append_data("traversed_test_suites", test_suite)
                # All parents + current = MAX
                tc.set_data("max_traversed_test_suites", len(self.__get_traversed_test_suites()) + 1)
                # ---------------------------------------------------------------------------------------------

                if tc.uniqueSuffix:
                    tc.set_data('id', '/'.join([test_suite_ids, tc.m_class,
                                                tc.uniqueSuffix]))
                else:
                    tc.set_data('id', '/'.join([test_suite_ids, tc.m_class]))
                # Create an empty list for string all test cases belonging to this TestClass
                tc.set_data('test_cases', [])

                # Set the TestClass as TestSuites Linked List member
                test_suites_linked_list.add_test_class(tc)

    ''' 
        Create test cases with all attributes in the form of python dictionaries 
            used as input for TestCase instance generation by the XrayClient
            and add them to the TestClass which is a part of the TestSuites Linked List structure
        The unique suffix of the TestClass is used to search for the tests
        @param root: the root element of the tree (testconfig.xml)
        @param root2: the root element of the tree (testresult.xml)
        @param type root: lxml.etree._Element
        @param type root2: lxml.etree._Element
        @param test_suites_linked_list: The TestSuites Linked List with a reference to the TestClasses
        @param type test_suites_linked_list: TestSuites instance
        @return: None
    '''

    @check_authorization("Pytefw")
    @accepts(etree._Element, etree._Element, TestSuites)
    def __create_test_case_list_from_test_class(self, root, root2, test_suites_linked_list):
        test_class_list = test_suites_linked_list.get_test_classes()
        global test_case_rank

        for test_class in test_class_list:
            if not test_class.uniqueSuffix:
                self.print_log_line("TestClass with ID %s does not have a unique suffix! ... Applying parsing workaround"
                                    % test_class.m_id, log_level="WARNING", color="YELLOW")
                expr = './/TestSuite[@class = $s_class]' \
                       '[@uniqueSuffix = $suffix]/TestClass[@class = $m_class]/TestCases/TestCase'

                if len(test_class.traversed_test_suites) == 0:
                    self.print_log_line("Can not apply parsing workaround, can not guarantee unique results! "
                                        "TestClass with ID %s was not parameterized by any TestSuite(s)"
                                        % test_class.m_id, log_level="ERROR", color="RED")
                    return

                test_suite = test_class.traversed_test_suites[-1]

                if not test_suite.uniqueSuffix:
                    self.print_log_line("Can not apply parsing workaround, can not guarantee unique results! "
                                        "TestSuite with ID %s has no uniqueSuffix"
                                        % test_suite.m_id, log_level="ERROR", color="RED")
                    return

                xpath_result = root.xpath(expr, s_class=test_suite.m_class, suffix=test_suite.uniqueSuffix,
                                          m_class=test_class.m_class)
            else:
                expr = './/TestClass[@class = $m_class][@uniqueSuffix = $suffix]/TestCases/TestCase'
                xpath_result = root.xpath(expr, m_class=test_class.m_class, suffix=test_class.uniqueSuffix)

            # Create TestCase structure and collect TestCase data
            for m_test_case in xpath_result:
                test_case = {}

                # Add the id
                test_case_id = get_attribute(m_test_case, 'id', None)
                # Add the name if one exists
                test_case_name = get_attribute(m_test_case, 'name', None).replace(" ", "_")
                if test_case_id is None:
                    raise GeneralError("Test case %s run by TestClass %s does not have a unique id"
                                       % (m_test_case, test_class.m_id), "ERROR")

                # -------- DEFINITIONS ---------
                test_case['summary'] = None
                test_case['definition'] = None
                test_case['status'] = None
                test_case['bug'] = None
                test_case['description'] = None
                test_case['requirements'] = None
                # ------------------------------

                # Add the id
                test_case['m_id'] = test_case_id
                # Add the rank
                test_case['rank'] = test_case_rank
                test_case_rank += 1
                # Add the summary
                if test_case_name:
                    test_case['summary'] = '/'.join((str(test_class.m_id), str(test_case_id), test_case_name))
                else:
                    self.print_log_line("Test case with ID %s in Test class %s does not have a name attribute"
                                        % (test_case['m_id'], test_class.m_id), log_level="WARNING", color="YELLOW")

                # Get the data params for the test and add it as the test case definition
                definition = '''
                '''
                for child in m_test_case.getchildren():
                    if has_attribute_value(child, "Label"):
                        # Override the summary in case a Label attribute is found in addition to the name attribute
                        test_case['summary'] = '/'.join((test_class.m_id, get_text(child, None)))
                        continue
                    if has_tag(child, "Data"):
                        definition += '''\
                            <{tag} {AttributeKey}="{AttributeValue}">{text}</{tag}>
                        '''.format(tag=child.tag, AttributeKey=child.keys()[0], AttributeValue=child.values()[0],
                                   text=get_text(child, ""))
                    if has_tag(child, "Requirements"):
                        req_text = child.text
                        if req_text:
                            test_case['requirements'] = req_text.split(" ")
                # Add the definition
                test_case['definition'] = definition

                # Get the result of the test case
                expr2 = ".//TestClass[@id = $name1]/TestCases/Test[@id = $name2]/Result"
                # Default
                failure_reason = ""
                for r_test_case in root2.xpath(expr2, name1=test_class.m_id, name2=test_case['m_id']):
                    test_case['status'] = get_attribute(r_test_case, "result", None)
                    failure_reason = get_text(r_test_case, "")

                if test_case['status'] is None:
                    error_msg = "Test case with ID %s in Test class with ID %s was not executed!" \
                                % (test_case['m_id'], test_class.m_id)
                    self.print_log_line(error_msg, log_level="ERROR", color="RED")
                    failure_reason = error_msg

                # Add a bug to the test case IF status != successful
                if test_case['status'] != "successful":
                    bug = {'m_id': "-".join(["BUG", str(test_case['m_id'])]), 'description': failure_reason,
                           'summary': "-".join(["ISSUE", str(test_case['m_id']), str(test_case_name)]),
                           'attachments': []}
                    test_case['bug'] = bug
                    self.__add_test_case_log_as_attachment_to_raw_test_case(test_case, test_class)

                test_class.test_cases.append(test_case)

            # Set the overall number of test cases as attribute
            test_class.set_data("num_test_cases", len(test_class.test_cases))

    '''
        Process the test spec raw and add additional attributes to all test cases which are part of a specific TestClass
        Additional attributes consists of the test case precondition and a detailed test case description
        @param root: the root element of the tree (testspec_raw.xml)
        @param type root: lxml.etree._Element
        @param test_suites_linked_list: The TestSuites Linked List with a reference to the TestClasses
        @param type test_suites_linked_list: TestSuites instance
        @return: None 
    '''

    @check_authorization("Pytefw")
    @accepts(etree._Element, TestSuites)
    def __process_testspec_raw(self, root, test_suites_linked_list):
        test_class_list = test_suites_linked_list.get_test_classes()
        for test_class in test_class_list:
            # Get a list of available test case ids
            expr = ".//TestClass[@id = $name]/TestCases"
            list_of_test_case_ids = []
            for m_test_cases in root.xpath(expr, name=test_class.m_id):
                children = m_test_cases.getchildren()
                list_of_test_case_ids = [get_attribute(child, "id") for child in children]

            # Create a detailed description and the precondition from the testspec raw
            precondition = {}
            expr = ".//TestClass[@id = $name]/TestDesc"
            test_case_description = '''
            '''
            precondition['m_id'] = test_class.parameterized_by_test_suites + "_0"
            precondition['summary'] = test_class.parameterized_by_test_suites

            for test_desc in root.xpath(expr, name=test_class.m_id):
                children = test_desc.getchildren()
                for child in children:
                    if has_tag(child, 'TestInit'):
                        precondition['description'] = get_text(child, None)
                    test_case_description += '''\
                        <{tag}>{text}</{tag}>
                    '''.format(tag=child.tag, text=get_text(child, None))
            for test_case in test_class.test_cases:
                if test_case['m_id'] in list_of_test_case_ids:
                    # Add the description to the Test case
                    test_case['description'] = test_case_description
                    # Add the precondition to the TestClass instance
                    test_class.set_data("precondition", precondition)

    ''' 
        Create the MasterData (Only ONE MasterData instance is allowed)
        @param root: the root element of the tree (testresult.xml)
        @param type root: lxml.etree._Element
        @return: MasterData instance
        @return type: instance
    '''

    @check_authorization("Pytefw")
    @accepts(etree._Element)
    def __create_master_data(self, root):
        master_data = {}
        expr = ".//MasterData"
        for m_master_data in root.xpath(expr):
            for child in m_master_data:
                attributes = child.attrib
                if not attributes:
                    master_data[child.tag] = child.text
                else:
                    for key, value in attributes.items():
                        master_data[key] = value

            MasterData = type("MasterData",
                              (),
                              {
                                  "__init__": init_data,
                                  "set_data": set_data,
                                  "append_data": append_data
                              })

            return MasterData(master_data)

    '''
        Extract the value of a test case attribute
            When extracted, the test case dictionary will no longer have this attribute included!
        @param attribute: the test case attribute (str)
        @param test_case: the test case in form of a python dictionary
        @param type test_case: dict
        @return: value of attribute (any type)
    '''

    @check_authorization("Pytefw")
    @accepts(str, dict)
    def __extract_attribute_from_test_case(self, attribute, test_case):
        if attribute in test_case.keys():
            return test_case.pop(attribute)
        return None

    '''
        Iterate through a list of TestSuites Linked List instances and return (TestSuites, TestSuite) pairs
        @param test_suites_id: TestSuites id or None, if None then all TestSuites are considered
        @param type test_suites_id: None or string or int
        @return: (TestSuites, TestSuite) pair
        @return type: tuple
    '''

    @check_authorization("Pytefw")
    @accepts((None, str, int))
    def __test_suites_iter(self, test_suites_id=None):
        test_suites = self.__get_current_test_suites(test_suites_id)

        for test_suite in test_suites:
            test_suite_iter = iter(test_suite)
            while True:
                try:
                    yield (test_suite, next(test_suite_iter))
                except StopIteration:
                    break

    '''
        Return a list of all currently available TestSuites Linked Lists or a specific one specified by 
        test_suites_id 
        @param test_suites_id: the unique id of the TestSuites Linked List , if None is passed all TestSuites are returned 
        @param type test_suites_id: None string or int
        @return: list of test executions with test nodes
        @return type: list
    '''

    @check_authorization("Pytefw")
    @accepts((None, str, int))
    def __get_current_test_suites(self, test_suites_id=None):
        if test_suites_id:
            return [test_suite for test_suite in self.__test_suites_pytefw if
                    test_suite.get_id() == test_suites_id]
        return self.__test_suites_pytefw

    '''
        Parse Pytefw xml output
        @return: None
    '''

    @XrayClientUIPyQtSlot()
    @measure_func_time
    def __parse_pytefw_xml_structure(self):
        """
        EXAMPLES:
        for i in range(0, 1):
            i = str(i)
            self.__xray_client_instance.create_test_execution(i, "EXEC-"+i, sort_by_rank=True)
            self.__xray_client_instance.add_test_plan_to_test_execution_with_key("EXEC-"+i, m_id="blalala")
            test_node = self.__xray_client_instance.create_test_node(test_key="TEST-124",
                                                                     m_id=666767,
                                                                     rank=5,
                                                                     reporter="me")
            test_node2 = self.__xray_client_instance.create_test_node(test_key="TEST-125",
                                                                      m_id=666767,
                                                                      rank=3,
                                                                      reporter="me")
            self.__xray_client_instance.add_test_set_to_test_node(test_node, m_id=99999)
            self.__xray_client_instance.add_test_set_to_test_node(test_node2, m_id=99999)
            self.__xray_client_instance.add_test_node_to_test_execution_with_key("EXEC-"+i, test_node)
            self.__xray_client_instance.add_test_node_to_test_execution_with_key("EXEC-"+i, test_node2)
            args = {
                "m_id": 24523534634,
                "rank": 1,
                "reporter": "you"
            }
            self.__xray_client_instance.add_test_node_to_test_execution_with_key("EXEC-"+i,
                                                                                 **args)
            self.__xray_client_instance.add_test_set_to_test_node(test_node, m_id=44444)
        """
        try:
            root1 = self.__get_root_element_from_tree("testconfig.xml")
            root2 = self.__get_root_element_from_tree("testresult.xml")
            root3 = self.__get_root_element_from_tree("testspec_raw.xml")
        except etree.XMLSyntaxError as e:
            raise GeneralError(e, "ERROR")

        self.__create_test_suites(root1)
        if not self.__test_suites_pytefw:
            raise GeneralError("Parsing failed: No TestSuite(s) received", "ERROR")

        # Create a MasterData instance which is global for all TestSuites
        master_data = self.__create_master_data(root2)

        # Create a DEFAULT TestExecution - add master data and test cases to it
        self.__xray_client_instance.create_test_execution("DEFAULT-PYTEFW", sort_by_rank=True)
        self.__xray_client_instance.add_master_data_to_test_execution_with_id("DEFAULT-PYTEFW", master_data)
        self.__xray_client_instance.add_summary_to_test_execution_with_id("DEFAULT-PYTEFW", master_data.Project)
        for test_suites_linked_list in self.__test_suites_pytefw:
            test_suites_linked_list.set_master_data(master_data)
            self.__create_test_classes_from_test_suites(root1, test_suites_linked_list)
            self.__create_test_case_list_from_test_class(root1, root2, test_suites_linked_list)
            self.__process_testspec_raw(root3, test_suites_linked_list)

            test_class_list = test_suites_linked_list.get_test_classes()
            for test_class in test_class_list:
                m_test_cases = test_class.test_cases

                """
                    Make a slim version of the TestClass without test nodes to reduce memory
                    Keep the original TestClass for tracking and debugging purpose
                    Since each test node refers to a TestClass in the XrayClient data structure, 
                        the test nodes are superfluous in the TestClass itself
                """

                test_class_simplified = copy.deepcopy(test_class)
                try:
                    delattr(test_class_simplified, 'test_cases')
                except AttributeError:
                    pass

                # First create a unique precondition for all following test cases
                precondition_instance = None
                if test_class.precondition:
                    precondition_instance = self.__xray_client_instance.create_precondition(**test_class.precondition)

                for test_case in m_test_cases:
                    # First extract the requirements and bug, requirements/bug
                    # will not be passed to the TestNode Constructor
                    # Keep the original test_case structure for debugging purpose
                    test_case_copy = test_case.copy()
                    requirements = self.__extract_attribute_from_test_case("requirements", test_case_copy)
                    bug = self.__extract_attribute_from_test_case("bug", test_case_copy)

                    test_node = self.__xray_client_instance.create_test_node(**test_case_copy)
                    if precondition_instance:
                        self.__xray_client_instance.add_precondition_to_test_node(test_node, precondition_instance)
                    if bug:
                        bug_instance = self.__xray_client_instance.create_bug(**bug)
                        self.__xray_client_instance.add_bug_to_test_node(test_node, bug_instance)

                    if requirements and isinstance(requirements, list):
                        for req in requirements:
                            self.__xray_client_instance.add_requirement_to_test_node(test_node, req)
                    self.__xray_client_instance.set_test_class_for_test_node(test_node, test_class_simplified)
                    self.__xray_client_instance.add_test_node_to_test_execution_with_id("DEFAULT-PYTEFW", test_node)

        if self.__print_data_containers:
            self.print_test_suites_container()

    '''
        Parse Tresos-ita xml output
        @return: None
    '''

    @XrayClientUIPyQtSlot()
    @measure_func_time
    def __parse_ita_xml_structure(self):
        pass

    class XrayClientNotifier(Observable):
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

    class XrayClientObserver(Observer, Logger):
        """
            define an observer class which fetches results from an observable class in form of an update
        """

        def __init__(self, handler, verbose=False):
            Logger.__init__(self, self.__class__.__name__)
            self.__handler = handler
            self.__verbose = verbose

        '''
            Overridden method from Observer class which is called when updates are available
            The update itself is fetched from a queueing structure as an item and checked for consistency
            If consistency checks passed, xml creation is started for the given framework
            @return: None or specific exception (AttributeError, InvalidType) is raised in case of errors
        '''

        @XrayClientUIPyQtSlot()
        def update(self, observable, arg):
            self.print_log_line("Got update from %s" % observable)

            if not self.__handler.__processing_queue.consume():
                self.print_log_line("No update received from %s" % observable, log_level="ERROR", color="RED")
                return

            test_executions = self.__handler.__xray_client_instance.get_current_test_executions()
            if not test_executions:
                self.print_log_line("Ignoring update from %s, no test executions received" % observable,
                                    log_level="ERROR", color="RED")
                return

            self.__handler.__xray_client_instance.print_test_execution_container()
            # process data
            # .....

            # Trigger xml creation
            try:
                self.__handler.__framework_map[self.__handler.__framework]["create_xml"](test_executions)
            except Exception as e:
                raise GeneralError("ParseXml failed: %s" % e, "ERROR")

            # clear test execution container after export is finished
            self.__handler.__xray_client_instance._clear_test_execution_container()
