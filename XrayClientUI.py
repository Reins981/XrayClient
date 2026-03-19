#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab

"""
Created on 03.05.2019

@author: reko8680
@Coding Guidelines: UI methods, functions and variables shall be written in Uppercase
"""

import pathmagic
import sys
import os
import re
import datetime

with pathmagic.context("qss"):
    import breeze_resources

with pathmagic.context("utils"):
    from DecoratorUtils import accepts, XrayClientUIPyQtSlot
    from ExceptionUtils import GeneralError

from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtCore import Qt, QTimer, QFile, QTextStream, QObject, pyqtSignal, pyqtSlot, QThread, QCoreApplication, \
    QSettings, QSize, QPoint
from PyQt5.QtWidgets import (QApplication, QComboBox, QCheckBox,
                             QDialog, QGridLayout, QGroupBox, QLabel, QLineEdit,
                             QPushButton, QTabWidget, QTextEdit,
                             QVBoxLayout, QWidget, QFrame, QFileDialog, QMessageBox)
from PyQt5.QtGui import QShowEvent, QTextCursor, QIntValidator
from multiprocessing import Queue
from XrayClientCs import XrayClient

# -- Global Config Dictionary --
ConfigDict = {}

'''
    The new Stream Object which replaces the default stream associated with sys.stdout
    This object just puts data in a queue
'''


class WriteStream(object):
    def __init__(self, m_queue):
        self.queue = m_queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


'''
    A QObject (to be run in a QThread) which sits waiting for data to come through a Queue.Queue().
    It blocks until data is available, and one it has got something from the queue, it sends
    it to the "MainThread" by emitting a Qt Signal
'''


class Receiver(QObject):
    signal = pyqtSignal(str)

    def __init__(self, m_queue, *args, **kwargs):
        QObject.__init__(self, *args, **kwargs)
        self.queue = m_queue

    @pyqtSlot()
    def run(self):
        while True:
            text = self.queue.get()
            self.signal.emit(text)


'''
    Create options for the XrayClient from a global configuration dictionary
'''


class Options(object):
    def __init__(self):
        keys = ConfigDict.keys()
        for key in keys:
            setattr(self, key, ConfigDict[key])


'''
    Run the XrayClient in this Thread
'''


class XrayClientThread(QThread):
    signal = pyqtSignal(str)

    @accepts(Options)
    def __init__(self, options):
        QThread.__init__(self)
        self.options = options
        # the xray client instance
        self.xrayClient = None

    # run method gets called when we start the thread
    def run(self):
        self.xrayClient = XrayClient(
            self.options.mode,
            self.options.import_mode_test_execution,
            self.options.import_mode_test_plan,
            self.options.issue_type_key,
            self.options.framework,
            self.options.configuration_location,
            self.options.framework_config_folder,
            self.options.remote_host,
            self.options.ssh_conn_timeout,
            self.options.remote_user,
            self.options.remote_password,
            self.options.remote_config_dir,
            self.options.rest_api_endpoint,
            self.options.use_threads,
            self.options.authentication,
            self.options.username,
            self.options.password,
            self.options.connection_timeout,
            self.options.connection_attempts,
            self.options.verify_ssl_certs,
            self.options.verbose,
            self.options.data_containers,
        )

        # send the signal when done
        self.signal.emit('DONE')

    '''
        Return an instance of the XrayClient
        @return: XrayClient instance
        @return type: instance
    '''

    def getXrayClientInstance(self):
        return self.xrayClient


'''
    The widget gallery which acts as the Main Thread of the Application
'''


