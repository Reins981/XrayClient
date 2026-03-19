#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab

"""
Created on 15.03.2019

@author: reko8680
@Coding Guidelines: TestExecutionContainer methods, functions and variables shall be written in Lowercase separated by _
"""

from Logger import Logger
from ExceptionUtils import NoneTypeObject, LengthLimitReached, InvalidType
from DecoratorUtils import accepts, XrayClientUIPyQtSlot

'''
    The JiraIssue from which all jira issue types inherit
'''


class JiraIssue:
    @accepts((int, str), (str, None))
    def __init__(self, jira_issue_id=None, jira_issue_key=None):
        self.__id = jira_issue_id
        self.__key = jira_issue_key

    '''
            Return the id of the jira issue
            @return: id (string or int)
    '''

    def get_id(self):
        return self.__id

    '''
        Check if the jira issue has a key
        @return: True or False (boolean)
    '''

    def has_key(self):
        if self.__key:
            return True
        return False

    '''
        Return the key of the jira issue
        @return: key (string)
    '''

    def get_key(self):
        return self.__key

    '''
        Set the key of the jira issue
        @param: key (string)
    '''

    @accepts((str, None))
    def set_key(self, jira_issue_key):
        self.__key = jira_issue_key


'''
    The XrayIssue from which all xray issue types inherit
'''


class XrayIssue:
    @accepts((int, str), (str, None))
    def __init__(self, xray_issue_id=None, xray_issue_key=None):
        self.__id = xray_issue_id
        self.__key = xray_issue_key

    '''
            Return the id of the xray issue
            @return: id (string or int)
    '''

    def get_id(self):
        return self.__id

    '''
        Check if the xray issue has a key
        @return: True or False (boolean)
    '''

    def has_key(self):
        if self.__key:
            return True
        return False

    '''
        Return the key of the xray issue
        @return: key (string)
    '''

    def get_key(self):
        return self.__key

    '''
        Set the key of the xray issue
        @param: key (string)
    '''

    @accepts((str, None))
    def set_key(self, xray_issue_key):
        self.__key = xray_issue_key


'''
    Define a TestPlan with properties
'''


class TestPlan(XrayIssue):
    @accepts((int, str), (str, None))
    def __init__(self, m_id=None, test_plan_key=None):
        super().__init__(m_id, test_plan_key)


'''
    Define a TestSet with properties
'''


class TestSet(XrayIssue):
    @accepts((int, str), (str, None), str, str)
    def __init__(self, m_id=None, test_set_key=None, description="", summary=""):
        super().__init__(m_id, test_set_key)
        self.__description = description
        self.__summary = summary

    '''
        Check if the test set has a description
        @return: True or False (boolean)
    '''

    def has_description(self):
        if self.__description:
            return True
        return False

    '''
        Check if the test set has a summary
        @return: True or False (boolean)
    '''

    def has_summary(self):
        if self.__summary:
            return True
        return False

    '''
        Return the description of the test set
        @return: description (string)
    '''

    def get_description(self):
        return self.__description

    '''
        Return the summary of the test set
        @return: summary (string)
    '''

    def get_summary(self):
        return self.__summary

    '''
        Set the description of the test set
        @param: description (string)
    '''

    @accepts(str)
    def set_description(self, description):
        self.__description = description

    '''
        Set the summary of the test set
        @param: summary (string)
    '''

    @accepts(str)
    def set_summary(self, summary):
        self.__summary = summary


'''
    Define a Bug with properties
'''


