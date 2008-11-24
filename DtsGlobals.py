
'''
DtsGlobals.py
Copyright (c) 2003 - 2008 James Urquhart(j_urquhart@btinternet.com)

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



'''
  Blender Exporter For Torque
-------------------------------
  Blender Dts Classes for Python
'''

#Version = "0.97 Beta1"
Version = "0.97"
Prefs = None
SceneInfo = None
Prefs_keyname = ""
export_tree = None
Debug = False
Profiling = False
pathSeparator = "/"
textDocName = "TorqueExporter_SCONF2"

# these types never contain exportable geometry
neverGeometryTypes = ['Empty', 'Camera', 'Lamp', 'Lattice', 'Armature']
# these types are always assumed to contain faces (exportable geometry)
alwaysGeometryTypes = ['Mesh', 'Text', 'MBall']
# we need to test these types to see if they actually have faces and not just verts
testGeometryTypes = ['Surf', 'Curve']
# we need to get the display data for the following types
needDisplayDataTypes = ['Surf', 'Curve', 'Text', 'MBall']


tracebackImported = True
try:
	import traceback
except:
	print "Could not import exception traceback module."
	tracebackImported = False


# utility methods

# gets the text portion of a string (with a trailing number)
def getTextPortion(string):
	for i in range(len(string)-1, -1, -1):
		if string[i].isalpha(): break
	retVal = string[0:i+1]
	return retVal

# gets a trailing number in a string
def getTrailingNumber(string):
	for i in range(len(string)-1, -1, -1):
		if string[i].isalpha(): break
	retVal = int(string[i+1:len(string)])
	return retVal


