#!-*- coding:utf-8 -*-
import logging
import pickle
import zlib

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
  timestamp = db.DateTimeProperty(required=True, auto_now=True)

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
  logging.info('Enter processdata. offset=%d, totallen=%d, input len=%d, input crc=%d' % (offset, totallen, len(input), zlib.crc32(input)))
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
    assert results.count() == 2
    try:
      if results[0].ready:
        assert not results[1].ready
        dictdata = results[1]
      else:
        dictdata = results[0]
    except AssertionError: # both are ready, remove the older one
      if results[0].timestamp < results[1].timestamp:
        alt = results[0].alternative
        results[0].delete()
      else:
        alt = results[1].alternative
        results[1].delete()
      dictdata = DictData(dict_name=dictname, alternative=alt, ready=False)
  if offset == 0:
    gz = GzipStreamReader()
    gz.feed(input)
    try:
      gz.read_header()
      dictdata.zipped = True
    except IOError:
      dictdata.zipped = False
      del gz
  else:
    if dictdata.zipped:
      assert dictdata.zip_data is not None
      gz = pickle.loads(dictdata.zip_data)
      gz.feed(input)
  flush = offset + len(input) >= totallen
  if dictdata.zipped:
    if not flush:
      input = gz.read()
    else:
      input = gz.read() + gz.flush()
    dictdata.zip_data = pickle.dumps(gz)
  #dictdata is expected to be put in engine's function
  return functionmap[engine](dictdata, flush, input, output)

def getdatabydictname(dictname):
  results = DictData.gql('WHERE dict_name = :1', dictname)
  if results.count() == 0:
    return None
  elif results.count() == 1:
    if results[0].ready:
      dictdata = results[0]
    else:
      dictdata = results[0]
      #return None
  else:
    assert results.count() == 2
    if results[0].ready:
      dictdata = results[0]
    elif results[1].ready:
      dictdata = results[1]
    else:
      return None
  return retrievedata(dictdata)

def retrievedata(dictdata):
  chunk = dictdata.out_data
  if not chunk:
    return ''
  result = [chunk.data]
  while chunk.next:
    chunk = chunk.next
    result.append(chunk.data)
  return ''.join(result)

def appenddata(dictdata, content):
  if dictdata.out_data:
    lastchunk = dictdata.out_data
  else:
    lastchunk = DataChunk()
    lastchunk.put()
    dictdata.out_data = lastchunk
  while lastchunk.next:
    lastchunk = lastchunk.next

  data = lastchunk.data or ''
  if len(data) + len(content) <= 1024000:
    lastchunk.data = data + content
  else:
    if len(data) < 900000:
      lastchunk.data = data + content[:1024000-len(data)]
      content = content[1024000-len(data):]
    while content:
      newchunk = DataChunk()
      newchunk.put()
      lastchunk.next = newchunk
      lastchunk.put()
      lastchunk = newchunk # now a new chunk is alloc'ed
      lastchunk.data = content[:1024000]
      content = content[1024000:]
  lastchunk.put()

def initfuncmap(functionmap={}):
  import jmdict
  functionmap['jmdict'] = jmdict.processdata
  import cedict
  functionmap['cedict'] = cedict.processdata
  return functionmap
