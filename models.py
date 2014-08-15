"""
Selfspy Reviewer
Adam Rule
8.15.2014

Program to guide participants through using full-screen and snippet screenshots
to recall past episodes tracked with Selfspy
"""


import datetime

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Index, Column, Boolean, Integer, Unicode, Binary, Float, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref


Base = declarative_base()

class SpookMixin(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)
    created_at = Column(Unicode, default=datetime.datetime.now, index=True)


class Experience(SpookMixin, Base):
    message = Column(Unicode, index=True)
    screenshot = Column(Unicode, index=True)
    user_initiated = Column(Boolean, index=True)
    ignored = Column(Boolean, index=True)

    def __init__(self, message, screenshot, user_initiated = True, ignored = False): #,  after_break = False):
        self.message = message
        self.screenshot = screenshot
        self.user_initiated = user_initiated
        self.ignored = ignored

    def __repr__(self):
        return "<Experience message: '%s'>" % self.message


class Debrief(SpookMixin, Base):
    experience_id = Column(Integer, ForeignKey('experience.id'), nullable=False, index=True)
    experience = relationship("Experience", backref=backref('debrief'))

    doing_report = Column(Unicode, index=True)
    audio_file = Column(Unicode, index=True)
    activity = Column(Unicode, index=True)
    memory_strength = Column(Integer, index=True)
    image_aptness = Column(Integer, index=True)

    def __init__(self, experience_id, doing_report, audio_file, activity, memory_strength, image_aptness):
        self.experience_id = experience_id
        self.doing_report = doing_report
        self.audio_file = audio_file
        self.activity = activity
        self.memory_strength = memory_strength
        self.image_aptness = image_aptness

    def __repr__(self):
        return "<Participant was: '%s'>" % self.doing_report


class Cue(SpookMixin, Base):

    experience_id = Column(Integer, ForeignKey('experience.id'), nullable=False, index=True)
    experience = relationship("Experience", backref=backref('cue'))
    debrief_id = Column(Integer, ForeignKey('debrief.id'), nullable=False, index=True)
    debrief = relationship("Debrief", backref=backref('cue'))
    screenshot = Column(Unicode, index=True)
    snippet = Column(Boolean)
    project_size = Column(Integer)
    project_time = Column(Float)
    activity_size = Column(Integer)
    activity_time = Column(Float)
    audio_file = Column(Unicode, index=True)
    doing_report = Column(Unicode, index=True)
    features = Column(Unicode, index=True)
    memory_strength = Column(Integer, index=True)
    image_aptness = Column(Integer, index=True)
    activity = Column(Unicode, index=True)

    def __init__(self, experience_id, debrief_id, screenshot, snippet, project_size, project_time, activity_size, activity_time, audio_file, doing_report, features, memory_strength, image_aptness, activity):
        self.experience_id = experience_id
        self.debrief_id = debrief_id
        self.screenshot = screenshot
        self.snippet = snippet
        self.project_size = project_size
        self.project_time = project_time
        self.activity_size = activity_size
        self.activity_time = activity_time
        self.audio_file = audio_file
        self.doing_report = doing_report
        self.features = features
        self.memory_strength = memory_strength
        self.image_aptness = image_aptness
        self.activity = activity

    def __repr__(self):
        return "<Cue(screenshot = '%s', snippet='%s', activity_size='%s')>" % (self.screenshot, self.snippet, self.activity_size)
