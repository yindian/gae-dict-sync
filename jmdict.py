#!-*- coding:utf-8 -*-
from dict_mngr import DataChunk, DictData

def processdata(dictdata, offset, totallen, input, output):
  output.append('offset = %d, length = %d, totallen = %d' % (offset, 
    len(input), totallen))
  output.append('input = %s' % (`input`[:100]))
  return True
