#!-*- coding:utf-8 -*-
import logging
import pickle

from google.appengine.ext import db, webapp
from google.appengine.api import urlfetch, memcache
from google.appengine.ext.webapp import template
from gzipstreamreader import GzipStreamReader

class DataChunk(db.Model):
  data = db.BlobProperty()
  next = db.SelfReferenceProperty()

class DictData(db.Model):
  dict_name = db.StringProperty(required=True)
  alternative = db.BooleanProperty(required=True)
  ready = db.BooleanProperty(required=True)
  zipped = db.BooleanProperty()
  zip_data = db.BlobProperty()
  eng_data = db.BlobProperty()
  out_data = db.ReferenceProperty(DataChunk, collection_name='out_data')

def getfuncmap():
  functionmap = memcache.get("functionmap")
  if functionmap is not None:
    return functionmap
  else:
    functionmap = initfuncmap()
    if not memcache.set("functionmap", functionmap, 600):
      logging.error("Memcache set failed for functionmap.")
    return functionmap

def processdata(engine, dictname, offset, totallen, input, output):
  functionmap = getfuncmap()
  if not functionmap.has_key(engine):
    logging.error('Engine %s not found in function map' % (engine,))
    return False
  results = DictData.gql('WHERE dict_name = :1', dictname)
  if results.count() == 0:
    dictdata = DictData(dict_name=dictname, alternative=False, ready=False)
  elif results.count() == 1:
    if results[0].ready:
      dictdata = DictData(dict_name=dictname, alternative=not results[0].ready,
          ready=False)
    else:
      dictdata = results[0]
  else:
    try:
      assert results.count() == 2
      if results[0].ready:
        assert not results[1].ready
        dictdata = results[1]
      else:
        dictdata = results[0]
    except:
      logging.error('Unexpected dictdata: ' + `e`)
      return False
  if offset == 0:
    gz = GzipStreamReader()
    gz.feed(input)
    try:
      gz.read_header()
      dictdata.zipped = True
    except:
      dictdata.zipped = False
      del gz
  else:
    if dictdata.zipped:
      assert dictdata.zip_data is not None
      gz = pickle.loads(dictdata.zip_data)
      gz.feed(input)
  if dictdata.zipped:
    if offset + len(input) < totallen:
      input = gz.read()
    else:
      input = gz.read() + gz.flush()
    dictdata.zip_data = pickle.dumps(gz)
  #dictdata is expected to be put in engine's function
  return functionmap[engine](dictdata, offset, totallen, input, output)

def initfuncmap(functionmap={}):
  import jmdict
  functionmap['jmdict'] = jmdict.processdata
  import cedict
  functionmap['cedict'] = cedict.processdata
  return functionmap
