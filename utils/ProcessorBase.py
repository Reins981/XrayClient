#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab

"""
Created on 20.02.2018

@author: reko8680
@Coding Guidelines: ProcessorBase methods, functions and variables shall be written in Lowercase separated by _
"""

from __future__ import division

import multiprocessing
import threading
from multiprocessing import current_process
from multiprocessing.managers import BaseManager
from threading import currentThread
from queue import Queue
from Logger import Logger
from DecoratorUtils import XrayClientUIPyQtSlot


class StoppableThread(threading.Thread, Logger):
    def __init__(self, verbose):
        threading.Thread.__init__(self)
        Logger.__init__(self, self.__class__.__name__)
        self.stop_event = threading.Event()
        self.__verbose = verbose

    '''
        stop the thread classified as stoppable thread
        @return: None
    '''

    def stop(self):
        if self.isAlive():
            if self.__verbose:
                self.print_log_line("sending event to thread %s" % currentThread(), log_level="DEBUG")
            # set event to signal thread to terminate
            self.stop_event.set()
            # block calling thread until thread really has terminated
            if self.__verbose:
                self.print_log_line("finally joining thread %s" % currentThread(), log_level="DEBUG")
            try:
                self.join()

            except RuntimeError:
                if self.__verbose:
                    self.print_log_line('%s already terminated' % currentThread(), log_level="DEBUG")


class StoppableProcess(multiprocessing.Process, Logger):
    def __init__(self, verbose):
        multiprocessing.Process.__init__(self)
        Logger.__init__(self, self.__class__.__name__)
        self.stop_event = multiprocessing.Event()
        self.__verbose = verbose

    '''
        stop the process classified as stoppable process
        @return: None
    '''

    def stop(self):

        if self.is_alive():
            if self.__verbose:
                self.print_log_line("Terminating process %s" % current_process().name, log_level="DEBUG")
            # set event to signal process to terminate
            self.stop_event.set()
            # block calling thread until thread really has terminated
            try:
                self.join()

            except RuntimeError:
                if self.__verbose:
                    self.print_log_line("%s already terminated" % current_process().name, log_level="DEBUG")
            except AssertionError:
                if self.__verbose:
                    self.print_log_line("%s already terminated" % current_process().name, log_level="DEBUG")


class ThreadCondition:
    def __init__(self, cond):
        self.__terminate = cond

    '''
        signal a thread or process to terminate
        @param state: True or False (boolean)
        @return: None
    '''

    def set_terminate_state(self, state):
        self.__terminate = state

    '''
        check if termination state is set
        @return: (boolean)
    '''

    def termination_state_set(self):
        return self.__terminate


class TaskCounter:
    def __init__(self):
        self.__task_counter = 0

    '''
        increase task counter
        @return: None
    '''

    def set_task_counter(self):
        self.__task_counter += 1

    '''
        get current task counter
        @return: None
    '''

    def get_task_counter(self):
        return self.__task_counter


class ThreadResultMap(Logger):
    """
        Add the result of a Thread task to a result dictionary
        NOTE: This class is only for Threads!
    """
    def __init__(self):
        Logger.__init__(self, self.__class__.__name__)
        self.__server_responses = {}

    '''
        Map the response for a specific thread into the result dictionary
        @param thread_name: the name of the thread
        @param type thread_name: string
        @param response: the response to be added
        @param type response: json object
        @return: None
    '''
    def set_server_response(self, thread_name, response=None):
        self.print_log_line("Adding server result from thread %s" % thread_name)
        if response is None:
            response = [{}]
        self.__server_responses[thread_name] = response

    '''
        Return the complete result map to the caller
        @return: result map 
        @return type: python dictionary
    '''
    def get_result_map(self):
        return self.__server_responses


class ProcessResultMap:
    """
        Add the result of a Process task to a result dictionary
        NOTE: This class is only for Processes!
    """
    def __init__(self):
        self.__chosen_result = {}

    '''
        Map the response for a specific process into the result dictionary
        @param process: the name of the process
        @param type process: string
        @param item: the response to be added in form of an item
        @param type item: any type
        @return: None
    '''
    def set_chosen_result(self, process, item=None):
        self.__chosen_result[process] = item

    '''
        Return the complete result map to the caller
        @return: result map
        @return type: python dictionary
    '''
    def get_results(self):
        return self.__chosen_result


