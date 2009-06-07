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
  queue_name = db.StringProperty(required=True)
  url = db.StringProperty(required=True)
  offset = db.IntegerProperty(required=True)
  totallen = db.IntegerProperty(required=True)
  timestamp = db.DateTimeProperty(required=True, auto_now=True)

class MyQueue():
  def push(queue_name, **kwargs):
    TaskMessage(queue_name=queue_name, **kwargs).put()
  push=staticmethod(push)

  def pop(queue_name):
    results = TaskMessage.gql("ORDER BY timestamp ASC LIMIT 1") or [None]
    return results[0]
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
    for dic in config['dictlist']:
      name = dic['name']
      task = MyQueue.pop(name)
      if task is not None: break;
    if task is None:
      self.response.out.write('No task in queue')
      return
    self.response.out.write('<p>queue=%s, url=%s, offset=%d, totallen=%d, timestamp=%s</p>' % (task.queue_name, task.url, task.offset, task.totallen, task.timestamp))
    try:
      result = urlfetch.fetch(url=url,
                              method=urlfetch.GET,
                              headers={'Range': 'bytes=%d-' % (task.offset)})
      assert result.status_code == 206
      assert result.headers.has_key('Content-Range')
    except DownloadError, e:
      self.response.out.write(`e` + '<br>')
      pass
    except Exception, e:
      logging.error('Failed updating %s: %s' % (dic['name'], `e`))
      self.response.out.write('Failed updating %s: %s<br>' % (dic['name'], `e`))
      task.delete()
      return

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
          totallen = result.headers['Content-Range']
          totallen = int(totallen[totallen.index('/')+1:])
          MyQueue.push(name, offset=0, totallen=totallen, url=url)
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
    self.response.out.write('<hr/>')
    results = TaskMessage.gql("ORDER BY timestamp") or []
    for task in results:
      self.response.out.write('<p>queue=%s, url=%s, offset=%d, totallen=%d, timestamp=%s</p>' % (task.queue_name, task.url, task.offset, task.totallen, task.timestamp))
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
