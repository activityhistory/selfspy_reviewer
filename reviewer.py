"""
Selfspy Reviewer
Adam Rule
8.15.2014

Program to guide participants through using full-screen and snippet screenshots
to recall past episodes tracked with Selfspy
"""


import os
import re   # for .split()
import time
import datetime
# import math
import random
import string
import mutagen.mp4

import objc
from objc import IBAction, IBOutlet

from Foundation import *
from AppKit import *
from Cocoa import NSTimer
import Quartz.CoreGraphics as CG

import sqlalchemy
from sqlalchemy.orm import sessionmaker, mapper, join
from sqlalchemy.dialects.sqlite.base import dialect

import models
from models import Experience, Debrief, Cue, Animation


# Experience Sampling window controller
class ReviewController(NSWindowController):

    # outlets for UI elements
    mainPanel = IBOutlet()
    errorMessage = IBOutlet()

    controlView = IBOutlet()
    dataView = IBOutlet()

    existAudioText = IBOutlet()
    recordButton = IBOutlet()
    playAudioButton = IBOutlet()
    deleteAudioButton = IBOutlet()
    doingText = IBOutlet()
    features = IBOutlet()
    memoryStrength = IBOutlet()
    imageAptness = IBOutlet()
    activityText = IBOutlet()

    recordImage = NSImage.alloc().initByReferencingFile_('../Resources/record.png')
    recordImage.setScalesWhenResized_(True)
    recordImage.setSize_((11, 11))

    stopImage = NSImage.alloc().initByReferencingFile_('../Resources/stop.png')
    stopImage.setScalesWhenResized_(True)
    stopImage.setSize_((11, 11))

    progressLabel = IBOutlet()
    progressButton = IBOutlet()

    # variables for controlling animation presenation and data recording
    samples = []
    currentSample = -1
    frames = []
    currentFrame = 0

    animationSpan = 300
    animationAdjacency = 0     #time around the screenshot
    animationSpeed = 30

    snippetW = 0
    snippetH = 320

    recordingAudio = False
    playingAudio = False
    audio_file = ''

    # data variables
    animationStartTime = 0
    project_size = 0
    project_frames = 0
    project_time = 0.0
    activity_size = 0
    activity_frames = 0
    activity_time = 0.0


    @IBAction
    def startAnimation_(self, sender):
        self.frames = filter(self.checkTime_, self.images)
        print "Animation Images"

        self.timings = []
        for f in self.frames:
            self.timings.append(datetime.datetime.strptime(f.split('_')[0], "%y%m%d-%H%M%S%f"))
        for t in range(len(self.timings)-1):
            self.timings[t] = (self.timings[t+1] - self.timings[t]).total_seconds()

        if len(self.frames) >=2:
            self.timings[-1] = 0
        else:
            print "Cannot run animaiton with less than 2 images"
            return

        self.currentFrame = 0
        self.playAnimation = True

        self.animationLoop()

    def animationLoop(self):
        if(self.currentFrame >= len(self.frames)-1):
            self.stopAnimation_(self)
            return

        time1 = time.time()
        print time1
        img = self.frames[self.currentFrame][:]
        path = "/Volumes/SELFSPY/screenshots/" + img
        cueImage = NSImage.alloc().initByReferencingFile_(path)

        if(self.playAnimation):
            if(self.samples[self.currentSample]['snippet']):
                self.snippetW = self.snippetH * cueImage.size().width / cueImage.size().height
                x = float(path.split("_")[-2])
                y = float(path.split("_")[-1].split('-')[0].split('.')[0])
                fromRect = CG.CGRectMake(x-self.snippetW/2, y-self.snippetH/2, self.snippetW, self.snippetH)
                toRect = CG.CGRectMake(0.0, 0.0, self.snippetW, self.snippetH)
                targetImage = NSImage.alloc().initWithSize_(NSMakeSize(self.snippetW, self.snippetH))

                targetImage.lockFocus()
                cueImage.drawInRect_fromRect_operation_fraction_( toRect, fromRect, NSCompositeCopy, 1.0 )
                targetImage.unlockFocus()

            else:
                targetImage = cueImage

            self.reviewController.mainPanel.setImage_(targetImage)
            print time.time()
            print ("Took " + str(time.time() - time1) + " seconds to show image")

            s = objc.selector(self.animationLoop,signature='v@:')
            self.imageLoop = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.timings[self.currentFrame]/self.animationSpeed, self, s, None, False)

            self.currentFrame += 1

    def checkTime_(self, x):
        span = datetime.timedelta(seconds = self.animationSpan)
        now = datetime.datetime.strptime(self.samples[self.currentSample]["screenshot"].split('_')[0], "%y%m%d-%H%M%S%f")

        if(self.animationAdjacency == -1):
            start = now - span
            end = now
        elif(self.animationAdjacency == 0):
            start = now - span/2
            end = now + span/2
        else:
            start = now
            end = now + span

        start = datetime.datetime.strftime(start, "%y%m%d-%H%M%S%f")
        end = datetime.datetime.strftime(end, "%y%m%d-%H%M%S%f")
        return ((x >= start) & (x <= end))

    @IBAction
    def recordProjectSize_(self, sender):
        self.project_size = self.snippetH
        self.project_frames = self.currentFrame + 1
        self.project_time = time.time() - self.animationStartTime

    @IBAction
    def stopAnimation_(self, sender):
        self.activity_time = time.time() - self.animationStartTime
        self.activity_size = self.snippetH
        self.activity_frames = self.currentFrame + 1
        self.playAnimation = False

        self.reviewController.dataView.setHidden_(False)
        self.reviewController.mainPanel.setImage_(None) # a hack since I cannot easily paint a background on the dataView

    @IBAction
    def toggleAudioRecording_(self, sender):
        try:
            if self.recordingAudio:
                self.recordingAudio = False

                print "Stoping Audio recording"
                imageName = self.samples[self.currentSample]['screenshot'][0:-4]
                if (imageName == None) | (imageName == ''):
                    imageName = datetime.datetime.now().strftime("%y%m%d-%H%M%S%f") + '-audio'
                imageName = str(os.path.join('/Volumes/SELFSPY', "audio/")) + imageName + '-week.m4a'
                self.audio_file = imageName
                imageName = string.replace(imageName, "/", ":")
                imageName = imageName[1:]

                s = NSAppleScript.alloc().initWithSource_("set filePath to \"" + imageName + "\" \n set placetosaveFile to a reference to file filePath \n tell application \"QuickTime Player\" \n set mydocument to document 1 \n tell document 1 \n stop \n end tell \n set newRecordingDoc to first document whose name = \"untitled\" \n export newRecordingDoc in placetosaveFile using settings preset \"Audio Only\" \n close newRecordingDoc without saving \n quit \n end tell")
                s.executeAndReturnError_(None)

                self.reviewController.recordButton.setImage_(self.recordImage)
                self.reviewController.recordButton.setEnabled_(False)
                self.reviewController.existAudioText.setStringValue_("You've recorded an answer:")
                self.reviewController.playAudioButton.setHidden_(False)
                self.reviewController.deleteAudioButton.setHidden_(False)

            else:
                self.recordingAudio = True

                print "Starting Audio Recording"
                s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n set new_recording to (new audio recording) \n tell new_recording \n start \n end tell \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n end tell")
                s.executeAndReturnError_(None)

                self.reviewController.recordButton.setImage_(self.stopImage)
        except:
            print "Problem recording audio. Please try typing your answer instead."

            alert = NSAlert.alloc().init()
            alert.addButtonWithTitle_("OK")
            alert.setMessageText_("Problem recording audio. Please try typing your answer instead.")
            alert.setAlertStyle_(NSWarningAlertStyle)
            alert.runModal()

    @IBAction
    def toggleAudioPlay_(self, sender):
        try:
            if self.playingAudio:
                self.playingAudio = False
                self.reviewController.playAudioButton.setTitle_("Play Audio")

                s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
                s.executeAndReturnError_(None)

            else:
                self.playingAudio = True
                self.reviewController.playAudioButton.setTitle_("Stop Audio")

                audio = mutagen.mp4.MP4(self.audio_file)
                length = audio.info.length

                s = NSAppleScript.alloc().initWithSource_("set filePath to POSIX file \"" + self.audio_file + "\" \n tell application \"QuickTime Player\" \n open filePath \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n play the front document \n end tell")
                s.executeAndReturnError_(None)

                s = objc.selector(self.stopAudioPlay,signature='v@:')
                self.audioTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(length, self, s, None, False)

        except:
            print "Problem playing audio. Please delete audio file and try again."

            alert = NSAlert.alloc().init()
            alert.addButtonWithTitle_("OK")
            alert.setMessageText_("Problem playing audio. Please delete audio file and try again.")
            alert.setAlertStyle_(NSWarningAlertStyle)
            alert.runModal()

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

        # close if user clicked Finish on window with no experiences to comment
        if self.currentSample == -2:
            controller.close()
            return

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

                alert = NSAlert.alloc().init()
                alert.addButtonWithTitle_("OK")
                alert.setMessageText_("Please answer the first four questions")
                alert.setAlertStyle_(NSWarningAlertStyle)
                alert.runModal()
                return

            else:
                print "Recording data"
                self.recordAnimation()

        if i == l-1:
            controller.progressButton.setTitle_("Finish")

        # prepare window for next sample
        if i < l:
            self.populateReviewWindow()
            controller.progressLabel.setStringValue_( str(i + 1) + '/' + str(l) )
            controller.dataView.setHidden_(True)

        else:
            controller.close()

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
            self.currentSample -= 1
            return

        self.currentSample += 1
        i = self.currentSample

        self.populateReviewWindow(self)
        controller.progressLabel.setStringValue_( str(i + 1) + '/' + str(l) )

        if i == l-1:
            controller.progressButton.setTitle_("Finish")

    def populateReviewWindow(self):
        print "Populating Review Window with prior answers"
        controller = self.reviewController
        current_experience = self.samples[self.currentSample]['experience_id']

        self.audio_file = ''
        self.project_size = 0
        self.project_frames = 0
        self.project_time = 0.0
        self.activity_size = 0
        self.activity_frames = 0
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

        prior_activities = self.session.query(Animation).distinct(Animation.activity).group_by(Animation.activity).order_by(Animation.id.desc()).limit(7)
        controller.activityText.removeAllItems()
        for d in prior_activities:
            if (d.activity != ''):
                controller.activityText.addItemWithObjectValue_(d.activity)

        # populate page with responses to last cue of this experience
        if current_experience != 0:
            q = self.session.query(Animation).filter(Animation.experience_id == current_experience).all()
        else:
            q = False

        if q:
            controller.doingText.setStringValue_(q[-1].doing_report)
            controller.features.setStringValue_(q[-1].features)
            controller.audio_file = q[-1].audio_file
            if (q[-1].audio_file != '') & (q[-1].audio_file != None):
                controller.recordButton.setEnabled_(False)
                controller.existAudioText.setStringValue_("You've recorded an answer:")
                controller.playAudioButton.setHidden_(False)
                controller.deleteAudioButton.setHidden_(False)
            else:
                controller.recordButton.setEnabled_(True)
                controller.existAudioText.setStringValue_("Record your answer:")
                controller.playAudioButton.setHidden_(True)
                controller.deleteAudioButton.setHidden_(True)
            if q[-1].memory_strength >= -1:
                controller.memoryStrength.selectCellWithTag_(q[-1].memory_strength)
            if q[-1].image_aptness >= -1:
                controller.imageAptness.selectCellWithTag_(q[-1].image_aptness)
            controller.activityText.setStringValue_(q[-1].activity)

    def recordAnimation(self):
        experience_id = self.samples[self.currentSample-1]['experience_id']
        debrief_id = self.samples[self.currentSample-1]['debrief_id']
        screenshot = self.samples[self.currentSample-1]['screenshot']
        snippet = self.samples[self.currentSample-1]['snippet']
        project_size = self.project_size
        project_frames = self.project_frames
        project_time = self.project_time
        activity_size = self.activity_size
        activity_frames = self.activity_frames
        activity_time = self.activity_time
        audio_file = self.reviewController.audio_file
        doing_report = self.reviewController.doingText.stringValue()
        features = self.reviewController.features.stringValue()
        memory_strength = self.reviewController.memoryStrength.selectedCell().tag()
        image_aptness = self.reviewController.imageAptness.selectedCell().tag()
        activity = self.reviewController.activityText.stringValue()

        self.session.add(Animation(experience_id, debrief_id, screenshot, snippet, project_size, project_frames, project_time, activity_size, activity_frames, activity_time, audio_file, doing_report, features, memory_strength, image_aptness, activity))
        self.trycommit()

    def trycommit(self):
        for _ in xrange(1000):
            try:
                self.session.commit()
                break
            except sqlalchemy.exc.OperationalError:
                print "Database operational error. Your storage device may be full."
                self.session.rollback()

                alert = NSAlert.alloc().init()
                alert.addButtonWithTitle_("OK")
                alert.setMessageText_("Database operational error. Your storage device may be full.")
                alert.setAlertStyle_(NSWarningAlertStyle)
                alert.runModal()

                break
            except:
                print "Rollback"
                self.session.rollback()

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)
        self.reviewController.window().contentView().layout()

    def windowWillClose_(self, notification):
        if(self.recordingAudio):
            "Stopping Audio Recording"
            self.toggleAudioRecording_(self)

    def windowDidEnterFullScreen_(self, notification):
        screenSize = NSScreen.mainScreen().frame().size
        self.reviewController.window().setFrame_display_(NSMakeRect(0.0 , 0.0, screenSize.width, screenSize.height) ,True)
        self.reviewController.mainPanel.setFrame_(NSMakeRect(0.0, 0.0, screenSize.width, screenSize.height))

    def createSession(self):
        dbPath = os.path.expanduser('/Volumes/SELFSPY/selfspy.sqlite')
        engine = sqlalchemy.create_engine('sqlite:///%s' % dbPath)
        models.Base.metadata.create_all(engine)

        return sessionmaker(bind=engine)

    def populateSamplesWithDebrief(self, session):
        q = session.query(Debrief).distinct(Debrief.experience_id).group_by(Debrief.experience_id).all()

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
            if i % 2 == 0:
                dict['snippet'] = False
            else:
                dict['snippet'] = True
            self.samples.append(NSDictionary.dictionaryWithDictionary_(dict))

    def populateSamplesWithRandom(self):
        self.images = os.listdir("/Volumes/SELFSPY/screenshots")
        items_to_get = len(self.samples)

        while(items_to_get > 0):
            img = random.choice(self.images)
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
                if items_to_get % 2 == 0:
                    dict['snippet'] = False
                else:
                    dict['snippet'] = True
                self.samples.append(NSDictionary.dictionaryWithDictionary_(dict))
                items_to_get -= 1

    def show(self):
        try:
            if self.reviewController:
                self.reviewController.close()
        except:
            pass

        screenSize = NSScreen.mainScreen().frame().size

        # open window from NIB file, show front and center
        self.reviewController = ReviewController.alloc().initWithWindowNibName_("Reviewer")
        self.reviewController.showWindow_(None)
        self.reviewController.window().setFrame_display_(NSMakeRect(0.0 , 0.0, screenSize.width, screenSize.height) ,True)
        self.reviewController.mainPanel.setFrame_(NSMakeRect(0.0, 0.0, screenSize.width, screenSize.height))
        self.reviewController.window().makeKeyAndOrderFront_(None)
        self.reviewController.window().center()
        self.reviewController.retain()

        self.reviewController.window().setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)

        self.currentSample = -1

        # get random set of debriefed experience and other points
        self.session_maker = self.createSession(self)
        self.session = self.session_maker()
        self.populateSamplesWithDebrief(self, self.session)
        self.populateSamplesWithRandom(self)
        random.shuffle(self.samples)

        self.loadFirstExperience(self)

    show = classmethod(show)