class ContinuousWorker(StoppableThread, Logger):
    def __init__(self, cond, tasks, task_counter=None, result_map=None, verbose=False):
        StoppableThread.__init__(self, verbose)
        Logger.__init__(self, self.__class__.__name__)
        self.__cond = cond
        self.__tasks = tasks
        self.__task_counter = task_counter
        self.__result_map = result_map
        self.__verbose = verbose
        # terminate process if timeout is reached
        self.__timeout = 30

        # execute run()
        print('[ContinuousWorker Thread] %s starting..' % (currentThread()))
        self.start()

    '''
        execute tasks from a given task queue
        @return: None
    '''

    def run(self):
        func, args, kwargs = self.__tasks.get(timeout=self.__timeout)
        result = None
        while True and not self.__cond.termination_state_set():
            try:
                if len(args) == 0:
                    result = func(**kwargs)
                else:
                    result = func(*args, **kwargs)
            except Exception as e:
                self.print_log_line('%s terminated with exception code %s' % (currentThread(), str(e)),
                                    log_level="ERROR", color="RED")
                break

        self.__result_map.set_server_response(currentThread(), result)
        self.__task_counter.set_task_counter()
        self.__tasks.task_done()
        self.stop()


class Worker(StoppableThread, Logger):
    def __init__(self, tasks, task_counter=None, result_map=None, verbose=False):
        StoppableThread.__init__(self, verbose)
        Logger.__init__(self, self.__class__.__name__)
        self.__tasks = tasks
        self.__task_counter = task_counter
        self.__result_map = result_map
        self.__verbose = verbose
        # terminate process or thread if timeout is reached
        self.__timeout = 30

        # execute run()
        print('[Worker Thread] %s starting..' % (currentThread()))
        self.start()

    '''
        execute tasks from a given task queue
        @return: None
    '''

    def run(self):
        while True:
            func, args, kwargs = self.__tasks.get(timeout=self.__timeout)
            result = None
            try:
                if len(args) == 0:
                    result = func(**kwargs)
                else:
                    result = func(*args, **kwargs)
            except Exception as e:
                self.print_log_line('%s terminated with exception code: %s' % (currentThread(), str(e)),
                                    log_level="ERROR", color="RED")
                result = e
            finally:
                self.__result_map.set_server_response(currentThread(), result)
                self.__task_counter.set_task_counter()
                self.__tasks.task_done()
                self.stop()
                break


class Processor(StoppableProcess, Logger):
    def __init__(self, cond, instance, tasks, lock, task_counter=None, result_map=None, verbose=False):
        StoppableProcess.__init__(self, verbose)
        Logger.__init__(self, self.__class__.__name__)
        self.__cond = cond
        self.__instance = instance
        self.__tasks = tasks
        self.__lock = lock
        self.__task_counter = task_counter
        self.__result_map = result_map
        self.__verbose = verbose
        # terminate process if timeout is reached
        self.__timeout = 30
        self.__timeout_error = False

    '''
        execute tasks from a given task queue
        @return: None
    '''

    def run(self):
        while True and not self.__cond.termination_state_set():
            if self.__tasks.empty() is True:
                continue

            try:
                job_name, args, kwargs = self.__tasks.get(block=True, timeout=self.__timeout)
            except Exception as e:
                self.print_log_line("Timeout occured ! -> %s" % str(e), log_level="WARNING", color="YELLOW")
                self.__timeout_error = True
                break

            try:
                if job_name == "TEST_JOB":
                    self.__instance.TEST_JOB(*args, **dict(kwargs, worker_proc=current_process().name,
                                                           proc_lock=self.__lock, result=self.__result_map))
                else:
                    self.print_log_line(
                        "%s invalid job name %s, job is not defined!" % (current_process().name, job_name),
                        log_level="ERROR", color="RED")
            except Exception as e:
                self.print_log_line("%s terminated with exception code %s" % (current_process().name, str(e)),
                                    log_level="ERROR", color="RED")
            finally:
                break

        self.print_log_line("%s finished task" % current_process().name)
        self.__lock.acquire()
        self.__task_counter.set_task_counter()
        if not self.__timeout_error:
            self.__tasks.task_done()
        self.__lock.release()
        self.stop()


