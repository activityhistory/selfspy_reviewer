"""
Selfspy Reviewer
Adam Rule
8.15.2014

Program to guide participants through using full-screen and snippet screenshots
to recall past episodes tracked with Selfspy
"""


from Foundation import NSObject
from Foundation import NSLog

import reviewer


class ApplicationDelegate(NSObject):

    def init(self):
        self = super(ApplicationDelegate, self).init()
        return self


    def applicationDidFinishLaunching_(self, _):
        NSLog("Selfspy Reviewer finished launching")
        reviewer.ReviewController.show()


    def applicationWillTerminate_(self, sender):
        pass
