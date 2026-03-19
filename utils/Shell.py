#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 29.11.2018

@param author: reko8680
@Coding Guidelines: Shell methods, functions and variables shall be written in Lowercase separated by _
"""

import sys
import paramiko
import socket
import time
import os
import fnmatch
from Logger import Logger
from socket import timeout as SocketTimeout
from DecoratorUtils import accepts, XrayClientUIPyQtSlot


class SCPClient(Logger):
    """
    An scp1 implementation, compatible with openssh scp.
    Raises SCPException for all transport related errors. Local filesystem
    and OS errors pass through. 

    Main public methods are .put and .get 
    The get method is controlled by the remote scp instance, and behaves 
    accordingly. This means that symlinks are resolved, and the transfer is
    halted after too many levels of symlinks are detected.
    The put method uses os.walk for recursion, and sends files accordingly.
    Since scp doesn't support symlinks, we send file symlinks as the file
    (matching scp behaviour), but we make no attempt at symlinked directories.
    """

    def __init__(self, transport, buff_size=16384, socket_timeout=5.0, progress=None):
        Logger.__init__(self, self.__class__.__name__)
        """
        Create an scp1 client.

        @param transport: an existing paramiko L{Transport}
        @param type transport: L{Transport}
        @param buff_size: size of the scp send buffer.
        @param type buff_size: int
        @param socket_timeout: channel socket timeout in seconds
        @param type socket_timeout: float
        @param progress: callback - called with (filename, size, sent) during transfers
        @param type progress: function(string, int, int)
        """
        self.__transport = transport
        self.__buff_size = buff_size
        self.__socket_timeout = socket_timeout
        self.__channel = None
        self.__preserve_times = False
        self.__progress = progress
        self.__recv_dir = ''
        self.__utime = None
        self.__dirtimes = {}

    '''
        Destructor
    '''

    def __del__(self):
        if self.__channel:
            self.__channel.close()

    @XrayClientUIPyQtSlot()
    def put(self, files, remote_path='.',
            recursive=False, preserve_times=False):
        """
        Transfer files to remote host.

        @param files: A single path, or a list of paths to be transfered.
            recursive must be True to transfer directories.
        @param type files: string OR list of strings
        @param remote_path: path in which to receive the files on the remote
            host. defaults to '.'
        @param type remote_path: str
        @param recursive: transfer files and directories recursively
        @param type recursive: bool
        @param preserve_times: preserve mtime and atime of transfered files
            and directories.
        @param type preserve_times: bool
        """
        self.__preserve_times = preserve_times
        self.__channel = self.__transport.open_session()
        self.__channel.settimeout(self.__socket_timeout)
        scp_command = ('scp -t %s', 'scp -r -t %s')[recursive]
        self.__channel.exec_command(scp_command % remote_path)
        self.__recv_confirm()

        if not isinstance(files, (list, tuple)):
            files = [files]

        self.__send_files(files, recursive=recursive)

    @XrayClientUIPyQtSlot()
    def get(self, remote_path, local_path='',
            recursive=False, preserve_times=False):
        """
        Transfer files from remote host to localhost

        @param remote_path: path to retreive from remote host. since this is
            evaluated by scp on the remote host, shell wildcards and 
            environment variables may be used.
        @param type remote_path: str
        @param local_path: path in which to receive files locally
        @param type local_path: str
        @param recursive: transfer files and directories recursively
        @param type recursive: bool
        @param preserve_times: preserve mtime and atime of transfered files
            and directories.
        @param type preserve_times: bool
        """
        self.__recv_dir = local_path or os.getcwd()
        rcsv = ('', ' -r')[recursive]
        prsv = ('', ' -p')[preserve_times]
        self.__channel = self.__transport.open_session()
        self.__channel.settimeout(self.__socket_timeout)
        self.__channel.exec_command('scp%s%s -f %s' % (rcsv, prsv, remote_path))
        self.__recv_all()
        # if self.channel:
        #    self.channel.close()

    '''
        return just the file stats needed for scp
        @param name: filename (string)
        @return: file stats (tuple)
    '''

    def __read_stats(self, name):
        stats = os.stat(name)
        mode = oct(stats.st_mode)[-4:]
        size = stats.st_size
        atime = int(stats.st_atime)
        mtime = int(stats.st_mtime)
        return mode, size, mtime, atime

    '''
        send a file
        @param file: file to send (string)
        @return: None
    '''

    def __send_single_files(self, files):
        if isinstance(files, str): files = [files]
        for name in files:
            basename = os.path.basename(name)
            (mode, size, mtime, atime) = self.__read_stats(name)
            if self.__preserve_times:
                self.__send_time(mtime, atime)
            file_hdl = open(name, 'rb')
            self.__channel.sendall('C%s %d %s\n' % (mode, size, basename))
            self.__recv_confirm()
            file_pos = 0
            buff_size = self.__buff_size
            chan = self.__channel
            if self.__progress:
                self.__progress(name, size, 0)  # send 0 progress to detect begin :)
            while file_pos < size:
                chan.sendall(file_hdl.read(buff_size))
                file_pos = file_hdl.tell()
                if self.__progress:
                    self.__progress(name, size, file_pos)
            chan.sendall('\x00')
            file_hdl.close()

    def __send_files(self, files, m_filter=[], recursive=False):
        """
        Send files to remote destination
            
        @param param files: list of files or paths to be transferred to remote destination
        (all files are put into the dest. dir!)
        @param type files: either str or list
        @param param m_filter: list of fnmatch filters (*,*.c,..) empty list = no filtering
        @param type m_filter: either str or list
        @param param recursive: recurse into subdirs
        @param type recursive: boolean
        """
        # for loop for recursive transfers
        # will only return one dir if recursive = False
        # handle multiple paths
        if isinstance(files, str): files = [files]
        for base in files:
            if os.path.isfile(base):
                # is file
                self.__send_single_files(base)
            elif os.path.isdir(base):
                # is pure dir
                last = base  # save base for get_dir_level_diff
                for root, fls in self.__list_dir(base, m_filter, recursive=recursive):
                    # build file-list for transfer, and transfer file by file
                    pop, push = self.__traverse_dir_instruction(last, root)
                    last = root
                    for i in range(pop):
                        self.__send_popd()
                    for i in range(push):
                        self.__send_pushd(root)

                    # actually transfer files
                    self.__send_single_files([os.path.join(root, f) for f in fls])
            elif not os.path.isfile(base) and not os.path.isdir(base):
                # wildcarded filename
                for root, fls in self.__list_dir(os.path.dirname(base), filters=os.path.basename(base),
                                                 recursive=False):
                    self.__send_single_files([os.path.join(root, f) for f in fls])

    '''
       return root dir + unique files matching filter condition
       @param paths: paths to search files in (string)
       @param filters: filter to be applied (list or string)
    '''

    def __list_dir(self, paths, filters=[], recursive=False):
        ffiles = []
        if isinstance(filters, str): filters = [filters]
        if isinstance(paths, str): paths = [paths]

        for root in paths:
            for root, dirs, files in os.walk(root, topdown=True):
                if len(filters) > 0:
                    ffiles = []
                    for f in filters:
                        ffiles += fnmatch.filter(files, f)  # join with prev. files
                    # return root dir + unique files
                    files = ffiles  # filtered files
                yield root, set(files)
                if not recursive: break

    '''
        normalize path to unix path
        @param p: path
        @return: normalized path (string)
    '''

    def __normalize_path(self, p):
        p = os.path.normpath(p)  # normalize /x/../A/./../b/ to /b/
        p = p.replace("\\", "/")  # normalize path to unix path
        return p

    '''
        Calculate the number of POPs and PUSHs to get from dir a to dir b
        @return: Returns (pops,pushs)
    '''

    def __traverse_dir_instruction(self, a, b):
        a = self.__normalize_path(a)
        b = self.__normalize_path(b)
        if a[-1] == "/": a = a[:-1]  # kill trailing / (to avoid extra pushes/pops)
        if b[-1] == "/": b = b[:-1]
        last = a.split("/")  # listify
        current = b.split("/")
        # compare last to current
        pos = 0
        for e in last:
            if pos >= len(current) or e != current[pos]: break
            pos += 1
            # calc_pops / pushes from last_dir to current dir
        num_pops = len(last) - pos
        num_pushs = len(current) - pos
        return num_pops, num_pushs

    '''
        send a push command
        @param directory: send push from this directory
        @return: None
    '''

    def __send_pushd(self, directory):
        (mode, size, mtime, atime) = self.__read_stats(directory)
        basename = os.path.basename(directory)
        if self.__preserve_times:
            self.__send_time(mtime, atime)
        self.__channel.sendall('D%s 0 %s\n' % (mode, basename))
        self.__recv_confirm()

    '''
        send a pop command
        @return: None
    '''

    def __send_popd(self):
        self.__channel.sendall('E\n')
        self.__recv_confirm()

    def __send_time(self, mtime, atime):
        self.__channel.sendall('T%d 0 %d 0\n' % (mtime, atime))
        self.__recv_confirm()

    '''
        Read scp response
        @return: None
    '''

    def __recv_confirm(self):
        # read scp response
        try:
            msg = self.__channel.recv(512)
            msg = msg.decode("utf-8")
        except SocketTimeout:
            raise SCPException('Timout waiting for scp response', "ERROR")
        if msg and msg[0] == '\x00':
            return
        elif msg and msg[0] == '\x01':
            raise SCPException(msg[1:])
        elif self.__channel.recv_stderr_ready():
            msg = self.__channel.recv_stderr(512)
            raise SCPException(msg)
        elif not msg:
            raise SCPException('No response from server', "ERROR")
        else:
            raise SCPException('Invalid response from server: ' + msg, "ERROR")

    '''
        Loop over scp commands, and receive as necessary
        @return: None
    '''

    def __recv_all(self):
        # loop over scp commands, and receive as necessary
        command = {'C': self.__recv_file,
                   'T': self.__set_time,
                   'D': self.__recv_pushd,
                   'E': self.__recv_popd}
        while not self.__channel.closed:
            # wait for command as long as we're open
            self.__channel.sendall('\x00')
            msg = self.__channel.recv(1024)
            msg = msg.decode("utf-8")
            if not msg:  # chan closed while recving
                break
            code = msg[0]
            try:
                command[code](msg[1:])
            except KeyError:
                raise SCPException(repr(msg))
        # directory times can't be set until we're done writing files
        self.__set_dirtimes()

    '''
        set time for command
        @param cmd: command
    '''

    def __set_time(self, cmd):
        try:
            times = cmd.split()
            mtime = int(times[0])
            atime = int(times[2]) or mtime
        except Exception:
            self.__channel.send('\x01')
            raise SCPException('Bad time format', "ERROR")
        # save for later
        self.__utime = (atime, mtime)

    '''
        Receive a file
        @param cmd: command
        @return: None
    '''

    def __recv_file(self, cmd):
        chan = self.__channel
        parts = cmd.split()
        try:
            mode = int(parts[0], 8)
            size = int(parts[1])
            path = os.path.join(self.__recv_dir, parts[2])
        except Exception:
            chan.send('\x01')
            chan.close()
            raise SCPException('Bad file format', "ERROR")

        try:
            file_hdl = open(path, 'wb')
        except IOError as e:
            chan.send('\x01' + e.message)
            chan.close()
            raise

        buff_size = self.__buff_size
        pos = 0
        chan.send('\x00')
        try:
            while pos < size:
                # we have to make sure we don't read the final byte
                if size - pos <= buff_size:
                    buff_size = size - pos
                file_hdl.write(chan.recv(buff_size))
                pos = file_hdl.tell()
                if self.__progress:
                    self.__progress(path, size, pos)

            msg = chan.recv(512)
            msg = msg.decode("utf-8")
            if msg and msg[0] != '\x00':
                raise SCPException(msg[1:])
        except SocketTimeout:
            chan.close()
            raise SCPException('Error receiving, socket.timeout', "ERROR")

        file_hdl.truncate()
        try:
            os.utime(path, self.__utime)
            self.__utime = None
            os.chmod(path, mode)
            # should we notify the other end?
        finally:
            file_hdl.close()
        # '\x00' confirmation sent in _recv_all

    '''
        Receive result of push command
        @param cmd: command
        @return: None
    '''

    def __recv_pushd(self, cmd):
        parts = cmd.split()
        try:
            mode = int(parts[0], 8)
            path = os.path.join(self.__recv_dir, parts[2])
        except Exception:
            self.__channel.send('\x01')
            raise SCPException('Bad directory format', "ERROR")
        try:
            if not os.path.exists(path):
                os.mkdir(path, mode)
            elif os.path.isdir(path):
                os.chmod(path, mode)
            else:
                raise SCPException('%s: Not a directory' % path, "ERROR")
            self.__dirtimes[path] = (self.__utime)
            self.__utime = None
            self.__recv_dir = path
        except (OSError, SCPException) as e:
            self.__channel.send('\x01' + e.message)
            raise

    '''
        Receive result of pop command
        @return: None
    '''

    def __recv_popd(self):
        self.__recv_dir = os.path.split(self.__recv_dir)[0]

    '''
        Set directory times
        @return: None
    '''

    def __set_dirtimes(self):
        try:
            for d in self.__dirtimes:
                os.utime(d, self.__dirtimes[d])
        finally:
            self.__dirtimes = {}


class SCPException(Exception):
    """
        SCP exception class
    """
    pass


class SshShell(Logger):
    __ssh_object = None
    __retries = 60
    __port = 22

    @accepts(str, str, str, int, bool)
    def __init__(self,
                 host="192.168.1.4",
                 username="root",
                 password="root",
                 timeout=1,
                 verbose=False):
        Logger.__init__(self, self.__class__.__name__)
        self.__host = host
        self.__username = username
        self.__password = password
        self.__verbose = verbose
        # SSH connection timeout in seconds
        self.__timeout = timeout
        self.success = False
        self.reconnect_triggered = False

        # NEW SSh connection object
        if self.__ssh_object is None:
            # paramiko ssh does not support host based authentication without a password
            if self.__password is None:
                self.__ssh_object = paramiko.Transport((self.__host, self.__port))
            else:
                self.__init_ssh_client()

    # - PRIVATE -
    '''
        Create the ssh connection object and load the system host keys if possible
        @return: None
    '''

    def __init_ssh_client(self):
        self.__ssh_object = paramiko.SSHClient()
        '''
            Add the server public key and server hostname for server authentication to the list of known hosts
           Note that AutoAddPolicy() might be a security thread    
        '''
        self.__ssh_object.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.__ssh_object.load_system_host_keys()

    '''
        Open the ssh connection
        @param timeout: terminate the connection attempt if timeout has reached (int)
        @return: True or False (boolean)
    '''

    def open(self):
        self.print_log_line("Connecting to %s on port %s" % (self.__host, str(self.__port)))
        if self.__verbose:
            self.print_log_line("username: " + self.__username, log_level="DEBUG")
            self.print_log_line("password: " + str(self.__password), log_level="DEBUG")
            self.print_log_line("timeout: " + str(self.__timeout), log_level="DEBUG")

        # in case of a reconnect create a new ssh object
        if self.reconnect_triggered and self.__ssh_object is None:
            if self.__password is None:
                # paramiko ssh does not support host based authentication when no password is given
                self.__ssh_object = paramiko.Transport((self.__host, self.__port))
            else:
                self.__init_ssh_client()
        try:
            if self.__password is not None:
                self.__ssh_object.connect(
                    hostname=self.__host,
                    username=self.__username,
                    password=self.__password,
                    timeout=self.__timeout,
                )
            else:
                self.__ssh_object.connect()
                self.__ssh_object.auth_none(self.__username)
            self.success = True
            self.print_log_line("Successfully connected to target IP: " + self.__host, color="OKGREEN")
            return True
        except socket.timeout as msg:
            self.print_log_line("Connection timeout %s" % msg, color="FAIL")
            return False
        except Exception as msg:
            self.print_log_line("%s" % msg)
            return False

    '''
        Close the ssh connection
        @return: None
    '''

    def close(self):
        if self.__verbose:
            self.print_log_line("Disconnecting")

        if self.__ssh_object is not None:
            self.__ssh_object.close()
            self.__ssh_object = None
            self.reconnect_triggered = False

    '''
        Try to reconnect x times to the ssh host in case the first connection attempt failed
        @return: True or False (boolean)
    '''

    def reconnect(self):
        self.print_log_line("Start reconnect..")
        for i in range(self.__retries):
            time.sleep(1)
            self.close()
            self.reconnect_triggered = True
            success = self.open()
            if not success:
                if self.__verbose:
                    self.print_log_line("Target {0} is not reachable after {1} retries".format(self.__host, str(i + 1)),
                                        log_level="ERROR", color="RED")
                if i < self.__retries - 1:
                    if self.__verbose:
                        self.print_log_line("Retrying to connect ...")
            else:
                self.print_log_line(
                    "Successfully reconnected to target IP: " + self.__host + " after " + str(i + 1) + ' retries.',
                    color="GREEN")
                return True

        self.print_log_line(
            "Could not reconnect to target host: " + self.__host + " after " + str(self.__retries) +
            ' retries. Giving up.', log_level="ERROR", color="RED")
        return False

    '''
        Define number of connection attempts in case of a failure
        @param num_retries: number of retries (int)
    '''

    @accepts(int)
    def set_retry_sequence(self, num_retries):
        self.__retries = num_retries

    '''
        Check if the ssh host is connected
        @return: True or False (boolean)
    '''

    def is_host_connected(self):
        return self.success and self.__ssh_object is not None

    '''
        Run a ssh command
        @param cmd: command (string)
        @return: exist status (int), stdout (string), stderr (string)
    '''

    @accepts(str)
    def run(self, cmd):
        if self.__verbose:
            self.print_log_line("Running command: " + cmd)

        if self.__password is None:
            cmd_channel = self.__ssh_object.open_session()
            stdin, stdout, stderr = cmd_channel.exec_command(cmd)
        else:
            stdin, stdout, stderr = self.__ssh_object.exec_command(cmd)

        # wait for cmd to finish and check exit status
        exit_status = stdout.channel.recv_exit_status()

        stdout_str = stdout.read()
        stderr_str = stderr.read()
        if self.__password is None:
            cmd_channel.close()

        if self.__verbose:
            self.print_log_line("status: ", str(exit_status))
            self.print_log_line("stdout: ", str(stdout_str))
        return exit_status, stdout_str, stderr_str

    def open_scp(self, socket_timeout=None, progress=None):
        """
            Open SCP Connection
            @param progress: callback function (name,size,sent)
            @param socket_timeout: timeout (float)
            @return: scp client instance
        """
        t = self.__ssh_object.get_transport()
        c = SCPClient(t, socket_timeout=socket_timeout, progress=progress)
        return c

    '''
        Destructor
    '''

    def __del__(self):
        if self.__ssh_object is not None:
            self.close()


if __name__ == '__main__':
    def progress(filename, size, sent):
        print("Uploading %s - %s - %s" % (filename, size, sent))


    shell = SshShell()
    shell.open()
    if not shell.is_host_connected() and not shell.reconnect():
        sys.exit(1)
    shell.run("ls -lh")
    scp = shell.open_scp(progress=progress)
    # scp.put("lib", remote_path="/tmp", recursive=True)
    scp.get("/tmp/libMIBBapLib.so", os.getcwd())
