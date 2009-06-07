#!-*- coding:utf-8 -*-
import logging
from dict_mngr import appenddata

def processdata(dictdata, flush, input, output):
  lastline = dictdata.eng_data or ''
  lines = input.splitlines(True)
  lines[0] = lastline + lines[0]

  if len(lines) > 0: # debug info
    output.append(u'Line 1:%s' % (unicode(lines[0], 'utf-8', 'replace'),))
    if len(lines) > 1:
      output.append(u'Line 2:%s' % (unicode(lines[1], 'utf-8', 'replace'),))
      output.append(u'Line %d:%s' % (len(lines)-1, unicode(lines[-2], 'utf-8', 'replace')))
    output.append(u'Line %d:%s' % (len(lines), unicode(lines[-1], 'utf-8', 'replace')))

  if not lines[-1].endswith('\n') and not flush:
    dictdata.eng_data = lines[-1]
    lines = lines[:-1]
  else:
    dictdata.eng_data = ''

  result = []
  for line in lines:
    if line.startswith('#'):
      continue
    ar = line.split('/')
    try:
      assert len(ar) > 1
    except:
      logging.warning('CEDICT: error with line ' + line)
      raise
    if ar[-1] not in ('\n', '\r\n'):
      logging.warning('CEDICT: error with line ' + line)
      logging.info(`ar`)
      continue
    p = ar[0].find('[')
    if p > 0:
      words = ar[0][:p].strip().split()
      pronun = ar[0][p+1:ar[0].index(']')]
      mean = ar[1:-1]
    else:
      words = ar[0].strip().split()
      pronun = ''
      mean = ar[1:-1]
    result.append('|'.join(words))
    result.append('\t')
    result.append('[%s]\\n' % (pronun,))
    result.append('\\n'.join(mean))
    result.append('\n')
  result = ''.join(result)
  appenddata(dictdata, result)

  if flush:
    dictdata.ready = True
  dictdata.put()
  return True