class WidgetGallery(QDialog):
    __qssFile = "native.qss"
    __styleSheetFile = None

    def __init__(self, parent=None):
        super(WidgetGallery, self).__init__(parent)

        self.getQssFile()
        self.createTopLeftGroupBox()
        self.createTopRightGroupBox()
        self.createXrayLog()

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.topLeftGroupBox, 1, 0)
        mainLayout.addWidget(self.topRightGroupBox, 1, 1)
        mainLayout.addWidget(self.xrayLogGroupBox, 3, 0, 1, 2)
        # mainLayout.setRowStretch(1, 1)
        mainLayout.setColumnStretch(0, 1)
        mainLayout.setColumnStretch(1, 1)
        self.setLayout(mainLayout)

        self.setWindowTitle("XrayClient")
        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet(self.__styleSheetFile)

        # Public Members
        self.textEditContentBackup = ""
        self.errorCounter = 0
        self.warningCounter = 0
        self.logFileHandle = None

    # -- PRIVATE --

    '''
        Read the contents of the stylesheet related file
        @return: None
    '''

    def __setSchema(self):
        file = QFile(":/" + self.__qssFile)
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        self.__styleSheetFile = stream.readAll()

    # -- PUBLIC --

    '''
        Write configuration settings to file
        @return: None
    '''

    def writeSettings(self):
        self.settings = QSettings(os.path.join(os.getcwd(), "XrayClient.ini"), QSettings.IniFormat)
        self.settings.beginGroup("Settings")
        self.settings.setValue("size", self.size())
        self.settings.setValue("position", self.pos())
        self.settings.setValue("mode", str(self.operationModeComboBox.currentText()))
        self.settings.setValue("importMode", str(self.importModeComboBox.currentText()))
        if self.issueTypeEdit.text():
            self.settings.setValue("issueTypeKey", str(self.issueTypeEdit.text()))
        else:
            self.settings.setValue("issueTypeKey", "None")
        self.settings.setValue("framework", str(self.frameworkComboBox.currentText()))
        self.settings.setValue("configurationLocation", str(self.configurationModeComboBox.currentText()))
        #                   -- Special Option --
        self.settings.setValue("frameworkConfigFolder", str(ConfigDict['framework_config_folder']))
        # -----------------------------------------------------------------------------------------
        self.settings.setValue("remoteHost", str(self.remoteHostEdit.text()))
        self.settings.setValue("sshConnTimeout", str(self.sshConnectionTimeoutEdit.text()))
        self.settings.setValue("remoteUser", str(self.remoteUserEdit.text()))
        self.settings.setValue("remotePassword", str(self.remotePasswordEdit.text()))
        self.settings.setValue("remoteConfigDir", str(self.remoteConfigDirEdit.text()))
        self.settings.setValue("restApiEndpoint", str(self.restApiEndpointEdit.text()))
        self.settings.setValue("connectionTimeout", str(self.connectionTimeoutEdit.text()))
        self.settings.setValue("connectionAttempts", str(self.connectionAttemptsEdit.text()))
        self.settings.setValue("useThreads", str(self.threadTuningCheckBox.isChecked()))
        self.settings.setValue("authentication", str(self.authenticationMethodComboBox.currentText()))
        self.settings.setValue("username", str(self.usernameEdit.text()))
        self.settings.setValue("password", str(self.passwordEdit.text()))
        self.settings.setValue("verifySslCerts", str(self.verifySslServerCertificatesCheckBox.isChecked()))
        self.settings.setValue("verbose", str(self.debugLogsCheckBox.isChecked()))
        self.settings.setValue("dataContainers", str(self.debugDataStructCheckBox.isChecked()))
        self.settings.setValue("logFormat", str(self.logFormatComboBox.currentText()))
        self.settings.endGroup()

    '''
        Read configuration settings from file
        @return: None
    '''

    def readSettings(self):
        self.settings.beginGroup("Settings")
        #                               -- Special options --
        ConfigDict['framework_config_folder'] = str(self.settings.value("frameworkConfigFolder"))
        if ConfigDict['framework_config_folder'] is None or ConfigDict['framework_config_folder'] == "None":
            ConfigDict['framework_config_folder'] = "/"
        # --------------------------------------------------------------------------------------------------
        self.resize(self.settings.value("size", QSize(400, 400)))
        self.move(self.settings.value("pos", QPoint(200, 200)))
        self.operationModeComboBox.setCurrentText(self.settings.value("mode"))
        self.importModeComboBox.setCurrentText(self.settings.value("importMode"))
        if str(self.settings.value("issueTypeKey")) == "None":
            self.issueTypeEdit.setText("")
        else:
            self.issueTypeEdit.setText(str(self.settings.value("issueTypeKey")))
        self.frameworkComboBox.setCurrentText(self.settings.value("framework"))
        self.configurationModeComboBox.setCurrentText(self.settings.value("configurationLocation"))
        self.remoteHostEdit.setText(self.settings.value("remoteHost"))
        self.sshConnectionTimeoutEdit.setText(str(self.settings.value("sshConnTimeout")))
        self.remoteUserEdit.setText(self.settings.value("remoteUser"))
        self.remotePasswordEdit.setText(self.settings.value("remotePassword"))
        self.remoteConfigDirEdit.setText(self.settings.value("remoteConfigDir"))
        self.restApiEndpointEdit.setText(self.settings.value("restApiEndpoint"))
        self.connectionTimeoutEdit.setText(str(self.settings.value("connectionTimeout")))
        self.connectionAttemptsEdit.setText(str(self.settings.value("connectionAttempts")))
        self.threadTuningCheckBox.setChecked(self.settings.value("useThreads", type=bool))
        self.authenticationMethodComboBox.setCurrentText(self.settings.value("authentication"))
        self.usernameEdit.setText(str(self.settings.value("username")))
        self.passwordEdit.setText(str(self.settings.value("password")))
        self.verifySslServerCertificatesCheckBox.setChecked(self.settings.value("verifySslCerts", type=bool))
        self.debugLogsCheckBox.setChecked(self.settings.value("verbose", type=bool))
        self.debugDataStructCheckBox.setChecked(self.settings.value("dataContainers", type=bool))
        self.logFormatComboBox.setCurrentText(str(self.settings.value("logFormat")))
        self.settings.endGroup()

    '''
        Increase the error counter
        @return: None
    '''

    def increaseErrorCounter(self):
        self.errorCounter += 1

    '''
        Increase the warnings counter
        @return: None
    '''

    def increaseWarningsCounter(self):
        self.warningCounter += 1

    '''
        Get the error counter
        @return: error counter (int)
    '''

    def getErrorCounter(self):
        return self.errorCounter

    '''
        Get the warning counter
        @return: warning counter (int)
    '''

    def getWarningsCounter(self):
        return self.getWarningsCounter

    '''
        Rest all counters
        @return: None
    '''

    def resetCounters(self):
        self.errorCounter = 0
        self.warningCounter = 0

    '''
        Retrieve a style sheet related file from a predefined configuration file
            and read the contents of the file IF no exception occured
        @return: None or GeneralError Exception in case something went wrong
    '''

    @pyqtSlot()
    def getQssFile(self):
        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application = os.path.basename(sys.executable)
        else:
            application = __file__
        path_to_config = os.path.join(os.path.dirname(os.path.abspath(application)), "qss/qss_file.txt")

        if getattr(sys, 'frozen', False):
            path_to_config = path_to_config.replace("/", "\\")

        try:
            with open(path_to_config) as f:
                self.__qssFile = f.readline().split("=")[1]
        except (FileNotFoundError, IndexError) as e:
            print("Could not retrieve style sheet file from %s -> (%s)" % (path_to_config, e))
            raise GeneralError("Could not retrieve style sheet file from %s -> (%s)" % (path_to_config, e))

        self.__setSchema()

    '''
        Calculate the current index of a combo box based on a given text string
        @param combo_box: the combo box instance
        @param type combo_box: QComboBox instance
        @param text: the text which is searched in the combo box list items.
                        If the text is found, the text position is used to set the current index
        @return: None
    '''

    @accepts(QComboBox, str)
    def setComboBoxActiveItem(self, combo_box, text):
        index = combo_box.findText(text, Qt.MatchFixedString)
        if index >= 0:
            combo_box.setCurrentIndex(index)

    '''
        Create the top left group of the widget gallery
        @return: None
    '''

    def createTopLeftGroupBox(self):
        self.topLeftGroupBox = QGroupBox("")

        # Initialize tab screen
        tabs = QTabWidget()
        tabs.setStyleSheet(self.__styleSheetFile)
        tab1 = QWidget()
        tab2 = QWidget()
        tab3 = QWidget()
        tab4 = QWidget()
        tab5 = QWidget()

        # Add tabs
        tabs.addTab(tab1, "Operation | ")
        tabs.addTab(tab2, "Framework | ")
        tabs.addTab(tab3, "Xray REST API | ")
        tabs.addTab(tab4, "Jira Authentication | ")
        tabs.addTab(tab5, "Performance && Analysis")
        tab1.adjustSize()
        tab2.adjustSize()
        tab3.adjustSize()
        tab4.adjustSize()
        tab5.adjustSize()
        # override font size of global style sheet
        tabs.setStyleSheet("font: 14pt")
        self.onlyInt = QIntValidator()

        # Create first tab
        tab1.layout = QVBoxLayout()
        tab1.gridLayout = QGridLayout()
        tab1.layout.addLayout(tab1.gridLayout)
        tab1.layout.addStretch()
        operationModeLabel = QLabel("Global Operation Mode:")
        operationModeLabel.setToolTip("Run the Xray Client either in 'Import Mode (import tests from Xray Server)' "
                                      "OR 'Export Mode (export test results to Xray Server)'")
        self.operationModeComboBox = QComboBox()
        self.operationModeComboBox.addItem("Import")
        self.operationModeComboBox.addItem("Export")
        operationModeLabel.setBuddy(self.operationModeComboBox)
        importModeLabel = QLabel("Import Xray Issue Type:")
        importModeLabel.setToolTip("Import tests either by issue type 'TestExecution' or 'TestPlan'")
        self.importModeComboBox = QComboBox()
        self.importModeComboBox.addItem("TestExecution")
        self.importModeComboBox.addItem("TestPlan")
        importModeLabel.setBuddy(self.importModeComboBox)
        issueTypeLabel = QLabel("Xray Issue Type Key:")
        issueTypeLabel.setToolTip("Depending on the import mode, specify the issue type key. "
                                  "If no key is provided all test executions OR test plans are imported")
        self.issueTypeEdit = QLineEdit()
        self.issueTypeEdit.insert("")
        issueTypeLabel.setBuddy(self.issueTypeEdit)
        frameworkLabel = QLabel("Generate Output For Framework:")
        frameworkLabel.setToolTip("Run the XrayClient for one of two supported frameworks")
        frameworkLabel.setToolTip("")
        self.frameworkComboBox = QComboBox()
        self.frameworkComboBox.addItem("Pytefw")
        self.frameworkComboBox.addItem("Ita")
        frameworkLabel.setBuddy(self.frameworkComboBox)
        tab1.gridLayout.addWidget(operationModeLabel)
        tab1.gridLayout.addWidget(self.operationModeComboBox)
        tab1.gridLayout.addWidget(importModeLabel)
        tab1.gridLayout.addWidget(self.importModeComboBox)
        tab1.gridLayout.addWidget(issueTypeLabel)
        tab1.gridLayout.addWidget(self.issueTypeEdit)
        tab1.gridLayout.addWidget(frameworkLabel)
        tab1.gridLayout.addWidget(self.frameworkComboBox)
        tab1.setLayout(tab1.layout)

        # create second tab
        tab2.layout = QVBoxLayout()
        tab2.gridLayout = QGridLayout()
        tab2.layout.addLayout(tab2.gridLayout)
        tab2.layout.addStretch()
        configurationLocationLabel = QLabel("Configuration Location:")
        self.configurationModeComboBox = QComboBox()
        self.configurationModeComboBox.addItem("Local")
        self.configurationModeComboBox.addItem("Remote")
        configurationLocationLabel.setBuddy(self.configurationModeComboBox)
        self.frameworkConfigButton = QPushButton("Select")
        remoteSettingsLabel = QLabel("Remote Host")
        remoteSettingsLabel.setToolTip("Connect to the remote host via SSH")
        self.remoteHostEdit = QLineEdit()
        self.remoteHostEdit.insert("MyRemoteServer")
        sshConnectionTimeoutLabel = QLabel("SSH Connection Timeout")
        sshConnectionTimeoutLabel.setToolTip("Terminate the ssh connection after this timeout in seconds has passed")
        self.sshConnectionTimeoutEdit = QLineEdit()
        self.sshConnectionTimeoutEdit.setValidator(self.onlyInt)
        self.sshConnectionTimeoutEdit.insert("1")
        sshConnectionTimeoutLabel.setBuddy(self.sshConnectionTimeoutEdit)
        remoteUserLabel = QLabel("Remote User")
        self.remoteUserEdit = QLineEdit()
        self.remoteUserEdit.insert("root")
        remotePasswordLabel = QLabel("Remote Password")
        self.remotePasswordEdit = QLineEdit()
        self.remotePasswordEdit.insert("root")
        remoteConfigDirLabel = QLabel("Remote Configuration Folder")
        self.remoteConfigDirEdit = QLineEdit()
        self.remoteConfigDirEdit.insert("/path/to/config")
        #  - Defaults -
        self.frameworkConfigButton.setDisabled(False)
        self.remoteHostEdit.setDisabled(True)
        self.sshConnectionTimeoutEdit.setDisabled(True)
        self.remoteUserEdit.setDisabled(True)
        self.remotePasswordEdit.setDisabled(True)
        self.remoteConfigDirEdit.setDisabled(True)
        # ---------------------------------------------
        remoteSettingsLabel.setBuddy(self.remoteHostEdit)
        remoteUserLabel.setBuddy(self.remoteUserEdit)
        remotePasswordLabel.setBuddy(self.remotePasswordEdit)
        remoteConfigDirLabel.setBuddy(self.remoteConfigDirEdit)
        tab2.layout.addWidget(configurationLocationLabel)
        tab2.layout.addWidget(self.configurationModeComboBox)
        tab2.layout.addWidget(self.frameworkConfigButton)
        tab2.layout.addWidget(remoteSettingsLabel)
        tab2.layout.addWidget(self.remoteHostEdit)
        tab2.layout.addWidget(sshConnectionTimeoutLabel)
        tab2.layout.addWidget(self.sshConnectionTimeoutEdit)
        tab2.layout.addWidget(remoteUserLabel)
        tab2.layout.addWidget(self.remoteUserEdit)
        tab2.layout.addWidget(remotePasswordLabel)
        tab2.layout.addWidget(self.remotePasswordEdit)
        tab2.layout.addWidget(remoteConfigDirLabel)
        tab2.layout.addWidget(self.remoteConfigDirEdit)
        tab2.setLayout(tab2.layout)

        # create third tab
        tab3.layout = QVBoxLayout()
        tab3.gridLayout = QGridLayout()
        tab3.layout.addLayout(tab3.gridLayout)
        tab3.layout.addStretch()
        restApiEndpointLabel = QLabel("Xray REST API Endpoint Base URL:")
        restApiEndpointLabel.setToolTip("Base URL of Xray REST API, URL ending similar to '/rest/raven/1.0/api")
        self.restApiEndpointEdit = QLineEdit()
        self.restApiEndpointEdit.insert("https://mbition.atlassian.net/rest/raven/1.0/api")
        restApiEndpointLabel.setBuddy(self.restApiEndpointEdit)
        connectionTimeoutLabel = QLabel("Connection Timeout:")
        connectionTimeoutLabel.setToolTip("Abort JIRA connection attempt if this timeout has exceeded")
        self.connectionTimeoutEdit = QLineEdit()
        self.connectionTimeoutEdit.setValidator(self.onlyInt)
        self.connectionTimeoutEdit.insert("5")
        connectionTimeoutLabel.setBuddy(self.connectionTimeoutEdit)
        connectionAttemptsLabel = QLabel("Connection Attempts:")
        connectionAttemptsLabel.setToolTip("Try to reconnect to the JIRA endpoint this amount of "
                                           "times in case the first connection attempt failed")
        self.connectionAttemptsEdit = QLineEdit()
        self.connectionAttemptsEdit.setValidator(self.onlyInt)
        self.connectionAttemptsEdit.insert("5")
        connectionAttemptsLabel.setBuddy(self.connectionAttemptsEdit)
        tab3.gridLayout.addWidget(restApiEndpointLabel)
        tab3.gridLayout.addWidget(self.restApiEndpointEdit)
        tab3.gridLayout.addWidget(connectionTimeoutLabel)
        tab3.gridLayout.addWidget(self.connectionTimeoutEdit)
        tab3.gridLayout.addWidget(connectionAttemptsLabel)
        tab3.gridLayout.addWidget(self.connectionAttemptsEdit)
        tab3.setLayout(tab3.layout)

        # create fourth tab
        tab4.layout = QVBoxLayout()
        tab4.gridLayout = QGridLayout()
        tab4.layout.addLayout(tab4.gridLayout)
        tab4.layout.addStretch()
        authenticationMethodLabel = QLabel("Authentication Method:")
        authenticationMethodLabel.setToolTip("Choose between 'Basic' and 'OAuth1' Jira Authentication")
        self.authenticationMethodComboBox = QComboBox()
        self.authenticationMethodComboBox.addItem("Basic")
        self.authenticationMethodComboBox.addItem("OAuth1")
        authenticationMethodLabel.setBuddy(self.authenticationMethodComboBox)
        usernameLabel = QLabel("Username:")
        usernameLabel.setToolTip("The username for 'Basic' Auth")
        self.usernameEdit = QLineEdit()
        self.usernameEdit.insert("root")
        usernameLabel.setBuddy(self.usernameEdit)
        passwordLabel = QLabel("Password:")
        passwordLabel.setToolTip("The password for 'Basic' Auth")
        self.passwordEdit = QLineEdit()
        self.passwordEdit.insert("root")
        passwordLabel.setBuddy(self.passwordEdit)
        sslCertificateLabel = QLabel("SSL Options:")
        sslCertificateLabel.setToolTip("Enable server certificate verification when using HTTPS")
        self.verifySslServerCertificatesCheckBox = QCheckBox("Verify SSL Server Certificates")
        tab4.gridLayout.addWidget(authenticationMethodLabel)
        tab4.gridLayout.addWidget(self.authenticationMethodComboBox)
        tab4.gridLayout.addWidget(usernameLabel)
        tab4.gridLayout.addWidget(self.usernameEdit)
        tab4.gridLayout.addWidget(passwordLabel)
        tab4.gridLayout.addWidget(self.passwordEdit)
        tab4.gridLayout.addWidget(sslCertificateLabel)
        tab4.gridLayout.addWidget(self.verifySslServerCertificatesCheckBox)
        tab4.setLayout(tab4.layout)

        # create fith tab
        tab5.layout = QVBoxLayout()
        tab5.gridLayout = QGridLayout()
        tab5.layout.addLayout(tab5.gridLayout)
        tab5.layout.addStretch()
        httpResourceLabel = QLabel("Performance Tuning:")
        httpResourceLabel.setToolTip("Use threading for I/O operations (HTTP(S) GET, POST Requests)")
        self.threadTuningCheckBox = QCheckBox("Enable HTTP(S) Threads")
        analysisLabel = QLabel("Tool Analysis:")
        analysisLabel.setToolTip("Run with debug log output and/or "
                                 "print internal data structure containers for further analysis")
        self.debugLogsCheckBox = QCheckBox("Enable Debug Logs")
        self.debugLogsCheckBox.setToolTip("Some errors are only visible in Debug Mode")
        self.debugDataStructCheckBox = QCheckBox("Print Internal Data Containers")
        self.debugDataStructCheckBox.setToolTip("Print the data structure of XmlHandler and XrayClient")
        logFormatLabel = QLabel("Select Log Format:")
        logFormatLabel.setToolTip("Choose between 'UI' and 'XrayClientLog.txt'")
        self.logFormatComboBox = QComboBox()
        self.logFormatComboBox.addItem("UI")
        self.logFormatComboBox.addItem("XrayClientLog.txt")
        logFormatLabel.setBuddy(self.logFormatComboBox)
        tab5.gridLayout.addWidget(httpResourceLabel)
        tab5.gridLayout.addWidget(self.threadTuningCheckBox)
        tab5.gridLayout.addWidget(analysisLabel)
        tab5.gridLayout.addWidget(self.debugLogsCheckBox)
        tab5.gridLayout.addWidget(self.debugDataStructCheckBox)
        tab5.gridLayout.addWidget(logFormatLabel)
        tab5.gridLayout.addWidget(self.logFormatComboBox)
        tab5.setLayout(tab5.layout)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addStretch(1)
        self.topLeftGroupBox.setLayout(layout)

        self.operationModeComboBox.currentIndexChanged.connect(self.importModeComboBox.setDisabled)
        self.operationModeComboBox.currentIndexChanged.connect(self.issueTypeEdit.setDisabled)
        self.authenticationMethodComboBox.currentIndexChanged.connect(self.usernameEdit.setDisabled)
        self.authenticationMethodComboBox.currentIndexChanged.connect(self.passwordEdit.setDisabled)
        self.configurationModeComboBox.activated.connect(self.handleFrameworkConfigurationModeSettings)

        configFile = os.path.join(os.getcwd(), "XrayClient.ini")
        if os.path.isfile(configFile):
            self.settings = QSettings(os.path.join(os.getcwd(), "XrayClient.ini"), QSettings.IniFormat)
            self.readSettings()
        else:
            # Default folder
            ConfigDict['framework_config_folder'] = "/"

        self.frameworkConfigButton.clicked.connect(self.selectConfigurationFolder)

    '''
        Enable/Disable framework specific widgets based on the Index
        @return: None
    '''

    def handleFrameworkConfigurationModeSettings(self):
        if self.configurationModeComboBox.currentIndex() == 0:
            self.frameworkConfigButton.setDisabled(False)
            self.remoteHostEdit.setDisabled(True)
            self.sshConnectionTimeoutEdit.setDisabled(True)
            self.remoteUserEdit.setDisabled(True)
            self.remotePasswordEdit.setDisabled(True)
            self.remoteConfigDirEdit.setDisabled(True)
        if self.configurationModeComboBox.currentIndex() == 1:
            self.frameworkConfigButton.setDisabled(True)
            self.remoteHostEdit.setDisabled(False)
            self.sshConnectionTimeoutEdit.setDisabled(False)
            self.remoteUserEdit.setDisabled(False)
            self.remotePasswordEdit.setDisabled(False)
            self.remoteConfigDirEdit.setDisabled(False)

    '''
        Create the layout for the Xray Client log
        @return: None
    '''

    def createXrayLog(self):
        self.xrayLogGroupBox = QGroupBox("")

        filterTextLabel = QLabel("Text Filter:")
        # override font size of global style sheet
        filterTextLabel.setStyleSheet("font: 14pt")
        self.filterTextEdit = QLineEdit()
        self.filterTextEdit.setStyleSheet("font: 14pt")
        self.filterTextEdit.insert("")
        filterLogLabel = QLabel("Generic Filter:")
        # override font size of global style sheet
        filterLogLabel.setStyleSheet("font: 14pt")
        self.filterLogComboBox = QComboBox()
        # override font size of global style sheet
        self.filterLogComboBox.setStyleSheet("font: 14pt")
        self.filterLogComboBox.addItem("ALL")
        self.filterLogComboBox.addItem("ERROR")
        self.filterLogComboBox.addItem("WARNING")
        self.filterLogComboBox.addItem("INFO")
        self.filterLogComboBox.addItem("DEBUG")
        self.filterLogComboBox.addItem("XmlHandler")
        self.filterLogComboBox.addItem("XrayClient")
        self.filterLogComboBox.addItem("JiraConnector")
        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        # self.textEdit.setFixedHeight(400)
        self.textEdit.setStyleSheet(self.__styleSheetFile)
        # override font size of global style sheet
        self.textEdit.setStyleSheet("font: 14pt")

        layout = QVBoxLayout()
        gridLayout = QGridLayout()
        layout.addLayout(gridLayout)
        gridLayout.addWidget(filterTextLabel)
        gridLayout.addWidget(self.filterTextEdit)
        gridLayout.addWidget(filterLogLabel)
        gridLayout.addWidget(self.filterLogComboBox)
        gridLayout.addWidget(self.textEdit)
        self.xrayLogGroupBox.setLayout(layout)

        self.filterTextEdit.textChanged.connect(self.filterLog)
        self.filterLogComboBox.currentTextChanged.connect(self.filterLog)

    '''
        Create the top right group of the widget gallery
        @return: None
    '''

    def createTopRightGroupBox(self):
        self.topRightGroupBox = QGroupBox("")
        self.topRightGroupBox.setStyleSheet(self.__styleSheetFile)

        failCountLabel = QLabel("Total Errors")
        failCountLabel.setAlignment(Qt.AlignCenter)
        failCountLabel.setFrameShape(QFrame.Panel)
        failCountLabel.setFrameShadow(QFrame.Sunken)
        failCountLabel.setStyleSheet("font-size: 36px;")
        self.failCountButton = QPushButton("0")
        self.failCountButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px;")
        failCountLabel.setBuddy(self.failCountButton)
        testCaseLabel = QLabel("Total TestCases")
        testCaseLabel.setAlignment(Qt.AlignCenter)
        testCaseLabel.setFrameShape(QFrame.Panel)
        testCaseLabel.setFrameShadow(QFrame.Sunken)
        testCaseLabel.setStyleSheet("font-size: 36px;")
        self.testCaseButton = QPushButton("0")
        self.testCaseButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px;")
        testCaseLabel.setBuddy(self.testCaseButton)
        warningCountLabel = QLabel("Total Warnings")
        warningCountLabel.setAlignment(Qt.AlignCenter)
        warningCountLabel.setFrameShape(QFrame.Panel)
        warningCountLabel.setFrameShadow(QFrame.Sunken)
        warningCountLabel.setStyleSheet("font-size: 36px;")
        self.warningCountButton = QPushButton("0")
        self.warningCountButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px;")
        warningCountLabel.setBuddy(self.warningCountButton)
        runTimeLabel = QLabel("Total RunTime")
        runTimeLabel.setAlignment(Qt.AlignCenter)
        runTimeLabel.setFrameShape(QFrame.Panel)
        runTimeLabel.setFrameShadow(QFrame.Sunken)
        runTimeLabel.setStyleSheet("font-size: 36px;")
        self.runTimeButton = QPushButton("00:00:00")
        self.runTimeButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px;")
        runTimeLabel.setBuddy(self.runTimeButton)
        self.runButton = QPushButton("RUN")
        self.runButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px;")
        clearLogButton = QPushButton("Clear Log")
        clearLogButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px;")

        layout = QVBoxLayout()
        gridLayout = QGridLayout()
        layout.addLayout(gridLayout)
        gridLayout.addWidget(failCountLabel)
        gridLayout.addWidget(self.failCountButton, 1, 0)
        gridLayout.addWidget(testCaseLabel, 0, 1)
        gridLayout.addWidget(self.testCaseButton, 1, 1)
        gridLayout.addWidget(warningCountLabel, 2, 0)
        gridLayout.addWidget(self.warningCountButton, 3, 0)
        gridLayout.addWidget(runTimeLabel, 2, 1)
        gridLayout.addWidget(self.runTimeButton, 3, 1)
        gridLayout.addWidget(self.runButton, 4, 0)
        gridLayout.addWidget(clearLogButton, 4, 1)

        self.topRightGroupBox.setLayout(layout)

        self.runButton.clicked.connect(self.startXrayClient)
        clearLogButton.clicked.connect(self.clearLog)

    '''
        Read the current user configuration and fill the global configuration dictionary with its values
        @return: None
    '''

    def getConfig(self):
        ConfigDict['mode'] = str(self.operationModeComboBox.currentText())

        import_mode = str(self.importModeComboBox.currentText())
        ConfigDict['import_mode_test_execution'] = False
        ConfigDict['import_mode_test_plan'] = False

        if import_mode == "TestExecution":
            ConfigDict['import_mode_test_execution'] = True
        else:
            ConfigDict['import_mode_test_plan'] = True

        ConfigDict['issue_type_key'] = str(self.issueTypeEdit.text())
        ConfigDict['framework'] = str(self.frameworkComboBox.currentText())
        ConfigDict['configuration_location'] = str(self.configurationModeComboBox.currentText())
        ConfigDict['remote_host'] = str(self.remoteHostEdit.text())
        ConfigDict['ssh_conn_timeout'] = int(self.sshConnectionTimeoutEdit.text())
        ConfigDict['remote_user'] = str(self.remoteUserEdit.text())
        ConfigDict['remote_password'] = str(self.remotePasswordEdit.text())
        ConfigDict['remote_config_dir'] = str(self.remoteConfigDirEdit.text())
        ConfigDict['rest_api_endpoint'] = str(self.restApiEndpointEdit.text())
        ConfigDict['connection_timeout'] = int(self.connectionTimeoutEdit.text())
        ConfigDict['connection_attempts'] = int(self.connectionAttemptsEdit.text())
        ConfigDict['use_threads'] = self.threadTuningCheckBox.isChecked()
        ConfigDict['authentication'] = str(self.authenticationMethodComboBox.currentText())
        ConfigDict['username'] = str(self.usernameEdit.text())
        ConfigDict['password'] = str(self.passwordEdit.text())
        ConfigDict['verify_ssl_certs'] = self.verifySslServerCertificatesCheckBox.isChecked()
        ConfigDict['verbose'] = self.debugLogsCheckBox.isChecked()
        ConfigDict['data_containers'] = self.debugDataStructCheckBox.isChecked()

    '''
        Open a log file handle for writing
        @return: None
    '''

    def openLogFile(self):
        self.logFileHandle = open("XrayClientLog.txt", "a")

    '''
        Close the log file handle
        @return: None
    '''

    def closeLogFile(self):
        self.logFileHandle.close()

    '''
        Append text to a text file
        @param text: text line to append (str)
        @return: None    
    '''

    @pyqtSlot(str)
    @accepts(str)
    def appendTextToFile(self, text):
        if "ERROR" in text:
            self.increaseErrorCounter()
            # update the error widget
            self.updateErrorCounter()
        elif "WARNING" in text:
            self.increaseWarningsCounter()
            # update the warnings widget
            self.updateWarningsCounter()

        try:
            self.logFileHandle.write(text)
        except ValueError as msg:
            if "I/O operation on closed file" in str(msg):
                # reopen file and try to write again
                self.openLogFile()
                self.logFileHandle.write(text)

        if "Finished: start_export" in text or \
                "Finished: start_import" in text:
            self.logFileHandle.close()
            msg = QMessageBox()
            msg.setStyleSheet("font: 14px")
            msg.setStyleSheet(self.__styleSheetFile)
            msg.setText("Finished")
            msg.setInformativeText("Logs written successfully")
            msg.exec()

    '''
        Append line by line to the TextEdit widget and store all received lines in a backup structure
        @param text: text line to append (str)
        @param store_backup: IF True , store all received lines in a backup structure
        @param type store_backup: Boolean
        @return: None    
    '''

    @pyqtSlot(str)
    @accepts(str, bool)
    def appendText(self, text, store_backup=True):
        self.textEdit.moveCursor(QTextCursor.End)
        if "ERROR" in text:
            self.textEdit.setTextColor(Qt.red)
            if store_backup:
                self.increaseErrorCounter()
            # update the error widget
            self.updateErrorCounter()
        elif "WARNING" in text:
            self.textEdit.setTextColor(Qt.yellow)
            if store_backup:
                self.increaseWarningsCounter()
            # update the warnings widget
            self.updateWarningsCounter()
        elif re.findall(r"\[91m", text):
            self.textEdit.setTextColor(Qt.darkGreen)
        elif re.findall(r"\[92m", text):
            self.textEdit.setTextColor(Qt.green)
        elif re.findall(r"\[93m", text):
            self.textEdit.setTextColor(Qt.darkYellow)
        elif re.findall(r"\[94m", text):
            self.textEdit.setTextColor(Qt.blue)
        elif re.findall(r"\[95m", text):
            self.textEdit.setTextColor(Qt.magenta)
        elif re.findall(r"\[96m", text):
            self.textEdit.setTextColor(Qt.cyan)
        elif re.findall(r"\[1m", text):
            self.textEdit.setTextColor(Qt.darkCyan)
        else:
            self.textEdit.setTextColor(Qt.white)
        self.textEdit.insertPlainText(text)

        if store_backup:
            self.textEditContentBackup = self.textEdit.toPlainText()

    '''
        Clear the Live Log
        @return: None
    '''

    def clearLog(self):
        self.textEdit.clear()
        # delete the backup content
        self.textEditContentBackup = ""
        # remove also the log file
        if os.path.isfile("XrayClientLog.txt"):
            if self.logFileHandle:
                self.logFileHandle.close()
            os.remove("XrayClientLog.txt")

    '''
        Filter Live Log based on a pattern
        @param m_filter: The filter pattern to be applied
        @param type m_filter: string
        @return: None
    '''

    @accepts(str)
    def filterLog(self, m_filter):
        if self.logFileHandle:
            try:
                self.logFileHandle = open("XrayClientLog.txt", "r")
            except FileNotFoundError:
                return
            filteredResults = list(filter(lambda x: m_filter in x or m_filter == "ALL",
                                          self.logFileHandle.readlines()))
            self.logFileHandle.close()
        else:
            filteredResults = list(filter(lambda x: m_filter in x or m_filter == "ALL",
                                          self.textEditContentBackup.splitlines(True)))
        self.textEdit.clear()
        for result in filteredResults:
            self.appendText(result, store_backup=False)

    '''
        Store the selected framework configuration directory in the ConfigDict
        @return: None
    '''

    def selectConfigurationFolder(self):
        ConfigDict['framework_config_folder'] \
            = str(QFileDialog.getExistingDirectory(None, '', ConfigDict['framework_config_folder']))

    '''
        Update the clock widget
        @return: None
    '''

    def updateClock(self):
        self.runTimeButton.setText(str(datetime.datetime.now() - self.startTime))

    '''
        Update the error counter widget
        @return: None
    '''

    def updateErrorCounter(self):
        if self.errorCounter > 0:
            self.failCountButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:red")
        else:
            self.failCountButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:white")
        self.failCountButton.setText(str(self.errorCounter))

    '''
        Update the warning counter widget
        @return: None
    '''

    def updateWarningsCounter(self):
        if self.warningCounter > 0:
            self.warningCountButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:yellow")
        else:
            self.warningCountButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:white")
        self.warningCountButton.setText(str(self.warningCounter))

    '''
        Update the test case counter widget
        @param xray_client: The xray client instance which calculates the number of test cases
        @parm type xray_client: XrayClient instance
        @return: None
    '''

    @accepts(XrayClient)
    def updateTestCaseCounter(self, xray_client):
        numTestCases = xray_client.total_number_of_tests()
        if numTestCases > 0:
            self.testCaseButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:green")
        else:
            self.testCaseButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:white")
        self.testCaseButton.setText(str(numTestCases))

    '''
        Reset all counters to default values
        @return: None
    '''

    def resetToDefaults(self):
        self.resetCounters()

        self.failCountButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:white")
        self.failCountButton.setText(str(self.errorCounter))
        self.warningCountButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:white")
        self.warningCountButton.setText(str(self.warningCounter))
        self.testCaseButton.setStyleSheet("font-size: 36px; height: 100px;width: 100px; color:white")
        self.testCaseButton.setText("0")
        self.runTimeButton.setStyleSheet("font-size: 36px;height: 100px;width: 100px; color:white")
        self.runTimeButton.setText("00:00:00")

    '''
        Create the options from the user configuration and start an instance of the xray client
    '''

    def startXrayClient(self):
        self.runButton.setDisabled(True)
        self.filterTextEdit.setDisabled(True)
        self.filterLogComboBox.setDisabled(True)
        self.resetToDefaults()
        self.startTime = datetime.datetime.now()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateClock)
        self.timer.start()

        self.getConfig()
        options = Options()

        self.xrayThread = XrayClientThread(options)
        self.xrayThread.signal.connect(self.finished)
        self.xrayThread.start()

    '''
        When a thread operation is finished, this method is executed in the Main Thread
        Additionally the test case counter widget is updated
        @param text: optional text string sent when the signal is emitted (str)
        @return: None 
    '''

    def finished(self, text):
        self.timer.stop()
        xrayClient = self.xrayThread.getXrayClientInstance()
        self.updateTestCaseCounter(xrayClient)
        self.runButton.setDisabled(False)
        self.filterTextEdit.setDisabled(False)
        self.filterLogComboBox.setDisabled(False)

    # -- Method Overrides --

    '''
        Resize the Main Layout when all widgets have been loaded
        @param QShowEvent: QShowEvent instance
        @return: None
    '''

    @accepts(QShowEvent)
    def showEvent(self, event):
        self.resize(1570, self.height())

    def closeEvent(self, event):
        self.writeSettings()
        event.accept()


if __name__ == '__main__':
    queue = Queue()
    sys.stdout = WriteStream(queue)
    sys.sterr = WriteStream(queue)

    appctxt = ApplicationContext()
    gallery = WidgetGallery()
    gallery.show()

    # Create thread that will listen on the other end of the queue, and send the text to the textedit in our application
    thread = QThread()
    queue_receiver = Receiver(queue)
    if gallery.logFormatComboBox.currentText() == "UI":
        queue_receiver.signal.connect(gallery.appendText)
    else:
        # Delete the old log file first
        if os.path.isfile("XrayClientLog.txt"):
            os.remove("XrayClientLog.txt")
        gallery.openLogFile()
        queue_receiver.signal.connect(gallery.appendTextToFile)
    queue_receiver.moveToThread(thread)
    thread.started.connect(queue_receiver.run)
    thread.start()

    try:
        sys.exit(appctxt.app.exec_())
    except Exception as e:
        print(e)
