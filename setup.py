"""
Selfspy Reviewer
Adam Rule
8.15.2014

Program to guide participants through using full-screen and snippet screenshots
to recall past episodes tracked with Selfspy
"""


from setuptools import setup
from setuptools import find_packages
import glob


PROJECT = "Selfspy Reviewer"
ICON = "eye.icns"

plist = {
    "CFBundleIconFile" : ICON,
    "CFBundleIdentifier" : "com.acrule.%s" % PROJECT,
    }


setup(
    name = "Selfspy Reviewer",
    version = "0.1",
    packages = find_packages(),
    author = "Adam Rule",
    description = "Tool for revieweing Selfspy Data",
    app=["Application.py"],
    data_files=["English.lproj"] +glob.glob("Resources/*.*"),
    options=dict(py2app=dict(
        plist=plist,
    )),
)
