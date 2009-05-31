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

class TaskMessage(db.Model):
  queue_name = db.StringProperty()
  type = db.IntegerProperty(required=True)
  url = db.StringProperty()
  offset = db.IntegerProperty()
  size = db.IntegerProperty()
  totallen = db.IntegerProperty()
  timestamp = db.DateTimeProperty(required=True, auto_now=True)

class MyQueue():
  BEGIN_FETCH=0
  FETCHING=1
  BEGIN_PROCESS=2
  PROCESSING=3

  def push(queue_name, **kwargs):
    TaskMessage(queue_name=queue_name, **kwargs).put()
  push=staticmethod(push)

  def pop(queue_name):
    results = TaskMessage.gql("ORDER BY timestamp ASC LIMIT 1") or [None]
    return result[0]
  pop=staticmethod(pop)


def get_my_config():
  config = memcache.get("config")
  if config is not None:
    return config
  else:
    config = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), 'my-config.yaml'), 'r'))
    if not config.has_key('dictlist') or not hasattr(config['dictlist'], '__iter__'):
      logging.warning('Config file does not contain valid dictlist.')
      contain['dictlist'] = []
    if not memcache.add("config", config, 600):
      logging.error("Memcache set failed for config.")
    return config

class DictionarySync(webapp.RequestHandler):
  def get(self):
    config = get_my_config()
    self.response.out.write('This is only a test')

class CheckUpdate(webapp.RequestHandler):
  def get(self):
    config = get_my_config()
    for dic in config['dictlist']:
      name = dic['name']
      url = dic['url']
      self.response.out.write('Checking %s... ' % (name))
      try:
        result = urlfetch.fetch(url=url,
                                method=urlfetch.GET,
                                headers={'Range': 'bytes=0-0'})
        assert result.status_code == 206
        assert result.headers.has_key('Content-Range')
        lastmod = memcache.get("lastmod-" + name)
        if lastmod is None or lastmod != result.headers['Last-Modified']:
          MyQueue.push(name, type=MyQueue.BEGIN_FETCH, url=url)
          if not memcache.set("lastmod-"+name, result.headers['Last-Modified']):
            logging.error("Memcache set failed for lastmod-%s." % (name))
          self.response.out.write('updated and added to queue.<br>')
        else:
          self.response.out.write('not updated.<br>')
      except Exception, e:
        logging.error('Failed checking update for %s: %s' % (dic['name'], `e`))
        self.response.out.write('Failed checking update for %s: %s<br>' % (dic['name'], `e`))

class MainPage(webapp.RequestHandler):
  def get(self):
    config = get_my_config()
    self.response.out.write('<html><body>\n')
    for dic in config['dictlist']:
      self.response.out.write('<p>name=%s<br>URL=%s</p>\n' % (dic['name'], dic['url']))
    self.response.out.write('</body></html>')

def main():
  application = webapp.WSGIApplication([
    ('/tasks/dict-sync', DictionarySync),
    ('/tasks/check-update', CheckUpdate),
    ('/', MainPage),
  ], debug=False)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
