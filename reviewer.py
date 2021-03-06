"""
Selfspy Reviewer
Adam Rule
8.15.2014

Program to guide participants through using full-screen and snippet screenshots
to recall past episodes tracked with Selfspy
"""


import os
import re
import time
import datetime
import math
import random
import string
import mutagen.mp4
import sqlite3
import shutil

import objc
from objc import IBAction
from objc import IBOutlet

from Foundation import *
from AppKit import *
from Cocoa import (NSURL, NSString, NSTimer,NSInvocation, NSNotificationCenter)
import Quartz.CoreGraphics as CG

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy.orm import join
from sqlalchemy.dialects.sqlite.base import dialect

import models
from models import Experience
from models import Debrief
from models import Cue


def showAlert(msg):
    print msg
    alert = NSAlert.alloc().init()
    alert.addButtonWithTitle_("OK")
    alert.setMessageText_(msg)
    alert.setAlertStyle_(NSWarningAlertStyle)
    alert.runModal()


# Experience Sampling window controller
class ReviewController(NSWindowController):

    # main image area
    mainPanel = IBOutlet()

    # right-side panels
    controlView = IBOutlet()
    dataView = IBOutlet()

    # reporting controls
    existAudioText = IBOutlet()
    recordButton = IBOutlet()
    playAudioButton = IBOutlet()
    deleteAudioButton = IBOutlet()
    doingText = IBOutlet()
    features = IBOutlet()
    memoryStrength = IBOutlet()
    imageAptness = IBOutlet()
    activityText = IBOutlet()

    # navigation controls
    progressLabel = IBOutlet()
    progressButton = IBOutlet()

    # images for audio recording button
    recordImage = NSImage.alloc().initByReferencingFile_('../Resources/record.png')
    recordImage.setScalesWhenResized_(True)
    recordImage.setSize_((11, 11))

    stopImage = NSImage.alloc().initByReferencingFile_('../Resources/stop.png')
    stopImage.setScalesWhenResized_(True)
    stopImage.setSize_((11, 11))

    # cue variables
    samples = []
    currentSample = -1

    cueW = 0
    cueH = 0

    project_size = 0
    project_time = 0.0
    activity_size = 0
    activity_time = 0.0

    # audio variables
    recordingAudio = False
    playingAudio = False
    audio_file = ''

    # main panel dimensions set to 75% of screen
    viewW = int(NSScreen.mainScreen().frame().size.width*0.75)
    viewH = int(NSScreen.mainScreen().frame().size.height*0.75)

    datadrive = ''


    @IBAction
    def startImageLoop_(self, sender):
        img = self.samples[self.currentSample]['screenshot'][:]
        path = os.path.join(self.datadrive, "screenshots", img)
        cueImage = NSImage.alloc().initByReferencingFile_(path)
        self.cueRatio = cueImage.size().width / cueImage.size().height
        self.cueH = 20
        self.cueW = self.cueH * self.cueRatio

        targetImage = NSImage.alloc().initWithSize_(NSMakeSize(self.cueW, self.cueH))

        if(self.samples[self.currentSample]['snippet']):
            x = float(path.split("_")[-2])
            y = float(path.split("_")[-1].split('-')[0].split('.')[0])
            fromRect = CG.CGRectMake(x-self.cueW/2, y-self.cueH/2, self.cueW, self.cueH)
            toRect = CG.CGRectMake(0.0, 0.0, self.cueW, self.cueH)
        else:
            fromRect = CG.CGRectMake(0.0, 0.0, cueImage.size().width, cueImage.size().height)
            toRect = CG.CGRectMake(0.0, 0.0, self.cueW, self.cueH)

        targetImage.lockFocus()
        cueImage.drawInRect_fromRect_operation_fraction_( toRect, fromRect, NSCompositeCopy, 1.0 )
        targetImage.unlockFocus()

        self.reviewController.mainPanel.setImage_(targetImage)

        self.growStartTime = time.time()
        self.growImage = True

        s = objc.selector(self.imageGrowLoop,signature='v@:')
        self.imageLoop = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(2, self, s, None, False)

    def imageGrowLoop(self):
        img = self.samples[self.currentSample]['screenshot'][:]
        path = os.path.join(self.datadrive, "screenshots", self.samples[self.currentSample]['screenshot'])
        cueImage = NSImage.alloc().initByReferencingFile_(path)
        max_height = min(cueImage.size().height, self.viewH)

        if(self.cueH <= max_height-20 and self.growImage):
            print 'increasing size'
            self.cueH = self.cueH + 20
            self.cueW = self.cueH * self.cueRatio

            targetImage = NSImage.alloc().initWithSize_(NSMakeSize(self.cueW, self.cueH))

            if(self.samples[self.currentSample]['snippet']):
                x = float(path.split("_")[-2])
                y = float(path.split("_")[-1].split('-')[0].split('.')[0])
                fromRect = CG.CGRectMake(x-self.cueW/2, y-self.cueH/2, self.cueW, self.cueH)
                toRect = CG.CGRectMake(0.0, 0.0, self.cueW, self.cueH)
            else:
                fromRect = CG.CGRectMake(0.0, 0.0, cueImage.size().width, cueImage.size().height)
                toRect = CG.CGRectMake(0.0, 0.0, self.cueW, self.cueH)

            targetImage.lockFocus()
            cueImage.drawInRect_fromRect_operation_fraction_( toRect, fromRect, NSCompositeCopy, 1.0 )
            targetImage.unlockFocus()

            self.reviewController.mainPanel.setImage_(targetImage)

            s = objc.selector(self.imageGrowLoop,signature='v@:')
            self.imageLoop = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(2, self, s, None, False)

    @IBAction
    def recordProjectSize_(self, sender):
        self.project_size = self.cueH
        self.project_time = time.time() - self.growStartTime

    @IBAction
    def stopImageLoop_(self, sender):
        self.growImage = False
        self.activity_time = time.time() - self.growStartTime
        self.activity_size = self.cueH

        self.reviewController.controlView.setHidden_(True)
        self.reviewController.dataView.setHidden_(False)

    @IBAction
    def returnToControls_(self, sender):
        self.reviewController.dataView.setHidden_(True)
        self.reviewController.controlView.setHidden_(False)

    @IBAction
    def toggleAudioRecording_(self, sender):
        controller = self.reviewController

        try:
            if self.recordingAudio:
                print "Stoping Audio recording"
                self.recordingAudio = False
                controller.recordButton.setImage_(self.recordImage)
                controller.recordButton.setEnabled_(False)
                controller.existAudioText.setStringValue_("You've recorded an answer:")
                controller.playAudioButton.setHidden_(False)
                controller.deleteAudioButton.setHidden_(False)

                imageName = self.samples[self.currentSample]['screenshot'][0:-4]
                if not imageName:
                    imageName = datetime.datetime.now().strftime("%y%m%d-%H%M%S%f") + '-audio'
                imageName = os.path.join(self.datadrive, "audio", imageName + '-week.m4a')
                self.audio_file = imageName
                s = NSAppleScript.alloc().initWithSource_("set filePath to \"" + string.replace(imageName[1:], "/", ":") + "\" \n set placetosaveFile to a reference to file filePath \n tell application \"QuickTime Player\" \n set mydocument to document 1 \n tell document 1 \n stop \n end tell \n set newRecordingDoc to first document whose name = \"untitled\" \n export newRecordingDoc in placetosaveFile using settings preset \"Audio Only\" \n close newRecordingDoc without saving \n quit \n end tell")
                s.executeAndReturnError_(None)
            else:
                print "Starting Audio Recording"
                self.recordingAudio = True
                controller.recordButton.setImage_(self.stopImage)

                s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n set new_recording to (new audio recording) \n tell new_recording \n start \n end tell \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n end tell")
                s.executeAndReturnError_(None)
        except:
            showAlert("Problem recording audio. Please try typing your answer instead.")

    @IBAction
    def toggleAudioPlay_(self, sender):
        try:
            if self.playingAudio:
                self.playingAudio = False

                s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
                s.executeAndReturnError_(None)

                self.reviewController.playAudioButton.setTitle_("Play Audio")
            else:
                self.playingAudio = True
                s = NSAppleScript.alloc().initWithSource_("set filePath to POSIX file \"" + self.audio_file + "\" \n tell application \"QuickTime Player\" \n open filePath \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n play the front document \n end tell")
                s.executeAndReturnError_(None)

                audio = mutagen.mp4.MP4(self.audio_file)
                length = audio.info.length
                s = objc.selector(self.stopAudioPlay,signature='v@:')
                self.audioTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(length, self, s, None, False)

                self.reviewController.playAudioButton.setTitle_("Stop Audio")
        except:
            showAlert("Problem playing audio. Please delete audio file and try again.")

    def stopAudioPlay(self):
        self.playingAudio = False
        self.reviewController.playAudioButton.setTitle_("Play Audio")

        s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
        s.executeAndReturnError_(None)

    @IBAction
    def deleteAudio_(self, sender):
        if (self.audio_file != '') & (self.audio_file != None) :
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
        self.audio_file = ''

        controller = self.reviewController
        controller.recordButton.setEnabled_(True)
        controller.existAudioText.setStringValue_("Record your answer:")
        controller.playAudioButton.setHidden_(True)
        controller.deleteAudioButton.setHidden_(True)

    @IBAction
    def advanceExperienceWindow_(self, sender):
        controller = self.reviewController
        l = len(self.samples)

        self.currentSample += 1
        i = self.currentSample

        # check if already to recording answers
        if i > 0:
            if(self.recordingAudio):
                self.toggleAudioRecording_(self)

            memory_selection = controller.memoryStrength.selectedCell()
            aptness_selection = controller.imageAptness.selectedCell()

            # tell user to fill in two ratings
            if(memory_selection == None or aptness_selection == None):
                self.currentSample -= 1
                showAlert("Please answer the first four questions")
                return
            else:
                print "Recording cue"
                self.recordCue()
        if i == l-1:
            controller.progressButton.setTitle_("Finish")

        # prepare window for next sample
        if i < l:
            self.populateReviewWindow()
            controller.progressLabel.setStringValue_( str(i + 1) + '/' + str(l) )
            self.reviewController.dataView.setHidden_(True)
            self.reviewController.controlView.setHidden_(False)

        else:
            self.reviewController.close()

    def loadFirstExperience(self):
        controller = self.reviewController
        l = len(self.samples)

        # Catch when no samples are available to show
        if (not self.samples) or (l == 0):
            controller.errorMessage.setHidden_(False)
            controller.doingText.setEnabled_(False)
            controller.recordButton.setEnabled_(False)
            controller.progressLabel.setStringValue_("0/0")
            controller.progressButton.setTitle_("Finish")
            self.currentSample += 1
            return

        self.currentSample += 1
        i = self.currentSample

        self.populateReviewWindow(self)
        controller.progressLabel.setStringValue_( str(i + 1) + '/' + str(l) )

        if i == l-1:
            controller.progressButton.setTitle_("Finish")

    def populateReviewWindow(self):
        print "Populating Review window"
        controller = self.reviewController
        current_experience = self.samples[self.currentSample]['experience_id']

        self.audio_file = ''
        self.project_size = 0
        self.project_time = 0.0
        self.activity_size = 0
        self.activity_time = 0.0

        controller.mainPanel.setImage_(None)
        controller.doingText.setStringValue_('')
        controller.features.setStringValue_('')
        controller.memoryStrength.deselectAllCells()
        controller.imageAptness.deselectAllCells()
        controller.activityText.setStringValue_('')
        controller.recordButton.setEnabled_(True)
        controller.existAudioText.setStringValue_("Record your answer:")
        controller.playAudioButton.setHidden_(True)
        controller.deleteAudioButton.setHidden_(True)

        prior_activities = self.session.query(Cue).distinct(Cue.activity).group_by(Cue.activity).order_by(Cue.id.desc()).limit(7)
        controller.activityText.removeAllItems()
        for d in prior_activities:
            if (d.activity != ''):
                controller.activityText.addItemWithObjectValue_(d.activity)

        # populate page with responses to last cue of this experience
        if current_experience != 0:
            q = self.session.query(Cue).filter(Cue.experience_id == current_experience).all()
        else:
            q = None

        if q:
            controller.doingText.setStringValue_(q[-1].doing_report)
            controller.features.setStringValue_(q[-1].features)
            controller.audio_file = q[-1].audio_file
            if (q[-1].audio_file):
                controller.recordButton.setEnabled_(False)
                controller.existAudioText.setStringValue_("You've recorded an answer:")
                controller.playAudioButton.setHidden_(False)
                controller.deleteAudioButton.setHidden_(False)
            else:
                controller.recordButton.setEnabled_(True)
                controller.existAudioText.setStringValue_("Record your answer:")
                controller.playAudioButton.setHidden_(True)
                controller.deleteAudioButton.setHidden_(True)
            if q[-1].memory_strength:
                controller.memoryStrength.selectCellWithTag_(q[-1].memory_strength)
            if q[-1].image_aptness:
                controller.imageAptness.selectCellWithTag_(q[-1].image_aptness)
            if q[-1].activity:
                controller.activityText.setStringValue_(q[-1].activity)

    def recordCue(self):
        experience_id = self.samples[self.currentSample-1]['experience_id']
        debrief_id = self.samples[self.currentSample-1]['debrief_id']
        screenshot = self.samples[self.currentSample-1]['screenshot']
        snippet = self.samples[self.currentSample-1]['snippet']
        project_size = self.project_size
        project_time = self.project_time
        activity_size = self.activity_size
        activity_time = self.activity_time
        audio_file = self.reviewController.audio_file
        doing_report = self.reviewController.doingText.stringValue()
        features = self.reviewController.features.stringValue()
        memory_strength = self.reviewController.memoryStrength.selectedCell().tag()
        image_aptness = self.reviewController.imageAptness.selectedCell().tag()
        activity = self.reviewController.activityText.stringValue()

        self.session.add(Cue(experience_id, debrief_id, screenshot, snippet, project_size, project_time, activity_size, activity_time, audio_file, doing_report, features, memory_strength, image_aptness, activity))
        self.trycommit()

    def trycommit(self):
        for _ in xrange(1000):
            try:
                self.session.commit()
                break
            except sqlalchemy.exc.OperationalError:
                self.session.rollback()
                showAlert("Database error. Your storage device may be full.")
                break
            except:
                print "Rollback"
                self.session.rollback()

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)
        self.reviewController.window().contentView().layout()

    def windowWillClose_(self, notification):
        if(self.recordingAudio):
            print "Stopping Audio Recording"
            self.toggleAudioRecording_(self)

    def createSession(self):
        dbPath = os.path.expanduser(os.path.join(self.datadrive, "selfspy.sqlite"))
        engine = sqlalchemy.create_engine('sqlite:///%s' % dbPath)
        models.Base.metadata.create_all(engine)

        return sessionmaker(bind=engine)

    def populateSamplesWithDebrief(self, session):
        span = datetime.timedelta(days = 7)
        last_week = datetime.datetime.now() - span
        cutoff = datetime.datetime.strftime(last_week, "%Y-%m-%d")

        q = session.query(Debrief).distinct(Debrief.experience_id).group_by(Debrief.experience_id).filter(sqlalchemy.func.substr(Debrief.created_at,0,11) >= cutoff).all()

        # trim to even length
        even_length = 2* (len(q) / 2)    # dividing two ints should produce a int rounded down
        if even_length > 20:
            even_length = 20
            q = random.sample(q, 20)

        for i in range(even_length):
            l = session.query(Debrief).filter(Debrief.experience_id == q[i].experience_id)
            u = session.query(Debrief, Experience).join(Experience, Experience.id==Debrief.experience_id).filter(Debrief.id == l[-1].id)
            dict = {}
            dict['experience_id'] = u[0].Experience.id
            dict['debrief_id'] = u[0].Debrief.id
            dict['screenshot'] = u[0].Experience.screenshot.split('/')[-1]
            dict['debriefed'] = True
            dict['snippet'] = bool(i % 2)
            self.samples.append(NSDictionary.dictionaryWithDictionary_(dict))

    def populateSamplesWithRandom(self):
        images = os.listdir(os.path.join(self.datadrive, "screenshots"))
        items_to_get = len(self.samples)

        while(items_to_get > 0):
            img = random.choice(images)
            enough_distance = True

            # check if an experience sample or too close to other samples
            if(img[-15:] == '-experience.jpg'):
                continue

            img_time = datetime.datetime.strptime(img[:19] , "%y%m%d-%H%M%S%f")

            for s in self.samples:
                sample_time = datetime.datetime.strptime(s['screenshot'][:19], "%y%m%d-%H%M%S%f")
                if (abs(sample_time-img_time) < datetime.timedelta(seconds = 300)):
                    enough_distance = False
                    print "Randomly selected image too close to other samples. Searching for another."

            if(enough_distance):
                dict = {}
                dict['experience_id'] = 0
                dict['debrief_id'] = 0
                dict['screenshot'] = img
                dict['debriefed'] = False
                dict['snippet'] = bool(items_to_get % 2)
                self.samples.append(NSDictionary.dictionaryWithDictionary_(dict))
                items_to_get -= 1

    def show(self):
        try:
            if self.reviewController:
                self.reviewController.close()
        except:
            pass

        # open window from NIB file, show front and center
        self.reviewController = ReviewController.alloc().initWithWindowNibName_("Reviewer")
        self.reviewController.showWindow_(None)
        self.reviewController.window().setFrame_display_(NSMakeRect(0.0 , 0.0, self.viewW+300, max(720, self.viewH+40)) ,True)
        self.reviewController.mainPanel.setFrame_(NSMakeRect(20.0, 20.0, self.viewW, self.viewH))
        self.reviewController.window().makeKeyAndOrderFront_(None)
        self.reviewController.window().center()
        self.reviewController.retain()

        self.currentSample = -1

        self.lookupDatadrive_(self)

        # get random set of debriefed experience and other points
        self.session_maker = self.createSession(self)
        self.session = self.session_maker()
        self.populateSamplesWithDebrief(self, self.session)
        self.populateSamplesWithRandom(self)
        random.shuffle(self.samples)

        self.loadFirstExperience(self)

    show = classmethod(show)

    def lookupDatadrive_(self, namefilter=""):
        self.datadrive = None
        for dir in os.listdir('/Volumes') :
            if namefilter in dir :
                volume = os.path.join('/Volumes', dir)
                if (os.path.ismount(volume)) :
                    subDirs = os.listdir(volume)
                    for filename in subDirs:
                        if "selfspy.cfg" == filename :
                            print "External Selfspy drive found ", volume
                            self.datadrive = volume
        if not self.datadrive:
            self.datadrive = os.path.expanduser("~/.selfspy")
            print "Using internal Selfspy storage ~/.selfspy"

    @IBAction
    def copyFiles_(self, notification):
        try:
            conn = sqlite3.connect(os.path.join(self.datadrive, 'selfspy.sqlite'))
            c = conn.cursor()

            # copy over database
            fldr = os.path.join(self.datadrive, "trimmed_data")
            if not os.path.exists(fldr):
                os.makedirs(fldr)
            db = os.path.join(self.datadrive, "selfspy.sqlite")
            if os.path.exists(db):
                shutil.copy(db, fldr)

            # copy over end-of-week and samples and experience screenshots
            dst = os.path.join(fldr,  "screenshots")
            if not os.path.exists(dst):
                os.makedirs(dst)
            screenshots = c.execute('SELECT screenshot from cue')
            for row in screenshots:
                absolute_path = os.path.join(self.datadrive, "screenshots", str(row[0]))
                if os.path.exists(absolute_path):
                    shutil.copy(absolute_path, dst)
            exp_screenshots = c.execute('SELECT screenshot from experience')
            for row in exp_screenshots:
                if os.path.exists(str(row[0])):
                    shutil.copy(str(row[0]), dst)

            # copy over audio files
            dst = os.path.join(fldr, 'audio')
            if not os.path.exists(dst):
                os.makedirs(dst)
            audio_files = os.listdir(os.path.join(self.datadrive, 'audio'))
            for file in audio_files:
                absolute_path = os.path.join(self.datadrive, 'audio', file)
                if os.path.exists(absolute_path):
                    shutil.copy(absolute_path, dst)
        except:
            print "Files did not copy"