class WorkerPool(Logger):
    """
        Pool of threads or processes consuming tasks from a queue
        @param cond: optional ThreadCondition object for which a terminate condition is set (type ThreadCondition)
        @param num_workers:  number of workers to start (int)
        @param class_instance: if processes are started instead of threads, the instance of a class for which functions
        are defined and executed must be supplied (type class instance)
        @param job_type: Thread or Process (string)
        @param start_continuous_worker_thread: if thread mode is applied run a specific task continuously until the
                                            terminate condition is met (boolean)
        @param verbose: enable debug logs (boolean)
    """

    @XrayClientUIPyQtSlot()
    def __init__(self, cond=None, num_workers=0, class_instance=None, job_type="Process",
                 start_continuous_worker_thread=False, verbose=False):
        Logger.__init__(self, self.__class__.__name__)
        self.__num_workers = num_workers
        self.__verbose = verbose
        if class_instance is None:
            self.__instance = self
        else:
            self.__instance = class_instance
        self.processor_jobs = []

        if cond is not None and not isinstance(cond, ThreadCondition):
            self.print_log_line("cond argument incorrect. Must be of type ThreadCondition", log_level="ERROR",
                                color="RED")
            raise Exception("cond argument incorrect. Must be of type ThreadCondition", "ERROR")

        if self.__verbose:
            self.print_log_line("Initializing task queue with %d tasks.." % self.__num_workers, log_level="DEBUG")

        if job_type == "Process":
            # share objects and queues between processes
            manager = multiprocessing.Manager()
            self.lock = manager.Lock()
            self.tasks = manager.Queue(self.__num_workers)

            BaseManager.register('TaskCounter', TaskCounter)
            BaseManager.register('ProcessResultMap', ProcessResultMap)
            manager = BaseManager()
            manager.start()
            self.task_counter = manager.TaskCounter()
            self.result_map = manager.ProcessResultMap()
        else:
            self.tasks = Queue(self.__num_workers)
            self.task_counter = TaskCounter()
            self.result_map = ThreadResultMap()

        if job_type == "Thread":
            for _ in range(self.__num_workers):
                self.print_log_line('%s -> starting Worker Thread' % (currentThread()))
                if not start_continuous_worker_thread:
                    Worker(
                        self.tasks,
                        task_counter=self.task_counter,
                        result_map=self.result_map,
                        verbose=self.__verbose
                    )
                else:
                    ContinuousWorker(
                        cond,
                        self.tasks,
                        task_counter=self.task_counter,
                        result_map=self.result_map,
                        verbose=self.__verbose
                    )
        else:
            for _ in range(self.__num_workers):
                p = Processor(
                    cond,
                    self.__instance,
                    self.tasks,
                    self.lock,
                    task_counter=self.task_counter,
                    result_map=self.result_map,
                    verbose=self.__verbose
                )
                p.start()
                self.print_log_line(" -> started Worker Process %s with pid %s" % (str(p), str(p.pid)))
                self.processor_jobs.append(p)

    '''
        add tasks to the queue for processes
        @param job_name: instance method to add (type instance method)
        @param *args: arguments of the method
        @param **kwargs: key word arguments of the method
        @return: None
    '''

    def add_task_processes(self, job_name, *args, **kwargs):
        # Add a task to the queue
        self.tasks.put((job_name, args, kwargs))

    '''
        add tasks to the queue for threads
        @param job_name: function or instance method to add (type func, type instance method)
        @param *args: arguments of the method or function
        @param **kwargs: key word arguments of the method or function
        @return: None
    '''

    def add_task_threads(self, func, *args, **kwargs):
        # Add a task to the queue
        self.tasks.put((func, args, kwargs))

    '''
        Wait till all tasks have completed
        @return: None
    '''

    def wait_completion(self):
        if self.__verbose:
            self.print_log_line("Waiting for task completion..", log_level="DEBUG")

        # wait for the first processes to finish
        while self.task_counter.get_task_counter() < self.__num_workers:
            pass

        self.terminate_all_workers()
        self.print_log_line("All tasks completed", log_level="INFO")

    '''
        terminate all worker processes or threads
        @return: None
    '''

    def terminate_all_workers(self):
        for process in self.processor_jobs:
            if process.is_alive():
                try:
                    if self.__verbose:
                        self.print_log_line("Terminating process %s" % process, log_level="DEBUG")
                    process.terminate()
                    process.join()
                except RuntimeError:
                    self.print_log_line("Could not join process! Tasks already completed", log_level="ERROR")

    '''
        get current task counter
        @return: task counter (int)
    '''

    def get_task_counter(self):
        return self.task_counter.get_task_counter()

    '''
        get all results for each process
        @return: results (dictionary)
    '''

    def get_process_results(self):
        return self.result_map.get_result_map()

    '''
        get all results for each thread
        @return: results (dictionary)
    '''

    def get_thread_results(self):
        return self.result_map.get_result_map()
