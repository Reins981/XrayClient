#!/usr/bin/python
# -*- coding: utf-8 -*

import os

script_path = os.path.dirname(__file__)

os.system("pyreverse3 -f 'ALL' -o png -p TestEnvironment " + os.path.abspath(os.path.join(script_path, '..')))
os.system("mv " + os.getcwd() + "/*.png" + " ../docs")
