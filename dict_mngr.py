#!-*- coding:utf-8 -*-
import os
import cgi
import logging
import yaml
import base64
import datetime
import urllib
import xmllib

import wsgiref.handlers
from google.appengine.ext import db, webapp
from google.appengine.api import urlfetch, memcache
from google.appengine.ext.webapp import template

class DataChunk(db.Model):
  data = db.BlobProperty()
  next = db.SelfReferenceProperty()

class DictData(db.Model):
  dict_name = db.StringProperty(required=True)
  alternative = db.BooleanProperty(required=True)
  ready = db.BooleanProperty()
  alt_ready = db.BooleanProperty()
  raw_data = db.ReferenceProperty(DataChunk, collection_name='raw_data')
  alt_raw_data = db.ReferenceProperty(DataChunk, collection_name='alt_raw_data')
  out_data = db.ReferenceProperty(DataChunk, collection_name='out_data')
  alt_out_data = db.ReferenceProperty(DataChunk, collection_name='alt_out_data')

def processdata(engine, offset, totallen, input):
  return True
