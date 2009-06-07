#!-*- coding:utf-8 -*-
from dict_mngr import DataChunk, DictData

def processdata(dictdata, offset, totallen, input, output):
  output.append('offset = %d, length = %d, totallen = %d' % (offset, 
    len(input), totallen))
  lines = input.splitlines()
  if len(lines) > 0:
    output.append(u'Line 1:%s' % (unicode(lines[0], 'utf-8', 'replace'),))
    if len(lines) > 1:
      output.append(u'Line 2:%s' % (unicode(lines[1], 'utf-8', 'replace'),))
      output.append(u'Line %d:%s' % (len(lines)-1, unicode(lines[-2], 'utf-8', 'replace')))
    output.append(u'Line %d:%s' % (len(lines), unicode(lines[-1], 'utf-8', 'replace')))
  dictdata.put()
  return True
