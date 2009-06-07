#!-*- coding:utf-8 -*-
import sys
import logging
import zlib
import struct

globaldic = {}

FTEXT, FHCRC, FEXTRA, FNAME, FCOMMENT = 1, 2, 4, 8, 16

class GzipStreamReader:
	def __init__(self, buf=''):
		self.reset(buf)

	def reset(self, buf=''):
		self._buf = buf
		self._readptr = 0
		self._writeptr = len(buf)
		self._decompress = None
		self._crc = zlib.crc32('')
		self._size = 0

	def _readbytes(self, bytes):
		if self._readptr >= self._writeptr:
			#raise IOError,"GzipStreamReader: Read past end of file"
			return ''
		if self._readptr + bytes > self._writeptr:
			bytes = self._writeptr - self._readptr
		result = self._buf[self._readptr:self._readptr+bytes]
		self._readptr += bytes
		return result

	def feed(self, buf):
		self._buf += buf
		self._writeptr += len(buf)
		if self._readptr > 10240:
			self._buf = self._buf[self._readptr:]
			self._writeptr -= self._readptr
			self._readptr = 0

	def read_header(self):
		self._decompress = zlib.decompressobj(-zlib.MAX_WBITS)
		self._crc = zlib.crc32('')
		self._size = 0

		magic = self._readbytes(2)
		if magic != '\037\213':
			raise IOError, 'Not a gzipped file'
		method = ord( self._readbytes(1) )
		if method != 8:
			raise IOError, 'Unknown compression method'
		flag = ord( self._readbytes(1) )
		# modtime = self._readbytes(4)
		# extraflag = self._readbytes(1)
		# os = self._readbytes(1)
		self._readbytes(6)

		if flag & FEXTRA:
			# Read & discard the extra field, if present
			xlen = ord(self._readbytes(1))
			xlen = xlen + 256*ord(self._readbytes(1))
			self._readbytes(xlen)
		if flag & FNAME:
			# Read and discard a null-terminated string containing the filename
			while True:
				s = self._readbytes(1)
				if not s or s=='\000':
					break
		if flag & FCOMMENT:
			# Read and discard a null-terminated string containing a comment
			while True:
				s = self._readbytes(1)
				if not s or s=='\000':
					break
		if flag & FHCRC:
			self._readbytes(2)	 # Read & discard the 16-bit header CRC

	def read(self):
		assert self._decompress is not None
		result = []
		while True:
			buf = self._readbytes(10240)
			if not buf:
				break
			d_buf = self._decompress.decompress(buf)
			result.append(d_buf)
			self._crc = zlib.crc32(d_buf, self._crc)
			self._size += len(d_buf)
		return ''.join(result)

	def flush(self):
		logging.info('GzipStreamReader: flush invoked')
		if self._decompress is not None\
				and self._decompress.unused_data != "":
			d_buf = self._decompress.flush()
			self._crc = zlib.crc32(d_buf, self._crc)
			self._size += len(d_buf)
			if len(self._buf) >= 8:
				crcsize = self._buf[-8:]
				crc, size = struct.unpack('<LL', crcsize)
				if self._crc < 0:
					self._crc += 1 << 32
				if crc != self._crc:
					logging.error('Gzip CRC %s != %s' % (
						hex(crc), hex(self._crc)))
				if size != self._size:
					logging.error('Gzip Size %d != %d' % (
						size, self._size))
			self.reset()
			return d_buf
		else:
			logging.warning('GzipStreamReader: nothing to flush')
			return ''

	def __getstate__(self):
		result = [self._buf, self._readptr, self._writeptr]
		if self._decompress is None:
			result.append(None)
		else:
			dconame = 'decompressobj-%d-%d-%d-%d' % (
					self._readptr,
					self._writeptr,
					self._crc,
					self._size)
			result.append(True)
			globaldic[dconame] = self._decompress
		result.append(self._crc)
		result.append(self._size)
		return result

	def __setstate__(self, state):
		assert len(state) == 6
		self._buf, self._readptr, self._writeptr = state[:3]
		if state[3] is None:
			self._decompress = None
		else:
			self._decompress = True
		self._crc, self._size = state[4:]
		if self._decompress == True:
			dconame = 'decompressobj-%d-%d-%d-%d' % (
					self._readptr,
					self._writeptr,
					self._crc,
					self._size)
			assert globaldic.has_key(dconame)
			self._decompress = globaldic[dconame]

if __name__ == '__main__':
	if len(sys.argv) < 2:
		sys.exit(0)
	import pickle
	if sys.platform == 'win32':
		import os, msvcrt
		msvcrt.setmode(sys.stdout.fileno(  ), os.O_BINARY)
	f = open(sys.argv[1], 'rb')
	gz = GzipStreamReader()
	buf = f.read(102400)
	gz.feed(buf)
	gz.read_header()
	while True:
		sys.stdout.write(gz.read())
		buf = f.read(10240)
		if not buf:
			break
		gz.feed(buf)
	f.close()
	sys.stdout.write(gz.flush())
