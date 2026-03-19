from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QFile, QTextStream

import sys

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = QMainWindow()
    file = QFile(":/dark.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    schema = stream.readAll()
    self.setStyleSheet(schema)
    window.resize(250, 150)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)