class Bug(JiraIssue):
    @accepts((int, str), (str, None), str, str, (None, list))
    def __init__(self,
                 m_id=None,
                 bug_key=None,
                 description="",
                 summary="",
                 attachments=None):
        super().__init__(m_id, bug_key)
        self.__description = description
        self.__summary = summary
        # attachments in form of paths
        if attachments is None:
            attachments = []
        self.__attachments = attachments

    # - PRIVATE -

    '''
        Add a unique attachment path to the bug __attachments list, 
        Ignore insertion if the path is a duplicate 
        @param attachment: absolute path to the attachment (including attachment file name)
        @param type attachment: str
        @return: True or False (boolean), True in case the operation was successful, 
                    False in case the attachment already exists
    '''

    def __add_attachment(self, attachment):
        if list(filter(lambda m_attach: m_attach == attachment, self.__attachments)):
            return False

        self.__attachments.append(attachment)
        return True

    # - PUBLIC -

    '''
        Check if the bug has a description
        @return: True or False (boolean)
    '''

    def has_description(self):
        if self.__description:
            return True
        return False

    '''
        Check if the bug has a summary
        @return: True or False (boolean)
    '''

    def has_summary(self):
        if self.__summary:
            return True
        return False

    '''
        Return the description of the bug
        @return: description (string)
    '''

    def get_description(self):
        return self.__description

    '''
        Return the summary of the bug
        @return: summary (string)
    '''

    def get_summary(self):
        return self.__summary

    '''
        Set the description of the bug
        @param: description (string)
    '''

    @accepts(str)
    def set_description(self, description):
        self.__description = description

    '''
        Set the summary of the bug
        @param: summary (string)
    '''

    @accepts(str)
    def set_summary(self, summary):
        self.__summary = summary

    '''
        Add an attachment to a given bug
        A bug might have more than one attachment
        @param attachment: the absolute path to the attachment (including attachment file name)
        @param type attachment: str
        @return: None
    '''

    @accepts(str)
    def add_attachment(self, attachment):
        success = self.__add_attachment(attachment)

        if not success:
            self.print_log_line("Could not add attachment %s to the attachments list - attachment is duplicate" % attachment,
                                log_level="ERROR", color="RED")


'''
    Define a Precondition with properties
'''


class Precondition(XrayIssue):
    @accepts((int, str), (str, None), str, str)
    def __init__(self, m_id=None, precondition_key=None, description="", summary=""):
        super().__init__(m_id, precondition_key)
        self.__description = description
        self.__summary = summary

    '''
        Check if the precondition has a description
        @return: True or False (boolean)
    '''

    def has_description(self):
        if self.__description:
            return True
        return False

    '''
        Check if the precondition has a summary
        @return: True or False (boolean)
    '''

    def has_summary(self):
        if self.__summary:
            return True
        return False

    '''
        Return the description of the precondition
        @return: description (string)
    '''

    def get_description(self):
        return self.__description

    '''
        Return the summary of the precondition
        @return: summary (string)
    '''

    def get_summary(self):
        return self.__summary

    '''
        Set the description of the precondition
        @param: description (string)
    '''

    @accepts(str)
    def set_description(self, description):
        self.__description = description

    '''
        Set the summary of the precondition
        @param: summary (string)
    '''

    @accepts(str)
    def set_summary(self, summary):
        self.__summary = summary


'''
    Define a TestCase with properties
'''


