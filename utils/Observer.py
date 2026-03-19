#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 03.3.2019

@param author: reko8680
@Coding Guidelines: Observer methods, functions and variables shall be written in Lowercase separated by _
"""

from Synchronization import *


class Observer:
    def update(observable, arg):
        """
            Called when observed object is updated or modified
            You call the observed objects notify_observers method to notify all the objects observers
            of the change
        """
        pass


class Observable(Synchronization):
    def __init__(self):
        self.obs = []
        self.changed = 0
        super().__init__()

    '''
        Add an observer to the list of observers
        @param observer: observer
        @param type observer: class instance
        @return: None
    '''
    def add_observer(self, observer):
        if observer not in self.obs:
            self.obs.append(observer)

    '''
        Delete an observer from the list of observers
        @param observer: observer
        @param type observer: class instance
        @return: None
    '''
    def delete_observer(self, observer):
        self.obs.remove(observer)

    '''
        Notify all observers
        @return: None
    '''
    def notify_observers(self, arg=None):
        """
            If the object has changed, notify all of its observers
            Each observer has its upate() method called with two arguments: this observable object and the generic arg
        """
        self.mutex.acquire()
        try:
            if not self.changed: return
            local_array = self.obs[:]
            self.clear_changed()
        finally:
            self.mutex.release()
        # Updating is not required to be synchronized
        for observer in local_array:
            observer.update(self, arg)

    '''
        Notify a specific observer
        @param n_observer: observer to be notified
        @param type n_observer: class instance
        @return: None
    '''
    def notify_observer(self, n_observer, arg=None):
        """
            Notify a specific observer when an object has changed
        """
        self.mutex.acquire()
        try:
            if not self.changed: return
            local_array = self.obs[:]
            self.clear_changed()
        finally:
            self.mutex.release()
        # Updating is not required to be synchronized
        for observer in local_array:
            if type(observer) is type(n_observer):
                observer.update(self, arg)
                break

    '''
        Delete all observers
        @return: None
    '''
    def delete_observers(self):
        self.obs = []

    '''
        Set a signal that an observer update shall be triggered
        @return: None
    '''
    def set_changed(self):
        self.changed = 1

    '''
        after an observer update was perfromed, reset the signal
        @return: None
    '''
    def clear_changed(self):
        self.changed = 0

    '''
        Check if an observer update was triggered
        @return: True or False (boolean)
    '''
    def has_changed(self):
        return self.changed

    '''
        Count the number of observers added
        @return: number of observers 
    '''
    def count_observers(self):
        return len(self.obs)


'''
    synchronize methods
'''
synchronize(Observable, "add_observer delete_observer delete_observers " +
                        "set_changed clear_changed has_changed count_observers")

