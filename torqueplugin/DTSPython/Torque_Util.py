'''
Torque_Util.py

Copyright (c) 2003 - 2006 James Urquhart(j_urquhart@btinternet.com)

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import struct, array, math, string
from struct import *
from array import *

#############################
# Torque Game Engine
# ---------------------------------
# Torque Utility Classes for Python
#############################

#Notes:
'''
- Code taken from various sources; See Credits.
'''

import Torque_Math
from Torque_Math import Vector2, Vector, Vector4, Quaternion, MatrixF, Quat16, PlaneF, Box

# String Table Class
class StringTable:
	def __init__(self):
		self.strings = []
	def __del__(self):
		del self.strings
	
	# Adds a string to the StringTable. The string is stored as an array of char
	def addString(self, strn, caseSensitive=False):
		# Change strn to array('c')
		if strn == None: # Add "" if a bad string
			return self.addString("")
		
		# Needs to be lower case if not case sensitive
		if caseSensitive: strn_compare = strn
		else: strn_compare = string.lower(strn)
		
		# Firstly, check if the string already exists
		for i in range(0, len(self.strings)):
			if caseSensitive:
				if self.strings[i].tostring() == strn_compare:
					return i
			else:
				if string.lower(self.strings[i].tostring()) == strn_compare:
					return i
				
		# If we got here, we have a new string to add
		arr = array('c')
		for c in range(0, len(strn)):
			arr.append(strn[c])
		self.strings.append(arr)
		return len(self.strings)-1
	
	# Gets a string from the StringTable as a string
	def get(self, no):
		if (no > -1) and (no < len(self.strings)):
			return self.strings[no].tostring()
		else:
			return "" # Nothing really
	
	# Inserts a string into the StringTable (sensitive)
	def insert(self):
		return self.addstring(strn, True)
	
	# Reads the StringTable from a file
	def reads(self, fs):
		# Read in string
		slen = struct.unpack('<B', fs.read(calcsize('B')))[0]
		if slen[0] == 0:
			return array('c') # 0 length array
		mystr = array('c')
		mystr.fromfile(fs, slen[0])
		self.strings.append(mystr)
		return mystr
	
	# Prints statistics of strings in the StringTable
	def print_table(self):
		print "Strings in table :"
		for sn in range(0, len(self.strings)):
			print self.strings[sn].tostring()
	
	# Writes the StringTable to a file
	def write(self): # Writes all of the strings
		count = 0
		for s in self.strings:
			fs.write(struct.pack('<B', len(self.strings[count])))
			self.strings[count].tofile(self.fs)
			count += 1

# Integer Sets...

# Reads a IntegerSet
def readIntegerSet(fs):
	words = array('i') # Array of S32
	numInts = struct.unpack('<i', fs.read(calcsize('<i')))[0] #S32, don't care about this
	sz = struct.unpack('<i', fs.read(calcsize('<i')))[0] #S32
	words.fromfile(fs, sz)
	total = len(words) * 32 # 32 bits in total
	bits = [0]*total
	for i in range(0, total):
		if (words[i>>5] & (1 << (i & 31)))!=0:
			bits[i] = True
		else:
			bits[i] = False
	del words
	return bits

# Writes an IntegerSet
def writeIntegerSet(fs, bits):
	# Save out the bool array as an array of bits, in 32bit chunks.
	words = []
	if  len(bits) >= 32:
		use = int(math.ceil(len(bits) / 32.0))
	else: use = 1

	words = [0]*use

	for i in range(0, len(bits)):
		if bits[i]:
			words[i >> 5] |= 1 << (i & 31)

	fs.write(struct.pack('<i', use)) #S32, don't care about this
	fs.write(struct.pack('<i', use)) #S32
	for w in words:
		# ugly ugly hack to deal with python 2.4's int -> long int conversion confusion
		w = struct.unpack('i', struct.pack('I', w))[0]
		fs.write(struct.pack('<i', w))
	del words

# A port of the nice map2dif tokenizer
class Tokenizer:
	def __init__(self, buff):
		self.mBuffer = array('c')	# Current File Buffer
		self.mBuffer.fromstring(buff.tostring())
		self.mCurrToken = ""		# Token we are on
		self.mCurrPos = 0		# Position in mBuffer
		self.mCurrLine = 0		# Current Line in mBuffer
	
	def __del__(self):
		del self.mBuffer
		self.mCurrToken = None
		self.mBuffer = None
	
	def advanceToken(self, crossLine = False):
		self.mCurrToken = ""
		currPos = 0
		while (self.mCurrPos < len(self.mBuffer)):
			c = self.mBuffer[self.mCurrPos]
			cont = 1
			if (c == ' ') or (c == '\t'):
				if currPos == 0:
					# Token hasn't started yet...
					self.mCurrPos += 1
				else:
					# End of token
					self.mCurrPos += 1
					cont = 0
			elif (c == '\r') or (c == '\n'):
				if crossLine:
					if currPos == 0:
						# Haven't started getting token, but we're crossing lines...
						while ((self.mBuffer[self.mCurrPos] == '\r') or (self.mBuffer[self.mCurrPos] == '\n')):
							self.mCurrPos += 1
							if (self.mCurrPos >= len(self.mBuffer)):
								break # end of the file
							self.mCurrLine += 1
					else:
						# Getting token, stop here, leave pointer at newline...
						cont = 0
				else:
					cont = 0 # do not continue
			elif (c == '\"'):
				# Quoted token
				if currPos != 0:
					print "ERROR: Quotes must be at beginning of token! (line : %d)" % (self.mCurrLine)
				
				startLine = self.mCurrLine
				self.mCurrPos += 1
				if (self.mBuffer[self.mCurrPos] == "\""):
					# Empty quote, set currPos to 1 to prevent the tokenizer from
					# thinking we failed. 
					currPos = 1
					
				while (self.mBuffer[self.mCurrPos] != '\"'):
					if self.mCurrPos >= len(self.mBuffer):
						print "End of file before quote closed.  Quote started: (line : %d)" % startLine
					if (self.mBuffer[self.mCurrPos] == '\n') or (self.mBuffer[self.mCurrPos] == '\r'):
						print "End of line reached before end of quote.  Quote started: (line : %d)" % startLine
					self.mCurrToken = self.mCurrToken + self.mBuffer[self.mCurrPos]
					self.mCurrPos += 1 # Advance buffer pos
					currPos += 1 # Advance token pos
				self.mCurrPos += 1 # Advance past the last "
				cont = 0
			elif (c == '/') and (self.mBuffer[self.mCurrPos+1] == '/'):
				# Line quote...
				if currPos != 0:
					cont = 0 # let crossLine determine on next pass
					# continue to end of line
				while (self.mCurrPos < len(self.mBuffer)) and (self.mBuffer[self.mCurrPos] != '\n') and (self.mBuffer[self.mCurrPos] != '\r'):
					self.mCurrPos += 1
			else:
				self.mCurrToken = self.mCurrToken + c
				currPos += 1
				self.mCurrPos += 1
			
			if cont == 0: # break if not continuing
				break
		# Return an appropriate value
		if currPos > 0: return 1
		else: return 0
		
	def getToken(self):
		return self.mCurrToken

# Dump print functions
dump_file = None

def dump_setout(filename="stdout"):
	global dump_file
	if filename == "stdout":
		if dump_file != None: dump_file.close()
		dump_file = None
		print "Dumping output to console"
	else:
		dump_file = open(filename, "w")
		print "Dumping output to file '%s'" % filename

def dump_finish():
	if dump_file != None:
		dump_file.flush()
	#dump_file.close()
	

def dump_write(string):
	if dump_file != None:
		dump_file.write("%s " % string)
	else:
		print string,

def dump_writeln(string):
	dump_write("%s\n" % string)

# Function to ensure all delete operations are called on objects in a list
def clearArray(array):
	while len(array) != 0:
		del array[0]
	del array

# Subtracts one bool array from another
def subtractSet(arr1, arr2):
	for i in range(0, len(arr2)):
		if arr2[i]:
			arr1[i] = False
	return arr1

# Determines if all items on a list are true
def allSet(arr):
	for a in arr:
		if not a: return False
	return True

# Overlaps two lists
def overlapSet(arr1, arr2):
	for i in range(0, len(arr2)):
		if arr2[i]:
			arr1[i] = True
	return arr1
	
# Strip image names of trailing extension
def stripImageExtension(filename):
	imageExts = ['jpg', 'jpeg', 'gif', 'png', 
		     'tif', 'tiff', 'mpg', 'mpeg',
		     'tga', 'pcx', 'xcf', 'pix',
		     'eps', 'fit', 'fits', 'jpe',
		     'ico', 'pgm', 'psd', 'ps',
		     'ppm', 'bmp', 'pcc', 'xbm',
		     'xpm', 'xwd', 'bitmap']
	temp = string.split(filename,".")	
	if len(temp)==1: return temp[0]
	retVal = ""
	for i in range(0, len(temp)):
		if not temp[i].lower() in imageExts:
			retVal += (temp[i] + ".")
	retVal = retVal[0:len(retVal)-1] # remove trailing "."
	return retVal