class TestNode(Logger, XrayIssue):
    @accepts((int, str), (str, None), (None, int), (None, str), (None, str), (None, str), (None, str), (None, str),
             (None, str), (None, str), (None, dict, str), None, None)
    def __init__(self,
                 m_id=None,
                 test_key=None,
                 rank=None,
                 m_self="",
                 reporter="",
                 assignee="",
                 description="",
                 summary="",
                 m_type="",
                 status="",
                 definition=None,
                 prev=None,
                 m_next=None):
        Logger.__init__(self, self.__class__.__name__)
        XrayIssue.__init__(self, m_id, test_key)
        self.__rank = rank
        self.__self = m_self
        self.__reporter = reporter
        self.__assignee = assignee
        self.__description = description
        self.__summary = summary
        self.__m_type = m_type
        self.__status = status
        self.__definition = definition

        # public previous and next pointer
        self.prev = prev
        self.next = m_next

        #   - Optional parameters -
        # test sets list
        self.__part_of_test_sets = []
        # preconditions list
        self.__preconditions = []
        # requirements
        self.__requirements = []
        # bug issues
        self.__bugs = []
        # TestClass identifier
        self.__run_by_test_class_instance = None

    # - PRIVATE -

    '''
        Add a unique test set with attributes to the test node __part_of_test_sets list, 
        Ignore insertion if the Test Set is a duplicate 
        @param test_set: the test set which is added to the list of test sets 
        @param type test_set: TestSet instance
        @return: True or False (boolean), True in case the operation was successful, 
                    False in case the test set already exists
    '''

    def __add_test_set(self, test_set):
        if list(filter(lambda m_test_set: id(m_test_set) is id(test_set), self.__part_of_test_sets)) \
                or list(filter(lambda m_test_set: m_test_set.get_id() == test_set.get_id(), self.__part_of_test_sets)):
            return False

        self.__part_of_test_sets.append(test_set)
        return True

    '''
        Add a unique precondition with attributes to the test node __preconditions list, 
        Ignore insertion if the precondition is a duplicate 
        @param precondition: the precondition which is added to the list of preconditions
        @param type precondition: Precondition instance
        @return: True or False (boolean), True in case the operation was successful, 
                    False in case the precondition already exists
    '''

    def __add_precondition(self, precondition):
        if list(filter(lambda m_precondition: id(m_precondition) is id(precondition), self.__preconditions)) \
                or list(filter(lambda m_precondition: m_precondition.get_id() == precondition.get_id(),
                               self.__preconditions)):
            return False

        self.__preconditions.append(precondition)
        return True

    '''
        Add a unique bug with attributes to the test node __bugs list, 
        Ignore insertion if the bug is a duplicate 
        @param bug: the bug which is added to the list of bugs
        @param type bug: Bug instance
        @return: True or False (boolean), True in case the operation was successful, 
                    False in case the bug already exists
    '''

    def __add_bug(self, bug):
        if list(filter(lambda m_bug: id(m_bug) is id(bug), self.__bugs)) \
                or list(filter(lambda m_bug: m_bug.get_id() == bug.get_id(),
                               self.__bugs)):
            return False

        self.__bugs.append(bug)
        return True

    '''
        Add a unique requirement string to the test node __requirements list, 
        Ignore insertion if the requirement is a duplicate 
        @param requirement: the requirement which is added to the list of requirements
        @param type requirement: str
        @return: True or False (boolean), True in case the operation was successful, 
                    False in case the requirement already exists
    '''

    def __add_requirement(self, requirement):
        if list(filter(lambda m_req: m_req == requirement, self.__requirements)):
            return False

        self.__requirements.append(requirement)
        return True

    # - PUBLIC -

    '''
        Return the list of test sets
        @return: test sets (list)
    '''

    def get_test_sets(self):
        return self.__part_of_test_sets

    '''
        Set a new list of test sets for the TestNode
        @param test_sets: list of TestSet instances
        @param type test_sets: list
    '''

    @accepts(list)
    def set_test_sets(self, test_sets):
        self.__part_of_test_sets = test_sets

    '''
        Set TestNode rank
        @param rank: rank (int)
    '''

    @accepts(int)
    def set_rank(self, rank):
        self.__rank = rank

    '''
        Set TestNode url
        @param url: url (string)
    '''

    @accepts(str)
    def set_self(self, url):
        self.__self = url

    '''
        Set TestNode reporter
        @param reporter: reporter (string)
    '''

    @accepts(str)
    def set_reporter(self, reporter):
        self.__reporter = reporter

    '''
        Set TestNode assignee
        @param assignee: assignee (string)
    '''

    @accepts(str)
    def set_assignee(self, assignee):
        self.__assignee = assignee

    '''
            Set TestNode description
            @param description: description (string)
    '''

    @accepts(str)
    def set_description(self, description):
        self.__description = description

    '''
            Set TestNode summary
            @param summary: summary (string)
    '''

    @accepts(str)
    def set_summary(self, summary):
        self.__summary = summary

    '''
        Set a new list of TestNode preconditions
        @param preconditions: list of Precondition instances
        @param type preconditions: list
    '''

    @accepts(list)
    def set_preconditions(self, preconditions):
        self.__preconditions = preconditions

    '''
        Set a new list of TestNode bugs
        @param bugs: list of Bug instances
        @param type bugs: list
    '''

    @accepts(list)
    def set_bugs(self, bugs):
        self.__bugs = bugs

    '''
        Set TestNode type
        @param m_type: (Automated[Generic], Manual,..)
        @param type m_type: string
    '''

    @accepts(str)
    def set_type(self, m_type):
        self.__m_type = m_type

    '''
        Set TestNode status
        @param status: 'Execute','Fail','Passed'
        @param type status: string
    '''

    @accepts(str)
    def set_status(self, status):
        self.__status = status

    '''
        Set TestNode test steps
        @param definition: List of test steps in the form {steps:[{key,value,..},{key,value}]} or as a String
        @param type definition: list or string
    '''

    @accepts((dict, str))
    def set_definition(self, definition):
        self.__definition = definition

    '''
        Set the TestClass which runs the TestNode as testcase
        NOTE: Pytefw only support 
        @param test_class_instance: instance of type TestClass
        @param type test_class_instance: instance
    '''

    def set_test_class(self, test_class_instance):
        self.__run_by_test_class_instance = test_class_instance

    '''
        Return the rank
        @return: rank (int)
    '''

    def get_rank(self):
        return self.__rank

    '''
        Return the url
        @return: url (string)
    '''

    def get_self(self):
        return self.__self

    '''
        Return the reporter
        @return: reporter (string)
    '''

    def get_reporter(self):
        return self.__reporter

    '''
        Return the assignee
        @return: assignee (string)
    '''

    def get_assignee(self):
        return self.__assignee

    '''
            Return the description
            @return: description (string)
    '''

    def get_description(self):
        return self.__description

    '''
            Return the summary
            @return: summary (string)
    '''

    def get_summary(self):
        return self.__summary

    '''
        Return a list of preconditions
        @return: precondition list
        @return type: list of Precondition instances
    '''

    def get_preconditions(self):
        return self.__preconditions

    '''
        Return a list of bugs
        @return: bug list
        @return type: list of Bug instances
    '''

    def get_bugs(self):
        return self.__bugs

    '''
        Return a list of requirements
        @return: requirement list
        @return type: list of requirement strings
    '''

    def get_requirements(self):
        return self.__requirements

    '''
        Return the type
        @return: type (string)
    '''

    def get_type(self):
        return self.__m_type

    '''
        Return the status
        @return: status (string)
    '''

    def get_status(self):
        return self.__status

    '''
        Return the test steps
        @return: test steps (dictionary or string)
    '''

    def get_definition(self):
        return self.__definition

    '''
        Check if TestNode has a rank
        @return: True or False (boolean)
    '''

    def has_rank(self):
        if self.__rank:
            return True
        return False

    '''
        Check if TestNode has a URL
        @return: True or False (boolean)
    '''

    def has_self(self):
        if self.__self:
            return True
        return False

    '''
        Check if TestNode has a reporter
        @return: True or False (boolean)
    '''

    def has_reporter(self):
        if self.__reporter:
            return True
        return False

    '''
        Check if TestNode has an assignee
        @return: True or False (boolean)
    '''

    def has_assignee(self):
        if self.__assignee:
            return True
        return False

    '''
            Check if TestNode has an description
            @return: True or False (boolean)
    '''

    def has_description(self):
        if self.__description:
            return True
        return False

    '''
            Check if TestNode has a summary
            @return: True or False (boolean)
    '''

    def has_summary(self):
        if self.__summary:
            return True
        return False

    '''
        Check if TestNode has preconditions
        @return: True or False (boolean)
    '''

    def has_preconditions(self):
        if self.__preconditions:
            return True
        return False

    '''
        Check if TestNode has bugs
        @return: True or False (boolean)
    '''

    def has_bugs(self):
        if self.__bugs:
            return True
        return False

    '''
        Check if TestNode has requirements
        @return: True or False (boolean)
    '''

    def has_requirements(self):
        if self.__requirements:
            return True
        return False

    '''
        Check if TestNode has a type
        @return: True or False (boolean)
    '''

    def has_type(self):
        if self.__m_type:
            return True
        return False

    '''
        Check if TestNode has test steps
        @return: True or False (boolean)
    '''

    def has_definition(self):
        if self.__definition:
            return True
        return False

    '''
        Check if TestNode has a status attribute
        @return: True or False (boolean)
    '''

    def has_status(self):
        if self.__status:
            return True
        return False

    '''
        Check if TestNode has a test sets
        @return: True or False (boolean)
    '''

    def has_test_sets(self):
        if self.__part_of_test_sets:
            return True
        return False

    '''
        Add a test set with defined properties to a given test node
            The test set can either be newly created using the properties given 
            or a test set instance can be passed as argument
        A test node might be part of more than one test set
        @param test_set_instance: test_set instance to be used
        @param type test_set_instance: None or TestSet
        test set properties:
        @param m_id: unique id of the test set (int or string) - None optional
        @param type m_id: string or int
        @param test_set_key: key of the test set (string or None)
        @param description: description (string) - optional
        @return: None
    '''

    @accepts((None, TestSet))
    def append_test_set(self, test_set_instance=None, **kwargs):

        if test_set_instance is None:
            args = {
                'm_id': None,
                'test_set_key': None,
                'description': "",
                'summary': ""
            }

            diff = set(kwargs.keys()) - set(args.keys())
            if diff:
                self.print_log_line("Ignore appending test set - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
                return

            args.update(kwargs)

            new_test_set = TestSet(args['m_id'],
                                   args['test_set_key'],
                                   args['description'],
                                   args['summary'])
        else:
            new_test_set = test_set_instance

        success = self.__add_test_set(new_test_set)

        if not success:
            self.print_log_line("Could not add test set with id %d to %s - test set is duplicate" %
                                (new_test_set.get_id(), str(new_test_set)),
                                log_level="ERROR", color="RED")

    '''
        Add a precondition with defined properties to a given test node
            The precondition can either be newly created using the properties given 
            or a precondition instance can be passed as argument
        A test node might has more than one precondition
        @param precondition_instance: precondition instance to be used
        @param type precondition_instance: None or Precondition
        precondition properties:
        @param m_id: unique id of the precondition (int or string) - None optional
        @param type m_id: string or int
        @param precondition_key: key of the precondition (string or None)
        @param description: description (string) - optional
        @param summary: summary (string) - optional
        @return: None
    '''

    @accepts((None, Precondition))
    def append_precondition(self, precondition_instance=None, **kwargs):

        if precondition_instance is None:
            args = {
                'm_id': None,
                'precondition_key': None,
                'description': "",
                'summary': ""
            }

            diff = set(kwargs.keys()) - set(args.keys())
            if diff:
                self.print_log_line("Ignore appending precondition - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
                return

            args.update(kwargs)

            new_precondition = Precondition(args['m_id'],
                                            args['precondition_key'],
                                            args['description'],
                                            args['summary'])
        else:
            new_precondition = precondition_instance

        success = self.__add_precondition(new_precondition)

        if not success:
            self.print_log_line("Could not add precondition with id %d to %s - precondition is duplicate" %
                                (new_precondition.get_id(), str(new_precondition)),
                                log_level="ERROR", color="RED")

    '''
        Add a bug with defined properties to a given test node
            The bug can either be newly created using the properties given 
            or a bug instance can be passed as argument
        A test node might has more than one bugs
        @param bug_instance: bug instance to be used
        @param type bug_instance: None or Bug
        bug properties:
        @param m_id: unique id of the bug (int or string) - None optional
        @param type m_id: string or int
        @param bug_key: key of the bug (string or None)
        @param description: description (string) - optional
        @param summary: summary (string) - optional
        @return: None
    '''

    @accepts((None, Bug))
    def append_bug(self, bug_instance=None, **kwargs):

        if bug_instance is None:
            args = {
                'm_id': None,
                'bug_key': None,
                'description': "",
                'summary': ""
            }

            diff = set(kwargs.keys()) - set(args.keys())
            if diff:
                self.print_log_line("Ignore appending bug - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
                return

            args.update(kwargs)

            new_bug = Bug(args['m_id'],
                          args['bug_key'],
                          args['description'],
                          args['summary'])
        else:
            new_bug = bug_instance

        success = self.__add_bug(new_bug)

        if not success:
            self.print_log_line("Could not add bug with id %d to %s - bug is duplicate" %
                                (new_bug.get_id(), str(new_bug)),
                                log_level="ERROR", color="RED")

    '''
        Add a requirement string to a given test node
        A test node might has more than one requirement
        @param requirement: the unique requirement to be added
        @param type requirement: str
        @return: None
    '''

    @accepts(str)
    def append_requirement(self, requirement):
        success = self.__add_requirement(requirement)

        if not success:
            self.print_log_line("Could not add requirement %s to requirements list - requirement is duplicate" % requirement,
                                log_level="ERROR", color="RED")


'''
    A test execution represents a sorted linked list which consists of TestNode instances.
    A test execution itself has a unique test_exec_id and is maybe part of one or more test plans 
'''


class TestExecution(Logger, XrayIssue):
    """
        @param test_exec_id: unique id of test execution - Non optional
        @param type test_exec_id: int or string
        @param test_exec_key: key of test execution
        @param type test_exec_key: string or None
        @param summary: the summary of the test execution (string)
        @param description: the description of the test execution (string)
        @param sort_by_rank: sort tests by rank for this test execution (boolean)
    """

    # tests with test keys exceeding the length limit will not be added to the test execution
    __TEST_KEY_LENGTH_LIMIT = 50

    @accepts((int, str), (None, str), str, str, bool)
    def __init__(self, test_exec_id, test_exec_key=None, summary="", description="", sort_by_rank=False):
        Logger.__init__(self, self.__class__.__name__)
        XrayIssue.__init__(self, test_exec_id, test_exec_key)
        self.__head = None
        self.__tail = None
        self.__max_test_nodes = 0

        """
            TestExecution attributes
        """
        self.__summary = summary
        self.__description = description
        self.__sort_by_rank = sort_by_rank
        # - optional attributes -
        # test plans
        self.__part_of_test_plans = []
        # MasterData identifier
        self.__master_data_instance = None

    '''
        Get the length of this test execution instance
        @return: number of TestNodes (int)
    '''

    def __len__(self):
        return self.__max_test_nodes

    '''
        destructor
    '''

    def __del__(self):
        del self

    '''
        create a TestExecution iterator
    '''

    def __iter__(self):
        self.test_node_number = 0
        self.start = True
        self.current_test_node = self.__head
        return self

    '''
        get next TestNode from TestExecution
    '''

    def __next__(self):
        if self.test_node_number < self.__max_test_nodes:
            self.test_node_number += 1
            if self.start:
                self.start = False
                return self.current_test_node
            else:
                current_node = self.__get_next_test_node(self.current_test_node)
                self.current_test_node = current_node
                return current_node
        else:
            raise StopIteration

    '''
        Get TestNode by test_id or test_key from the TestExecution
        @param test_identifier: unique id or key of test node
        @param type test_identifier: tuple
        @return: TestNode
        @return type TestNode: TestNode instance
    '''

    @XrayClientUIPyQtSlot()
    def __getitem__(self, test_identifier):
        test_attribute, test_ident_type = test_identifier
        if test_ident_type.lower() == 'key':
            return self.__get_test_node_by_test_key(test_attribute)
        elif test_ident_type.lower() == 'id':
            return self.__get_test_node_by_test_id(test_attribute)
        else:
            raise InvalidType("test_identifier type must be key or id", "ERROR")

    '''
        Check if TestExecution contains a TestNode with the given test_id
        @param test_id: unique id
        @param type test_id: int
        @return: True or False (boolean) 
    '''

    def __contains__(self, test_id):
        if self.__get_test_node_by_test_id(test_id):
            return True
        return False

    '''
        Check if TestExecution contains a TestNode with the given test_key
        @param test_key: test key
        @param type test_key: string
        @return: True or False (boolean)
    '''

    def contains_test_key(self, test_key):
        if self.__get_test_node_by_test_key(test_key):
            return True
        return False

    # - PRIVATE -

    '''
        Get TestNode by test_id
        @param test_id: unique id
        @param type test_id: int
        @return: TestNode or None
        @return type TestNode: TestNode instance or None
    '''

    def __get_test_node_by_test_id(self, test_id):
        current_node = self.__head

        while current_node is not None:
            if current_node.get_id() == test_id:
                return current_node
            current_node = self.__get_next_test_node(current_node)
        return None

    '''
        Get TestNode by test_key
        @param test_key: test key
        @param type test_key: string
        @return: TestNode or None
        @return type TestNode: TestNode instance or None
    '''

    def __get_test_node_by_test_key(self, test_key):
        current_node = self.__head

        while current_node is not None:
            if current_node.get_key() == test_key:
                return current_node
            current_node = self.__get_next_test_node(current_node)
        return None

    '''
        Check if TestNode has a successor 
        @param current_node: the TestNode to be checked
        @return: True or False (boolean)
    '''

    def __has_next_test_node(self, current_node):
        if not isinstance(current_node, TestNode):
            return False
        if current_node.next is not None:
            return True
        return False

    '''
        Check the successor of the TestNode
        @param current_node: the TestNode for which the successor is returned
        @return: successor TestNode
        @return type: TestNode
    '''

    def __get_next_test_node(self, current_node):
        if not self.__has_next_test_node(current_node):
            return None
        return current_node.next

    # - PUBLIC -

    '''
        Check if the test execution has a summary
        @return: True or False (boolean)
    '''

    def has_summary(self):
        if self.__summary:
            return True
        return False

    '''
        Return the summary of the test execution
        @return: summary (string)
    '''

    def get_summary(self):
        return self.__summary

    '''
        Set the summary of the test execution
        @param summary: summary (string)
        @return: None
    '''

    @accepts(str)
    def set_summary(self, summary):
        self.__summary = summary

    '''
        Check if the test execution has a description
        @return: True or False (boolean)
    '''

    def has_description(self):
        if self.__description:
            return True
        return False

    '''
        Return the description of the test execution
        @return: description (string)
    '''

    def get_description(self):
        return self.__description

    '''
        Set the description of the test execution
        @param description: description (string)
        @return: None
    '''

    @accepts(str)
    def set_description(self, description):
        self.__description = description

    '''
        Set the MasterData of the TestExecution
        NOTE: Pytefw only support 
        @param master_data_instance: instance of type MasterData
        @param type master_data_instance: instance
    '''

    def set_master_data(self, master_data_instance):
        self.__master_data_instance = master_data_instance

    '''
        Check if the test execution has test plans
        @return: True or False (boolean)
    '''

    def has_test_plans(self):
        if self.__part_of_test_plans:
            return True
        return False

    '''
        Return the test plans of the test execution
        @return: dictionary consisting of key value pairs in the form {id:test_plan_key, ..}
        @return type: dictionary
    '''

    def get_test_plans(self):
        return self.__part_of_test_plans

    '''
         Add a test plan with defined properties to a given test execution
            The test plan can either be newly created using the properties given 
            or a test plan instance can be passed as argument
        A test execution might be part of more than one test plan
        @param test_plan_instance: test_plan instance to be used
        @param type test_pan_instance: None or TestPlan
        test plan properties:
        @param m_id: unique id of the test plan (int or string) - None optional
        @param test_plan_key: key of the test set (string or None)
        @return: None
    '''

    @accepts((None, TestPlan))
    def append_test_plan(self, test_plan_instance=None, **kwargs):

        if test_plan_instance is None:
            args = {
                'm_id': None,
                'test_plan_key': None,
            }

            diff = set(kwargs.keys()) - set(args.keys())
            if diff:
                self.print_log_line("Ignore appending test plan - "
                                    "Invalid args: %s" % str(tuple(diff)), log_level="ERROR", color="RED")
                return

            args.update(kwargs)

            new_test_plan = TestPlan(args['m_id'], args['test_plan_key'])

        else:
            new_test_plan = test_plan_instance

        if list(filter(lambda m_test_plan: id(m_test_plan) is id(new_test_plan), self.__part_of_test_plans)) \
                or list(filter(lambda m_test_plan: m_test_plan.get_id() == new_test_plan.get_id(),
                               self.__part_of_test_plans)):
            self.print_log_line(
                "Could not add Test Plan with id %d to %s - Test Plan is duplicate" %
                (new_test_plan.get_id(), str(new_test_plan)), log_level="ERROR", color="RED")
            return

        self.__part_of_test_plans.append(new_test_plan)

    '''
        Add TestNode with properties to TestExecution LinkedList (sorted)
        The TestNode can be newly created and added 
        or a given test_node_instance is added
        
        @param test_node_instance: test_node instance to be used
        @param type test_node_instance: None or TestNode
            
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
        @return: None
    '''

    @accepts((None, TestNode))
    def append_test_node(self,
                         test_node_instance=None,
                         **kwargs):

        if test_node_instance is None:
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
                self.print_log_line("Ignoring appending Test - Invalid args: %s" % str(tuple(diff)),
                                    log_level="ERROR", color="RED")
                return

            args.update(kwargs)
            # add default pointers to previous and next TestNode
            args.update({'prev': None, 'm_next': None})

            if args['test_key'] and len(args['test_key']) > self.__TEST_KEY_LENGTH_LIMIT:
                self.print_log_line("Ignore adding test with key %s to test execution, "
                                    "length limit reached, MAX_LENGTH=%d"
                                    % (args['test_key'], self.__TEST_KEY_LENGTH_LIMIT), log_level="ERROR", color="RED")
                return

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
        else:
            new_test_node = test_node_instance

            if new_test_node.has_key() and len(new_test_node.get_key()) \
                    > self.__TEST_KEY_LENGTH_LIMIT:
                self.print_log_line("Ignore adding test with key %s to test execution, "
                                    "length limit reached, MAX_LENGTH=%d"
                                    % (new_test_node.get_key(), self.__TEST_KEY_LENGTH_LIMIT), log_level="ERROR", color="RED")
                return

        if self.__head is None:
            self.__head = self.__tail = new_test_node
        else:
            if self.__sort_by_rank:
                n = self.__head
                while n is not None:
                    if new_test_node.get_rank() is None:
                        n = None
                        break
                    if n.get_rank() is None or new_test_node.get_rank() < n.get_rank():
                        break
                    n = n.next
                # insert before selected node n
                if n is not None:
                    new_test_node.next = n
                    if n.prev is not None:
                        new_test_node.prev = n.prev
                        n.prev.next = new_test_node
                    else:
                        new_test_node.prev = None
                        self.__head = new_test_node
                    n.prev = new_test_node
                # insert after selected node n (IF >= n)
                else:
                    new_test_node.prev = self.__tail
                    new_test_node.next = None
                    self.__tail.next = new_test_node
                    self.__tail = new_test_node
            else:
                new_test_node.prev = self.__tail
                new_test_node.next = None
                self.__tail.next = new_test_node
                self.__tail = new_test_node
        self.__max_test_nodes += 1
