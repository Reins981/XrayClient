#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab

"""
Created on 08.03.2019

@author: reko8680
@Coding Guidelines: Connector methods, functions and variables shall be written in Lowercase separated by _
"""

import time
import os
import json
import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth1
from Logger import Logger
from ExceptionUtils import RequestException, InvalidResponse, AuthenticationException
from DecoratorUtils import accepts, XrayClientUIPyQtSlot


class JiraConnector(Logger):
    """
        send/post content from/to a web server using HTTP(S)
        @param base_url: base url of Xray REST API
        @param type base_url: string
        @param auth: choose between "Basic" and "OAuth1" authentication (string)
        @param user: username [if Basic Auth] (string)
        @param password: password [if Basic Auth] (string)
        @param timeout: abort JIRA connection attempt if timeout has exceeded (int)
        @param verify_ssl_certs: enable or disable server certificate verification (boolean)
        @param verbose: enable or disable debug log output (boolean)
    """
    __conn_established = (None, None)
    __retries = 5
    __auth_method = None

    # Oauth key setup
    APP_KEY = None
    APP_SECRET = None
    USER_OAUTH_TOKEN = None
    USER_OAUTH_TOKEN_SECRET = None

    @accepts(str, str, str, str, int, bool, bool)
    def __init__(self,
                 base_url="",
                 auth="Basic",
                 user="",
                 password="",
                 timeout=5,
                 verify_ssl_certs=False,
                 verbose=False):
        Logger.__init__(self, self.__class__.__name__)
        self.__user = user
        self.__password = password
        self.__timeout = timeout
        self.__verify_ssl_certs = verify_ssl_certs
        self.__verbose = verbose

        self.__setup(auth, base_url)
        self.__connect()

    '''
        setup authentication schema and basic attributes
    '''

    @accepts(str, str)
    def __setup(self, auth_method, base_url):
        auth_method = auth_method.lower()
        if auth_method == "basic":
            self.__auth_method = HTTPBasicAuth(self.__user,
                                               self.__password
                                               )
        elif auth_method == "oauth1":
            self.__auth_method = OAuth1(self.APP_KEY,
                                        self.APP_SECRET,
                                        self.USER_OAUTH_TOKEN,
                                        self.USER_OAUTH_TOKEN_SECRET
                                        )
        self.base_url = base_url
        self.success_resp_codes = {
            200: "OK",
            201: "Created",
            202: "Accepted",
            203: "Non-Authoritive Information",
            204: "No Content"
        }

    '''
        Try to reconnect this amount of time if first webhost connection attempt failed
        @param retries: number of retries (int)
        @return: None
    '''

    @accepts(int)
    def set_retry_sequence(self, retries):
        self.__retries = retries

    # -- PRIVATE --
    '''
        is the http response a valid one
        @param response: response object (type response)
        @return: (boolean)
    '''

    def __is_valid_response_status_code(self, response):
        if response.status_code not in self.success_resp_codes:
            return False
        return True

    '''
        check if the REST API Endpoint responds
        @return: None
    '''

    def __connect(self):
        try:
            allow_redirects = True
            r = requests.head(self.base_url,
                              allow_redirects=allow_redirects,
                              timeout=self.__timeout,
                              verify=self.__verify_ssl_certs,
                              auth=self.__auth_method
                              )
            self.__conn_established = (r.status_code in self.success_resp_codes.keys(), r.status_code)
        except requests.exceptions.RequestException as e:
            self.print_log_line("%s" % e, log_level="ERROR", color="RED")

    '''
        disconnect webhost
        @return: None
    '''

    def __disconnect(self):
        self.print_log_line("Start disconnect")
        self.__conn_established = (False, None)
        self.print_log_line("Disconnected")

    '''
        destructor
    '''

    def __del__(self):
        self.print_log_line("Deleted")

    '''
        Test the resource for a content type
        @param url: resource to test (string)
        @return: (boolean) or exception (RequestException) is raised
    '''

    def __is_content_type_set(self, url):
        try:
            allow_redirects = True
            r = requests.head(url,
                              allow_redirects=allow_redirects,
                              timeout=self.__timeout,
                              verify=self.__verify_ssl_certs,
                              auth=self.__auth_method
                              )
        except requests.exceptions.RequestException as e:
            raise RequestException("%s" % e, "ERROR")

        header = r.headers
        content_type = header.get('content-encoding')

        if self.__verbose:
            self.print_log_line("Content type is %s" % str(content_type), log_level="DEBUG")

        if content_type is None or content_type is 'None':
            return False
        return True

    '''
        fetch the given resource (GET request)
        @param url: resource to fetch (string)
        @return: response object (type response) or specific exceptions (RequestException, AuthenticationRequired) are 
                 raised
    '''

    def __get_resource(self, url):

        if self.__verbose and not self.__verify_ssl_certs:
            self.print_log_line("NOTE: Certificate verification is disabled!", log_level="WARNING", color="YELLOW")

        self.print_log_line("Starting download..", color="BOLD")
        try:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            allow_redirects = True
            r = requests.get(url,
                             headers=headers,
                             allow_redirects=allow_redirects,
                             timeout=self.__timeout,
                             verify=self.__verify_ssl_certs,
                             auth=self.__auth_method
                             )
        except requests.exceptions.RequestException as e:
            raise RequestException('%s' % e, "ERROR")

        header = r.headers
        authentication_required = header.get('WWW-Authenticate')

        if authentication_required is not None:
            self.print_log_line('Authentication failed! - Method in use: %s' % str(authentication_required),
                                log_level="ERROR", color="RED")
            raise AuthenticationException('Authentication failed! - Method in use: %s' % str(authentication_required),
                                          "ERROR")

        return r

    '''
        post to a given resource with data supplied (POST request)
        @param url: resource to post to (string)
        @param data: data (json) to post
        @return: response object (type response) or specific exceptions (RequestException, AuthenticationRequired) are 
                 raised
    '''

    def __post_resource(self, url, data):

        if self.__verbose and not self.__verify_ssl_certs:
            self.print_log_line("NOTE: Certificate verification is disabled!", log_level="WARNING", color="YELLOW")

        self.print_log_line("Starting upload..", color="BOLD")
        try:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            allow_redirects = True
            r = requests.post(url,
                              json=data,
                              headers=headers,
                              allow_redirects=allow_redirects,
                              timeout=self.__timeout,
                              verify=self.__verify_ssl_certs,
                              auth=self.__auth_method
                              )
        except requests.exceptions.RequestException as e:
            raise RequestException('%s' % e, "ERROR")

        header = r.headers
        authentication_required = header.get('WWW-Authenticate')

        if authentication_required is not None:
            self.print_log_line('Authentication failed! - Method in use: %s' % str(authentication_required),
                                log_level="ERROR", color="RED")
            raise AuthenticationException('Authentication failed! - Method in use: %s' % str(authentication_required),
                                          "ERROR")

        return r

    '''
        request the given resource with or without data
        @param url: resource to request
        @param data: None -> GET request, json -> POST request
        @return: response object (type response)
    '''

    def __request(self, url, data=None):
        r = None
        if data is None:
            if self.__is_content_type_set(url):
                r = self.__get_resource(url)
            else:
                if self.__verbose:
                    self.print_log_line("No content_type received for url %s" % url, log_level="ERROR", color="RED")
        else:
            r = self.__post_resource(url, data)

        return r

    # -- PUBLIC --
    '''
        Reconnect to webhost if initial connection attempt failed
        @return: True or False (boolean)
    '''

    def reconnect(self):
        self.print_log_line("Start reconnect")
        for i in range(self.__retries):
            time.sleep(0.2)
            self.__disconnect()
            self.__connect()
            success = self.__conn_established[0]
            response = self.__conn_established[1]
            if success:
                self.print_log_line(
                    "Successfully reconnected to REST API endpoint {0} after {1} retries: ".format(self.base_url,
                                                                                                   str(i)),
                    color="GREEN")
                return True
            else:
                self.print_log_line(
                    "REST API endpoint with URI {0} is not reachable after {1} retries, response code was {2}".format(
                        self.base_url,
                        str(i + 1),
                        str(response)), log_level="ERROR", color="RED")
                if i < self.__retries - 1:
                    self.print_log_line("Retrying to connect")
                continue

        self.print_log_line(
            "Could not reconnect to REST API endpoint with URI {0} after {1} retries: ".format(self.base_url,
                                                                                               str(self.__retries)),
            log_level="ERROR", color="RED")
        return False

    '''
        Check if webhost connection is established
        @return: True or False (boolean)
    '''

    def is_xray_api_connected(self):
        success = self.__conn_established[0]
        response = self.__conn_established[1]
        if success:
            self.print_log_line("Successfully connected to REST API endpoint with URI {0}".format(self.base_url),
                                color="GREEN")
        else:
            self.print_log_line(
                "Could not connect to REST API endpoint with URI {0}, response code was {1}: ".format(self.base_url,
                                                                                                      str(response)),
                log_level="ERROR", color="RED")
        return success

    '''
        send a GET request
        @param url: resource to request (string)
        @return: response (json) or exception InvalidResponse is raised
    '''

    @XrayClientUIPyQtSlot()
    def send_get(self, url):
        if self.__verbose:
            self.print_log_line("GET " + url, log_level="DEBUG")

        response = self.__request(url)

        if not response:
            raise InvalidResponse("Response from server was None", "ERROR")
        if not self.__is_valid_response_status_code(response):
            raise InvalidResponse("Invalid response status - %s - received" % response.status_code, "ERROR")

        return response.json()

    '''
        send a POST request with data supplied. The data will be converted to json format.
        @param url: resource to request (string)
        @param data: data to be posted (python dictionary)
        @return: response (json) or exception InvalidResponse is raised
    '''

    @XrayClientUIPyQtSlot()
    def send_post(self, url, data=None):
        if data is None:
            data = {}
        json_data = json.dumps(data)
        if self.__verbose:
            self.print_log_line("POST " + data + " to " + url, log_level="DEBUG")

        response = self.__request(url, json_data)

        if not response:
            raise InvalidResponse("Response from server was None", "ERROR")
        if not self.__is_valid_response_status_code(response):
            raise InvalidResponse("Invalid response status - %s - received" % response.status_code, "ERROR")

        return response.json()
