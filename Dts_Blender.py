#!BPY

"""
Name: 'Torque Shape (.dts)...'
Blender: 241
Group: 'Export'
Tooltip: 'Export to Torque (.dts) format.'
"""

'''
Dts_Blender.py
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

import DTSPython
from DTSPython import *
import Blender
from Blender import *
import Common_Gui
import string, math, re, gc

import DtsShape_Blender
from DtsShape_Blender import *


import os.path

tracebackImported = True
try:
	import traceback	
except:
	print "Could not import exception traceback module."
	tracebackImported = False


'''
  Blender Exporter For Torque
-------------------------------
  Blender Dts Classes for Python
'''

Version = "0.952 (IFL Branch)"
Prefs = None
Prefs_keyname = ""
export_tree = None
Debug = True
Profiling = False
textDocName = "TorqueExporter_SCONF"
pathSeperator = "/"



'''
Utility Functions
'''
#-------------------------------------------------------------------------------------------------
# Gets the Base Name from the File Path
def basename(filepath):
	if "\\" in filepath:
		words = string.split(filepath, "\\")
	else:
		words = string.split(filepath, "/")
	words = string.split(words[-1], ".")
	return string.join(words[:-1], ".")

# Gets base path with trailing /
def basepath(filepath):
	if "\\" in filepath: sep = "\\"
	else: sep = "/"
	words = string.split(filepath, sep)
	return string.join(words[:-1], sep)
	
def getPathSeperator(filepath):
	global pathSeperator
	if "\\" in filepath: pathSeperator = "\\"
	else: pathSeperator = "/"

# Gets the Base Name & path from the File Path
def noext(filepath):
	words = string.split(filepath, ".")
	if len(words)==1: return filepath
	return string.join(words[:-1], ".")

# Gets the children of an object
def getChildren(obj):
	return filter(lambda x: x.parent==obj, Blender.Object.Get())

# Gets all the children of an object (recursive)
def getAllChildren(obj):
	obj_children = getChildren(obj)
	for child in obj_children[:]:
		obj_children += getAllChildren(child)
	return obj_children

# converts a file name into a legal python variable name.
# this is need for blender registry support.
def pythonizeFileName(filename):
	# replace all non-alphanumeric chars with _
	p = re.compile('\W')
	return p.sub('_', filename)


'''
	Preferences Code
'''

def initPrefs():
	Prefs = {}
	Prefs['Version'] = 96 # NOTE: change version if anything *major* is changed.
	Prefs['DTSVersion'] = 24
	Prefs['WriteShapeScript'] = False
	Prefs['Sequences'] = {}
	Prefs['PrimType'] = 'Tris'
	Prefs['MaxStripSize'] = 6
	Prefs['ClusterDepth'] = 1
	Prefs['AlwaysWriteDepth'] = False
	Prefs['Billboard'] = {'Enabled' : False,'Equator' : 10,'Polar' : 10,'PolarAngle' : 25,'Dim' : 64,'IncludePoles' : True, 'Size' : 20.0}
	Prefs['BannedBones'] = []
	Prefs['CollapseRootTransform'] = True
	Prefs['TSEMaterial'] = False
	Prefs['exportBasename'] = basename(Blender.Get("filename"))
	Prefs['exportBasepath'] = basepath(Blender.Get("filename"))
	Prefs['LastActivePanel'] = 'Sequences'
	Prefs['LastActiveSubPanel'] = 'Common'
	return Prefs

# Loads preferences
def loadPrefs():
	global Prefs, Prefs_keyname, textDocName
	Prefs_keyname = 'TorqueExporterPlugin_%s' % pythonizeFileName(basename(Blender.Get("filename")))
	Prefs = Registry.GetKey(Prefs_keyname, True)
	if not Prefs:
		#Torque_Util.dump_writeln("Registry key '%s' could not be loaded, resorting to text object." % Prefs_keyname)
		Prefs = initPrefs()
		
		success = True
		newConfig = True
		try: text_doc = Text.Get(textDocName)
		except:
			# User hasn't updated yet?
			newConfig = False
			try: text_doc = Text.Get("TORQUEEXPORTER_CONF")
			except: 
				success = False
				
		if not success:
			# No registry, no text, so need a new Prefs
			print "No Registry and no text objects, must be new."
		else:
			# Ok, so now we can load the text document
			if newConfig:
				# Go ahead and load the stuff from the text buffer
				execStr = "loadPrefs = "
				for line in text_doc.asLines():
					execStr += line
				try:
					exec(execStr)
				except:
					return False
					
				Prefs = loadPrefs
				
				# make sure the output path is valid.
				if not os.path.exists(Prefs['exportBasepath']):
					Prefs['exportBasepath'] = basepath(Blender.Get("filename"))
				savePrefs()
				return True
			else:
				print "Error: failed to load old preferences!"
				print " To generate new preferences, delete the TorqueExporter_SCONF"
				print " text buffer, then save and reload the .blend file."
				return False
				# We'll leave it up to the user to delete the text object
		
		Torque_Util.dump_writeln("Loaded Preferences.")
		# Save prefs (to update text and registry versions)
		savePrefs()

	# make sure the output path is valid.
	if not os.path.exists(Prefs['exportBasepath']):
		Prefs['exportBasepath'] = basepath(Blender.Get("filename"))
	

		
# Saves preferences to registry and text object
def savePrefs():
	global Prefs, Prefs_keyname
	Registry.SetKey(Prefs_keyname, Prefs, False) # must NOT cache the data to disk!!!
	saveTextPrefs()

# Saves preferences to a text buffer
def saveTextPrefs():
	global Prefs, textDocName
	# We need a blank buffer
	try: text_doc = Text.Get(textDocName)
	except: text_doc = Text.New(textDocName)
	text_doc.clear()
	
	# Use python's amazing str() function to create a string based
	# representation of the config dictionary
	text_doc.write(str(Prefs))


dummySequence =	\
{
	'Dsq': False,
	'Cyclic': False,
	'NoExport': False,
	'Priority': 0,
	'TotalFrames': 0,
	'Duration': 1,
	'FPS': 25,
	'DurationLocked': False,
	'FPSLocked': True
}

# Gets a sequence key from the preferences
# Creates default if key does not exist
# this function needs to be updated whenever the structure of the preferences changes
def getSequenceKey(value):	
	global Prefs, dummySequence
	if value == "N/A":
		return dummySequence.copy()
	try:
		return Prefs['Sequences'][value]	
	except KeyError:
		# create a copy of the dummy sequence
		Prefs['Sequences'][value] = dummySequence.copy()

		# and set everything that needs a default
		Prefs['Sequences'][value]['Triggers'] = [] # [State, Time, On]
		Prefs['Sequences'][value]['Action'] = {'Enabled': False,'NumGroundFrames': 0,'BlendRefPoseAction': None,'BlendRefPoseFrame': 8,'FrameSamples': 0,'Blend': False}
		Prefs['Sequences'][value]['IFL'] = { 'Enabled': False,'Material': None,'NumImages': 0,'TotalFrames': 0,'IFLFrames': [], 'WriteIFLFile': True}
		Prefs['Sequences'][value]['Vis'] = { 'Enabled': False,'StartFrame': 1,'EndFrame': 1, 'Tracks':{}}
		Prefs['Sequences'][value]['Action']['Enabled'] = True

		try:
			action = Blender.Armature.NLA.GetActions()[value]
			maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
		except KeyError:
			Prefs['Sequences'][value]['Action']['Enabled'] = False
			maxNumFrames = 0
		except:
			Prefs['Sequences'][value]['Action']['Enabled'] = False
			maxNumFrames = 0		

		Prefs['Sequences'][value]['Action']['StartFrame'] = 1
		Prefs['Sequences'][value]['Action']['EndFrame'] = maxNumFrames
		Prefs['Sequences'][value]['Action']['AutoSamples'] = True
		Prefs['Sequences'][value]['Action']['AutoFrames'] = True
		Prefs['Sequences'][value]['Action']['FrameSamples'] = maxNumFrames
		Prefs['Sequences'][value]['Action']['NumGroundFrames'] = 0

		# default reference pose for blends is in the middle of the same action
		Prefs['Sequences'][value]['Action']['BlendRefPoseAction'] = value			
		Prefs['Sequences'][value]['Action']['BlendRefPoseFrame'] = maxNumFrames/2
		Prefs['Sequences'][value]['Priority'] = 0
		return Prefs['Sequences'][value]

# Creates an independent copy of a sequence key
# this function needs to be updated whenever the structure of the preferences changes
def copySequenceKey(value):
	global Prefs, dummySequence
	retVal = dummySequence.copy()

	# global sequence stuff
	retVal['Dsq'] = Prefs['Sequences'][value]['Dsq']
	retVal['Cyclic'] = Prefs['Sequences'][value]['Cyclic']
	retVal['NoExport'] = Prefs['Sequences'][value]['NoExport']
	retVal['Priority'] = Prefs['Sequences'][value]['Priority']
	retVal['TotalFrames'] = Prefs['Sequences'][value]['TotalFrames']
	retVal['Duration'] = Prefs['Sequences'][value]['Duration']
	retVal['FPS'] = Prefs['Sequences'][value]['FPS']
	retVal['DurationLocked'] = Prefs['Sequences'][value]['DurationLocked']
	retVal['FPSLocked'] = Prefs['Sequences'][value]['FPSLocked']
	# Create anything that cannot be copied (reference objects like lists)
	retVal['Triggers'] = []
	# copy triggers
	for entry in Prefs['Sequences'][value]['Triggers']:
		retVal['Triggers'].append([])
		for item in entry:
			retVal['Triggers'][-1].append(item)
			

	# copy action key
	retVal['Action'] = {}
	retVal['Action']['Enabled'] = Prefs['Sequences'][value]['Action']['Enabled']
	retVal['Action']['StartFrame'] = Prefs['Sequences'][value]['Action']['StartFrame']
	retVal['Action']['EndFrame'] = Prefs['Sequences'][value]['Action']['EndFrame']
	retVal['Action']['AutoSamples'] = Prefs['Sequences'][value]['Action']['AutoSamples']
	retVal['Action']['AutoFrames'] = Prefs['Sequences'][value]['Action']['AutoFrames']
	retVal['Action']['FrameSamples'] = Prefs['Sequences'][value]['Action']['FrameSamples']
	retVal['Action']['NumGroundFrames'] = Prefs['Sequences'][value]['Action']['NumGroundFrames']
	retVal['Action']['BlendRefPoseAction'] = Prefs['Sequences'][value]['Action']['BlendRefPoseAction']
	retVal['Action']['BlendRefPoseFrame'] = Prefs['Sequences'][value]['Action']['BlendRefPoseFrame']
	retVal['Action']['Blend'] = Prefs['Sequences'][value]['Action']['Blend']



	# copy IFL key
	retVal['IFL'] = {}
	retVal['IFL']['Enabled'] = Prefs['Sequences'][value]['IFL']['Enabled']
	retVal['IFL']['Material'] = Prefs['Sequences'][value]['IFL']['Material']
	retVal['IFL']['NumImages'] = Prefs['Sequences'][value]['IFL']['NumImages']
	retVal['IFL']['TotalFrames'] = Prefs['Sequences'][value]['IFL']['TotalFrames']
	retVal['IFL']['WriteIFLFile'] = Prefs['Sequences'][value]['IFL']['WriteIFLFile']
	# copy IFL Frames
	retVal['IFL']['IFLFrames'] = []
	for entry in Prefs['Sequences'][value]['IFL']['IFLFrames']:
		retVal['IFL']['IFLFrames'].append([])
		for item in entry:
			retVal['IFL']['IFLFrames'][-1].append(item)
	
	# copy Vis key
	retVal['Vis'] = {}
	retVal['Vis']['Enabled'] = Prefs['Sequences'][value]['Vis']['Enabled']
	retVal['Vis']['StartFrame'] = Prefs['Sequences'][value]['Vis']['StartFrame']
	retVal['Vis']['EndFrame'] = Prefs['Sequences'][value]['Vis']['EndFrame']
	# copy visibility tracks
	retVal['Vis']['Tracks'] = {}
	for trackName in Prefs['Sequences'][value]['Vis']['Tracks'].keys():
		retVal['Vis']['Tracks'][trackName] = {}
		retVal['Vis']['Tracks'][trackName]['hasVisTrack'] = Prefs['Sequences'][value]['Vis']['Tracks'][trackName]['hasVisTrack']
		retVal['Vis']['Tracks'][trackName]['IPOType'] = Prefs['Sequences'][value]['Vis']['Tracks'][trackName]['IPOType']
		retVal['Vis']['Tracks'][trackName]['IPOChannel'] = Prefs['Sequences'][value]['Vis']['Tracks'][trackName]['IPOChannel']
		retVal['Vis']['Tracks'][trackName]['IPOObject'] = Prefs['Sequences'][value]['Vis']['Tracks'][trackName]['IPOObject']

	return retVal

# Cleans up extra sequence keys that may not be used anymore (e.g. action deleted)
# also calls cleanVisTracks to get rid of unused visibility tracks
def cleanKeys():
	global Prefs
	# clean visibility tracks
	cleanVisTracks()
	# Sequences
	for keyName in Prefs['Sequences'].keys():
		key = getSequenceKey(keyName)
		actionFound = False
		try: actEnabled = key['Action']['Enabled']
		except: actEnabled = False
		# if action is enabled for the sequence
		if actEnabled:
			for actionName in Armature.NLA.GetActions().keys():
				if actionName == keyName:
					# we found a (hopefully) valid action
					actionFound = True
					break
		# if we didn't find a valid action
		if not actionFound:
			key['Action']['Enabled'] = False
			# see if any of the other sequence types are enabled
			VisFound = False
			IFLFound = False
			try: IFLFound = Prefs['Sequences'][keyName]['IFL']['Enabled']
			except: IFLFound = False
			try: VisFound = Prefs['Sequences'][keyName]['Vis']['Enabled']
			except: VisFound = False
			# if no sequence type is enabled for the key, get rid of it.
			if VisFound == False and IFLFound == False:
				del Prefs['Sequences'][keyName]

# Cleans up unused visibility tracks
def cleanVisTracks():
	global Prefs
	for keyName in Prefs['Sequences'].keys():
		key = getSequenceKey(keyName)
		VisFound = False
		try: VisFound = key['Vis']['Enabled']
		except: VisFound = False
		if not VisFound: continue
		visKey = key['Vis']
		# check each track in the prefs and see if it's enabled.
		# if it's not enabled, get rid of the track key.
		for trackName in visKey['Tracks'].keys():
			track = visKey['Tracks'][trackName]
			try: hasTrack = track['hasVisTrack']
			except: hasTrack = False
			if not hasTrack:
				del Prefs['Sequences'][keyName]['Vis']['Tracks'][trackName]
		


# Creates action keys that don't already exist
def createActionKeys():
	for action in Blender.Armature.NLA.GetActions().keys():
		getSequenceKey(action)


# Intelligently renames sequence keys.
def renameSequence(oldName, newName):
	global Prefs
	seq = Prefs['Sequences'][oldName]

	# Are we merging two sequences together?
	try: 
		newSeq = Prefs['Sequences'][newName]
		# above line should throw and excepting if the new sequence name
		# does not already exist.
		
		# Copy IFL and Vis data to the existing sequence, and
		# delete the old sequence.
		if (not newSeq['IFL']['Enabled']) and Prefs['Sequences'][oldName]['IFL']['Enabled']:
			newSeq['IFL'] = Prefs['Sequences'][oldName]['IFL']
		if (not newSeq['Vis']['Enabled']) and Prefs['Sequences'][oldName]['Vis']['Enabled']:
			newSeq['Vis'] = Prefs['Sequences'][oldName]['Vis']
		del Prefs['Sequences'][oldName]
	# Nope.
	except:
		# copy the key
		newKey = copySequenceKey(oldName)
		# insert the copied key into the prefs under the new name
		Prefs['Sequences'][newName] = newKey
		# are we splitting the old sequence name from an action?
		# if so, the action continues to exist, but the other animations
		# must go.
		if Prefs['Sequences'][oldName]['Action']['Enabled']:
			# disable the IFL and Vis attributes of the old key
			Prefs['Sequences'][oldName]['IFL']['Enabled'] = False
			Prefs['Sequences'][oldName]['Vis']['Enabled'] = False
		# delete old key
		else:
			del Prefs['Sequences'][oldName]


# Converts an old style visibility sequence to the new prefs format
def importOldVisAnim(seqName, seqPrefs):
		try: x = seqPrefs['Vis']
		except: seqPrefs['Vis'] = {}
		try: x = seqPrefs['Vis']['Enabled']
		except:
			seqPrefs['Vis']['Enabled'] = seqPrefs['AnimateMaterial']
			del seqPrefs['AnimateMaterial']
		try: x = seqPrefs['Vis']['StartFrame']
		except:			
			seqPrefs['Vis']['StartFrame'] = seqPrefs['MaterialIpoStartFrame']
			try:
				action = Blender.Armature.NLA.GetActions()[seqName]
				seqPrefs['Vis']['EndFrame'] = (seqPrefs['Vis']['StartFrame'] + DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False))-1
			except:
				seqPrefs['Vis']['EndFrame'] = seqPrefs['Vis']['StartFrame']
			del seqPrefs['MaterialIpoStartFrame']
		try: x = seqPrefs['Vis']['Tracks']
		except:
			# todo - set up tracks automatically for old style vis sequences.
			seqPrefs['Vis']['Tracks'] = {}
			if not seqPrefs['Vis']['Enabled']: return
			
			# make a list of blender materials with alpha IPOs
			IPOMatList = []
			for mat in Blender.Material.Get():
				ipo = mat.getIpo()
				if ipo == None:	continue
				alphaFound = False
				for curve in ipo:
					print mat.name, ":",curve.name
					if curve.name != "Alpha": contrinue
					alphaFound = True
					IPOMatList.append(mat.name)
					break
			print IPOMatList

			# check an arbitrary poly in each mesh (in highest dl) to see if we can find a material in the list
			shapeTree = export_tree.find("SHAPE")
			if shapeTree == None: return
			# find the highest detail level.
			highest = 0
			for marker in getChildren(shapeTree.obj):
				if marker.name[0:6].lower() != "detail": continue
				numPortion = int(marker.name[6:len(marker.name)])
				if numPortion > highest: highest = numPortion
			markerName = "detail" + str(numPortion)
			for marker in getChildren(shapeTree.obj):
				if marker.name.lower() != markerName: continue
				# loop through all objects, and sort into two lists
				for obj in getAllChildren(marker):
					if obj.getType() != "Mesh": continue
					if obj.name == "Bounds": continue
					# process mesh objects
					objData = obj.getData()
					# Does the mesh that use this material?
					if len(objData.faces) < 1: continue
					if len(objData.materials) <= objData.faces[0].mat: continue
					matName = objData.materials[objData.faces[0].mat].name
					print objData.materials[objData.faces[0].mat].name
					# if so, create a vis track for the object.
					if not (matName in IPOMatList): continue
					# if we made it here, it should be OK to create the track.
					print "Creating track for",obj.name
					seqPrefs['Vis']['Tracks'][obj.name] = {}
					seqPrefs['Vis']['Tracks'][obj.name]['hasVisTrack'] = True
					seqPrefs['Vis']['Tracks'][obj.name]['IPOType'] = 'Material'
					seqPrefs['Vis']['Tracks'][obj.name]['IPOChannel'] = 'Alpha'
					seqPrefs['Vis']['Tracks'][obj.name]['IPOObject'] = matName


# Converts all old preferences to the new format.
def updateOldPrefs():
	global Prefs

	try: x = Prefs['LastActivePanel']
	except: Prefs['LastActivePanel'] = 'Sequences'
	try: x = Prefs['LastActiveSubPanel']
	except: Prefs['LastActiveSubPanel'] = 'Common'

	for seqName in Prefs['Sequences'].keys():
		seq = getSequenceKey(seqName)


		# Do the really old stuff first
		try: x = seq['Priority']
		except: seq['Priority'] = 0

		# Move keys into the new "Action" subkey.and delete old keys
		try: x = seq['Action']
		except:
			seq['Action'] = {}
		actKey = seq['Action']
		try: x = actKey['Enabled']
		except: 
			actKey['Enabled'] = True

		try: x = actKey['StartFrame']
		except: actKey['StartFrame'] = 1
		
		try: x = actKey['EndFrame']
		except:
			try:
				action = Blender.Armature.NLA.GetActions()[seqName]
				actKey['EndFrame'] = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
			except:
				actKey['EndFrame'] = 0
		try: x = actKey['AutoFrames']
		except: actKey['AutoFrames'] = True

		try: x = actKey['AutoSamples']
		except: actKey['AutoSamples'] = True
		try: x = actKey['FrameSamples']
		except:
			try: actKey['FrameSamples'] = actKey['InterpolateFrames']
			except:
				try: actKey['FrameSamples'] = seq['InterpolateFrames']
				except: actKey['FrameSamples'] = getNumActFrames(seqName, seq)
			try: del actKey['InterpolateFrames']
			except:
				try: del seq['InterpolateFrames']
				except: pass
		try: x = actKey['NumGroundFrames']
		except:
			actKey['NumGroundFrames'] = seq['NumGroundFrames']
			del seq['NumGroundFrames']
		try: x = actKey['Blend']
		except:
			actKey['Blend'] = seq['Blend']
			del seq['Blend']
		try: x = actKey['BlendRefPoseAction']
		except:
			actKey['BlendRefPoseAction'] = seq['BlendRefPoseAction']
			del seq['BlendRefPoseAction']
		try: x = actKey['BlendRefPoseFrame']
		except:
			actKey['BlendRefPoseFrame'] = seq['BlendRefPoseFrame']
			del seq['BlendRefPoseFrame']
		
		importOldVisAnim(seqName, seq)
		
		try: x = seq['TotalFrames']
		except: seq['TotalFrames'] = 0

		try: x = seq['FPS']
		except:
			print "Sequence FPS not found..."
			try:
				seq['FPS'] = float(Blender.Scene.GetCurrent().getRenderingContext().framesPerSec())
				if seq['FPS'] == 0: seq['FPS'] = 25
			except:
				seq['FPS'] = 25
			print "Sequence FPS was set to:",seq['FPS']
		try: x = seq['Duration']		
		except:
			maxNumFrames = 0
			try:
				action = Blender.Armature.NLA.GetActions()[seqName]
				maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
			except KeyError:
				maxNumFrames = 0			
			#seq['Duration'] = float(Torque_Util.getSeqNumFrames(seqName, seq)) / float(seq['FPS'])
			#print "You are here..."
			#try: seq['Duration'] = float(Torque_Util.getSeqNumFrames(seqName, seq)) / float(seq['FPS'])
			try: seq['Duration'] = float(maxNumFrames) / float(seq['FPS'])
			except:
				print "Could not determine sequence duration!!!"
				seq['Duration'] = 1.0
				seq['FPS'] = 1.0
		try: x = seq['DurationLocked']
		except: seq['DurationLocked'] = False
		try: x = seq['FPSLocked']
		except: seq['FPSLocked'] = True


	# loop through all actions in the preferences and add the 'IFL' key to them with some reasonable default values.
	for seqName in Prefs['Sequences'].keys():
		seq = getSequenceKey(seqName)
		try: x = seq['IFL']
		except KeyError:
			seq['IFL'] = {}
			seq['IFL']['Enabled'] = False
			seq['IFL']['Material'] = None
			seq['IFL']['NumImages'] = 0
			seq['IFL']['TotalFrames'] = 0
			seq['IFL']['IFLFrames'] = []
			seq['IFL']['WriteIFLFile'] = True


'''
	Class to handle the 'World' branch
'''
#-------------------------------------------------------------------------------------------------
class SceneTree:
	# Creates trees to handle children
	def handleChild(self,obj):
		tname = string.split(obj.getName(), ":")[0]
		if tname.upper()[0:5] == "SHAPE":
			handle = ShapeTree(self, obj)
		else:
			return None
		return handle

	def __init__(self,parent=None,obj=None):
		self.obj = obj
		self.parent = parent
		self.children = []
		if obj != None:
			self.handleObject()

	def __del__(self):
		self.clear()
		del self.children

	# Performs tasks to handle this object, and its children
	def handleObject(self):
		# Go through children and handle them
		for c in Blender.Object.Get():
			if c.getParent() != None: continue
			self.children.append(self.handleChild(c))

	def process(self, progressBar):
		# Process children
		found = False
		for c in self.children:
			if c == None: continue
			found = True
			c.process(progressBar)
		if not found: Torque_Util.dump_writeln("  Error: No Shape Marker found!  See the readme.html file.")

	def getChild(self, name):
		for c in self.children:
			if c.getName() == name:
				return c
		return None

	def getName(self):
		return "SCENETREE"
		
	def find(self, name):
		for c in self.children:
			if c == None: continue
			if c.getName() == name:
				return c
		for c in self.children:
			if c == None: continue
			ret = c.find(name)
			if ret: return ret
		return None

	# Clears out tree
	def clear(self):
		try:
			while len(self.children) != 0:
				if self.children[0] != None:
					self.children[0].clear()
				del self.children[0]
		except: pass

'''
	Shape Handling code
'''
#-------------------------------------------------------------------------------------------------

class ShapeTree(SceneTree):
	def __init__(self,parent=None,obj=None):
		self.Shape = None
		
		self.normalDetails = []
		self.collisionMeshes = []
		self.losCollisionMeshes = []
		
		SceneTree.__init__(self,parent,obj)

	def handleChild(self, obj):
		# Process marker (detail level) nodes
		tname = obj.getName()
		if tname[0:6].upper() == "DETAIL":
			if len(tname) > 6: size = int(tname[6:])
			else: size = -1
			self.normalDetails.append([size, obj])
		elif (tname[0:3].upper() == "COL") or (tname[0:9].upper() == "COLLISION"):
			self.collisionMeshes.append(obj)
			if tname[0:9].upper() != "COLLISION":
				Torque_Util.dump_writeln("Warning: 'COL' designation for collision node deprecated, use 'COLLISION' instead.")
		elif (tname[0:3].upper() == "LOS") or (tname[0:20].upper() == "LOSCOLLISION"):
			self.losCollisionMeshes.append(obj)
			if tname[0:12].upper() != "LOSCOLLISION":
				Torque_Util.dump_writeln("Warning: 'LOS' designation for los collision node deprecated, use 'LOSCOLLISION' instead.")
		else:
			# Enforce proper organization
			Torque_Util.dump_writeln("     Warning: Could not accept child %s on shape %s" % (obj.getName(),self.obj.getName()))
			return None
		return obj

	def process(self, progressBar):
		global Debug
		global Prefs
		# Set scene frame to 1 in case we have any problems
		Scene.GetCurrent().getRenderingContext().currentFrame(1)
		try:
			# double check the base path before opening the stream
			if not os.path.exists(Prefs['exportBasepath']):
				Prefs['exportBasepath'] = basepath(Blender.Get("filename"))
			# make sure our path seperator is correct.
			getPathSeperator(Prefs['exportBasepath'])
			Stream = DtsStream("%s%s%s.dts" % (Prefs['exportBasepath'], pathSeperator, Prefs['exportBasename']), False, Prefs['DTSVersion'])
			Torque_Util.dump_writeln("Writing shape to  '%s'." % ("%s\\%s.dts" % (Prefs['exportBasepath'], Prefs['exportBasename'])))
			# Now, start the shape export process if the Stream loaded
			if Stream.fs:
				self.Shape = BlenderShape(Prefs)
				Torque_Util.dump_writeln("Processing...")
				
				# Import child objects
				if len(self.children) != 0:
					'''
					This part of the routine is split up into 4 sections:
					
					1) Get armatures from base details and add them.
					2) Add every single thing from the base details that isn't an armature or special object.
					3) Add the billboard detail, if required.
					4) Add every single collision mesh we can find.
					'''
					progressBar.pushTask("Importing Objects...", len(self.children), 0.4)
					
					# Collect everything into bins...
					meshDetails = []
					armatures = []
					nodes = []
					for detail in self.normalDetails:
						meshList = []
						for child in getAllChildren(detail[1]):
							if child.getType() == "Armature":
								# Need to ensure we only add one instance of an armature datablock
								for arm in armatures:
									#if arm.getData().getName() == child.getData().getName():
									if arm.getData().name == child.getData().name:
										progressBar.update()
										continue
								armatures.append(child)
							elif child.getType() == "Camera":
								# Treat these like nodes
								nodes.append(child)
							elif child.getType() == "Mesh":
								meshList.append(child)
							elif child.getType() == "Empty":
								# Anything we need here?
								progressBar.update()
								continue
							else:
								Torque_Util.dump_writeln("Warning: Unhandled object '%s'" % child.getType())
								progressBar.update()
								continue
								
						meshDetails.append(meshList)
					
					# Now we can add it in order
					for arm in armatures:
						self.Shape.addArmature(arm, Prefs['CollapseRootTransform'])
						progressBar.update()
						
					for n in nodes:
						self.Shape.addNode(n)
						progressBar.update()
						
					for i in range(0, len(self.normalDetails)):
						self.Shape.addDetailLevel(meshDetails[i], self.normalDetails[i][0])
						progressBar.update()
					curSize = -1
					for marker in self.collisionMeshes:
						meshes = getAllChildren(marker)
						self.Shape.addCollisionDetailLevel(meshes, False, curSize)
						curSize -= 1
						progressBar.update()					
					curSize = -1
					for marker in self.losCollisionMeshes:
						meshes = getAllChildren(marker)
						self.Shape.addCollisionDetailLevel(meshes, True, curSize)
						curSize -= 1
						progressBar.update()
					
					# We have finished adding the regular detail levels. Now add the billboard if required.
					if Prefs['Billboard']['Enabled']:
						self.Shape.addBillboardDetailLevel(0,
							Prefs['Billboard']['Equator'],
							Prefs['Billboard']['Polar'],
							Prefs['Billboard']['PolarAngle'],
							Prefs['Billboard']['Dim'],
							Prefs['Billboard']['IncludePoles'],
							Prefs['Billboard']['Size'])
					
					progressBar.popTask()
				
				progressBar.pushTask("Finalizing Geometry..." , 2, 0.6)
				# Finalize static meshes, do triangle strips
				self.Shape.finalizeObjects()
				self.Shape.finalizeMaterials()
				progressBar.update()
				if Prefs['PrimType'] == "TriStrips":
					self.Shape.stripMeshes(Prefs['MaxStripSize'])
				progressBar.update()
				
				# Add all actions (will ignore ones not belonging to shape)
				scene = Blender.Scene.GetCurrent()
				context = scene.getRenderingContext()
				actions = Armature.NLA.GetActions()

				# check the armatures to see if any are locked in rest position
				for armOb in Blender.Object.Get():
					if (armOb.getType() != 'Armature'): continue
					if armOb.getData().restPosition:
						Blender.Draw.PupMenu("Warning%t|One or more of your armatures is locked into rest position. This will cause problems with exported animations.")
						break

				# Process sequences
				seqKeys = Prefs['Sequences'].keys()
				if len(seqKeys) > 0:
					progressBar.pushTask("Adding Sequences..." , len(seqKeys*4), 0.8)
					for seqName in seqKeys:
						seqKey = getSequenceKey(seqName)

						# does the sequence have anything to export?
						if (seqKey['NoExport']) or not (seqKey['Action']['Enabled'] or seqKey['IFL']['Enabled'] or seqKey['Vis']['Enabled']):
							progressBar.update()
							progressBar.update()
							progressBar.update()
							progressBar.update()
							continue
						
						# try to add the sequence
						try: action = actions[seqName]
						except: action = None
						sequence = self.Shape.addSequence(seqName, context, seqKey, scene, action)
						if sequence == None:
							Torque_Util.dump_writeln("Warning : Couldn't add action '%s' to shape!" % seqName)
							progressBar.update()
							progressBar.update()
							progressBar.update()
							progressBar.update()
							continue
						progressBar.update()

						# Pull the triggers
						if len(seqKey['Triggers']) != 0:
							self.Shape.addSequenceTriggers(sequence, seqKey['Triggers'], getSeqNumFrames(seqName, seqKey))
						progressBar.update()
						progressBar.update()						

						# Hey you, DSQ!
						if seqKey['Dsq']:
							self.Shape.convertAndDumpSequenceToDSQ(sequence, "%s/%s.dsq" % (Prefs['exportBasepath'], seqName), Stream.DTSVersion)
							Torque_Util.dump_writeln("Loaded and dumped sequence '%s' to '%s/%s.dsq'." % (seqName, Prefs['exportBasepath'], seqName))
						else:
							Torque_Util.dump_writeln("Loaded sequence '%s'." % seqName)

						# Clear out matters if we don't need them
						if not sequence.has_loc: sequence.matters_translation = []
						if not sequence.has_rot: sequence.matters_rotation = []
						if not sequence.has_scale: sequence.matters_scale = []
						progressBar.update()

					progressBar.popTask()

				Torque_Util.dump_writeln("> Shape Details")
				self.Shape.dumpShapeInfo()
				progressBar.update()
				progressBar.popTask()

				# Now we've finished, we can save shape and burn it.
				progressBar.pushTask("Writing out DTS...", 1, 0.9)
				Torque_Util.dump_writeln("Writing out DTS...")
				self.Shape.finalize(Prefs['WriteShapeScript'])
				self.Shape.write(Stream)
				Torque_Util.dump_writeln("Done.")
				progressBar.update()
				progressBar.popTask()

				Stream.closeStream()
				del Stream
				del self.Shape
			else:
				Torque_Util.dump_writeln("Error: failed to open shape stream!")
				del self.Shape
				progressBar.popTask()
				return None
		except Exception, msg:
			Torque_Util.dump_writeln("Error: Exception encountered, bailing out.")
			Torque_Util.dump_writeln(Exception)
			if tracebackImported:
				print "Dumping traceback to log..."
				Torque_Util.dump_writeln(traceback.format_exc())
			Torque_Util.dump_setout("stdout")
			if self.Shape: del self.Shape
			progressBar.popTask()
			raise

	# Handles the whole branch
	def handleObject(self):
		global Prefs
		self.clear() # clear just in case we already have children
		
		if len(self.normalDetails) > 0: del self.normalDetails[0:-1]
		if len(self.collisionMeshes) > 0: del self.collisionMeshes[0:-1]
		if len(self.losCollisionMeshes) > 0: del self.losCollisionMeshes[0:-1]

		if len(self.children) > 0: self.clear()

		# Gather metrics on children so we have a better idea of what we are dealing with
		for c in getChildren(self.obj):
			self.children.append(self.handleChild(c))

		# Sort detail level sizes
		self.normalDetails.sort()
		self.normalDetails.reverse()
		
	def getName(self):
		return "SHAPE"
		
	def getShapeBoneNames(self):
		boneList = []
		armBoneList = [] # temp list for bone sorting
		# We need a list of bones for our gui, so find them
		for obj in self.normalDetails:
			for c in getAllChildren(obj[1]):
				if c.getType() == "Armature":
					armBoneList = []
					for bone in c.getData().bones.values():
						armBoneList.append(bone.name)
					# sort each armature's bone list before
					# appending it to the main list.
					armBoneList.sort(lambda x, y: cmp(x.lower(),y.lower()))
					for bone in armBoneList:
						boneList.append(bone)
		return boneList
		
	def find(self, name):
		# Not supported
		return None
	

'''
	Functions to export shape and load script
'''
#-------------------------------------------------------------------------------------------------
def handleScene():
	global export_tree
	Torque_Util.dump_writeln("Processing Scene...")
	# What we do here is clear any existing export tree, then create a brand new one.
	# This is useful if things have changed.
	if export_tree != None: export_tree.clear()
	scn = Blender.Scene.GetCurrent()
	scn.update(1)
	export_tree = SceneTree(None,Blender.Scene.GetCurrent())
	updateOldPrefs()
	Torque_Util.dump_writeln("Cleaning Preference Keys")
	cleanKeys()
	createActionKeys()

def export():
	Torque_Util.dump_writeln("Exporting...")
	print "Exporting..."
	savePrefs()
	
	cur_progress = Common_Gui.Progress()

	if export_tree != None:
		cur_progress.pushTask("Done", 1, 1.0)
		export_tree.process(cur_progress)
		cur_progress.update()
		cur_progress.popTask()
		Torque_Util.dump_writeln("Finished.")
	else:
		Torque_Util.dump_writeln("Error. Not processed scene yet!")
		
	del cur_progress
	print "Finished.  See generated log file for details."
	Torque_Util.dump_finish()
	# Reselect any objects that are currently selected.
	# this prevents a strange bug where objects are selected after
	# export, but behave as if they are not.
	if Blender.Object.GetSelected() != None:
		for ob in Blender.Object.GetSelected():
			ob.select(True)

'''
	Gui Handling Code
'''
#-------------------------------------------------------------------------------------------------

'''
	Gui Init Code
'''

# Controls referenced in functions
guiSequenceTab, guiGeneralTab, guiArmatureTab, guiAboutTab, guiTabBar, guiHeaderTab = None, None, None, None, None, None

SeqCommonControls = None
IFLControls = None
VisControls = None
MaterialControls = None
ActionControls = None
ArmatureControls = None
GeneralControls = None
AboutControls = None


guiSeqActOpts = None
guiSeqActList = None
guiBoneList = None

# Global control event table.  Containers have their own event tables for child controls
globalEvents = Common_Gui.EventTable(1)


# Special callbacks for gui control tabs
def guiBaseCallback(control):
	global Prefs
	global guiSequenceTab, guiArmatureTab, guiMaterialsTab, guiGeneralTab, guiAboutTab, guiTabBar
	global guiSequenceButton, guiMeshButton, guiArmatureButton, guiMaterialsButton, guiAboutButton

	if control.name == "guiExportButton":
		export()
		return

	# Need to associate the button with it's corresponding tab container.
	ctrls = [[guiSequenceButton,guiSequenceTab, "Sequences"],\
	[guiMeshButton,guiGeneralTab, "General"],\
	[guiMaterialsButton,guiMaterialsTab, "Materials"],\
	[guiArmatureButton,guiArmatureTab, "Armature"],\
	[guiAboutButton,guiAboutTab, "About"]]
	for ctrl in ctrls:
		if control.name == ctrl[0].name:
			# turn on the tab button, show and enable the tab container
			control.state = True
			ctrl[1].visible = True
			ctrl[1].enabled = True
			Prefs['LastActivePanel'] = ctrl[2]
			#if ctrl[2] != "Sequences": Prefs['LastActiveSubPanel'] = None
			continue
		# disable all other tab containers and set tab button states to false.
		ctrl[0].state = False
		ctrl[1].visible = False
		ctrl[1].enabled = False
		
def guiSequenceTabsCallback(control):
	global Prefs
	global guiSeqCommonButton, guiSeqActButton, guiSequenceIFLButton, guiSequenceVisibilityButton, guiSequenceUVButton, guiSequenceMorphButton, guiSequenceTabBar
	global guiSeqCommonSubtab, guiSeqActSubtab, guiSequenceIFLSubtab, guiSequenceVisibilitySubtab, guiSequenceUVSubtab, guiSequenceMorphSubtab
	global SeqCommonControls, ActionControls, IFLControls, VisControls
	
	# Need to associate the button with it's corresponding tab container and refresh method
	ctrls = [[guiSeqCommonButton, guiSeqCommonSubtab, SeqCommonControls, "Common"],\
		[guiSeqActButton, guiSeqActSubtab, ActionControls, "Action"],\
		[guiSequenceIFLButton, guiSequenceIFLSubtab, IFLControls, "IFL"],\
		[guiSequenceVisibilityButton, guiSequenceVisibilitySubtab, VisControls, "Visibility"],\
		[guiSequenceUVButton, guiSequenceUVSubtab, None, "TexUV"],\
		[guiSequenceMorphButton, guiSequenceMorphSubtab, None, "Morph"]]
	for ctrl in ctrls:
		if control.name == ctrl[0].name:
			# turn on the tab button, show and enable the tab container
			control.state = True
			ctrl[1].visible = True
			ctrl[1].enabled = True
			if ctrl[2] != None:
				ctrl[2].refreshAll()
			Prefs['LastActiveSubPanel'] = ctrl[3]
			continue
		# disable all other tab containers and set tab button states to false.
		ctrl[0].state = False
		ctrl[1].visible = False
		ctrl[1].enabled = False

def restoreLastActivePanel():
	global Prefs
	global guiSeqCommonButton, guiSeqActButton, guiSequenceIFLButton, guiSequenceVisibilityButton, guiSequenceUVButton, guiSequenceMorphButton, guiSequenceTabBar
	global guiSeqCommonSubtab, guiSeqActSubtab, guiSequenceIFLSubtab, guiSequenceVisibilitySubtab, guiSequenceUVSubtab, guiSequenceMorphSubtab
	global SeqCommonControls, ActionControls, IFLControls, VisControls
	panels =\
	[[guiSequenceButton,guiSequenceTab, "Sequences"],\
	 [guiMeshButton,guiGeneralTab, "General"],\
	 [guiMaterialsButton,guiMaterialsTab, "Materials"],\
	 [guiArmatureButton,guiArmatureTab, "Armature"],\
	 [guiAboutButton,guiAboutTab, "About"]]

	seqSubPanels =\
	[[guiSeqCommonButton, guiSeqCommonSubtab, SeqCommonControls, "Common"],\
	 [guiSeqActButton, guiSeqActSubtab, ActionControls, "Action"],\
	 [guiSequenceIFLButton, guiSequenceIFLSubtab, IFLControls, "IFL"],\
	 [guiSequenceVisibilityButton, guiSequenceVisibilitySubtab, VisControls, "Visibility"],\
	 [guiSequenceUVButton, guiSequenceUVSubtab, None, "TexUV"],\
	 [guiSequenceMorphButton, guiSequenceMorphSubtab, None, "Morph"]]
	
	matchFound = False
	for panel in panels:
		if panel[2] == Prefs['LastActivePanel']:
			# turn on the tab button, show and enable the tab container
			panel[0].state = True
			panel[1].visible = True
			panel[1].enabled = True
			matchFound = True
			continue
		# disable all other tab containers and set tab button states to false.
		panel[0].state = False
		panel[1].visible = False
		panel[1].enabled = False
	if not matchFound:
		guiSequenceButton.state = True
		guiSequenceTab.visible = True
		guiSequenceTab.enabled = True
	
	matchFound = False
	for subPanel in seqSubPanels:
		if subPanel[3] == Prefs['LastActiveSubPanel']:
			# turn on the tab button, show and enable the tab container
			subPanel[0].state = True
			subPanel[1].visible = True
			subPanel[1].enabled = True
			if subPanel[2] != None:
				subPanel[2].refreshAll()
			matchFound = True
			continue			
		# disable all other tab containers and set tab button states to false.
		subPanel[0].state = False
		subPanel[1].visible = False
		subPanel[1].enabled = False
	if not matchFound:
		guiSeqCommonButton.state = True
		guiSeqCommonSubtab.visible = True
		guiSeqCommonSubtab.enabled = True
		SeqCommonControls.refreshAll()

			
# Resize callback for all global gui controls
def guiBaseResize(control, newwidth, newheight):
	tabContainers = ["guiSequenceTab", "guiGeneralTab", "guiArmatureTab", "guiAboutTab", "guiMaterialsTab"]
	tabSubContainers = ["guiSeqCommonSubtab", "guiSeqActSubtab", "guiSequenceIFLSubtab", "guiSequenceVisibilitySubtab","guiSequenceUVSubtab","guiSequenceMorphSubtab", "guiSequenceNLASubtab", "guiMaterialsSubtab", "guiGeneralSubtab", "guiArmatureSubtab", "guiAboutSubtab"]
	
	if control.name == "guiTabBar":
		control.x, control.y = 0, 378
		control.width, control.height = 506, 55
	elif control.name == "guiSequencesTabBar":
		control.x, control.y = 8, 343
		control.width, control.height = 490, 30
	elif control.name in tabContainers:
		control.x, control.y = 0, 0
		control.width, control.height = 506, 378
	elif control.name in tabSubContainers:
		control.x, control.y = 8, 8
		control.width, control.height = 490, 335
	elif control.name == "guiHeaderBar":
		control.x, control.y = 0, newheight - 20
		control.width, control.height = 506, 20
	elif control.name == "guiSequenceButton":
		control.x, control.y = 10, 0
		control.width, control.height = 70, 25
	elif control.name == "guiArmatureButton":
		control.x, control.y = 82, 0
		control.width, control.height = 65, 25
	elif control.name == "guiMaterialsButton":
		control.x, control.y = 149, 0
		control.width, control.height = 60, 25
	elif control.name == "guiMeshButton":
		control.x, control.y = 211, 0
		control.width, control.height = 55, 25
	elif control.name == "guiAboutButton":
		control.x, control.y = 268, 0
		control.width, control.height = 45, 25
	elif control.name == "guiExportButton":
		control.x, control.y = 414, -30
		control.width, control.height = 70, 25
	
	# Sequences sub-tab buttons
	elif control.name == "guiSeqCommonButton":
		control.x, control.y = 10, 0
		control.width, control.height = 75, 25
	elif control.name == "guiSeqActButton":
		control.x, control.y = 87, 0
		control.width, control.height = 50, 25
	elif control.name == "guiSequenceIFLButton":
		control.x, control.y = 139, 0
		control.width, control.height = 35, 25
	elif control.name == "guiSequenceVisibilityButton":
		control.x, control.y = 176, 0
		control.width, control.height = 55, 25
	elif control.name == "guiSequenceUVButton":
		control.x, control.y = 233, 0
		control.width, control.height = 70, 25
	elif control.name == "guiSequenceMorphButton":
		control.x, control.y = 305, 0
		control.width, control.height = 50, 25



# Resize callback for gui header	
def guiHeaderResize(control, newwidth, newheight):
	if control.name == "guiHeaderText":
		control.x = 5
		control.y = 5
	elif control.name == "guiVersionText":
		control.x = newwidth-80
		control.y = 5


# Used to validate a sequence name entered by the user.
# Sequence names must be unique amongst other sequences
# having the same type.
def validateSequenceName(seqName, seqType, oldName = None):
	global Prefs

	# check the obvious stuff first.
	# is the sequence name blank?
	if seqName == "" or seqName == None:
		Blender.Draw.PupMenu("The sequence name is not valid (blank).%t|Cancel")
		return False
	
	
	seqPrefs = Prefs['Sequences']
	# loop thorough each sequence and see what we've got.
	for pSeqName in seqPrefs.keys():
		if pSeqName != seqName: continue
		seq = seqPrefs[seqName]
		if (seq['IFL']['Enabled'] and seqType == "IFL")\
		or (seq['Vis']['Enabled'] and seqType == "Vis"):
			message = ("%s animation sequence named %s already exists." % (seqType, seqName)) + "%t|Cancel"
			Blender.Draw.PupMenu(message)
			return False
		# If a sequence containing visibility and ifl animations is merged with an action sequence that already
		# contains one or the other animation type, that animation type will be overwritten by the merged in values;
		# we need to ask the user what they want to do in this case.
		if oldName != None:
			print "checking oldName:", oldName, "against newName:", seqName
			oldSeq = seqPrefs[oldName]
			if seqType == "Vis" and seq['IFL']['Enabled'] and oldSeq['IFL']['Enabled']:
				message = ("IFL animation in \'%s\' will be overwritten with IFL animation from \'%s\' !" % (seqName, oldName)) + "%t|Merge Sequences and Overwrite IFL animation.|Cancel Merge"
				if Blender.Draw.PupMenu(message) == 1:
					return True
				else:
					return False
			if seqType == "IFL" and seq['Vis']['Enabled'] and oldSeq['Vis']['Enabled']:
				message = ("Vis animation in \'%s\' will be overwritten with Vis animation from \'%s\' !" % (seqName, oldName)) + "%t|Merge Sequences and Overwrite Vis animation.|Cancel Merge"
				if Blender.Draw.PupMenu(message) == 1:
					return True
				else:
					return False


	return True
	pass


'''
***************************************************************************************************
*
* Template for creating new control pages
*
***************************************************************************************************

class SomeControlsClass:
	def __init__(self):
		global guiSomeSubtab
		global globalEvents
		
		# initialize GUI controls
		
		# set initial states
		
		# add controls to containers
		
		# populate lists

	def cleanup(self):

		# Must destroy any GUI objects that are referenced in a non-global scope
		# explicitly before interpreter shutdown to avoid the dreaded
		# "error totblock" message when exiting Blender.
		# Note: __del__ is not guaranteed to be called for objects that still
		# exist when the interpreter exits.

		pass


	def handleEvent(self, control):
		pass
		
	def resize(self, control, newwidth, newheight):
		pass
	
	# other event callbacks and helper methods go here.
'''

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the About control page
*
***************************************************************************************************
'''
class AboutControlsClass:
	def __init__(self):
		global guiAboutSubtab
		global globalEvents
		
		# initialize GUI controls
		self.guiAboutText = Common_Gui.MultilineText("guiAboutText", 
		"Torque Exporter Plugin for Blender\n" +
		"\n"
		"Written by James Urquhart, with assistance from Tim Gift, Clark Fagot, Wes Beary,\n" +
		"Ben Garney, Joshua Ritter, Emanuel Greisen, Todd Koeckeritz,\n" +
		"Ryan J. Parker, Walter Yoon, and Joseph Greenawalt.\n" +
		"GUI code written with assistance from Xen and Xavier Amado.\n" +
		"Additional thanks goes to the testers.\n" +
		"\n" +
		"Visit GarageGames at http://www.garagegames.com", None, self.resize)
		
		# add controls to containers
		guiAboutSubtab.addControl(self.guiAboutText)
		

	def cleanup(self):

		# Must destroy any GUI objects that are referenced in a non-global scope
		# explicitly before interpreter shutdown to avoid the dreaded
		# "error totblock" message when exiting Blender.
		# Note: __del__ is not guaranteed to be called for objects that still
		# exist when the interpreter exits.
		del self.guiAboutText

	def refreshAll(self):
		pass
		
	def resize(self, control, newwidth, newheight):
		if control.name == "guiAboutText":
			control.x = 10
			control.y = 120

	
	# other event callbacks and helper methods go here.



'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the General sub-panel.
*
***************************************************************************************************
'''
class GeneralControlsClass:
	def __init__(self):
		global guiGeneralSubtab
		global globalEvents
		
		# initialize GUI controls
		self.guiStripText = Common_Gui.SimpleText("guiStripText", "Geometry type:", None, self.resize)
		self.guiTriMeshesButton = Common_Gui.ToggleButton("guiTriMeshesButton", "Triangles", "Generate individual triangles for meshes", 6, self.handleEvent, self.resize)
		self.guiTriListsButton = Common_Gui.ToggleButton("guiTriListsButton", "Triangle Lists", "Generate triangle lists for meshes", 7, self.handleEvent, self.resize)
		self.guiStripMeshesButton = Common_Gui.ToggleButton("guiStripMeshesButton", "Triangle Strips", "Generate triangle strips for meshes", 8, self.handleEvent, self.resize)
		self.guiMaxStripSizeSlider = Common_Gui.NumberSlider("guiMaxStripSizeSlider", "Strip Size ", "Maximum size of generated triangle strips", 9, self.handleEvent, self.resize)
		# --
		self.guiClusterText = Common_Gui.SimpleText("guiClusterText", "Cluster Mesh", None, self.resize)
		self.guiClusterWriteDepth = Common_Gui.ToggleButton("guiClusterWriteDepth", "Write Depth ", "Always Write the Depth on Cluster meshes", 10, self.handleEvent, self.resize)
		self.guiClusterDepth = Common_Gui.NumberSlider("guiClusterDepth", "Depth", "Maximum depth Clusters meshes should be calculated to", 11, self.handleEvent, self.resize)
		# --
		self.guiBillboardText = Common_Gui.SimpleText("guiBillboardText", "Auto-Billboard LOD:", None, self.resize)
		self.guiBillboardButton = Common_Gui.ToggleButton("guiBillboardButton", "Enable", "Add a billboard detail level to the shape", 12, self.handleEvent, self.resize)
		self.guiBillboardEquator = Common_Gui.NumberPicker("guiBillboardEquator", "Equator", "Number of images around the equator", 13, self.handleEvent, self.resize)
		self.guiBillboardPolar = Common_Gui.NumberPicker("guiBillboardPolar", "Polar", "Number of images around the polar", 14, self.handleEvent, self.resize)
		self.guiBillboardPolarAngle = Common_Gui.NumberSlider("guiBillboardPolarAngle", "Polar Angle", "Angle to take polar images at", 15, self.handleEvent, self.resize)
		self.guiBillboardDim = Common_Gui.NumberPicker("guiBillboardDim", "Dim", "Dimensions of billboard images", 16, self.handleEvent, self.resize)
		self.guiBillboardPoles = Common_Gui.ToggleButton("guiBillboardPoles", "Poles", "Take images at the poles", 17, self.handleEvent, self.resize)
		self.guiBillboardSize = Common_Gui.NumberSlider("guiBillboardSize", "Size", "Size of billboard's detail level", 18, self.handleEvent, self.resize)
		# --
		self.guiOutputText = Common_Gui.SimpleText("guiOutputText", "Output:", None, self.resize)
		self.guiShapeScriptButton =  Common_Gui.ToggleButton("guiShapeScriptButton", "Write Shape Script", "Write .cs script that details the .dts and all .dsq sequences", 19, self.handleEvent, self.resize)
		self.guiCustomFilename = Common_Gui.TextBox("guiCustomFilename", "Filename: ", "Filename to write to", 20, self.handleEvent, self.resize)
		self.guiCustomFilenameSelect = Common_Gui.BasicButton("guiCustomFilenameSelect", "Select...", "Select a filename and destination for export", 21, self.handleEvent, self.resize)
		self.guiCustomFilenameDefaults = Common_Gui.BasicButton("guiCustomFilenameDefaults", "Default", "Reset filename and destination to defaults", 22, self.handleEvent, self.resize)
		self.guiTGEAMaterial = Common_Gui.ToggleButton("guiTGEAMaterial", "Write TGEA Materials", "Write materials and scripts geared for TSE", 24, self.handleEvent, self.resize)
		self.guiLogToOutputFolder = Common_Gui.ToggleButton("guiLogToOutputFolder", "Log to Output Folder", "Write Log file to .DTS output folder", 25, self.handleEvent, self.resize)

		
		# set initial states
		try: x = Prefs['PrimType']
		except KeyError: Prefs['PrimType'] = "Tris"
		if Prefs['PrimType'] == "Tris": self.guiTriMeshesButton.state = True
		else: self.guiTriMeshesButton.state = False
		if Prefs['PrimType'] == "TriLists": self.guiTriListsButton.state = True
		else: self.guiTriListsButton.state = False
		if Prefs['PrimType'] == "TriStrips": self.guiStripMeshesButton.state = True
		else: self.guiStripMeshesButton.state = False
		self.guiMaxStripSizeSlider.min, self.guiMaxStripSizeSlider.max = 3, 30
		self.guiMaxStripSizeSlider.value = Prefs['MaxStripSize']
		self.guiClusterDepth.min, self.guiClusterDepth.max = 3, 30
		self.guiClusterDepth.value = Prefs['ClusterDepth']
		self.guiClusterWriteDepth.state = Prefs['AlwaysWriteDepth']
		self.guiBillboardButton.state = Prefs['Billboard']['Enabled']
		self.guiBillboardEquator.min, self.guiBillboardEquator.max = 2, 64
		self.guiBillboardEquator.value = Prefs['Billboard']['Equator']
		self.guiBillboardPolar.min, self.guiBillboardPolar.max = 3, 64
		self.guiBillboardPolar.value = Prefs['Billboard']['Polar']
		self.guiBillboardPolarAngle.min, self.guiBillboardPolarAngle.max = 0.0, 45.0
		self.guiBillboardPolarAngle.value = Prefs['Billboard']['PolarAngle']
		self.guiBillboardDim.min, self.guiBillboardDim.max = 16, 128
		self.guiBillboardDim.value = Prefs['Billboard']['Dim']
		self.guiBillboardPoles.state = Prefs['Billboard']['IncludePoles']		
		self.guiBillboardSize.min, self.guiBillboardSize.max = 0.0, 128.0
		self.guiBillboardSize.value = Prefs['Billboard']['Size']
		self.guiCustomFilename.length = 255
		if "\\" in Prefs['exportBasepath']:
			pathSep = "\\"
		else:
			pathSep = "/"
		self.guiCustomFilename.value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename'] + ".dts"
		self.guiTGEAMaterial.state = Prefs['TSEMaterial']		
		try: self.guiLogToOutputFolder.state = Prefs['LogToOutputFolder']
		except:
			Prefs['LogToOutputFolder'] = True
			self.guiLogToOutputFolder.state = True
		# Hiding these for now, since cluster mesh sorting is still broken.
		self.guiClusterText.visible = False
		self.guiClusterWriteDepth.visible = False
		self.guiClusterDepth.visible = False
		
		
		
		# add controls to containers
		guiGeneralSubtab.addControl(self.guiStripText)
		guiGeneralSubtab.addControl(self.guiTriMeshesButton)
		guiGeneralSubtab.addControl(self.guiTriListsButton)
		guiGeneralSubtab.addControl(self.guiStripMeshesButton)	
		guiGeneralSubtab.addControl(self.guiMaxStripSizeSlider)
		guiGeneralSubtab.addControl(self.guiClusterText)
		guiGeneralSubtab.addControl(self.guiClusterDepth)
		guiGeneralSubtab.addControl(self.guiClusterWriteDepth)
		guiGeneralSubtab.addControl(self.guiBillboardText)
		guiGeneralSubtab.addControl(self.guiBillboardButton)
		guiGeneralSubtab.addControl(self.guiBillboardEquator)
		guiGeneralSubtab.addControl(self.guiBillboardPolar)
		guiGeneralSubtab.addControl(self.guiBillboardPolarAngle)
		guiGeneralSubtab.addControl(self.guiBillboardDim)
		guiGeneralSubtab.addControl(self.guiBillboardPoles)
		guiGeneralSubtab.addControl(self.guiBillboardSize)
		guiGeneralSubtab.addControl(self.guiOutputText)
		guiGeneralSubtab.addControl(self.guiShapeScriptButton)
		guiGeneralSubtab.addControl(self.guiCustomFilename)
		guiGeneralSubtab.addControl(self.guiCustomFilenameSelect)
		guiGeneralSubtab.addControl(self.guiCustomFilenameDefaults)
		guiGeneralSubtab.addControl(self.guiTGEAMaterial)
		guiGeneralSubtab.addControl(self.guiLogToOutputFolder)

		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiStripText
		del self.guiTriMeshesButton
		del self.guiTriListsButton
		del self.guiStripMeshesButton
		del self.guiMaxStripSizeSlider
		# --
		del self.guiClusterText
		del self.guiClusterWriteDepth
		del self.guiClusterDepth
		# --
		del self.guiBillboardText
		del self.guiBillboardButton
		del self.guiBillboardEquator
		del self.guiBillboardPolar
		del self.guiBillboardPolarAngle
		del self.guiBillboardDim
		del self.guiBillboardPoles
		del self.guiBillboardSize
		# --
		del self.guiOutputText
		del self.guiShapeScriptButton
		del self.guiCustomFilename
		del self.guiCustomFilenameSelect
		del self.guiCustomFilenameDefaults
		del self.guiTGEAMaterial
		del self.guiLogToOutputFolder

	def refreshAll(self):
		pass

	def handleEvent(self, control):
		global Prefs
		global guiGeneralSubtab
		if control.name == "guiTriMeshesButton":
			Prefs['PrimType'] = "Tris"
			self.guiTriListsButton.state = False
			self.guiStripMeshesButton.state = False
			self.guiTriMeshesButton.state = True
		elif control.name == "guiTriListsButton":
			Prefs['PrimType'] = "TriLists"
			self.guiTriListsButton.state = True
			self.guiStripMeshesButton.state = False
			self.guiTriMeshesButton.state = False
		elif control.name == "guiStripMeshesButton":
			Prefs['PrimType'] = "TriStrips"
			self.guiTriListsButton.state = False
			self.guiStripMeshesButton.state = True
			self.guiTriMeshesButton.state = False
		elif control.name == "guiMaxStripSizeSlider":
			Prefs['MaxStripSize'] = control.value
		elif control.name == "guiClusterWriteDepth":
			Prefs['AlwaysWriteDepth'] = control.state
		elif control.name == "guiClusterDepth":
			Prefs['ClusterDepth'] = control.value
		elif control.name == "guiBillboardButton":
			Prefs['Billboard']['Enabled'] = control.state
		elif control.name == "guiBillboardEquator":
			Prefs['Billboard']['Equator'] = control.value
		elif control.name == "guiBillboardPolar":
			Prefs['Billboard']['Polar'] = control.value
		elif control.name == "guiBillboardPolarAngle":
			Prefs['Billboard']['PolarAngle'] = control.value
		elif control.name == "guiBillboardDim":
			val = int(control.value)
			# need to constrain this to be a power of 2
			# it would be easier just to use a combo box, but this is more fun.
			# did the value go up or down?
			if control.value > Prefs['Billboard']['Dim']:
				# we go up
				val = int(2**math.ceil(math.log(control.value,2)))
			elif control.value < Prefs['Billboard']['Dim']:
				# we go down
				val = int(2**math.floor(math.log(control.value,2)))
			control.value = val
			Prefs['Billboard']['Dim'] = control.value
		elif control.name == "guiBillboardPoles":
			Prefs['Billboard']['IncludePoles'] = control.state
		elif control.name == "guiBillboardSize":
			Prefs['Billboard']['Size'] = control.value
		elif control.name == "guiShapeScriptButton":
			Prefs['WriteShapeScript'] = control.state
		elif control.name == "guiCustomFilename":
			Prefs['exportBasename'] = basename(control.value)
			Prefs['exportBasepath'] = basepath(control.value)
			if guiGeneralSubtab.controls[18].value[len(guiGeneralSubtab.controls[18].value)-4:] != ".dts":
				guiGeneralSubtab.controls[18].value += ".dts"

			if Prefs['LogToOutputFolder']:
				Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSeperator, noext(Prefs['exportBasename'])) )
		elif control.name == "guiCustomFilenameSelect":
			Blender.Window.FileSelector (self.guiGeneralSelectorCallback, 'Select destination and filename')
		elif control.name == "guiCustomFilenameDefaults":
			Prefs['exportBasename'] = basename(Blender.Get("filename"))
			Prefs['exportBasepath'] = basepath(Blender.Get("filename"))		
			pathSep = "/"
			if "\\" in Prefs['exportBasepath']:
				pathSep = "\\"
			else:
				pathSep = "/"
			guiGeneralSubtab.controls[18].value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']
			if guiGeneralSubtab.controls[18].value[len(guiGeneralSubtab.controls[18].value)-4:] != ".dts":
				guiGeneralSubtab.controls[18].value += ".dts"
		elif control.name == "guiTGEAMaterial":
			Prefs['TSEMaterial'] = control.state

		elif control.name == "guiLogToOutputFolder":
			Prefs['LogToOutputFolder'] = control.state
			if control.state:
				Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSeperator, noext(Prefs['exportBasename'])) )
			else:
				Torque_Util.dump_setout("%s.log" % noext(Blender.Get("filename")))
			Prefs['exportBasename']

		
	def resize(self, control, newwidth, newheight):
		if control.name == "guiStripText":
			control.x, control.y = 10,newheight-20
		elif control.name == "guiClusterText":
			control.x, control.y = 10,newheight-70
		elif control.name == "guiBillboardText":
			control.x, control.y = 10,newheight-120
		elif control.name == "guiOutputText":
			control.x, control.y = 10,newheight-250
		elif control.name == "guiTriMeshesButton":
			control.x, control.y, control.width = 10,newheight-30-control.height, 90
		elif control.name == "guiTriListsButton":
			control.x, control.y, control.width = 102,newheight-30-control.height, 90
		elif control.name == "guiStripMeshesButton":
			control.x, control.y, control.width = 194,newheight-30-control.height, 90
		elif control.name == "guiMaxStripSizeSlider":
			control.x, control.y, control.width = 286,newheight-30-control.height, 180
		elif control.name == "guiClusterWriteDepth":
			control.x, control.y, control.width = 10,newheight-80-control.height, 80
		elif control.name == "guiClusterDepth":
			control.x, control.y, control.width = 92,newheight-80-control.height, 180
		elif control.name == "guiBillboardButton":
			control.x, control.y, control.width = 10,newheight-130-control.height, 50
		elif control.name == "guiBillboardEquator":
			control.x, control.y, control.width = 62,newheight-130-control.height, 100
		elif control.name == "guiBillboardPolar":
			control.x, control.y, control.width = 62,newheight-152-control.height, 100
		elif control.name == "guiBillboardPolarAngle":
			control.x, control.y, control.width =  164,newheight-152-control.height, 200
		elif control.name == "guiBillboardDim":
			control.x, control.y, control.width = 366,newheight-130-control.height, 100
		elif control.name == "guiBillboardPoles":
			control.x, control.y, control.width = 366,newheight-152-control.height, 100
		elif control.name == "guiBillboardSize":
			control.x, control.y, control.width = 164,newheight-130-control.height, 200
		elif control.name == "guiShapeScriptButton":
			control.x, control.y, control.width = 346,newheight-260-control.height, 132
		elif control.name == "guiCustomFilename":
			control.x, control.y, control.width = 10,newheight-260-control.height, 220
		elif control.name == "guiCustomFilenameSelect":
			control.x, control.y, control.width = 232,newheight-260-control.height, 55
		elif control.name == "guiCustomFilenameDefaults":
			control.x, control.y, control.width = 289,newheight-260-control.height, 55
		elif control.name == "guiTGEAMaterial":
			control.x, control.y, control.width = 346,newheight-282-control.height, 132
		elif control.name == "guiLogToOutputFolder":
			control.x, control.y, control.width = 346,newheight-304-control.height, 132

	
	def guiGeneralSelectorCallback(self, filename):
		global guiGeneralSubtab
		if filename != "":
			Prefs['exportBasename'] = basename(filename)
			Prefs['exportBasepath'] = basepath(filename)

			pathSep = "/"
			if "\\" in Prefs['exportBasepath']: pathSep = "\\"

			guiGeneralSubtab.controls[18].value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']
			if guiGeneralSubtab.controls[18].value[len(guiGeneralSubtab.controls[18].value)-4:] != ".dts":
				guiGeneralSubtab.controls[18].value += ".dts"




'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Armatures sub-panel.
*
***************************************************************************************************
'''
class ArmatureControlsClass:
	def __init__(self):
		global guiArmatureSubtab
		global globalEvents

		# initialize GUI controls
		self.guiBoneText = Common_Gui.SimpleText("guiBoneText", "Bones that should be exported :", None, self.resize)
		self.guiBoneList = Common_Gui.BoneListContainer("guiBoneList", None, None, self.resize)
		self.guiMatchText =  Common_Gui.SimpleText("guiMatchText", "Match pattern", None, self.resize)
		self.guiPatternText = Common_Gui.TextBox("guiPatternText", "", "pattern to match bone names, asterix is wildcard", 6, self.handleEvent, self.resize)
		self.guiPatternOn = Common_Gui.BasicButton("guiPatternOn", "On", "Turn on export of bones matching pattern", 7, self.handleEvent, self.resize)
		self.guiPatternOff = Common_Gui.BasicButton("guiPatternOff", "Off", "Turn off export of bones matching pattern", 8, self.handleEvent, self.resize)
		self.guiRefresh = Common_Gui.BasicButton("guiRefresh", "Refresh", "Refresh bones list", 9, self.handleEvent, self.resize)
				
		# set initial states
		self.guiPatternText.value = "*"
		
		# add controls to containers
		guiArmatureSubtab.addControl(self.guiBoneText)
		guiArmatureSubtab.addControl(self.guiBoneList)
		guiArmatureSubtab.addControl(self.guiMatchText)
		guiArmatureSubtab.addControl(self.guiPatternText)
		guiArmatureSubtab.addControl(self.guiPatternOn)
		guiArmatureSubtab.addControl(self.guiPatternOff)
		guiArmatureSubtab.addControl(self.guiRefresh)
		
		# populate bone grid
		self.populateBoneGrid()
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiBoneText		
		del self.guiMatchText
		del self.guiPatternText
		del self.guiPatternOn
		del self.guiPatternOff
		del self.guiRefresh		
		#for control in self.guiBoneList.controls: del control
		#del self.guiBoneList.controls
		del self.guiBoneList

	
	def refreshAll(self):
		pass

	def handleEvent(self, control):
		global Prefs, export_tree, guiBoneList, guiPatternText
		if control.name == "guiPatternOn" or control.name == "guiPatternOff":
			userPattern = self.guiPatternText.value
			# convert to uppercase
			userPattern = userPattern.upper()
			newPat = re.sub("\\*", ".*", userPattern)
			if newPat[-1] != '*':
				newPat += '$'
			shapeTree = export_tree.find("SHAPE")
			if shapeTree == None: return
			for name in shapeTree.getShapeBoneNames():
				name = name.upper()
				if re.match(newPat, name) != None:				
						if control.name == "guiPatternOn":
							for i in range(len(Prefs['BannedBones'])-1, -1, -1):
								boneName = Prefs['BannedBones'][i].upper()
								if name == boneName:
									del Prefs['BannedBones'][i]
						elif control.name == "guiPatternOff":
							Prefs['BannedBones'].append(name)
			self.clearBoneGrid()
			self.populateBoneGrid()
		elif control.name == "guiRefresh":
			self.clearBoneGrid()
			self.populateBoneGrid()

	def resize(self, control, newwidth, newheight):
		if control.name == "guiBoneText":
			control.x, control.y = 10,newheight-15
		elif control.name == "guiBoneList":
			control.x, control.y, control.width, control.height = 10,70, 470,242
		elif control.name == "guiMatchText":
			control.x, control.y = 10,newheight-285
		elif control.name == "guiPatternText":
			control.x, control.y, control.width = 10,newheight-315, 70
		elif control.name == "guiPatternOn":
			control.x, control.y, control.width = 84,newheight-315, 35
		elif control.name == "guiPatternOff":
			control.x, control.y, control.width = 121,newheight-315, 35
		elif control.name == "guiRefresh":
			control.x, control.y, control.width = 400,newheight-315, 75

	def guiBoneListItemCallback(self, control):
		global Prefs, guiSeqActList

		# Determine id of clicked button
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) #/ 4
		real_name = control.text.upper()
		if control.state:
			# Remove entry from BannedBones
			for i in range(0, len(Prefs['BannedBones'])):
				if Prefs['BannedBones'][i] == real_name:
					del Prefs['BannedBones'][i]
					break
		else:
			Prefs['BannedBones'].append(real_name)

	def createBoneListitem(self, bone1, bone2, bone3, bone4, bone5, startEvent):
		#seqPrefs = getSequenceKey(seq_name)
		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0
		guiContainer.borderColor = None
		if bone1 != None:
			guiBone1 = Common_Gui.ToggleButton("guiBone_" + bone1, bone1, "Toggle Status of " + bone1, startEvent, self.guiBoneListItemCallback, None)
			guiBone1.x, guiBone1.y = 1, 0
			guiBone1.width, guiBone1.height = 90, 19
			guiBone1.state = True
			guiContainer.addControl(guiBone1)
		if bone2 != None:
			guiBone2 = Common_Gui.ToggleButton("guiBone_" + bone2, bone2, "Toggle Status of " + bone2, startEvent+1, self.guiBoneListItemCallback, None)
			guiBone2.x, guiBone2.y = 92, 0
			guiBone2.width, guiBone2.height = 90, 19
			guiBone2.state = True
			guiContainer.addControl(guiBone2)
		if bone3 != None:
			guiBone3 = Common_Gui.ToggleButton("guiBone_" + bone3, bone3, "Toggle Status of " + bone3, startEvent+3, self.guiBoneListItemCallback, None)
			guiBone3.x, guiBone3.y = 183, 0
			guiBone3.width, guiBone3.height = 90, 19
			guiBone3.state = True
			guiContainer.addControl(guiBone3)
		if bone4 != None:
			guiBone4 = Common_Gui.ToggleButton("guiBone_" + bone4, bone4, "Toggle Status of " + bone4, startEvent+4, self.guiBoneListItemCallback, None)
			guiBone4.x, guiBone4.y = 274, 0
			guiBone4.width, guiBone4.height = 89, 19
			guiBone4.state = True
			guiContainer.addControl(guiBone4)	
		if bone5 != None:
			guiBone5 = Common_Gui.ToggleButton("guiBone_" + bone5, bone5, "Toggle Status of " + bone5, startEvent+5, self.guiBoneListItemCallback, None)
			guiBone5.x, guiBone5.y = 364, 0
			guiBone5.width, guiBone5.height = 89, 19
			guiBone5.state = True
			guiContainer.addControl(guiBone5)
		return guiContainer

	def populateBoneGrid(self):
		global Prefs, export_tree, guiBoneList
		shapeTree = export_tree.find("SHAPE")
		if shapeTree == None: return
		evtNo = 40
		count = 0
		names = []
		for name in shapeTree.getShapeBoneNames():
			names.append(name)
			if len(names) == 5:
				self.guiBoneList.addControl(self.createBoneListitem(names[0],names[1],names[2],names[3],names[4], evtNo))
				self.guiBoneList.controls[count].controls[0].state = not (self.guiBoneList.controls[count].controls[0].text.upper() in Prefs['BannedBones'])
				self.guiBoneList.controls[count].controls[1].state = not (self.guiBoneList.controls[count].controls[1].text.upper() in Prefs['BannedBones'])
				self.guiBoneList.controls[count].controls[2].state = not (self.guiBoneList.controls[count].controls[2].text.upper() in Prefs['BannedBones'])
				self.guiBoneList.controls[count].controls[3].state = not (self.guiBoneList.controls[count].controls[3].text.upper() in Prefs['BannedBones'])
				self.guiBoneList.controls[count].controls[4].state = not (self.guiBoneList.controls[count].controls[4].text.upper() in Prefs['BannedBones'])

				evtNo += 6
				count += 1
				names = []
		# add leftovers in last row
		if len(names) > 0:
			for i in range(len(names)-1, 5):
				names.append(None)
			self.guiBoneList.addControl(self.createBoneListitem(names[0],names[1],names[2],names[3], names[4], evtNo))
			if names[0] != None: self.guiBoneList.controls[count].controls[0].state = not (self.guiBoneList.controls[count].controls[0].text.upper() in Prefs['BannedBones'])
			if names[1] != None: self.guiBoneList.controls[count].controls[1].state = not (self.guiBoneList.controls[count].controls[1].text.upper() in Prefs['BannedBones'])
			if names[2] != None: self.guiBoneList.controls[count].controls[2].state = not (self.guiBoneList.controls[count].controls[2].text.upper() in Prefs['BannedBones'])
			if names[3] != None: self.guiBoneList.controls[count].controls[3].state = not (self.guiBoneList.controls[count].controls[3].text.upper() in Prefs['BannedBones'])
			if names[4] != None: self.guiBoneList.controls[count].controls[4].state = not (self.guiBoneList.controls[count].controls[4].text.upper() in Prefs['BannedBones'])


	def clearBoneGrid(self):
		global guiBoneList
		del self.guiBoneList.controls[:]
		#for control in self.guiBoneList.controls:
		#	del control
		

	def guiBoneGridCallback(self, control):
		global Prefs
		real_name = control.name.upper()
		if control.state:
			# Remove entry from BannedBones
			for i in range(0, len(Prefs['BannedBones'])):
				if Prefs['BannedBones'][i] == real_name:
					del Prefs['BannedBones'][i]
					break
		else:
			Prefs['BannedBones'].append(real_name)



'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the "Common/All" sub-panel of the Sequences panel.
*
***************************************************************************************************
'''
class SeqCommonControlsClass:
	def __init__(self):
		global guiSeqCommonSubtab
		global globalEvents
		
		# initialize GUI controls
		self.guiSeqList = Common_Gui.ListContainer("guiSeqList", "sequence.list", self.handleListEvent, self.resize)
		self.guiSeqListTitle = Common_Gui.SimpleText("guiSeqListTitle", "All Sequences:", None, self.resize)
		self.guiToggle = Common_Gui.ToggleButton("guiToggle", "Toggle All", "Toggle export of all sequences", 6, self.handleEvent, self.resize)
		self.guiRefresh = Common_Gui.BasicButton("guiRefresh", "Refresh", "Refresh list of sequences", 7, self.handleEvent, self.resize)
		self.guiSeqOptsContainerTitle = Common_Gui.SimpleText("guiSeqOptsContainerTitle", "Sequence: None Selected", None, self.resize)
		self.guiSeqOptsContainer = Common_Gui.BasicContainer("guiSeqOptsContainer", "guiSeqOptsContainer", None, self.resize)
		self.guiSeqFramesLabel =  Common_Gui.SimpleText("guiSeqFramesLabel", "Highest Frame Count:  ", None, self.resize)
		self.guiSeqDuration = Common_Gui.NumberPicker("guiSeqDuration", "Duration (seconds): ", "The animation plays for this number of seconds", 10, self.handleEvent, self.resize)
		self.guiSeqDurationLock = Common_Gui.ToggleButton("guiSeqDurationLock", "Lock", "Lock Sequence Duration (changes in frame count don't affect playback time)", 24, self.handleEvent, self.resize)
		self.guiSeqFPS = Common_Gui.NumberPicker("guiSeqFPS", "Sequence FPS: ", "The animation plays back at a rate of this number of keyframes per second", 11, self.handleEvent, self.resize)
		self.guiSeqFPSLock = Common_Gui.ToggleButton("guiSeqFPSLock", "Lock", "Lock Sequence FPS (changes in frame count affect playback time, but not Frames Per Second)", 25, self.handleEvent, self.resize)		
		self.guiPriority = Common_Gui.NumberPicker("guiPriority", "Priority", "Sequence playback priority", 23, self.handleEvent, self.resize)
		self.guiTriggerTitle = Common_Gui.SimpleText("guiTriggerTitle", "Triggers", None, self.resize)
		self.guiTriggerMenu = Common_Gui.ComboBox("guiTriggerMenu", "Trigger List", "Select a trigger from this list to edit its properties", 14, self.handleTriggersEvent, self.resize)
		self.guiTriggerState = Common_Gui.NumberPicker("guiTriggerState", "Trigger", "Trigger state to alter", 15, self.handleTriggersEvent, self.resize)
		self.guiTriggerStateOn = Common_Gui.ToggleButton("guiTriggerStateOn", "On", "Determines if state will be activated or deactivated", 16, self.handleTriggersEvent, self.resize)
		self.guiTriggerFrame = Common_Gui.NumberPicker("guiTriggerFrame", "Frame", "Frame to activate trigger on", 17, self.handleTriggersEvent, self.resize)
		self.guiTriggerAdd = Common_Gui.BasicButton("guiTriggerAdd", "Add", "Add new trigger", 18, self.handleTriggersEvent, self.resize)
		self.guiTriggerDel = Common_Gui.BasicButton("guiTriggerDel", "Del", "Delete currently selected trigger", 19, self.handleTriggersEvent, self.resize)
		
		self.guiSeqGraph = Common_Gui.BarGraph("guiSeqGraph", "", 5, "Graph of animation frames for sequence", 20, self.handleTriggersEvent, self.resize)
		self.guiSeqGraph.setBarText(4, "Act Frames:")
		self.guiSeqGraph.setBarText(3, "IFL Frames:")
		self.guiSeqGraph.setBarText(2, "Vis Frames:")
		self.guiSeqGraph.setBarText(1, "Tex Frames:")
		self.guiSeqGraph.setBarText(0, "Mor Frames:")
		self.guiSeqGraph.setBarValue(4, 0.9)
		self.guiSeqGraph.setBarValue(3, 0.5)
		self.guiSeqGraph.setBarValue(2, 0.75)
		self.guiSeqGraph.setBarValue(1, 0.2)
		self.guiSeqGraph.setBarValue(0, 0.8)
		self.guiSeqGraph.setBarColor(4, (0.5, 1.0, 0.5))
		self.guiSeqGraph.setBarColor(3, (0.5, 1.0, 0.5))
		self.guiSeqGraph.setBarColor(2, (0.5, 1.0, 0.5))
		self.guiSeqGraph.setBarColor(1, (0.5, 1.0, 0.5))
		self.guiSeqGraph.setBarColor(0, (0.5, 1.0, 0.5))

		# set initial states
		self.guiToggle.state = False
		self.guiSeqOptsContainer.enabled = False
		self.guiSeqOptsContainer.fade_mode = 5
		self.guiSeqOptsContainer.borderColor = None
		self.guiSeqList.fade_mode = 0
		self.guiSeqDuration.min = 0.00392  # minimum duration = 1/255 of a second
		self.guiSeqDuration.max = 3600.0
		self.guiSeqDuration.value = 0.00392
		self.guiSeqFPS.min = 0.00027777778
		self.guiSeqFPS.max = 255.0
		self.guiSeqFPS.value = 25.0
		self.guiPriority.min = 0
		self.guiPriority.max = 64 # this seems resonable
		self.guiTriggerState.min, self.guiTriggerState.max = 1, 32
		self.guiTriggerFrame.min = 1
		

		# add controls to containers
		guiSeqCommonSubtab.addControl(self.guiSeqList)
		guiSeqCommonSubtab.addControl(self.guiSeqListTitle)
		guiSeqCommonSubtab.addControl(self.guiToggle)
		guiSeqCommonSubtab.addControl(self.guiRefresh)
		guiSeqCommonSubtab.addControl(self.guiSeqOptsContainerTitle)
		guiSeqCommonSubtab.addControl(self.guiSeqOptsContainer)
		self.guiSeqOptsContainer.addControl(self.guiSeqFramesLabel)
		self.guiSeqOptsContainer.addControl(self.guiSeqDuration)
		self.guiSeqOptsContainer.addControl(self.guiSeqDurationLock)
		self.guiSeqOptsContainer.addControl(self.guiSeqFPSLock)
		self.guiSeqOptsContainer.addControl(self.guiSeqFPS)
		self.guiSeqOptsContainer.addControl(self.guiTriggerTitle) # 5
		self.guiSeqOptsContainer.addControl(self.guiTriggerMenu) # 6
		self.guiSeqOptsContainer.addControl(self.guiTriggerState) # 7
		self.guiSeqOptsContainer.addControl(self.guiTriggerStateOn) # 8
		self.guiSeqOptsContainer.addControl(self.guiTriggerFrame) # 9
		self.guiSeqOptsContainer.addControl(self.guiTriggerAdd) # 10
		self.guiSeqOptsContainer.addControl(self.guiTriggerDel) # 11
		self.guiSeqOptsContainer.addControl(self.guiPriority) # 15
		self.guiSeqOptsContainer.addControl(self.guiSeqGraph)
		
		
		# set initial states
		self.triggerMenuTemplate = "Frame:%d Trigger:%d "
		
		
		# populate lists
		self.populateSequenceList()


	def cleanup(self):

		# Must destroy any GUI objects that are referenced in a non-global scope
		# explicitly before interpreter shutdown to avoid the dreaded
		# "error totblock" message when exiting Blender.
		# Note: __del__ is not guaranteed to be called for objects that still
		# exist when the interpreter exits.
		
		# todo - cleanup code here
		pass

	def refreshAll(self):		
		# store last sequence selection
		seqName = None
		seqPrefs = None
		if self.guiSeqList.itemIndex != -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
		
		# repopulate the sequence list
		cleanKeys()
		createActionKeys()
		self.populateSequenceList()
		
		# restore last sequence selection
		for itemIndex in range(0, len(self.guiSeqList.controls)):
			#print "Checking item",itemIndex
			#print "self.guiSeqList.controls[itemIndex].controls[0].label =",self.guiSeqList.controls[itemIndex].controls[0].label
			#print "seqName =",seqName
			if self.guiSeqList.controls[itemIndex].controls[0].label == seqName:
				#print "found matching control for",seqName
				self.guiSeqList.selectItem(itemIndex)
				self.guiSeqList.scrollToSelectedItem()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
				return
		self.guiSeqList.selectItem(0)
		self.guiSeqList.scrollToSelectedItem()
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
		


	def handleEvent(self, control):
		if control.name == "guiToggle":
			for child in self.guiSeqList.controls:
				child.controls[1].state = control.state
				getSequenceKey(child.controls[0].label)['NoExport'] = not control.state
		elif control.name == "guiRefresh":
			self.refreshAll()

		elif self.guiSeqList.itemIndex != -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			if control.name == "guiSampleFrames":
				seqPrefs['Action']['FrameSamples'] = control.value
			elif control.name == "guiPriority":
				seqPrefs['Priority'] = control.value
			elif control.name == "guiSeqDurationLock":
				seqPrefs['DurationLocked'] = control.state
				seqPrefs['FPSLocked'] = False
				self.guiSeqDurationLock.state = True
				self.guiSeqFPSLock.state = False
			elif control.name == "guiSeqFPSLock":
				seqPrefs['FPSLocked'] = control.state
				seqPrefs['DurationLocked'] = False
				self.guiSeqDurationLock.state = False
				self.guiSeqFPSLock.state = True
			if control.name == "guiSeqDuration":
				if not validateIFL(seqName, seqPrefs):
					seqPrefs['Duration'] = float(control.value)					
					recalcFPS(seqName, seqPrefs)
					updateSeqDurationAndFPS(seqName, seqPrefs)
					
					self.guiSeqDuration.value = float(seqPrefs['Duration'])
					self.guiSeqDuration.tooltip = "Playback Time: %f Seconds" % float(seqPrefs['Duration'])
					self.guiSeqFPS.value = float(seqPrefs['FPS'])
					self.guiSeqFPS.tooltip = "Playback Rate: %f Frames Per Second" % float(seqPrefs['FPS'])
				else:
					message = "Sequences w/ IFL animations are locked at 30 fps.%t|Cancel"
					Blender.Draw.PupMenu(message)
					control.value = seqPrefs['Duration']
			elif control.name == "guiSeqFPS":
				if not validateIFL(seqName, seqPrefs):
					seqPrefs['FPS'] = float(control.value)
					recalcDuration(seqName, seqPrefs)
					updateSeqDurationAndFPS(seqName, seqPrefs)
					
					self.guiSeqDuration.value = float(seqPrefs['Duration'])
					self.guiSeqDuration.tooltip = "Playback Time: %f Seconds" % float(seqPrefs['Duration'])
					self.guiSeqFPS.value = float(seqPrefs['FPS'])
					self.guiSeqFPS.tooltip = "Playback Rate: %f Frames Per Second" % float(seqPrefs['FPS'])
				else:
					message = "Sequences w/ IFL animations are locked at 30 fps.%t|Cancel"
					Blender.Draw.PupMenu(message)
					control.value = seqPrefs['FPS']

				pass


	def handleListEvent(self, control):
		# Clear triggers menu
		del self.guiTriggerMenu.items[:]
		if control.itemIndex != -1:
			seqName = control.controls[control.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			self.guiSeqOptsContainerTitle.label = "Sequence '%s'" % seqName

			try:
				#action = Blender.Armature.NLA.GetActions()[seqName]
				#maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
				maxNumFrames = getSeqNumFrames(seqName, seqPrefs)
			except:
				maxNumFrames = 0

			
			# Update gui control states
			if seqPrefs['Action']['NumGroundFrames'] > maxNumFrames:
				seqPrefs['Action']['NumGroundFrames'] = maxNumFrames
			self.guiSeqOptsContainer.enabled = True
			
			updateSeqDurationAndFPS(seqName, seqPrefs)

			self.guiSeqFramesLabel.label = "Highest Frame Count:  " + str(maxNumFrames)
			
			if maxNumFrames == 0:
				self.guiSeqDuration.value = 0.0
				self.guiSeqDuration.tooltip = "Playback Time: 0.0 Seconds, Sequence has no key frames!"
				self.guiSeqDuration.enabled = False
				try: self.guiSeqFPS.value = float(Blender.Scene.GetCurrent().getRenderingContext().framesPerSec())
				except: self.guiSeqFPS.value = 25.0
				self.guiSeqDuration.tooltip = "Playback Time: %f Seconds, Sequence has no key frames!" % float(seqPrefs['Duration'])
				self.guiSeqFPS.enabled = False
				self.guiPriority.value = 0
			else:			
				self.guiSeqDuration.value = float(seqPrefs['Duration'])
				self.guiSeqDuration.tooltip = "Playback Time: %f Seconds" % float(seqPrefs['Duration'])
				self.guiSeqDuration.enabled = True
				self.guiSeqFPS.value = float(seqPrefs['FPS'])
				self.guiSeqFPS.tooltip = "Playback Rate: %f Frames Per Second" % float(seqPrefs['FPS'])
				self.guiSeqFPS.enabled = True
			
			self.guiSeqDurationLock.state = seqPrefs['DurationLocked']
			self.guiSeqFPSLock.state = seqPrefs['FPSLocked']
			self.guiPriority.value = seqPrefs['Priority']


			# Triggers
			for t in seqPrefs['Triggers']:
				if t[2]: stateStr = "(ON)"
				else: stateStr = "(OFF)"
				self.guiTriggerMenu.items.append((self.triggerMenuTemplate % (t[1], t[0])) + stateStr)
			self.guiTriggerMenu.itemIndex = 0

			if maxNumFrames > 0: self.guiTriggerFrame.max = maxNumFrames
			else: self.guiTriggerFrame.max = 1
			self.guiSequenceUpdateTriggers(seqPrefs['Triggers'], 0)
			self.refreshBarChart(seqName, seqPrefs)

		else:
			self.guiSeqOptsContainer.enabled = False
			self.guiSeqOptsContainerTitle.label = "Sequence: None Selected"
			self.guiSeqDuration.value = 0.0
			self.guiSeqFPS.value = 0.0
			self.guiPriority.value = 0
			self.guiSequenceUpdateTriggers([], 0)
			self.clearBarChart()

		
	def resize(self, control, newwidth, newheight):
		#self.guiSeqOptsContainerTitle = Common_Gui.SimpleText("guiSeqOptsContainerTitle", "Sequence: None Selected", None, self.resize)
		if control.name == "guiSeqList":
			control.x, control.y, control.height, control.width = 10,28, newheight - 68,230
			#control.x, control.y, control.height, control.width = 10,100, 200,230
		elif control.name == "guiSeqListTitle":
			control.x, control.y, control.height, control.width = 10,310, 20,82
		elif control.name == "guiSeqOptsContainer":
			control.x, control.y, control.height, control.width = 241,0, 334,249
		elif control.name == "guiSeqOptsContainerTitle":
			control.x, control.y, control.height, control.width = 250,310, 20,82
		# Sequence options
		elif control.name == "guiSeqFramesLabel":
			control.x = 5
			control.y = newheight - 156
			control.width = newwidth - 10
		elif control.name == "guiSeqDuration":
			control.x = 5
			control.y = newheight - 185
			control.width = newwidth - 55
		elif control.name == "guiSeqDurationLock":
			control.x = newwidth - 48
			control.y = newheight - 185
			control.width = 40
		elif control.name == "guiSeqFPS":
			control.x = 5
			control.y = newheight - 207
			control.width = newwidth - 55
		elif control.name == "guiSeqFPSLock":
			control.x = newwidth - 48
			control.y = newheight - 207
			control.width = 40
		elif control.name == "guiPriority":
			control.x = 5
			control.y = newheight - 240
			control.width = newwidth - 10
		elif control.name == "guiSeqGraph":
			control.x = 5
			control.y = 195
			control.height = 85
			control.width = newwidth - 10		
		# Triggers
		elif control.name == "guiTriggerTitle":
			control.x = 5
			control.y = 76
		elif control.name == "guiTriggerMenu":
			control.x = 5
			control.y = 49
			control.width = newwidth - 10
		elif control.name == "guiTriggerFrame":
			control.x = 5
			control.y = 27
			control.width = 100
		elif control.name == "guiTriggerState":
			control.x = 106
			control.y = 27
			control.width = 100
		elif control.name == "guiTriggerStateOn":
			control.x = 207
			control.y = 27
			control.width = 34
		elif control.name == "guiTriggerAdd":
			control.x = 5
			control.y = 5
			control.width = (newwidth / 2) - 6
		elif control.name == "guiTriggerDel":
			control.x = (newwidth / 2)
			control.y = 5
			control.width = (newwidth / 2) - 6
		# Sequence list buttons
		elif control.name == "guiToggle":
			control.x = 10
			control.y = 5
			control.width = 100
		elif control.name == "guiRefresh":
			control.x = 112
			control.y = 5
			control.width = 100

	
	def refreshBarChart(self, seqName, seqPrefs):
		maxFrames = getSeqNumFrames(seqName, seqPrefs)
		if maxFrames == 0: maxFrames = 0.0001 # heh.
		actFrames = getNumActFrames(seqName, seqPrefs)
		IFLFrames = getNumIFLFrames(seqName, seqPrefs)
		visFrames = getNumVisFrames(seqName, seqPrefs)
		
		if validateAction(seqName, seqPrefs):
			self.guiSeqGraph.setBarText(4, "Act Frames:%i" % getNumActFrames(seqName, seqPrefs))
			self.guiSeqGraph.setBarValue(4, float(actFrames)/float(maxFrames))
		else:
			self.guiSeqGraph.setBarText(4, "Act Frames: None")
			self.guiSeqGraph.setBarValue(4, 0)
		
		if validateIFL(seqName, seqPrefs):
			self.guiSeqGraph.setBarText(3, "IFL Frames:%i" % getNumIFLFrames(seqName, seqPrefs))
			self.guiSeqGraph.setBarValue(3, float(IFLFrames)/float(maxFrames))
		else:
			self.guiSeqGraph.setBarText(3, "IFL Frames: None")
			self.guiSeqGraph.setBarValue(3, 0)
		
		if validateVisibility(seqName, seqPrefs):
			self.guiSeqGraph.setBarText(2, "Vis Frames:%i" % getNumVisFrames(seqName, seqPrefs))
			self.guiSeqGraph.setBarValue(2, float(visFrames)/float(maxFrames))
		else:
			self.guiSeqGraph.setBarText(2, "Vis Frames: None")
			self.guiSeqGraph.setBarValue(2, 0)
			
		self.guiSeqGraph.setBarText(1, "Tex Frames: N/A")
		self.guiSeqGraph.setBarText(0, "Mor Frames: N/A")
		self.guiSeqGraph.setBarValue(1, 0.0)
		self.guiSeqGraph.setBarValue(0, 0.0)

		if actFrames == maxFrames: self.guiSeqGraph.setBarColor(4, (0.4, 1.0, 0.4))
		else: self.guiSeqGraph.setBarColor(4, (1.0, float(actFrames)/float(maxFrames), 0.0))
		if IFLFrames == maxFrames: self.guiSeqGraph.setBarColor(3, (0.4, 1.0, 0.4))
		else: self.guiSeqGraph.setBarColor(3, (1.0, float(IFLFrames)/float(maxFrames), 0.0))
		if visFrames == maxFrames: self.guiSeqGraph.setBarColor(2, (0.4, 1.0, 0.4))
		else: self.guiSeqGraph.setBarColor(2, (1.0, float(visFrames)/float(maxFrames), 0.0))
		self.guiSeqGraph.setBarColor(1, (0.0, 0.0, 0.0))
		self.guiSeqGraph.setBarColor(0, (0.0, 0.0, 0.0))

	def clearBarChart(self):	
		self.guiSeqGraph.setBarText(4, "Act Frames:")
		self.guiSeqGraph.setBarText(3, "IFL Frames:")
		self.guiSeqGraph.setBarText(2, "Vis Frames:")
		self.guiSeqGraph.setBarText(1, "Tex Frames:")
		self.guiSeqGraph.setBarText(0, "Mor Frames:")
		self.guiSeqGraph.setBarValue(4, 0.0)
		self.guiSeqGraph.setBarValue(3, 0.0)
		self.guiSeqGraph.setBarValue(2, 0.0)
		self.guiSeqGraph.setBarValue(1, 0.0)
		self.guiSeqGraph.setBarValue(0, 0.0)
		self.guiSeqGraph.setBarColor(4, (0.4, 1.0, 0.4))
		self.guiSeqGraph.setBarColor(3, (0.4, 1.0, 0.4))
		self.guiSeqGraph.setBarColor(2, (0.4, 1.0, 0.4))
		self.guiSeqGraph.setBarColor(1, (0.4, 1.0, 0.4))
		self.guiSeqGraph.setBarColor(0, (0.4, 1.0, 0.4))


	def guiSequenceUpdateTriggers(self, triggerList, itemIndex):
		if (len(triggerList) == 0) or (itemIndex >= len(triggerList)):
			self.guiTriggerState.value = 1
			self.guiTriggerStateOn.state = False
			self.guiTriggerFrame.value = 1
		else:
			self.guiTriggerState.value = triggerList[itemIndex][0] # Trigger State			
			self.guiTriggerStateOn.state = triggerList[itemIndex][2] # On
			self.guiTriggerFrame.value = triggerList[itemIndex][1] # Time

	

	def handleTriggersEvent(self, control):
		if self.guiSeqList.itemIndex == -1:
			return

		seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
		seqPrefs = getSequenceKey(seqName)
		itemIndex = self.guiTriggerMenu.itemIndex

		if control.name == "guiTriggerMenu":
			self.guiSequenceUpdateTriggers(seqPrefs['Triggers'], itemIndex)
		elif control.name == "guiTriggerAdd":
			# Add
			seqPrefs['Triggers'].append([1, 1, True])
			self.guiTriggerMenu.items.append((self.triggerMenuTemplate % (1, 1)) + "(ON)")
			self.guiTriggerMenu.itemIndex = len(seqPrefs['Triggers'])-1
			self.guiSequenceUpdateTriggers(seqPrefs['Triggers'], self.guiTriggerMenu.itemIndex)
		elif (len(self.guiTriggerMenu.items) != 0):
			if control.name == "guiTriggerState":
				seqPrefs['Triggers'][itemIndex][0] = control.value
			elif control.name == "guiTriggerStateOn":
				seqPrefs['Triggers'][itemIndex][2] = control.state
			elif control.name == "guiTriggerFrame":
				seqPrefs['Triggers'][itemIndex][1] = control.value
			elif control.name == "guiTriggerDel":
				# Remove the trigger
				del seqPrefs['Triggers'][itemIndex]
				del self.guiTriggerMenu.items[itemIndex]
				# Must decrement itemIndex if we are out of bounds
				if itemIndex <= len(seqPrefs['Triggers']):
					self.guiTriggerMenu.itemIndex = len(seqPrefs['Triggers'])-1
					itemIndex = self.guiTriggerMenu.itemIndex
				self.guiSequenceUpdateTriggers(seqPrefs['Triggers'], itemIndex)

			# Update menu caption
			if itemIndex == -1:
				return
			if seqPrefs['Triggers'][itemIndex][2]: stateStr = "(ON)"
			else: stateStr = "(OFF)"
			self.guiTriggerMenu.items[itemIndex] = (self.triggerMenuTemplate % (seqPrefs['Triggers'][itemIndex][1], seqPrefs['Triggers'][itemIndex][0])) + stateStr

	def handleListItemEvent(self, control):
		global Prefs

		# Determine sequence name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / 2

		seqName = self.guiSeqList.controls[calcIdx].controls[0].label
		realItem = control.evt - 40 - (calcIdx*2)
		seqPrefs = getSequenceKey(seqName)

		if realItem == 0:
			seqPrefs['NoExport'] = not control.state
		elif realItem == 1:
			seqPrefs['Cyclic'] = control.state

	def createSequenceListItem(self, seqName):
		startEvent = self.curSeqListEvent

		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance of scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)

		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", seqName, None, None)
		guiName.x, guiName.y = 5, 5
		guiExport = Common_Gui.ToggleButton("guiExport", "Export", "Export Sequence", startEvent, self.handleListItemEvent, None)
		guiExport.x, guiExport.y = 105, 5
		guiExport.width, guiExport.height = 50, 15
		guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+1, self.handleListItemEvent, None)
		guiCyclic.x, guiCyclic.y = 157, 5
		guiCyclic.width, guiCyclic.height = 50, 15

		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiExport)
		guiContainer.addControl(guiCyclic)
		
		guiExport.state = not Prefs['Sequences'][seqName]['NoExport']
		guiCyclic.state = Prefs['Sequences'][seqName]['Cyclic']
		
		# increment the current event counter
		self.curSeqListEvent += 2
		
		return guiContainer

	def populateSequenceList(self):
		self.clearSequenceList()
		# loop through all actions in the preferences
		global Prefs
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seq = getSequenceKey(seqName)
			self.guiSeqList.addControl(self.createSequenceListItem(seqName))

	def clearSequenceList(self):
		for i in range(0, len(self.guiSeqList.controls)):
			del self.guiSeqList.controls[i].controls[:]
		del self.guiSeqList.controls[:]
		self.curSeqListEvent = 40
		self.guiSeqList.itemIndex = -1
		self.guiSeqList.scrollPosition = 0
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList) # Bit of a hack, but works

		
'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Actions sub-panel of the Sequences panel.
*
***************************************************************************************************
'''
class ActionControlsClass:
	def __init__(self):
		global guiSeqActSubtab
		global globalEvents
		
		
		
		# initialize GUI controls
		self.guiActTitle = Common_Gui.SimpleText("guiActTitle", "Action Sequences :", None, self.resize)
		self.guiSeqList = Common_Gui.ListContainer("guiSeqList", "sequence.list", self.handleListEvent, self.resize)		
		self.guiToggle = Common_Gui.ToggleButton("guiToggle", "Toggle All", "Toggle export of all sequences", 6, self.handleEvent, self.resize)
		self.guiRefresh = Common_Gui.BasicButton("guiRefresh", "Refresh", "Refresh list of sequences", 7, self.handleEvent, self.resize)
		self.guiSeqOpts = Common_Gui.BasicContainer("guiSeqOpts", "sequence.prefs", None, self.resize)
		self.guiOptsTitle = Common_Gui.SimpleText("guiOptsTitle", "Sequence: None Selected", None, self.resize)
		self.guiStartFrame = Common_Gui.NumberPicker("guiStartFrame", "Sta fr:", "When exporting the action, start with this frame #", 22, self.handleEvent, self.resize)
		self.guiEndFrame = Common_Gui.NumberPicker("guiEndFrame", "End fr:", "When exporting the action, end with this frame #", 23, self.handleEvent, self.resize)
		self.guiAutoFrames = Common_Gui.ToggleButton("guiAutoFrames", "Auto Start/End frames", "Automatically determine frame range", 24, self.handleEvent, self.resize)
		self.guiAutoSamples = Common_Gui.ToggleButton("guiAutoSamples", "Use all frames in range", "When turned on, every frame in the defined range is exported.", 25, self.handleEvent, self.resize)
		self.guiFrameSamples = Common_Gui.NumberPicker("guiFrameSamples", "Frame Samples", "Number of frames to export", 28, self.handleEvent, self.resize)
		self.guiGroundFrameSamples = Common_Gui.NumberPicker("guiGroundFrameSamples", "Ground Frames", "Amount of ground frames to export", 27, self.handleEvent, self.resize)
		self.guiBlendControlsBox = Common_Gui.BasicFrame("guiBlendControlsBox", None, None, None, None, self.resize)
		self.guiBlendSequence = Common_Gui.ToggleButton("guiBlendSequence", "Blend animation", "Export action as a Torque blend sequence", 8, self.handleEvent, self.resize)
		self.guiRefPoseTitle = Common_Gui.SimpleText("guiRefPoseTitle", "Ref Pose for ", None, self.resize)
		self.guiRefPoseMenu = Common_Gui.ComboBox("guiRefPoseMenu", "Use Action", "Select an action containing your refernce pose for this blend.", 20, self.handleEvent, self.resize)
		self.guiRefPoseFrame = Common_Gui.NumberPicker("guiRefPoseFrame", "Frame", "Frame to use for reference pose", 21, self.handleEvent, self.resize)
		
		# set initial states
		self.guiSeqList.fade_mode = 0
		self.guiToggle.state = False
		self.guiBlendSequence.state = False
		self.guiSeqOpts.enabled = False
		self.guiSeqOpts.fade_mode = 5
		self.guiSeqOpts.borderColor = None
		self.guiRefPoseTitle.visible = False
		self.guiRefPoseMenu.visible = False
		self.guiRefPoseFrame.visible = False
		self.guiRefPoseFrame.min = 1
		self.guiStartFrame.min = 1
		self.guiStartFrame.max = 65535
		self.guiEndFrame.min = 1
		self.guiEndFrame.max = 65535
		self.guiFrameSamples.min = 1
		
		# add controls to containers
		guiSeqActSubtab.addControl(self.guiActTitle)
		guiSeqActSubtab.addControl(self.guiSeqList)
		guiSeqActSubtab.addControl(self.guiToggle)
		guiSeqActSubtab.addControl(self.guiRefresh)
		guiSeqActSubtab.addControl(self.guiSeqOpts)
		self.guiSeqOpts.addControl(self.guiOptsTitle)
		self.guiSeqOpts.addControl(self.guiStartFrame)
		self.guiSeqOpts.addControl(self.guiEndFrame)
		self.guiSeqOpts.addControl(self.guiAutoFrames)
		self.guiSeqOpts.addControl(self.guiAutoSamples)
		self.guiSeqOpts.addControl(self.guiFrameSamples)
		self.guiSeqOpts.addControl(self.guiGroundFrameSamples) # 2
		self.guiSeqOpts.addControl(self.guiBlendControlsBox)
		self.guiSeqOpts.addControl(self.guiBlendSequence)
		self.guiSeqOpts.addControl(self.guiRefPoseTitle) # 12
		self.guiSeqOpts.addControl(self.guiRefPoseMenu) # 13
		self.guiSeqOpts.addControl(self.guiRefPoseFrame) # 14

		# populate actions list
		self.populateSequenceList()


		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiActTitle
		del self.guiSeqList
		del self.guiToggle
		del self.guiRefresh
		del self.guiSeqOpts
		del self.guiOptsTitle
		del self.guiStartFrame
		del self.guiEndFrame
		del self.guiAutoFrames
		del self.guiAutoSamples
		del self.guiFrameSamples
		del self.guiGroundFrameSamples
		del self.guiBlendControlsBox
		del self.guiBlendSequence
		del self.guiRefPoseTitle
		del self.guiRefPoseMenu
		del self.guiRefPoseFrame

	
	def refreshAll(self):		
		# store last sequence selection
		seqName = None
		seqPrefs = None
		if self.guiSeqList.itemIndex != -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
		
		# repopulate the sequence list
		cleanKeys()
		createActionKeys()
		self.populateSequenceList()
		
		# restore last sequence selection
		for itemIndex in range(0, len(self.guiSeqList.controls)):
			if self.guiSeqList.controls[itemIndex].controls[0].label == seqName:
				self.guiSeqList.selectItem(itemIndex)
				self.guiSeqList.scrollToSelectedItem()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
				return
		self.guiSeqList.selectItem(0)
		self.guiSeqList.scrollToSelectedItem()
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)

			
	# This method validates the current control states, adjusts preference values, and generally keeps everything consistent
	def updateSequenceControls(self, seqName, seqPrefs):
		# update affected preferences
		if not seqPrefs['Action']['AutoFrames']:
			seqPrefs['Action']['EndFrame'] = self.guiEndFrame.value
			seqPrefs['Action']['StartFrame'] = self.guiStartFrame.value
		else:
			seqPrefs['Action']['StartFrame'] = 1
			action = Blender.Armature.NLA.GetActions()[seqName]
			seqPrefs['Action']['EndFrame'] = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
		try:
			action = Blender.Armature.NLA.GetActions()[seqName]
			maxFrames = (seqPrefs['Action']['EndFrame'] - seqPrefs['Action']['StartFrame']) + 1
		except:
			maxFrames = 0
		if seqPrefs['Action']['FrameSamples'] > maxFrames or seqPrefs['Action']['AutoSamples']: seqPrefs['Action']['FrameSamples'] = maxFrames
		if seqPrefs['Action']['NumGroundFrames'] > maxFrames: seqPrefs['Action']['NumGroundFrames'] = maxFrames

		# refresh control states
		self.guiFrameSamples.max = maxFrames
		self.guiFrameSamples.value = seqPrefs['Action']['FrameSamples']
		self.guiGroundFrameSamples.max = maxFrames
		self.guiGroundFrameSamples.value = seqPrefs['Action']['NumGroundFrames']
		self.guiEndFrame.min = seqPrefs['Action']['StartFrame']
		self.guiEndFrame.value = seqPrefs['Action']['EndFrame']
		self.guiStartFrame.max = seqPrefs['Action']['EndFrame']
		self.guiStartFrame.value = seqPrefs['Action']['StartFrame']

	def clearSequenceControls(self):
		# refresh control states
		self.guiFrameSamples.value = 0
		self.guiGroundFrameSamples.value = 0
		self.guiEndFrame.value = 0
		self.guiStartFrame.value = 0
		self.guiAutoFrames.state = False
		self.guiAutoSamples.state = False
		self.guiOptsTitle.label = "Sequence: None Selected"
		self.guiBlendSequence.state = False
		self.guiRefPoseTitle.visible = False
		self.guiRefPoseMenu.visible = False
		self.guiRefPoseFrame.visible = False

	
	def handleEvent(self, control):
		global guiSeqOpts, guiSeqList

		if control.name == "guiToggle":
			for child in self.guiSeqList.controls:
				child.controls[1].state = control.state
				getSequenceKey(child.controls[0].label)['NoExport'] = not control.state
		elif control.name == "guiRefresh":
			self.refreshAll()
		else:
			if self.guiSeqList.itemIndex != -1:
				seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
				seqPrefs = getSequenceKey(seqName)
				# blend ref pose selection
				if control.name == "guiBlendSequence":
					seqPrefs['Action']['Blend'] = control.state					
					# if blend is true, show the ref pose controls
					if seqPrefs['Action']['Blend'] == True:
						self.guiRefPoseTitle.visible = True
						self.guiRefPoseMenu.visible = True
						self.guiRefPoseFrame.visible = True
						# reset max to raw number of frames in ref pose action
						try:
							action = Blender.Armature.NLA.GetActions()[seqPrefs['Action']['BlendRefPoseAction']]
							maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
						except: maxNumFrames = 1
						self.guiRefPoseFrame.max = maxNumFrames
					else:
						self.guiRefPoseTitle.visible = False
						self.guiRefPoseMenu.visible = False
						self.guiRefPoseFrame.visible = False
					

				elif control.name == "guiRefPoseMenu":
					seqPrefs['Action']['BlendRefPoseAction'] = control.items[control.itemIndex]
					seqPrefs['Action']['BlendRefPoseFrame'] = 1
					# reset max to raw number of frames in ref pose action
					try:
						action = Blender.Armature.NLA.GetActions()[seqPrefs['Action']['BlendRefPoseAction']]
						maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
					except: maxNumFrames = 1
					self.guiRefPoseFrame.max = maxNumFrames
					self.guiRefPoseFrame.value = seqPrefs['Action']['BlendRefPoseFrame']					
				elif control.name == "guiRefPoseFrame":
					seqPrefs['Action']['BlendRefPoseFrame'] = control.value
				elif control.name == "guiStartFrame":
					self.updateSequenceControls(seqName, seqPrefs)
				elif control.name == "guiEndFrame":
					self.updateSequenceControls(seqName, seqPrefs)
				elif control.name == "guiAutoFrames":
					seqPrefs['Action']['AutoFrames'] = control.state
					if seqPrefs['Action']['AutoFrames']:
						self.guiEndFrame.enabled = False
						self.guiStartFrame.enabled = False
					else:
						self.guiEndFrame.enabled = True
						self.guiStartFrame.enabled = True
					self.updateSequenceControls(seqName, seqPrefs)					
				elif control.name == "guiAutoSamples":
					seqPrefs['Action']['AutoSamples'] = control.state
					if seqPrefs['Action']['AutoSamples']:
						self.guiFrameSamples.enabled = False
					else:
						self.guiFrameSamples.enabled = True
					self.updateSequenceControls(seqName, seqPrefs)
				elif control.name == "guiFrameSamples":
					seqPrefs['Action']['FrameSamples'] = control.value
				elif control.name == "guiGroundFrameSamples":
					seqPrefs['Action']['NumGroundFrames'] = control.value


	# This method handles list events (list item selection changed)
	def handleListEvent(self, control):
		if control.itemIndex != -1:
			seqName = control.controls[control.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			self.guiSeqOpts.enabled = True
			self.guiOptsTitle.label = "Sequence '%s'" % seqName
			try:
				action = Blender.Armature.NLA.GetActions()[seqName]
				maxNumFrames = (seqPrefs['Action']['EndFrame'] - seqPrefs['Action']['StartFrame']) + 1
			except:
				maxNumFrames = 0

			# Update gui control states
			# make sure the user didn't delete the action containing the refrence pose
			# out from underneath us while we weren't looking.
			if seqPrefs['Action']['FrameSamples'] > maxNumFrames:
				seqPrefs['Action']['FrameSamples'] = maxNumFrames
			try: blah = Blender.Armature.NLA.GetActions()[seqPrefs['Action']['BlendRefPoseAction']]
			except: seqPrefs['Action']['BlendRefPoseAction'] = seqName
			self.guiRefPoseTitle.label = "Ref pose for '%s'" % seqName
			self.guiRefPoseMenu.setTextValue(seqPrefs['Action']['BlendRefPoseAction'])
			self.guiRefPoseFrame.min = 1
			# reset max to raw number of frames in ref pose action
			try:
				action = Blender.Armature.NLA.GetActions()[seqPrefs['Action']['BlendRefPoseAction']]
				maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
			except: maxNumFrames = 1
			self.guiRefPoseFrame.max = maxNumFrames
			self.guiRefPoseFrame.value = seqPrefs['Action']['BlendRefPoseFrame']
			self.guiGroundFrameSamples.value = seqPrefs['Action']['NumGroundFrames']
			self.guiGroundFrameSamples.max = maxNumFrames
			self.guiFrameSamples.value = seqPrefs['Action']['FrameSamples']
			self.guiFrameSamples.max = maxNumFrames
			self.guiStartFrame.value = seqPrefs['Action']['StartFrame']
			self.guiEndFrame.value = seqPrefs['Action']['EndFrame']
			self.guiEndFrame.min = seqPrefs['Action']['StartFrame']
			self.guiStartFrame.max = seqPrefs['Action']['EndFrame']
			self.guiAutoFrames.state = seqPrefs['Action']['AutoFrames']
			self.guiAutoSamples.state = seqPrefs['Action']['AutoSamples']

			self.updateSequenceControls(seqName, seqPrefs)


			if seqPrefs['Action']['AutoFrames']:
				self.guiEndFrame.enabled = False
				self.guiStartFrame.enabled = False
			else:
				self.guiEndFrame.enabled = True
				self.guiStartFrame.enabled = True

			if seqPrefs['Action']['AutoSamples']:
				self.guiFrameSamples.enabled = False
			else:
				self.guiFrameSamples.enabled = True

			# show/hide ref pose stuff.
			self.guiBlendSequence.state = seqPrefs['Action']['Blend']
			if seqPrefs['Action']['Blend'] == True:				
				self.guiRefPoseTitle.visible = True
				self.guiRefPoseMenu.visible = True
				self.guiRefPoseFrame.visible = True
			else:
				self.guiRefPoseTitle.visible = False
				self.guiRefPoseMenu.visible = False
				self.guiRefPoseFrame.visible = False

		else:
			self.clearSequenceControls()
			self.guiSeqOpts.enabled = False



	def resize(self, control, newwidth, newheight):
		if control.name == "guiSeqList":
			control.x = 10
			control.y = 30
			control.height = newheight - 70
			control.width = 300
		elif control.name == "guiActTitle":
			control.x = 10
			control.y = newheight-25
		elif control.name == "guiSeqOpts":
			control.x = newwidth - 180
			control.y = 0
			control.width = 180
			control.height = newheight
		elif control.name == "guiOptsTitle":
			control.x = 5
			control.y = newheight - 25
		# Sequence options
		elif control.name == "guiAutoFrames":
			control.x = 5
			control.y = newheight - 70
			control.width = newwidth - 10
		elif control.name == "guiStartFrame":
			control.x = 5
			control.y = newheight - 92
			control.width = 83
		elif control.name == "guiEndFrame":
			control.x = 90
			control.y = newheight - 92
			control.width = 83
		elif control.name == "guiAutoSamples":
			control.x = 5
			control.y = newheight - 125
			control.width = newwidth - 10
		elif control.name == "guiFrameSamples":
			control.x = 5
			control.y = newheight - 147
			control.width = newwidth - 10
		elif control.name == "guiGroundFrameSamples":
			control.x = 5
			control.y = newheight - 197
			control.width = newwidth - 10
		elif control.name == "guiBlendSequence":
			control.x = 10
			control.width = newwidth - 20
			control.y = newheight - 246
		elif control.name == "guiBlendControlsBox":
			control.x = 5
			control.y = newheight - 323
			control.width = newwidth - 10
			control.height = 89
		elif control.name == "guiRefPoseTitle":
			control.x = 8
			control.y = newheight - 263
		elif control.name == "guiRefPoseMenu":
			control.x = 8
			control.y = newheight - 293
			control.width = (newwidth) - 16
		elif control.name == "guiRefPoseFrame":
			control.x = 8
			control.y = newheight - 318
			control.width = (newwidth) - 16
		# Sequence list buttons
		elif control.name == "guiToggle":
			control.x = 10
			control.y = 5
			control.width = 100
		elif control.name == "guiRefresh":
			control.x = 112
			control.y = 5
			control.width = 100

	
	def populateSequenceList(self):
		self.clearSequenceList()
		actions = Armature.NLA.GetActions()
		keys = actions.keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))

		# There are a finite number of events we can allocate in blender, so we need to
		# assign events in batches of the maximum number of visible list items.
		startEvent = 40
		for key in keys:
			# skip the fake action (hack for blender 2.41 bug)
			if key == "DTSEXPFAKEACT": continue		
			self.guiSeqList.addControl(self.createSequenceListItem(key, startEvent))
			startEvent += 3
			# add any new animations to the ref pose combo box
			if not (key in self.guiRefPoseMenu.items):
				self.guiRefPoseMenu.items.append(key)

	def clearSequenceList(self):

		for i in range(0, len(self.guiSeqList.controls)):
			del self.guiSeqList.controls[i].controls[:]
		del self.guiSeqList.controls[:]

		self.guiSeqList.itemIndex = -1
		self.guiSeqList.scrollPosition = 0
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList) # Bit of a hack, but works

	def handleListItemEvent(self, control):
		global Prefs

		# Determine sequence name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / 3

		seqName = self.guiSeqList.controls[calcIdx].controls[0].label
		realItem = control.evt - 40 - (calcIdx*3)
		seqPrefs = getSequenceKey(seqName)

		if realItem == 0:
			seqPrefs['NoExport'] = not control.state
		elif realItem == 1:
			seqPrefs['Dsq'] = control.state
		elif realItem == 2:
			seqPrefs['Cyclic'] = control.state

	def createSequenceListItem(self, seq_name, startEvent):
		seqPrefs = getSequenceKey(seq_name)
		seqPrefs['Action']['Enabled'] = True
		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)

		# testing new fade modes for sequence list items
		#guiContainer.fade_mode = 8  # same as 2 but with a brighter endcolor, easier on the eyes.
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", seq_name, None, None)
		guiName.x, guiName.y = 5, 5
		guiExport = Common_Gui.ToggleButton("guiExport", "Export", "Export Sequence", startEvent, self.handleListItemEvent, None)
		guiExport.x, guiExport.y = 122, 5
		guiExport.width, guiExport.height = 50, 15
		guiExport.state = not seqPrefs['NoExport']
		guiDSQ = Common_Gui.ToggleButton("guiDSQ", "Dsq", "Export Sequence as DSQ", startEvent+1, self.handleListItemEvent, None)
		guiDSQ.x, guiDSQ.y = 174, 5
		guiDSQ.width, guiDSQ.height = 50, 15
		guiDSQ.state = seqPrefs['Dsq']
		guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+2, self.handleListItemEvent, None)
		guiCyclic.x, guiCyclic.y = 226, 5
		guiCyclic.width, guiCyclic.height = 50, 15
		guiCyclic.state = seqPrefs['Cyclic']

		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiExport)
		guiContainer.addControl(guiDSQ)
		guiContainer.addControl(guiCyclic)

		return guiContainer


'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the IFL sub-panel of the Sequences panel.
*
***************************************************************************************************
'''
class IFLControlsClass:
	def __init__(self):
		global guiSequenceIFLSubtab		
		global globalEvents

		# panel state
		self.curSeqListEvent = 40

		# initialize GUI controls
		self.guiSeqList = Common_Gui.ListContainer("guiSeqList", "sequence.list", self.handleListEvent, self.resize)
		self.guiSeqName = Common_Gui.TextBox("guiSeqName", "Sequence Name: ", "Name of the Current Sequence", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqAdd = Common_Gui.BasicButton("guiSeqAdd", "Add", "Add new IFL Sequence with the given name", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqDel = Common_Gui.BasicButton("guiSeqDel", "Del", "Delete Selected IFL Sequence", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqRename = Common_Gui.BasicButton("guiSeqRename", "Rename", "Rename Selected IFL Sequence to the given name", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqAddToExistingTxt = Common_Gui.SimpleText("guiSeqAddToExistingTxt", "Add IFL Animation to existing Sequence:", None, self.resize)
		self.guiSeqExistingSequences = Common_Gui.ComboBox("guiSeqExistingSequences", "Sequence", "Select a Sequence from this list to which to add an IFL Animation", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqAddToExisting = Common_Gui.BasicButton("guiSeqAddToExisting", "Add IFL", "Add an IFL Animation to an existing sequence.", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqListTitle = Common_Gui.SimpleText("guiSeqListTitle", "IFL Sequences:", None, self.resize)
		self.guiSeqOptsContainerTitle = Common_Gui.SimpleText("guiSeqOptsContainerTitle", "Sequence: None Selected", None, self.resize)
		self.guiSeqOptsContainer = Common_Gui.BasicContainer("guiSeqOptsContainer", "guiSeqOptsContainer", None, self.resize)
		self.guiMatTxt = Common_Gui.SimpleText("guiMatTxt", "Select IFL Material:", None, self.resize)
		self.guiMat = Common_Gui.ComboBox("guiMat", "IFL Material", "Select a Material from this list to use in the IFL Animation", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiNumImagesTxt = Common_Gui.SimpleText("guiNumImagesTxt", "Number of Images:", None, self.resize)
		self.guiNumImages = Common_Gui.NumberPicker("guiNumImages", "Images", "Number of Images in the IFL animation", globalEvents.getNewID(), self.handleGuiNumImagesEvent, self.resize)
		self.guiFramesListTxt = Common_Gui.SimpleText("guiFramesListTxt", "IFL Image Frames:", None, self.resize)
		self.guiFramesList = Common_Gui.ListContainer("guiFramesList", "", self.handleFrameListEvent, self.resize)
		self.guiFramesListSelectedTxt = Common_Gui.SimpleText("guiFramesListSelectedTxt", "Selected:", None, self.resize)
		self.guiNumFrames = Common_Gui.NumberPicker("guiNumFrames", "Frames", "Hold Selected image for n frames", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiApplyToAll = Common_Gui.BasicButton("guiApplyToAll", "Apply to all", "Apply current frame display value to all IFL images", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiWriteIFLFile = Common_Gui.ToggleButton("guiWriteIFLFile", "Write .ifl file", "Write .ifl file for this sequence to disk on export.", globalEvents.getNewID(), self.handleEvent, self.resize)

		# set initial states
		self.guiSeqOptsContainer.enabled = False
		self.guiSeqOptsContainer.fade_mode = 5
		self.guiSeqOptsContainer.borderColor = None
		self.guiSeqList.fade_mode = 0
		self.guiFramesList.enabled = True
		self.guiNumImages.min = 1
		self.guiNumFrames.min = 1
		self.guiNumImages.value = 1
		self.guiNumFrames.value = 1
		self.guiNumFrames.max = 65535 # <- reasonable?  I wonder if anyone wants to do day/night cycles with IFL? - Joe G.
		self.guiWriteIFLFile.state = False

		# add controls to containers
		guiSequenceIFLSubtab.addControl(self.guiSeqList)
		guiSequenceIFLSubtab.addControl(self.guiSeqName)
		guiSequenceIFLSubtab.addControl(self.guiSeqAdd)
		guiSequenceIFLSubtab.addControl(self.guiSeqDel)
		guiSequenceIFLSubtab.addControl(self.guiSeqRename)
		guiSequenceIFLSubtab.addControl(self.guiSeqAddToExistingTxt)
		guiSequenceIFLSubtab.addControl(self.guiSeqExistingSequences)
		guiSequenceIFLSubtab.addControl(self.guiSeqAddToExisting)
		guiSequenceIFLSubtab.addControl(self.guiSeqListTitle)
		guiSequenceIFLSubtab.addControl(self.guiSeqOptsContainerTitle)
		guiSequenceIFLSubtab.addControl(self.guiSeqOptsContainer)
		self.guiSeqOptsContainer.addControl(self.guiMatTxt)
		self.guiSeqOptsContainer.addControl(self.guiMat)
		self.guiSeqOptsContainer.addControl(self.guiNumImagesTxt)
		self.guiSeqOptsContainer.addControl(self.guiNumImages)
		self.guiSeqOptsContainer.addControl(self.guiFramesListTxt)
		self.guiSeqOptsContainer.addControl(self.guiFramesList)
		self.guiSeqOptsContainer.addControl(self.guiFramesListSelectedTxt)
		self.guiSeqOptsContainer.addControl(self.guiNumFrames)
		self.guiSeqOptsContainer.addControl(self.guiApplyToAll)
		self.guiSeqOptsContainer.addControl(self.guiWriteIFLFile)
		
		# populate the IFL sequence list
		self.populateSequenceList()
		
		# populate the ifl material pulldown
		self.populateIFLMatPulldown()
		
		# populate the existing sequences pulldown.
		self.populateExistingSeqPulldown()
	
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiSeqList
		del self.guiSeqName
		del self.guiSeqAdd
		del self.guiSeqDel
		del self.guiSeqRename
		del self.guiSeqAddToExistingTxt
		del self.guiSeqExistingSequences
		del self.guiSeqAddToExisting
		del self.guiSeqListTitle
		del self.guiSeqOptsContainerTitle
		del self.guiSeqOptsContainer
		del self.guiMatTxt
		del self.guiMat
		del self.guiNumImagesTxt
		del self.guiNumImages
		del self.guiFramesListTxt
		del self.guiFramesList
		del self.guiFramesListSelectedTxt
		del self.guiNumFrames
		del self.guiApplyToAll
		del self.guiWriteIFLFile


	# called when we switch to this control page to make sure everything is in sync.
	def refreshAll(self):
		# store last sequence selection
		seqName = None
		seqPrefs = None
		if self.guiSeqList.itemIndex != -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
		
		# repopulate the sequence list
		cleanKeys()
		createActionKeys()
		self.populateSequenceList()
		self.populateExistingSeqPulldown()

		
		# restore last sequence selection
		for itemIndex in range(0, len(self.guiSeqList.controls)):
			if self.guiSeqList.controls[itemIndex].controls[0].label == seqName:
				self.guiSeqList.selectItem(itemIndex)
				self.guiSeqList.scrollToSelectedItem()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
				return
		self.guiSeqList.selectItem(0)
		self.guiSeqList.scrollToSelectedItem()
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
		

	def resize(self, control, newwidth, newheight):
		# handle control resize events.
		if control.name == "guiSeqList":
			control.x, control.y, control.height, control.width = 10,100, newheight - 140,230
		elif control.name == "guiSeqName":
			control.x, control.y, control.height, control.width = 10,75, 20,230
		elif control.name == "guiSeqAdd":
			control.x, control.y, control.height, control.width = 10,53, 20,75
		elif control.name == "guiSeqDel":
			control.x, control.y, control.height, control.width = 87,53, 20,75
		elif control.name == "guiSeqRename":
			control.x, control.y, control.height, control.width = 164,53, 20,76
		elif control.name == "guiSeqAddToExistingTxt":
			control.x, control.y, control.height, control.width = 10,38, 20,230
		elif control.name == "guiSeqExistingSequences":
			control.x, control.y, control.height, control.width = 10,11, 20,145
		elif control.name == "guiSeqAddToExisting":
			control.x, control.y, control.height, control.width = 157,11, 20,82
		elif control.name == "guiSeqListTitle":			
			control.x, control.y, control.height, control.width = 10,310, 20,82
		elif control.name == "guiSeqOptsContainer":
			control.x, control.y, control.height, control.width = 241,0, 334,249
		elif control.name == "guiSeqOptsContainerTitle":
			control.x, control.y, control.height, control.width = 250,310, 20,82
		elif control.name == "guiMatTxt":
			control.x, control.y, control.height, control.width = 10,278, 20,120
		elif control.name == "guiMat":
			control.x, control.y, control.height, control.width = 125,275, 20,120
		elif control.name == "guiNumImagesTxt":
			control.x, control.y, control.height, control.width = 10,256, 20,120
		elif control.name == "guiNumImages":
			control.x, control.y, control.height, control.width = 125,253, 20,120
		elif control.name == "guiSeqIFLFrame":
			control.x, control.y, control.height, control.width = 64,211, 20,120
		elif control.name == "guiSeqIFLImageBox":
			control.x, control.y, control.height, control.width = 4,5, 220,241
		elif control.name == "guiSeqImageName":
			control.x, control.y, control.height, control.width = 15,183, 20,219
		elif control.name == "guiFramesListTxt":
			control.x, control.y, control.height, control.width = 10,232, 20,120
		elif control.name == "guiFramesList":
			control.x, control.y, control.height, control.width = 20,52, 173,223
		elif control.name == "guiFramesListSelectedTxt":
			control.x, control.y, control.height, control.width = 20,34, 20,120
		elif control.name == "guiNumFrames":
			control.x, control.y, control.height, control.width = 75,29, 20,85
		elif control.name == "guiApplyToAll":
			control.x, control.y, control.height, control.width = 164,29, 20,80
		elif control.name == "guiWriteIFLFile":
			control.x, control.y, control.height, control.width = 20,5, 20,223
		

	def createSequenceListItem(self, seqName):
		startEvent = self.curSeqListEvent

		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance of scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)

		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", seqName, None, None)
		guiName.x, guiName.y = 5, 5
		guiExport = Common_Gui.ToggleButton("guiExport", "Export", "Export Sequence", startEvent, self.handleListItemEvent, None)
		guiExport.x, guiExport.y = 105, 5
		guiExport.width, guiExport.height = 50, 15
		guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+1, self.handleListItemEvent, None)
		guiCyclic.x, guiCyclic.y = 157, 5
		guiCyclic.width, guiCyclic.height = 50, 15

		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiExport)
		guiContainer.addControl(guiCyclic)
		
		guiExport.state = not Prefs['Sequences'][seqName]['NoExport']
		guiCyclic.state = Prefs['Sequences'][seqName]['Cyclic']
		
		# increment the current event counter
		self.curSeqListEvent += 2
		
		return guiContainer

	def createFramesListItem(self, matName, holdFrames = 1):
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", matName, None, None)
		guiName.x, guiName.y = 5, 5
		guiHoldFrames = Common_Gui.SimpleText("", "fr:"+ str(holdFrames), None, None)
		guiHoldFrames.x, guiHoldFrames.y = 170, 5

		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiHoldFrames)
		return guiContainer
	
	# add a new IFL sequence in the GUI and the prefs
	def AddNewIFLSeq(self, seqName):
		seq = getSequenceKey(seqName)

		# add ifl stuff
		seq['IFL'] = {}
		seq['IFL']['Enabled'] = True
		seq['IFL']['Material'] = None
		seq['IFL']['NumImages'] = 1
		seq['IFL']['TotalFrames'] = 1
		seq['IFL']['IFLFrames'] = []
		seq['IFL']['WriteIFLFile'] = True

		# add sequence to GUI sequence list		
		self.guiSeqList.addControl(self.createSequenceListItem(seqName))
		self.populateSequenceList()
		# restore last sequence selection
		for itemIndex in range(0, len(self.guiSeqList.controls)):
			if self.guiSeqList.controls[itemIndex].controls[0].label == seqName:
				self.guiSeqList.selectItem(itemIndex)
		self.guiSeqList.scrollToSelectedItem()
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)

		self.guiSeqOptsContainer.enabled = True
		# refresh the Image frames list
		self.clearImageFramesList()
		self.populateImageFramesList(seqName)
	

	def determineIFLMatStartNumber(self, matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		digitPortion = matName[i:len(matName)]
		if len(digitPortion) > 0:
			return int(digitPortion)
		else:
			return 0
	
	def determineIFLMatNumberPadding(self, matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		digitPortion = matName[i:len(matName)]
		return len(matName) - i

	def numToPaddedString(self, num, padding):
		retVal = '0' * (padding - len(str(num)))
		retVal += str(num)
		return retVal

	def getIFLMatTextPortion(self, matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		textPortion = matName[0:i]
		if len(textPortion) > 0:
			return textPortion
		else:
			return ""
	def handleGuiNumImagesEvent(self, control):
		if self.guiMat.itemIndex < 0:
			control.value = 1
			return
		guiSeqList = self.guiSeqList
		guiMat = self.guiMat
		guiFramesList = self.guiFramesList
		seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
		matName = guiMat.getSelectedItemString()
		seqPrefs = getSequenceKey(seqName)
		seqPrefs['IFL']['NumImages'] = control.value			
		startNum = self.determineIFLMatStartNumber(matName)
		textPortion = self.getIFLMatTextPortion(matName)
		numPadding = self.determineIFLMatNumberPadding(matName)			
		fr = seqPrefs['IFL']['IFLFrames']
		while len(fr) > control.value:				
			del fr[len(fr)-1]
			self.removeLastItemFromFrameList()
		i = len(guiFramesList.controls)
		while len(guiFramesList.controls) < control.value:
			newItemName = textPortion + self.numToPaddedString(startNum + i, numPadding)
			guiFramesList.addControl(self.createFramesListItem(newItemName, self.guiNumFrames.value))
			Prefs['Sequences'][seqName]['IFL']['IFLFrames'].append([newItemName, self.guiNumFrames.value])
			i += 1

	def handleEvent(self, control):
		if control.name == "guiSeqName":
			pass
		elif control.name == "guiSeqAdd":
			if validateSequenceName(self.guiSeqName.value, "IFL"):
				self.guiSeqExistingSequences.selectStringItem(self.guiSeqName.value)
				self.AddNewIFLSeq(self.guiSeqName.value)
				# remove from existing sequences list if this sequence already exists			
				if self.guiSeqExistingSequences.itemIndex != -1:
					del self.guiSeqExistingSequences.items[self.guiSeqExistingSequences.itemIndex]
				self.guiSeqExistingSequences.selectStringItem("")
		elif control.name == "guiSeqDel":
			guiSeqList = self.guiSeqList
			if guiSeqList.itemIndex > -1 and guiSeqList.itemIndex < len(guiSeqList.controls):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				seqKey = getSequenceKey(seqName)
				guiSeqList.removeItem(guiSeqList.itemIndex)
				seqKey['IFL']['Enabled'] = False
				if seqKey['Action']['Enabled'] == True or seqKey['Vis']['Enabled'] == True:
					self.guiSeqExistingSequences.items.append(seqName)
				else:
					del Prefs['Sequences'][seqName]		
				self.populateSequenceList()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)

		elif control.name == "guiSeqRename":
			guiSeqList = self.guiSeqList
			seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
			newName = self.guiSeqName.value
			# Move sequence values to new key and delete the old.
			if guiSeqList.itemIndex < 0:
				message = "No IFL animation was selected.%t|Cancel"
				Blender.Draw.PupMenu(message)
				return
			if validateSequenceName(newName, "IFL", seqName):
				renameSequence(seqName, newName)
				self.populateSequenceList()
				# restore last sequence selection
				for itemIndex in range(0, len(self.guiSeqList.controls)):
					if self.guiSeqList.controls[itemIndex].controls[0].label == newName:
						self.guiSeqList.selectItem(itemIndex)
				self.guiSeqList.scrollToSelectedItem()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
		elif control.name == "guiSeqAddToExisting":
			existingSequences = self.guiSeqExistingSequences
			itemIndex = existingSequences.itemIndex
			if itemIndex >=0 and itemIndex < len(existingSequences.items):
				existingName = existingSequences.getSelectedItemString()
				if validateSequenceName(existingName, "IFL"):
					self.AddNewIFLSeq(existingName)
					del existingSequences.items[itemIndex]
					existingSequences.selectStringItem("")
					self.populateSequenceList()
					for itemIndex in range(0, len(self.guiSeqList.controls)):
						if self.guiSeqList.controls[itemIndex].controls[0].label == existingName:
							self.guiSeqList.selectItem(itemIndex)
					#self.guiSeqList.selectItem(existingName)
					self.guiSeqList.scrollToSelectedItem()
					if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)

		elif control.name == "guiMat":
			guiSeqList = self.guiSeqList
			guiMat = self.guiMat
			itemIndex = guiMat.itemIndex
			# set the pref for the selected sequence
			if guiSeqList.itemIndex > -1 and itemIndex >=0 and itemIndex < len(guiMat.items):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				if Prefs['Sequences'][seqName]['IFL']['Material'] != control.getSelectedItemString():
					Prefs['Sequences'][seqName]['IFL']['Material'] = control.getSelectedItemString()
					# replace existing frame names with new ones					
					guiFramesList = self.guiFramesList
					matName = guiMat.getSelectedItemString()
					seqPrefs = getSequenceKey(seqName)
					startNum = self.determineIFLMatStartNumber(matName)
					textPortion = self.getIFLMatTextPortion(matName)
					numPadding = self.determineIFLMatNumberPadding(matName)
					i = 0
					while i < self.guiNumImages.value:
						newItemName = textPortion + self.numToPaddedString(startNum + i, numPadding)
						guiFramesList.addControl(self.createFramesListItem(newItemName))
						try: Prefs['Sequences'][seqName]['IFL']['IFLFrames'][i][0] = newItemName
						except IndexError: Prefs['Sequences'][seqName]['IFL']['IFLFrames'].append([newItemName, 1])
						i += 1
					# add initial image frame
					self.handleGuiNumImagesEvent(self.guiNumImages)
					self.clearImageFramesList()
					self.populateImageFramesList(seqName)			
		elif control.name == "guiNumFrames":			
			guiSeqList = self.guiSeqList
			guiFramesList = self.guiFramesList
			if guiFramesList.itemIndex > -1:
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				seqPrefs = getSequenceKey(seqName)
				itemIndex = guiFramesList.itemIndex
				seqPrefs['IFL']['IFLFrames'][itemIndex][1] = control.value
				guiFramesList.controls[guiFramesList.itemIndex].controls[1].label = "fr:" + str(control.value)
				if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works
		elif control.name == "guiApplyToAll":
			guiSeqList = self.guiSeqList
			guiFramesList = self.guiFramesList
			seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			itemIndex = guiFramesList.itemIndex
			for i in range(0, len(seqPrefs['IFL']['IFLFrames'])):				
				seqPrefs['IFL']['IFLFrames'][i][1] = self.guiNumFrames.value
				guiFramesList.controls[i].controls[1].label = "fr:" + str(self.guiNumFrames.value)
			if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works
		elif control.name == "guiWriteIFLFile":
			if self.guiSeqList.itemIndex > -1:
				seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
				seqPrefs = getSequenceKey(seqName)
				seqPrefs['IFL']['WriteIFLFile'] = control.state
		
	# called when an item is selected in the sequence list
	def handleListEvent(self, control):
		if control.itemIndex < 0:
			self.guiSeqName.value = ""
			self.guiMat.selectStringItem("")
			self.guiNumImages.value = 1
			self.guiNumFrames.value = 1
			self.clearImageFramesList()
			self.guiNumFrames.value = 1
			self.guiSeqOptsContainer.enabled = False
			self.guiSeqOptsContainerTitle.label = "Sequence: None Selected"
			self.guiWriteIFLFile.state = False			
		else:
			self.guiSeqOptsContainer.enabled = True
			seqName = control.controls[control.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			self.guiSeqName.value = seqName 
			self.guiMat.selectStringItem(seqPrefs['IFL']['Material'])
			self.guiNumImages.value = seqPrefs['IFL']['NumImages']
			try: self.guiNumFrames.value = seqPrefs['IFL']['IFLFrames'][1]
			except: self.guiNumFrames.value = 1
			self.populateImageFramesList(seqName)
			self.guiSeqOptsContainerTitle.label = ("Sequence: %s" % seqName)
			self.guiWriteIFLFile.state = seqPrefs['IFL']['WriteIFLFile']

	
	def handleListItemEvent(self, control):
		# Determine sequence name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / 2
		seqName = self.guiSeqList.controls[calcIdx].controls[0].label
		realItem = control.evt - 40 - (calcIdx*2)
		seqPrefs = getSequenceKey(seqName)
		if realItem == 0:
			seqPrefs['NoExport'] = not control.state
		elif realItem == 1:
			seqPrefs['Cyclic'] = control.state

	
	# called when an item is selected in the IFL image frames list
	def handleFrameListEvent(self, control):
		guiFramesList = self.guiFramesList
		guiNumFrames = self.guiNumFrames
		if control.itemIndex > -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			guiNumFrames.value = seqPrefs['IFL']['IFLFrames'][control.itemIndex][1]
		else:
			guiNumFrames.value = 1
		

	def populateSequenceList(self):
		self.clearIFLList()
		# loop through all actions in the preferences and check for IFL animations
		global Prefs
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seq = getSequenceKey(seqName)
			if seq['IFL']['Enabled'] == True:
				self.guiSeqList.addControl(self.createSequenceListItem(seqName))

	def clearIFLList(self):
		for i in range(0, len(self.guiSeqList.controls)):
			del self.guiSeqList.controls[i].controls[:]
		del self.guiSeqList.controls[:]
		self.curSeqListEvent = 40
		self.guiSeqList.itemIndex = -1
		self.guiSeqList.scrollPosition = 0
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList) # Bit of a hack, but works

	

	def populateExistingSeqPulldown(self):
		self.clearExistingSeqPulldown()
		# loop through all actions in the preferences and check for sequences without IFL animations
		global Prefs
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seq = getSequenceKey(seqName)
			if seq['IFL']['Enabled'] == False:
				self.guiSeqExistingSequences.items.append(seqName)

	def clearExistingSeqPulldown(self):
		self.guiSeqExistingSequences.itemsIndex = -1
		self.guiSeqExistingSequences.items = []	
	
	def populateIFLMatPulldown(self):
		self.clearIFLMatPulldown()
		# loop through all materials in the preferences and check for IFL materials
		global Prefs
		try: x = Prefs['Materials'].keys()
		except: Prefs['Materials'] = {}
		keys = Prefs['Materials'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for matName in Prefs['Materials'].keys():
			mat = Prefs['Materials'][matName]
			try: x = mat['IFLMaterial']
			except KeyError: mat['IFLMaterial'] = False
			if mat['IFLMaterial'] == True:
				self.guiMat.items.append(matName)

	def clearIFLMatPulldown(self):
		self.guiMat.itemIndex = -1
		self.guiMat.items = []

	
	def clearImageFramesList(self):
		for i in range(0, len(self.guiFramesList.controls)):
			del self.guiFramesList.controls[i].controls[:]
		del self.guiFramesList.controls[:]
		self.guiFramesList.itemIndex = -1
		self.guiFramesList.scrollPosition = 0
		if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works

	# removes the last item from the frames list box
	def removeLastItemFromFrameList(self):
		i = len(self.guiFramesList.controls)-1
		try:
			del self.guiFramesList.controls[i].controls[:]
			del self.guiFramesList.controls[i]
		except IndexError: pass
		self.guiFramesList.itemIndex = -1
		self.guiFramesList.scrollPosition = 0
		if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works

	
	def populateImageFramesList(self, seqName):
		self.clearImageFramesList()
		guiFramesList = self.guiFramesList
		
		IFLMat = Prefs['Sequences'][seqName]['IFL']['IFLFrames']
		for fr in IFLMat:
			guiFramesList.addControl(self.createFramesListItem(fr[0], fr[1]))
			
		



# helper functions for VisControlsClass
def getIPOTypes():
	typeList = ["Object", "Material"]
	return typeList

def getIPOChannelTypes(IPOType):
	typesDict = {	"Object": ["LocX", "LocY", "LocZ", "dLocX", "dLocY", "dLocZ", "RotX", "RotY", "RotZ", "dRotX", "dRotY", "dRotZ", "ScaleX", "ScaleY", "ScaleZ", "dScaleX", "dScaleY", "dScaleZ", "Layer", "Time", "ColR", "ColG", "ColB", "ColA", "FSteng", "FFall", "RDamp", "Damping", "Perm"],\
			"Material":["R", "G", "B", "SpecR", "SpecG", "SpecB", "MirR", "MirG", "MirB", "Ref", "Alpha", "Emit", "Amb", "Spec", "Hard"],\
		    }
	try: retVal = typesDict[IPOType]
	except: retVal = []
	return retVal
	

def getAllSceneObjectNames(IPOType):
	scene = Blender.Scene.getCurrent()
	retVal = []
	if IPOType == "Object":
		allObjs = Blender.Object.Get()
		for obj in allObjs:
			retVal.append(obj.name)
	elif IPOType == "Material":
		allObjs = Blender.Material.Get()
		for obj in allObjs:
			retVal.append(obj.name)

	return retVal
	
def getArmBoneNames(armature):
	try: arm = Blender.Armature.Get(armature)
	except: return []
	retVal = []
	for bone in arm.bones.keys():
		retVal.append(bone)
	return retVal

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Visibility sub-panel of the Sequences panel.
*
***************************************************************************************************
'''


class VisControlsClass:
	def __init__(self):
		global guiSequenceVisibilitySubtab		
		global globalEvents
		
		# panel state
		self.curSeqListEvent = 40
		self.curVisTrackEvent = 80

		# initialize GUI controls
		self.guiSeqList = Common_Gui.ListContainer("guiSeqList", "sequence.list", self.handleListEvent, self.resize)
		self.guiSeqName = Common_Gui.TextBox("guiSeqName", "Sequence Name: ", "Name of the Current Sequence", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqAdd = Common_Gui.BasicButton("guiSeqAdd", "Add", "Add new Visibility Sequence with the given name", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqDel = Common_Gui.BasicButton("guiSeqDel", "Del", "Delete Selected Visibility Sequence", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqRename = Common_Gui.BasicButton("guiSeqRename", "Rename", "Rename Selected Visibility Sequence to the given name", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqAddToExistingTxt = Common_Gui.SimpleText("guiSeqAddToExistingTxt", "Add Vis Animation to existing Sequence:", None, self.resize)
		self.guiSeqExistingSequences = Common_Gui.ComboBox("guiSeqExistingSequences", "Sequence", "Select a Sequence from this list to which to add a Visibility Animation", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqAddToExisting = Common_Gui.BasicButton("guiSeqAddToExisting", "Add Visibility", "Add an Visibility Animation to an existing sequence.", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiSeqListTitle = Common_Gui.SimpleText("guiSeqListTitle", "Visibility Sequences:", None, self.resize)
		self.guiSeqOptsContainerTitle = Common_Gui.SimpleText("guiSeqOptsContainerTitle", "Sequence: None Selected", None, self.resize)
		self.guiSeqOptsContainer = Common_Gui.BasicContainer("guiSeqOptsContainer", "guiSeqOptsContainer", None, self.resize)
		self.guiStartFrame = Common_Gui.NumberPicker("guiStartFrame", "Start Frame", "Start frame for visibility IPO curve samples", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiEndFrame = Common_Gui.NumberPicker("guiEndFrame", "End Frame", "End frame for visibility IPO curve samples", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiVisTrackListTxt = Common_Gui.SimpleText("guiVisTrackListTxt", "Object Visibility Tracks:", None, self.resize)
		self.guiVisTrackList = Common_Gui.ListContainer("guiVisTrackList", "", self.handleVisTrackListEvent, self.resize)
		self.guiIpoTypeTxt = Common_Gui.SimpleText("guiIpoTypeTxt", "IPO Type:", None, self.resize)
		self.guiIpoType = Common_Gui.ComboBox("guiIpoType", "IPO Type", "Select the type of IPO curve to use for Visibility Animation", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiIpoChannelTxt = Common_Gui.SimpleText("guiIpoChannelTxt", "IPO Channel:", None, self.resize)
		self.guiIpoChannel = Common_Gui.ComboBox("guiIpoChannel", "IPO Channel", "Select the IPO curve to use for Visibility Animation", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiIpoObjectTxt = Common_Gui.SimpleText("guiIpoObjectTxt", "IPO Object:", None, self.resize)
		self.guiIpoObject = Common_Gui.ComboBox("guiIpoObject", "IPO Object", "Select the object whose IPO curve will be used for Visibility Animation", globalEvents.getNewID(), self.handleEvent, self.resize)


		# set initial states
		self.guiSeqOptsContainer.enabled = False
		self.guiSeqOptsContainer.fade_mode = 5
		self.guiSeqOptsContainer.borderColor = None
		self.guiSeqList.fade_mode = 0
		self.guiVisTrackList.enabled = True
		self.guiStartFrame.min = 1
		self.guiEndFrame.min = 1
		self.guiStartFrame.value = 1
		self.guiEndFrame.value = 1


		# add controls to containers
		guiSequenceVisibilitySubtab.addControl(self.guiSeqList)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqName)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqAdd)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqDel)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqRename)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqAddToExistingTxt)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqExistingSequences)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqAddToExisting)
		guiSequenceVisibilitySubtab.addControl(self.guiSeqListTitle)		
		guiSequenceVisibilitySubtab.addControl(self.guiSeqOptsContainer)
		self.guiSeqOptsContainer.addControl(self.guiSeqOptsContainerTitle)
		self.guiSeqOptsContainer.addControl(self.guiVisTrackListTxt)
		self.guiSeqOptsContainer.addControl(self.guiVisTrackList)
		self.guiSeqOptsContainer.addControl(self.guiStartFrame)
		self.guiSeqOptsContainer.addControl(self.guiEndFrame)
		self.guiSeqOptsContainer.addControl(self.guiVisTrackList)
		self.guiSeqOptsContainer.addControl(self.guiIpoTypeTxt)
		self.guiSeqOptsContainer.addControl(self.guiIpoChannelTxt)
		self.guiSeqOptsContainer.addControl(self.guiIpoObjectTxt)
		self.guiSeqOptsContainer.addControl(self.guiIpoType)
		self.guiSeqOptsContainer.addControl(self.guiIpoChannel)
		self.guiSeqOptsContainer.addControl(self.guiIpoObject)

		
		# populate the IFL sequence list
		self.populateSequenceList()
		
		# populate the IPO type pulldown
		self.populateIpoTypePulldown()
		
		# populate the existing sequences pulldown.
		self.populateExistingSeqPulldown()
		
	
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiSeqList
		del self.guiSeqName
		del self.guiSeqAdd
		del self.guiSeqDel
		del self.guiSeqRename
		del self.guiSeqAddToExistingTxt
		del self.guiSeqExistingSequences
		del self.guiSeqAddToExisting
		del self.guiSeqListTitle
		del self.guiSeqOptsContainerTitle
		del self.guiSeqOptsContainer
		del self.guiStartFrame
		del self.guiEndFrame
		del self.guiVisTrackListTxt
		del self.guiVisTrackList
		del self.guiIpoTypeTxt
		del self.guiIpoType
		del self.guiIpoChannelTxt
		del self.guiIpoChannel
		del self.guiIpoObjectTxt
		del self.guiIpoObject



	def refreshAll(self):
		# store last sequence selection
		seqName = None
		seqPrefs = None
		if self.guiSeqList.itemIndex != -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)

		# get the currently selected vis track item before clearing the list
		if self.guiVisTrackList.itemIndex > -1:
			selection = self.guiVisTrackList.controls[self.guiVisTrackList.itemIndex].controls[0].label
		else:
			selection = None

		
		# repopulate the sequence list
		cleanKeys()
		createActionKeys()
		self.populateSequenceList()
		self.populateExistingSeqPulldown()

		
		# restore last sequence selection
		for itemIndex in range(0, len(self.guiSeqList.controls)):
			#print "Checking item",itemIndex
			#print "self.guiSeqList.controls[itemIndex].controls[0].label =",self.guiSeqList.controls[itemIndex].controls[0].label
			#print "seqName =",seqName
			if self.guiSeqList.controls[itemIndex].controls[0].label == seqName:
				#print "found matching control for",seqName
				self.guiSeqList.selectItem(itemIndex)
				self.guiSeqList.scrollToSelectedItem()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
				# restore vis track list selection
				for i in range(0, len(self.guiVisTrackList.controls)):
					label = self.guiVisTrackList.controls[i].controls[0].label
					if label == selection:
						self.guiVisTrackList.selectItem(i)
						self.guiVisTrackList.scrollToSelectedItem()
						self.refreshIpoControls()
						break
				return

		self.guiSeqList.selectItem(0)
		self.guiSeqList.scrollToSelectedItem()

		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)


	
	def resize(self, control, newwidth, newheight):
		# handle control resize events.
		if control.name == "guiSeqList":
			control.x, control.y, control.height, control.width = 10,100, newheight - 140,230
		elif control.name == "guiSeqName":
			control.x, control.y, control.height, control.width = 10,75, 20,230
		elif control.name == "guiSeqAdd":
			control.x, control.y, control.height, control.width = 10,53, 20,75
		elif control.name == "guiSeqDel":
			control.x, control.y, control.height, control.width = 87,53, 20,75
		elif control.name == "guiSeqRename":
			control.x, control.y, control.height, control.width = 164,53, 20,76
		elif control.name == "guiSeqAddToExistingTxt":
			control.x, control.y, control.height, control.width = 10,38, 20,230
		elif control.name == "guiSeqExistingSequences":
			control.x, control.y, control.height, control.width = 10,11, 20,145
		elif control.name == "guiSeqAddToExisting":
			control.x, control.y, control.height, control.width = 157,11, 20,82
		elif control.name == "guiSeqListTitle":			
			control.x, control.y, control.height, control.width = 10,310, 20,82
		elif control.name == "guiSeqOptsContainer":
			control.x, control.y, control.height, control.width = 241,0, 334,249
		elif control.name == "guiSeqOptsContainerTitle":
			control.x, control.y, control.height, control.width = 10,310, 20,82
		elif control.name == "guiStartFrame":
			control.x, control.y, control.height, control.width = 20,280, 20,110
		elif control.name == "guiEndFrame":
			control.x, control.y, control.height, control.width = 133,280, 20,110
		elif control.name == "guiVisTrackListTxt":
			control.x, control.y, control.height, control.width = 10,258, 20,120
		elif control.name == "guiVisTrackList":
			control.x, control.y, control.height, control.width = 20,100, 145,223
		elif control.name == "guiIpoTypeTxt":
			control.x, control.y, control.height, control.width = 20,80, 20,223
		elif control.name == "guiIpoType":
			control.x, control.y, control.height, control.width = 110,75, 20,133
		elif control.name == "guiIpoChannelTxt":
			control.x, control.y, control.height, control.width = 20,58, 20,223
		elif control.name == "guiIpoChannel":
			control.x, control.y, control.height, control.width = 110,53, 20,133
		elif control.name == "guiIpoObjectTxt":
			control.x, control.y, control.height, control.width = 20,36, 20,223
		elif control.name == "guiIpoObject":
			control.x, control.y, control.height, control.width = 110,31, 20,133

	def createSequenceListItem(self, seqName):
		startEvent = self.curSeqListEvent
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", seqName, None, None)
		guiName.x, guiName.y = 5, 5
		guiExport = Common_Gui.ToggleButton("guiExport", "Export", "Export Sequence", startEvent, self.handleListItemEvent, None)
		guiExport.x, guiExport.y = 105, 5
		guiExport.width, guiExport.height = 50, 15
		guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+1, self.handleListItemEvent, None)
		guiCyclic.x, guiCyclic.y = 157, 5
		guiCyclic.width, guiCyclic.height = 50, 15

		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiExport)
		guiContainer.addControl(guiCyclic)
		
		guiExport.state = not Prefs['Sequences'][seqName]['NoExport']
		guiCyclic.state = Prefs['Sequences'][seqName]['Cyclic']
		
		# increment the current event counter
		self.curSeqListEvent += 2
		
		return guiContainer

	def createVisTrackListItem(self, objName):
		startEvent = self.curVisTrackEvent
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", objName, None, None)
		guiName.x, guiName.y = 5, 5
		guiEnable = Common_Gui.ToggleButton("guiEnable", "Enable", "Enable Visibility track for object", startEvent, self.handleVisTrackListItemEvent, None)
		guiEnable.x, guiEnable.y = 152, 5
		guiEnable.width, guiEnable.height = 50, 15


		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiEnable)
		
		self.curVisTrackEvent += 1
		return guiContainer
	
	# add a new Visibility sequence in the GUI and the prefs
	def AddNewVisSeq(self, seqName):
		seq = getSequenceKey(seqName)
		# add vis stuff
		seq['Vis'] = {}
		seq['Vis']['Enabled'] = True
		seq['Vis']['StartFrame'] = 1
		seq['Vis']['EndFrame'] = 1
		seq['Vis']['Enabled'] = True
		seq['Vis']['Tracks'] = {}
		# add sequence to GUI sequence list		
		self.guiSeqList.addControl(self.createSequenceListItem(seqName))
		# refresh the Image frames list
		self.populateVisTrackList(seqName)
	
	def handleEvent(self, control):
		global Prefs
		if control.name == "guiSeqName":
			pass
		elif control.name == "guiSeqAdd":
			if validateSequenceName(self.guiSeqName.value, "Vis"):
				self.AddNewVisSeq(self.guiSeqName.value)
				self.guiSeqList.selectItem(len(self.guiSeqList.controls)-1)
				self.guiSeqName.value = ""
				self.guiSeqOptsContainer.enabled = True
				self.refreshAll()

		elif control.name == "guiSeqDel":			
			guiSeqList = self.guiSeqList
			if guiSeqList.itemIndex > -1 and guiSeqList.itemIndex < len(guiSeqList.controls):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				seqKey = getSequenceKey(seqName)
				guiSeqList.removeItem(guiSeqList.itemIndex)
				seqKey['Vis']['Enabled'] = False
				if seqKey['Action']['Enabled'] == True or seqKey['IFL']['Enabled'] == True:
					self.guiSeqExistingSequences.items.append(seqName)
				else:
					seqKey['Vis']['StartFrame'] = 1
					seqKey['Vis']['EndFrame'] = 1					
					seqKey['Vis']['Tracks'] = {}
				self.populateVisTrackList(seqName)
			else:
				self.clearVisTrackList()
			self.populateSequenceList()
			if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)

		elif control.name == "guiSeqRename":
			guiSeqList = self.guiSeqList
			seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
			newName = self.guiSeqName.value
			if guiSeqList.itemIndex < 0:
				message = "No Visibility animation was selected.%t|Cancel"
				Blender.Draw.PupMenu(message)
				return
			if validateSequenceName(newName, "Vis", seqName):
				renameSequence(seqName, newName)
				guiSeqList.controls[guiSeqList.itemIndex].controls[0].label = newName
				self.populateVisTrackList(newName)
				self.refreshAll()
		elif control.name == "guiSeqAddToExisting":
			existingSequences = self.guiSeqExistingSequences
			itemIndex = existingSequences.itemIndex
			if itemIndex >=0 and itemIndex < len(existingSequences.items):
				existingName = existingSequences.getSelectedItemString()
				if validateSequenceName(existingName, "Vis"):
					self.AddNewVisSeq(existingName)
					del existingSequences.items[itemIndex]
					existingSequences.selectStringItem("")
		elif control.name == "guiStartFrame":
			guiSeqList = self.guiSeqList
			if guiSeqList.itemIndex > -1 and guiSeqList.itemIndex < len(guiSeqList.controls):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				seqKey = getSequenceKey(seqName)
				seqKey['Vis']['StartFrame'] = control.value
				if self.guiEndFrame.value < seqKey['Vis']['StartFrame']:
					self.guiEndFrame.value = seqKey['Vis']['StartFrame']
					seqKey['Vis']['EndFrame'] = seqKey['Vis']['StartFrame']
				self.guiEndFrame.min = seqKey['Vis']['StartFrame']
		elif control.name == "guiEndFrame":
			guiSeqList = self.guiSeqList
			if guiSeqList.itemIndex > -1 and guiSeqList.itemIndex < len(guiSeqList.controls):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				seqKey = getSequenceKey(seqName)
				seqKey['Vis']['EndFrame'] = control.value
				if self.guiStartFrame.value > seqKey['Vis']['EndFrame']:
					self.guiStartFrame.value = seqKey['Vis']['EndFrame']
					seqKey['Vis']['StartFrame'] = seqKey['Vis']['EndFrame']
				self.guiStartFrame.max = seqKey['Vis']['EndFrame']
		elif control.name == "guiIpoType":
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqKey = getSequenceKey(seqName)
			objName = self.guiVisTrackList.controls[self.guiVisTrackList.itemIndex].controls[0].label
			type = self.guiIpoType.getSelectedItemString()
			if type == "":
				self.clearIpoCurvePulldown()
				self.clearIpoObjectPulldown()
				return
			seqKey['Vis']['Tracks'][objName]['IPOType'] = type
			seqKey['Vis']['Tracks'][objName]['IPOChannel'] = None
			seqKey['Vis']['Tracks'][objName]['IPOObject'] = None
			self.refreshIpoControls()
		elif control.name == "guiIpoChannel":
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqKey = getSequenceKey(seqName)
			objName = self.guiVisTrackList.controls[self.guiVisTrackList.itemIndex].controls[0].label
			channel = self.guiIpoChannel.getSelectedItemString()
			seqKey['Vis']['Tracks'][objName]['IPOChannel'] = channel
		elif control.name == "guiIpoObject":
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqKey = getSequenceKey(seqName)
			objName = self.guiVisTrackList.controls[self.guiVisTrackList.itemIndex].controls[0].label
			type = self.guiIpoType.getSelectedItemString()
			if control.itemIndex > -1:
				seqKey['Vis']['Tracks'][objName]['IPOObject'] = self.guiIpoObject.getSelectedItemString()
		
	# called when an item is selected in the sequence list
	def handleListEvent(self, control):
		if control.itemIndex < 0:
			self.guiSeqName.value = ""
			self.guiSeqOptsContainer.enabled = False
			self.clearVisTrackList()
			self.guiStartFrame.value = 1
			self.guiEndFrame.value = 1
			self.guiSeqOptsContainerTitle.label = "Sequence: None Selected"
		else:
			self.guiSeqOptsContainer.enabled = True
			seqName = control.controls[control.itemIndex].controls[0].label
			seqKey = getSequenceKey(seqName)
			self.guiSeqName.value = seqName 
			self.populateVisTrackList(seqName)
			self.guiStartFrame.value = seqKey['Vis']['StartFrame']
			self.guiStartFrame.max = seqKey['Vis']['EndFrame']
			self.guiEndFrame.value = seqKey['Vis']['EndFrame']
			self.guiEndFrame.min = seqKey['Vis']['StartFrame']			
			self.guiSeqOptsContainerTitle.label = ("Sequence: %s" % seqName)
		self.guiVisTrackList.selectItem(0)
		self.guiVisTrackList.scrollToSelectedItem()
		self.refreshIpoControls()


	def handleListItemEvent(self, control):
		# Determine sequence name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / 2
		seqName = self.guiSeqList.controls[calcIdx].controls[0].label
		realItem = control.evt - 40 - (calcIdx*2)
		seqPrefs = getSequenceKey(seqName)
		if realItem == 0:
			seqPrefs['NoExport'] = not control.state
		elif realItem == 1:
			seqPrefs['Cyclic'] = control.state


	def refreshIpoControls(self):
		guiVisTrackList = self.guiVisTrackList		
		try: seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
		except: seqName = "N/A"
		try: objName = self.guiVisTrackList.controls[self.guiVisTrackList.itemIndex].controls[0].label
		except: objName = ""
		seqKey = getSequenceKey(seqName)
		try: type = seqKey['Vis']['Tracks'][objName]['IPOType']
		except: type = ""
		foundKey = True
		try: x = seqKey['Vis']['Tracks'][objName]
		except: foundKey = False

		if guiVisTrackList.itemIndex > -1 and foundKey:
			
			self.guiIpoType.enabled = True
			self.guiIpoChannel.enabled = True
			self.guiIpoObject.enabled = True
			if objName == "" or objName == None:
				self.guiIpoType.itemIndex = -1
				self.guiIpoChannel.itemIndex = -1
				self.guiIpoObject.itemIndex = -1
			if type != "":
				self.populateIpoCurvePulldown(type)
				self.populateIpoObjectPulldown(type)
				arm = seqKey['Vis']['Tracks'][objName]['IPOObject']
			else:
				self.clearIpoCurvePulldown()
				self.clearIpoObjectPulldown()
			try:
				self.guiIpoType.setTextValue(seqKey['Vis']['Tracks'][objName]['IPOType'])
			except:
				seqKey['Vis']['Tracks'][objName]['IPOType'] = None
			try:
				self.guiIpoChannel.setTextValue(seqKey['Vis']['Tracks'][objName]['IPOChannel'])
			except:
				seqKey['Vis']['Tracks'][objName]['IPOChannel'] = None
			try:
				self.guiIpoObject.setTextValue(seqKey['Vis']['Tracks'][objName]['IPOObject'])
			except:
				seqKey['Vis']['Tracks'][objName]['IPOObject'] = None
		else:
			self.guiIpoType.itemIndex = -1
			self.guiIpoChannel.itemIndex = -1
			self.guiIpoObject.itemIndex = -1
			self.clearIpoCurvePulldown()
			self.clearIpoObjectPulldown()
			self.guiIpoType.enabled = False
			self.guiIpoChannel.enabled = False
			self.guiIpoObject.enabled = False
		
		if type == "Object":
			self.guiIpoObjectTxt.label = "IPO Object:"
		elif type == "Material":
			self.guiIpoObjectTxt.label = "IPO Material:"

	
	
	# called when an item is selected in the Vis track list
	def handleVisTrackListEvent(self, control):
		self.refreshIpoControls()

	def handleVisTrackListItemEvent(self, control):
		# Determine sequence name
		calcIdx = (control.evt - 80)
		seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
		objName = self.guiVisTrackList.controls[calcIdx].controls[0].label
		seqPrefs = getSequenceKey(seqName)
		if control.state:
			try: x = seqPrefs['Vis']['Tracks'][objName]
			except:
				seqPrefs['Vis']['Tracks'][objName] = {}
				seqPrefs['Vis']['Tracks'][objName]['hasVisTrack'] = True
				seqPrefs['Vis']['Tracks'][objName]['IPOType'] = 'Object'
				seqPrefs['Vis']['Tracks'][objName]['IPOChannel'] = None
				seqPrefs['Vis']['Tracks'][objName]['IPOObject'] = None

		Prefs['Sequences'][seqName]['Vis']['Tracks'][objName]['hasVisTrack'] = control.state	
		
	# this method clears the sequence list and then repopulates it.
	def populateSequenceList(self):
		self.curSeqListEvent = 40
		self.clearSequenceList()
		# loop through all actions in the preferences and check for IFL animations
		global Prefs
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seq = getSequenceKey(seqName)
			if seq['Vis']['Enabled'] == True:
				self.guiSeqList.addControl(self.createSequenceListItem(seqName))

	def clearSequenceList(self):
		for i in range(0, len(self.guiSeqList.controls)):
			del self.guiSeqList.controls[i].controls[:]
		del self.guiSeqList.controls[:]
		self.curSeqListEvent = 40
		self.guiSeqList.itemIndex = -1
		self.guiSeqList.scrollPosition = 0
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList) # Bit of a hack, but works


	def populateExistingSeqPulldown(self):
		self.clearExistingSeqPulldown()
		# loop through all actions in the preferences and check for sequences without IFL animations
		global Prefs
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seq = getSequenceKey(seqName)
			if seq['Vis']['Enabled'] == False:
				self.guiSeqExistingSequences.items.append(seqName)

	def clearExistingSeqPulldown(self):
		self.guiSeqExistingSequences.items = []
		self.guiSeqExistingSequences.itemIndex = -1

	def populateIpoTypePulldown(self):		
		self.guiIpoType.itemIndex = -1
		for type in getIPOTypes():
			self.guiIpoType.items.append(type)
			
	
	def clearIpoObjectPulldown(self):
		self.guiIpoObject.itemIndex = -1
		self.guiIpoObject.items = []

	def populateIpoObjectPulldown(self, type):
		self.guiIpoObject.itemIndex = -1
		self.clearIpoObjectPulldown()
		objs = getAllSceneObjectNames(type)		
		objs.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for obj in objs:
			self.guiIpoObject.items.append(obj)

	def clearIpoCurvePulldown(self):
		self.guiIpoChannel.itemIndex = -1
		self.guiIpoChannel.items = []
		
	def populateIpoCurvePulldown(self, type):
		self.guiIpoChannel.itemIndex = -1
		self.clearIpoCurvePulldown()
		for chann in getIPOChannelTypes(type):
			self.guiIpoChannel.items.append(chann)

	def clearVisTrackList(self):
		for i in range(0, len(self.guiVisTrackList.controls)):
			del self.guiVisTrackList.controls[i].controls[:]
		del self.guiVisTrackList.controls[:]

		self.guiVisTrackList.itemIndex = -1
		self.guiVisTrackList.scrollPosition = 0
		self.curVisTrackEvent = 80
		if self.guiVisTrackList.callback: self.guiVisTrackList.callback(self.guiVisTrackList) # Bit of a hack, but works


	def populateVisTrackList(self, seqName):
		self.clearVisTrackList()		
		shapeTree = export_tree.find("SHAPE")
		if shapeTree != None:
			# find the highest detail level.
			highest = 0
			for marker in getChildren(shapeTree.obj):
				if marker.name[0:6].lower() != "detail": continue
				numPortion = int(marker.name[6:len(marker.name)])
				if numPortion > highest: highest = numPortion
			markerName = "detail" + str(numPortion)
			for marker in getChildren(shapeTree.obj):
				if marker.name.lower() != markerName: continue
				# loop through all objects, and sort into two lists
				enabledList = []
				disabledList = []
				for obj in getAllChildren(marker):
					if obj.getType() != "Mesh": continue
					if obj.name == "Bounds": continue
					# process mesh objects
					objData = obj.getData()
					# add an entry in the track list for the mesh object.
					#self.guiVisTrackList.addControl(self.createVisTrackListItem(obj.name))
					# set the state of the enabled button
					try: enabled = Prefs['Sequences'][seqName]['Vis']['Tracks'][obj.name]['hasVisTrack']
					except: enabled = False
					if enabled: enabledList.append(obj.name)
					else: disabledList.append(obj.name)
				# combine lists
				enabledList.sort(lambda x, y: cmp(x.lower(),y.lower()))
				disabledList.sort(lambda x, y: cmp(x.lower(),y.lower()))
				combinedList = enabledList + disabledList
				# add everything in the list
				for item in combinedList:
					self.guiVisTrackList.addControl(self.createVisTrackListItem(item))
					try: self.guiVisTrackList.controls[-1].controls[1].state = Prefs['Sequences'][seqName]['Vis']['Tracks'][item]['hasVisTrack']
					except: self.guiVisTrackList.controls[-1].controls[1].state = False
		
		
		
'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Materials panel.
*
***************************************************************************************************
'''
class MaterialControlsClass:
	def __init__(self):
		global guiMaterialsSubtab
		global globalEvents
		# panel state
		self.curSeqListEvent = 40

		self.guiMaterialListTitle = Common_Gui.SimpleText("guiMaterialListTitle", "U/V Textures:", None, self.resize)
		self.guiMaterialList = Common_Gui.ListContainer("guiMaterialList", "material.list", self.handleEvent, self.resize)		
		self.guiMaterialOptions = Common_Gui.BasicContainer("guiMaterialOptions", "", None, self.resize)
		self.guiMaterialOptionsTitle = Common_Gui.SimpleText("guiMaterialOptionsTitle", "DTS Material: None Selected", None, self.resize)
		self.guiMaterialTransFrame = Common_Gui.BasicFrame("guiMaterialTransFrame", "", None, 29, None, self.resize)
		self.guiMaterialAdvancedFrame = Common_Gui.BasicFrame("guiMaterialAdvancedFrame", "", None, 30, None, self.resize)
		self.guiMaterialImportRefreshButton = Common_Gui.BasicButton("guiMaterialImportRefreshButton", "Refresh", "Import Blender materials and settings", 7, self.handleEvent, self.resize)
		self.guiMaterialSWrapButton = Common_Gui.ToggleButton("guiMaterialSWrapButton", "SWrap", "SWrap", 9, self.handleEvent, self.resize)
		self.guiMaterialTWrapButton = Common_Gui.ToggleButton("guiMaterialTWrapButton", "TWrap", "TWrap", 10, self.handleEvent, self.resize)
		self.guiMaterialTransButton = Common_Gui.ToggleButton("guiMaterialTransButton", "Translucent", "Translucent", 11, self.handleEvent, self.resize)
		self.guiMaterialAddButton = Common_Gui.ToggleButton("guiMaterialAddButton", "Additive", "Blending Additive", 12, self.handleEvent, self.resize)
		self.guiMaterialSubButton = Common_Gui.ToggleButton("guiMaterialSubButton", "Subtractive", "Blending Subtractive", 13, self.handleEvent, self.resize)
		self.guiMaterialSelfIllumButton = Common_Gui.ToggleButton("guiMaterialSelfIllumButton", "Self Illuminating", "Mark material as self illuminating", 14, self.handleEvent, self.resize)
		self.guiMaterialEnvMapButton = Common_Gui.ToggleButton("guiMaterialEnvMapButton", "Environment Mapping", "Enable Environment Mapping", 15, self.handleEvent, self.resize)
		self.guiMaterialMipMapButton = Common_Gui.ToggleButton("guiMaterialMipMapButton", "Mipmap", "Allow MipMapping", 16, self.handleEvent, self.resize)
		self.guiMaterialMipMapZBButton = Common_Gui.ToggleButton("guiMaterialMipMapZBButton", "Mipmap Zero Border", "Use Zero border MipMaps", 17, self.handleEvent, self.resize)
		self.guiMaterialIFLMatButton = Common_Gui.ToggleButton("guiMaterialIFLMatButton", "IFL Material", "Use this material as an IFL material", 28, self.handleEvent, self.resize)
		self.guiMaterialDetailMapButton = Common_Gui.ToggleButton("guiMaterialDetailMapButton", "Detail Map", "Use a detail map texture", 18, self.handleEvent, self.resize)
		self.guiMaterialBumpMapButton = Common_Gui.ToggleButton("guiMaterialBumpMapButton", "Bump Map", "Use a bump map texture", 19, self.handleEvent, self.resize)
		self.guiMaterialRefMapButton = Common_Gui.ToggleButton("guiMaterialRefMapButton", "Reflectance Map", "Use a reflectance map texture", 20, self.handleEvent, self.resize)
		self.guiMaterialDetailMapMenu = Common_Gui.ComboBox("guiMaterialDetailMapMenu", "Detail Texture", "Select a texture from this list to use as a detail map", 22, self.handleEvent, self.resize)
		self.guiMaterialShowAdvancedButton = Common_Gui.ToggleButton("guiMaterialShowAdvancedButton", "Show Advanced Settings", "Show advanced material settings. USE WITH CAUTION!!", 23, self.handleEvent, self.resize)
		self.guiMaterialBumpMapMenu = Common_Gui.ComboBox("guiMaterialBumpMapMenu", "Bumpmap Texture", "Select a texture from this list to use as a bump map", 24, self.handleEvent, self.resize)
		self.guiMaterialReflectanceMapMenu = Common_Gui.ComboBox("guiMaterialReflectanceMapMenu", "Reflectance Map", "Select a texture from this list to use as a Reflectance map", 25, self.handleEvent, self.resize)
		self.guiMaterialReflectanceSlider = Common_Gui.NumberPicker("guiMaterialReflectanceSlider", "Reflectivity %", "Material reflectivity as a percentage", 26, self.handleEvent, self.resize)
		self.guiMaterialDetailScaleSlider = Common_Gui.NumberPicker("guiMaterialDetailScaleSlider", "Detail Scale %", "Detail map scale as a percentage of original size", 27, self.handleEvent, self.resize)	


		# set initial control states and default values
		self.guiMaterialList.fade_mode = 0
		self.guiMaterialReflectanceSlider.min, self.guiMaterialReflectanceSlider.max = 0, 100
		self.guiMaterialDetailScaleSlider.min, self.guiMaterialDetailScaleSlider.max = 1, 1000
		self.guiMaterialDetailScaleSlider.value = 100
		self.guiMaterialRefMapButton.enabled = False
		self.guiMaterialBumpMapButton.enabled = False
		self.guiMaterialBumpMapMenu.enabled = False
		self.guiMaterialReflectanceMapMenu.enabled = False
		self.guiMaterialRefMapButton.visible = False
		self.guiMaterialBumpMapButton.visible = False
		self.guiMaterialBumpMapMenu.visible = False
		self.guiMaterialReflectanceMapMenu.visible = False
		self.guiMaterialOptions.enabled = False
		guiMaterialsTab.borderColor = [0,0,0,0]
		
		
		# add controls to their respective containers
		guiMaterialsSubtab.addControl(self.guiMaterialListTitle)
		guiMaterialsSubtab.addControl(self.guiMaterialList)
		guiMaterialsSubtab.addControl(self.guiMaterialOptions)
		guiMaterialsSubtab.addControl(self.guiMaterialImportRefreshButton)

		self.guiMaterialOptions.addControl(self.guiMaterialOptionsTitle)
		self.guiMaterialOptions.addControl(self.guiMaterialTransFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialAdvancedFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialSWrapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialTWrapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialTransButton)
		self.guiMaterialOptions.addControl(self.guiMaterialAddButton)
		self.guiMaterialOptions.addControl(self.guiMaterialSubButton)
		self.guiMaterialOptions.addControl(self.guiMaterialSelfIllumButton)
		self.guiMaterialOptions.addControl(self.guiMaterialEnvMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialMipMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialMipMapZBButton)
		self.guiMaterialOptions.addControl(self.guiMaterialIFLMatButton)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialBumpMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialShowAdvancedButton)
		self.guiMaterialOptions.addControl(self.guiMaterialRefMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailMapMenu)
		self.guiMaterialOptions.addControl(self.guiMaterialBumpMapMenu)
		self.guiMaterialOptions.addControl(self.guiMaterialReflectanceMapMenu)
		self.guiMaterialOptions.addControl(self.guiMaterialReflectanceSlider)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailScaleSlider)

		# populate the Material list
		self.populateMaterialList()
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiMaterialListTitle
		del self.guiMaterialList
		del self.guiMaterialOptions
		del self.guiMaterialOptionsTitle
		del self.guiMaterialTransFrame
		del self.guiMaterialAdvancedFrame
		del self.guiMaterialImportRefreshButton
		del self.guiMaterialSWrapButton
		del self.guiMaterialTWrapButton
		del self.guiMaterialTransButton
		del self.guiMaterialAddButton
		del self.guiMaterialSubButton
		del self.guiMaterialSelfIllumButton
		del self.guiMaterialEnvMapButton
		del self.guiMaterialMipMapButton
		del self.guiMaterialMipMapZBButton
		del self.guiMaterialIFLMatButton
		del self.guiMaterialDetailMapButton
		del self.guiMaterialBumpMapButton
		del self.guiMaterialRefMapButton
		del self.guiMaterialDetailMapMenu
		del self.guiMaterialShowAdvancedButton
		del self.guiMaterialBumpMapMenu
		del self.guiMaterialReflectanceMapMenu
		del self.guiMaterialReflectanceSlider
		del self.guiMaterialDetailScaleSlider
		

	
	def resize(self, control, newwidth, newheight):
		# handle control resize events.
		if control.name == "guiMaterialListTitle":
			control.x, control.y, control.height, control.width = 10,310, 20,150
		elif control.name == "guiMaterialList":
			control.x, control.y, control.height, control.width = 10,30, newheight - 70,150
		elif control.name == "guiMaterialOptionsTitle":
			control.x, control.y, control.height, control.width = 25,310, 20,150
		elif control.name == "guiMaterialOptions":
			control.x, control.y, control.height, control.width = 161,0, 335,328
		elif control.name == "guiMaterialTransFrame":
			control.x, control.y, control.height, control.width = 8,newheight-105, 50,170
		elif control.name == "guiMaterialAdvancedFrame":
			control.x, control.y, control.height, control.width = 8,newheight-325, 75,315
		elif control.name == "guiMaterialImportRefreshButton":
			control.x, control.y, control.width = 10,newheight-330, 100
		elif control.name == "guiMaterialSWrapButton":
			control.x, control.y, control.width = 195,newheight-105, 60
		elif control.name == "guiMaterialTWrapButton":
			control.x, control.y, control.width = 257,newheight-105, 60
		elif control.name == "guiMaterialTransButton":
			control.x, control.y, control.width = 15,newheight-65, 75
		elif control.name == "guiMaterialAddButton":
			control.x, control.y, control.width = 15,newheight-95, 75
		elif control.name == "guiMaterialSubButton":
			control.x, control.y, control.width = 92,newheight-95, 75
		elif control.name == "guiMaterialSelfIllumButton":
			control.x, control.y, control.width = 195,newheight-75, 122
		elif control.name == "guiMaterialMipMapButton":
			control.x, control.y, control.width = 8,newheight-137, 50
		elif control.name == "guiMaterialMipMapZBButton":
			control.x, control.y, control.width = 60,newheight-137, 125
		elif control.name == "guiMaterialIFLMatButton":
			control.x, control.y, control.width = 195,newheight-137, 122
		elif control.name == "guiMaterialDetailMapButton":
			control.x, control.y, control.width = 8,newheight-167, 150
		elif control.name == "guiMaterialDetailMapMenu":
			control.x, control.y, control.width = 160,newheight-167, 150
		elif control.name == "guiMaterialDetailScaleSlider":
			control.x, control.y, control.width = 160,newheight-189, 150
		elif control.name == "guiMaterialEnvMapButton":
			control.x, control.y, control.width = 8,newheight-217, 150
		elif control.name == "guiMaterialReflectanceSlider":
			control.x, control.y, control.width = 160,newheight-217, 150
		elif control.name == "guiMaterialShowAdvancedButton":
			control.x, control.y, control.width = 89,newheight-260, 150
		elif control.name == "guiMaterialRefMapButton":
			control.x, control.y, control.width = 15,newheight-295, 150
		elif control.name == "guiMaterialReflectanceMapMenu":
			control.x, control.y, control.width = 167,newheight-295, 150
		elif control.name == "guiMaterialBumpMapButton":
			control.x, control.y, control.width = 15,newheight-317, 150
		elif control.name == "guiMaterialBumpMapMenu":
			control.x, control.y, control.width = 167,newheight-317,150 


	def createMaterialListItem(self, matName, startEvent):
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", matName, None, None)
		guiName.x, guiName.y = 5, 5
		guiContainer.addControl(guiName)
		return guiContainer


	def importMaterialList(self):	
		global Prefs
		guiMaterialOptions = self.guiMaterialOptions
		guiMaterialList = self.guiMaterialList

		try:
			materials = Prefs['Materials']
		except:			
			Prefs['Materials'] = {}
			materials = Prefs['Materials']

		# loop through all faces of all meshes in the shape tree and compile a list
		# of unique images that are UV mapped to the faces.
		imageList = []
		shapeTree = export_tree.find("SHAPE")
		if shapeTree != None:
			for marker in getChildren(shapeTree.obj):		
				if marker.name[0:6].lower() != "detail": continue
				for obj in getAllChildren(marker):
					if obj.getType() != "Mesh": continue
					objData = obj.getData()
					for face in objData.faces:					
						try: x = face.image
						except IndexError: x = None
						# If we don't Have an image assigned to the face
						if x == None:						
							try: x = objData.materials[face.mat]
							except IndexError: x = None
							# is there a material index assigned?
							if x != None:
								#  add the material name to the imagelist
								imageName = stripImageExtension(objData.materials[face.mat].name)
								if not (imageName in imageList):
									imageList.append(imageName)

						# Otherwise we do have an image assigned to the face, so add it to the imageList.
						else:
							imageName = stripImageExtension(face.image.getName())
							if not (imageName in imageList):
								imageList.append(imageName)


		# remove unused materials from the prefs
		for imageName in materials.keys()[:]:
			if not (imageName in imageList): del materials[imageName]

		if len(imageList)==0: return

		# populate materials list with all blender materials
		for imageName in imageList:
			bmat = None
			# Do we have a blender material that matches the image name?
			try: bmat = Blender.Material.Get(imageName)
			except NameError:
				# No blender material, do we have a prefs key for this material?
				try: x = Prefs['Materials'][imageName]
				except KeyError:
					# no corresponding blender material and no existing texture material, so use reasonable defaults.
					Prefs['Materials'][imageName] = {}
					pmi = Prefs['Materials'][imageName]
					pmi['SWrap'] = True
					pmi['TWrap'] = True
					pmi['Translucent'] = False
					pmi['Additive'] = False
					pmi['Subtractive'] = False
					pmi['SelfIlluminating'] = False
					pmi['NeverEnvMap'] = True
					pmi['NoMipMap'] = False
					pmi['MipMapZeroBorder'] = False
					pmi['IFLMaterial'] = False
					pmi['DetailMapFlag'] = False
					pmi['BumpMapFlag'] = False
					pmi['ReflectanceMapFlag'] = False
					pmi['BaseTex'] = imageName
					pmi['DetailTex'] = None
					pmi['BumpMapTex'] = None
					pmi['RefMapTex'] = None
					pmi['reflectance'] = 0.0
					pmi['detailScale'] = 1.0
				continue

			# We have a blender material, do we have a prefs key for it?
			try: x = Prefs['Materials'][bmat.name]			
			except:
				# No prefs key, so create one.
				Prefs['Materials'][bmat.name] = {}
				pmb = Prefs['Materials'][bmat.name]
				# init everything to make sure all keys exist with sane values
				pmb['SWrap'] = True
				pmb['TWrap'] = True
				pmb['Translucent'] = False
				pmb['Additive'] = False
				pmb['Subtractive'] = False
				pmb['SelfIlluminating'] = False
				pmb['NeverEnvMap'] = True
				pmb['NoMipMap'] = False
				pmb['MipMapZeroBorder'] = False
				pmb['IFLMaterial'] = False
				pmb['DetailMapFlag'] = False
				pmb['BumpMapFlag'] = False
				pmb['ReflectanceMapFlag'] = False
				pmb['BaseTex'] = imageName
				pmb['DetailTex'] = None
				pmb['BumpMapTex'] = None
				pmb['RefMapTex'] = None
				pmb['reflectance'] = 0.0
				pmb['detailScale'] = 1.0

				if bmat.getEmit() > 0.0: pmb['SelfIlluminating'] = True
				else: pmb['SelfIlluminating'] = False

				pmb['RefMapTex'] = None
				pmb['BumpMapTex'] = None
				pmb['DetailTex'] = None

				# Look at the texture channels if they exist
				textures = bmat.getTextures()
				if len(textures) > 0:
					if textures[0] != None:
						if textures[0].tex.image != None:						
							pmb['BaseTex'] = stripImageExtension(textures[0].tex.image.getName())
						else:
							pmb['BaseTex'] = None

						if (textures[0] != None) and (textures[0].tex.type == Texture.Types.IMAGE):
							# Translucency?
							if textures[0].mapto & Texture.MapTo.ALPHA:
								pmb['Translucent'] = True
								if bmat.getAlpha() < 1.0: pmb['Additive'] = True
								else: pmb['Additive'] = False
							else:
								pmb['Translucent'] = False
								pmb['Additive'] = False
							# Disable mipmaps?
							if not (textures[0].tex.imageFlags & Texture.ImageFlags.MIPMAP):
								pmb['NoMipMap'] = True
							else:pmb['NoMipMap'] = False

							if bmat.getRef() > 0 and (textures[0].mapto & Texture.MapTo.REF):
								pmb['NeverEnvMap'] = False

					pmb['ReflectanceMapFlag'] = False
					pmb['DetailMapFlag'] = False
					pmb['BumpMapFlag'] = False
					for i in range(1, len(textures)):
						texture_obj = textures[i]					
						if texture_obj == None: continue
						# Figure out if we have an Image
						if texture_obj.tex.type != Texture.Types.IMAGE:
							continue

						# Determine what this texture is used for
						# A) We have a reflectance map
						if (texture_obj.mapto & Texture.MapTo.REF):
							# We have a reflectance map
							pmb['ReflectanceMapFlag'] = True
							pmb['NeverEnvMap'] = False
							if textures[0].tex.image != None:
								pmb['RefMapTex'] = stripImageExtension(textures[i].tex.image.getName())
								self.guiMaterialReflectanceMapMenu.selectStringItem(stripImageExtension(textures[i].tex.image.getName()))
							else:
								pmb['RefMapTex'] = None
						# B) We have a normal map (basically a 3d bump map)
						elif (texture_obj.mapto & Texture.MapTo.NOR):
							pmb['BumpMapFlag'] = True
							if textures[0].tex.image != None:
								pmb['BumpMapTex'] = stripImageExtension(textures[i].tex.image.getName())
								self.guiMaterialBumpMapMenu.selectStringItem(stripImageExtension(textures[i].tex.image.getName()))
							else:
								pmb['BumpMapTex'] = None
						# C) We have a texture; Lets presume its a detail map (since its laid on top after all)
						else:
							pmb['DetailMapFlag'] = True
							if textures[0].tex.image != None:
								pmb['DetailTex'] = stripImageExtension(textures[i].tex.image.getName())
								self.guiMaterialDetailMapMenu.selectStringItem(stripImageExtension(textures[i].tex.image.getName()))
							else:
								pmb['DetailTex'] = None

	def handleEvent(self, control):
		global Prefs, IFLControls
		guiMaterialList = self.guiMaterialList
		guiMaterialOptions = self.guiMaterialOptions

		try:matList = Prefs['Materials']
		except:
			Prefs['Materials'] = {}
			matList = Prefs['Materials']	


		if control.name == "guiMaterialImportRefreshButton":
			# import Blender materials and settings
			self.clearMaterialList()
			self.populateMaterialList()
			return

		if guiMaterialList.itemIndex != -1:
			materialName = guiMaterialList.controls[guiMaterialList.itemIndex].controls[0].label	

		if control.name == "guiMaterialList":
			if control.itemIndex != -1:
				guiMaterialOptions.enabled = True
				materialName = guiMaterialList.controls[control.itemIndex].controls[0].label
				# referesh and repopulate the material option controls
				self.guiMaterialSWrapButton.state = matList[materialName]['SWrap']
				self.guiMaterialTWrapButton.state = matList[materialName]['TWrap']
				self.guiMaterialTransButton.state = matList[materialName]['Translucent']
				self.guiMaterialAddButton.state = matList[materialName]['Additive']
				self.guiMaterialSubButton.state = matList[materialName]['Subtractive']
				self.guiMaterialSelfIllumButton.state = matList[materialName]['SelfIlluminating']
				self.guiMaterialEnvMapButton.state = not matList[materialName]['NeverEnvMap']
				self.guiMaterialMipMapButton.state = not matList[materialName]['NoMipMap']
				self.guiMaterialMipMapZBButton.state = matList[materialName]['MipMapZeroBorder']
				self.guiMaterialIFLMatButton.state = matList[materialName]['IFLMaterial']
				self.guiMaterialDetailMapButton.state = matList[materialName]['DetailMapFlag']
				self.guiMaterialBumpMapButton.state = matList[materialName]['BumpMapFlag']
				self.guiMaterialRefMapButton.state = matList[materialName]['ReflectanceMapFlag']			
				self.guiMaterialDetailMapMenu.selectStringItem(matList[materialName]['DetailTex'])
				self.guiMaterialBumpMapMenu.selectStringItem(matList[materialName]['BumpMapTex'])
				self.guiMaterialReflectanceMapMenu.selectStringItem(matList[materialName]['RefMapTex'])
				self.guiMaterialReflectanceSlider.value = matList[materialName]['reflectance'] * 100.0
				self.guiMaterialDetailScaleSlider.value = matList[materialName]['detailScale'] * 100.0
				self.guiMaterialOptionsTitle.label = ("DTS Material: %s" % materialName)
			else:
				self.guiMaterialSWrapButton.state = False
				self.guiMaterialTWrapButton.state = False
				self.guiMaterialTransButton.state = False
				self.guiMaterialAddButton.state = False
				self.guiMaterialSubButton.state = False
				self.guiMaterialSelfIllumButton.state = False
				self.guiMaterialEnvMapButton.state = False
				self.guiMaterialMipMapButton.state = False
				self.guiMaterialMipMapZBButton.state = False
				self.guiMaterialIFLMatButton.state = False
				self.guiMaterialDetailMapButton.state = False
				self.guiMaterialBumpMapButton.state = False
				self.guiMaterialRefMapButton.state = False
				self.guiMaterialDetailMapMenu.selectStringItem("")
				self.guiMaterialBumpMapMenu.selectStringItem("")
				self.guiMaterialReflectanceMapMenu.selectStringItem("")
				self.guiMaterialReflectanceSlider.value = 0
				self.guiMaterialDetailScaleSlider.value = 100
				guiMaterialOptions.enabled = False
				self.guiMaterialOptionsTitle.label = "DTS Material: None Selected"


		if guiMaterialList.itemIndex == -1: return

		elif control.name == "guiMaterialSWrapButton":
			Prefs['Materials'][materialName]['SWrap'] = control.state
		elif control.name == "guiMaterialTWrapButton":
			Prefs['Materials'][materialName]['TWrap'] = control.state
		elif control.name == "guiMaterialTransButton":
			if not control.state:
				Prefs['Materials'][materialName]['Subtractive'] = False
				self.guiMaterialSubButton.state = False
				Prefs['Materials'][materialName]['Additive'] = False
				self.guiMaterialAddButton.state = False
			Prefs['Materials'][materialName]['Translucent'] = control.state
		elif control.name == "guiMaterialAddButton":
			if control.state:
				Prefs['Materials'][materialName]['Translucent'] = True
				self.guiMaterialTransButton.state = True
				Prefs['Materials'][materialName]['Subtractive'] = False
				self.guiMaterialSubButton.state = False
			Prefs['Materials'][materialName]['Additive'] = control.state
		elif control.name == "guiMaterialSubButton":
			if control.state:
				Prefs['Materials'][materialName]['Translucent'] = True
				self.guiMaterialTransButton.state = True
				Prefs['Materials'][materialName]['Additive'] = False
				self.guiMaterialAddButton.state = False
			Prefs['Materials'][materialName]['Subtractive'] = control.state
		elif control.name == "guiMaterialSelfIllumButton":
			Prefs['Materials'][materialName]['SelfIlluminating'] = control.state
		elif control.name == "guiMaterialEnvMapButton":
			if not control.state:
				Prefs['Materials'][materialName]['ReflectanceMapFlag'] = False
				self.guiMaterialRefMapButton.state = False
			Prefs['Materials'][materialName]['NeverEnvMap'] = not control.state
		elif control.name == "guiMaterialMipMapButton":
			if not control.state:
				Prefs['Materials'][materialName]['MipMapZeroBorder'] = False
				self.guiMaterialMipMapZBButton.state = False
			Prefs['Materials'][materialName]['NoMipMap'] = not control.state
		elif control.name == "guiMaterialMipMapZBButton":
			if control.state:
				Prefs['Materials'][materialName]['NoMipMap'] = False
				self.guiMaterialMipMapButton.state = True
			Prefs['Materials'][materialName]['MipMapZeroBorder'] = control.state
		elif control.name == "guiMaterialIFLMatButton":
			Prefs['Materials'][materialName]['IFLMaterial'] = control.state
			IFLControls.clearIFLMatPulldown()
			IFLControls.populateIFLMatPulldown()
		elif control.name == "guiMaterialDetailMapButton":
			Prefs['Materials'][materialName]['DetailMapFlag'] = control.state
		elif control.name == "guiMaterialBumpMapButton":
			Prefs['Materials'][materialName]['BumpMapFlag'] = control.state
		elif control.name == "guiMaterialRefMapButton":
			if control.state:
				Prefs['Materials'][materialName]['NeverEnvMap'] = False
				self.guiMaterialEnvMapButton.state = True
			Prefs['Materials'][materialName]['ReflectanceMapFlag'] = control.state
		elif control.name == "guiMaterialDetailMapMenu":
			Prefs['Materials'][materialName]['DetailTex'] = control.getSelectedItemString()
		elif control.name == "guiMaterialShowAdvancedButton":
			if control.state == True:
				self.guiMaterialRefMapButton.enabled = True
				self.guiMaterialBumpMapButton.enabled = True
				self.guiMaterialBumpMapMenu.enabled = True
				self.guiMaterialReflectanceMapMenu.enabled = True
				self.guiMaterialRefMapButton.visible = True
				self.guiMaterialBumpMapButton.visible = True
				self.guiMaterialBumpMapMenu.visible = True
				self.guiMaterialReflectanceMapMenu.visible = True
			else:
				self.guiMaterialRefMapButton.enabled = False
				self.guiMaterialBumpMapButton.enabled = False
				self.guiMaterialBumpMapMenu.enabled = False
				self.guiMaterialReflectanceMapMenu.enabled = False
				self.guiMaterialRefMapButton.visible = False
				self.guiMaterialBumpMapButton.visible = False
				self.guiMaterialBumpMapMenu.visible = False
				self.guiMaterialReflectanceMapMenu.visible = False
		elif control.name == "guiMaterialBumpMapMenu":
			Prefs['Materials'][materialName]['BumpMapTex'] = control.getSelectedItemString()
		elif control.name == "guiMaterialReflectanceMapMenu":
			Prefs['Materials'][materialName]['RefMapTex'] = control.getSelectedItemString()
		elif control.name == "guiMaterialReflectanceSlider":
			Prefs['Materials'][materialName]['reflectance'] = control.value / 100.0
		elif control.name == "guiMaterialDetailScaleSlider":
			Prefs['Materials'][materialName]['detailScale'] = control.value / 100.0


	def clearMaterialList(self):
		global Prefs
		guiMaterialList = self.guiMaterialList
		for i in range(0, len(guiMaterialList.controls)):
			del guiMaterialList.controls[i].controls[:]
		del guiMaterialList.controls[:]
		guiMaterialList.itemIndex = -1
		guiMaterialList.scrollPosition = 0
		if guiMaterialList.callback: guiMaterialList.callback(guiMaterialList) # Bit of a hack, but works


	def populateMaterialList(self):
		global Prefs
		guiMaterialList = self.guiMaterialList
		guiMaterialOptions = self.guiMaterialOptions
		# clear texture pulldowns
		self.guiMaterialDetailMapMenu.items = []
		self.guiMaterialBumpMapMenu.items = []
		self.guiMaterialReflectanceMapMenu.items = []
		# populate the texture pulldowns
		for img in Blender.Image.Get():
			self.guiMaterialDetailMapMenu.items.append(stripImageExtension(img.getName()))
			self.guiMaterialBumpMapMenu.items.append(stripImageExtension(img.getName()))
			self.guiMaterialReflectanceMapMenu.items.append(stripImageExtension(img.getName()))


		# autoimport blender materials
		self.importMaterialList()
		try:
			materials = Prefs['Materials']
		except:
			importMaterialList()
			materials = Prefs['Materials']


		# add the materials to the list
		startEvent = 40
		for mat in materials.keys():
			self.guiMaterialList.addControl(self.createMaterialListItem(mat, startEvent))
			startEvent += 1






def initGui():
	'''
		Steps to create and initialize a new control:

			1. Declare control in initGui() as global
			2. Initialize control giving: control name, text, tooltip, event id, onAction callback, and resize callback
			3. Add control to Common_Gui or to a container control
			4. Set gui control dimensions and position in resize callback
			5. Add code in onAction callback that responds to GUI events
		
		Button controls and other native controls that respond to user input must have a unique event ID assigned.
		
		A "tab book" is actually made up of 3 kinds of controls:
			1. A tab bar container (usually just a basic container), which holds the tab button controls
			3. Multiple TabButton controls for switching between tabs
			2. Multiple TabContainer controls (each corresponding to a tab button control) 
			   that hold the control sheets for each tab.		
	'''

	global Version, Prefs
	global guiSequenceTab, guiArmatureTab, guiMaterialsTab, guiGeneralTab, guiAboutTab, guiHeaderTab
	global guiSequenceSubtab, guiArmatureSubtab, guiGeneralSubtab, guiAboutSubtab, guiMaterialsSubtab
	global guiSequenceButton, guiMeshButton, guiArmatureButton, guiMaterialsButton, guiAboutButton
	global guiSeqActList, guiSeqActOpts, guiBoneList, guiMaterialList, guiMaterialOptions
	global guiTriListsButton, guiStripMeshesButton, guiTriMeshesButton
	global guiBonePatternText
	global GlobalEvents
	
	global SeqCommonControls, IFLControls, VisControls, ActionControls, MaterialControls, ArmatureControls, GeneralControls, AboutControls
	
	global guiTabBar, guiSequencesTabBar
	
	global guiSeqCommonButton, guiSeqActButton, guiSequenceIFLButton, guiSequenceVisibilityButton, guiSequenceUVButton, guiSequenceMorphButton
	global guiSeqCommonSubtab, guiSeqActSubtab, guiSequenceIFLSubtab, guiSequenceVisibilitySubtab, guiSequenceUVSubtab, guiSequenceMorphSubtab
	                                
	Common_Gui.initGui(exit_callback)
	
	# Main tab button controls
	guiSequenceButton = Common_Gui.TabButton("guiSequenceButton", "Sequences", "Sequence options", None, guiBaseCallback, guiBaseResize)
	guiSequenceButton.state = True
	guiArmatureButton = Common_Gui.TabButton("guiArmatureButton", "Armatures", "Armature options", None, guiBaseCallback, guiBaseResize)
	guiMaterialsButton = Common_Gui.TabButton("guiMaterialsButton", "Materials", "Material options", None, guiBaseCallback, guiBaseResize)
	guiMeshButton = Common_Gui.TabButton("guiMeshButton", "General", "Mesh and other options", None, guiBaseCallback, guiBaseResize)
	guiAboutButton = Common_Gui.TabButton("guiAboutButton", "About", "About", None, guiBaseCallback, guiBaseResize)
	
	# export button
	guiExportButton = Common_Gui.BasicButton("guiExportButton", "Export", "Export .dts shape", globalEvents.getNewID("Export"), guiBaseCallback, guiBaseResize)
	
	# Sequence Subtab button controls
	guiSeqCommonButton = Common_Gui.TabButton("guiSeqCommonButton", "Common/All", "All Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSeqActButton = Common_Gui.TabButton("guiSeqActButton", "Action", "Action Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSeqActButton.state = True
	guiSequenceIFLButton = Common_Gui.TabButton("guiSequenceIFLButton", "IFL", "IFL Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSequenceVisibilityButton = Common_Gui.TabButton("guiSequenceVisibilityButton", "Visibility", "Visibility Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSequenceUVButton = Common_Gui.TabButton("guiSequenceUVButton", "Texture UV", "Texture UV Coord Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSequenceMorphButton = Common_Gui.TabButton("guiSequenceMorphButton", "Morph", "Mesh Morph Animations", None, guiSequenceTabsCallback, guiBaseResize)

	
	# Header controls
	guiHeaderText = Common_Gui.SimpleText("guiHeaderText", "Torque Exporter Plugin", None, guiHeaderResize)
	headerTextColor = headerColor = Common_Gui.curTheme.get('buts').text_hi
	guiHeaderText.color = [headerTextColor[0]/255.0, headerTextColor[1]/255.0, headerTextColor[2]/255.0, headerTextColor[3]/255.0]
	guiVersionText = Common_Gui.SimpleText("guiVersionText", "Version %s" % Version, None, guiHeaderResize)
	
	# Container Controls
	guiHeaderBar = Common_Gui.BasicContainer("guiHeaderBar", "header", None, guiBaseResize)
	guiHeaderBar.borderColor = None
	headerColor = Common_Gui.curTheme.get('buts').header
	guiHeaderBar.color = [headerColor[0]/255.0, headerColor[1]/255.0, headerColor[2]/255.0, headerColor[3]/255.0]
	guiHeaderBar.fade_mode = 0
	guiTabBar = Common_Gui.BasicContainer("guiTabBar", "tabs", None, guiBaseResize)
	guiTabBar.fade_mode = 0
	guiSequenceTab = Common_Gui.TabContainer("guiSequenceTab", "content.sequence", guiSequenceButton, None, guiBaseResize)
	guiSequenceTab.fade_mode = 1
	guiSequenceTab.enabled, guiSequenceTab.visible = True, True
	guiSequencesTabBar = Common_Gui.BasicContainer("guiSequencesTabBar", "Sequence tabs", None, guiBaseResize)
	guiSequencesTabBar.fade_mode = 0
	guiSequencesTabBar.color = None
	guiSequencesTabBar.borderColor = None
	guiArmatureTab = Common_Gui.TabContainer("guiArmatureTab", "content.armature", guiArmatureButton, None, guiBaseResize)
	guiArmatureTab.fade_mode = 1
	guiArmatureTab.enabled, guiArmatureTab.visible = False, False
	guiMaterialsTab = Common_Gui.TabContainer("guiMaterialsTab", "content.materials", guiMaterialsButton, None, guiBaseResize)
	guiMaterialsTab.fade_mode = 1
	guiMaterialsTab.enabled, guiMaterialsTab.visible = False, False
	guiGeneralTab = Common_Gui.TabContainer("guiGeneralTab", "content.general", guiMeshButton, None, guiBaseResize)
	guiGeneralTab.fade_mode = 1
	guiGeneralTab.enabled, guiGeneralTab.visible = False, False
	guiAboutTab = Common_Gui.TabContainer("guiAboutTab", "content.about", guiAboutButton, None, guiBaseResize)
	guiAboutTab.fade_mode = 1
	guiAboutTab.enabled, guiAboutTab.visible = False, False
	
	# Sub-container Controls
	guiSeqCommonSubtab = Common_Gui.TabContainer("guiSeqCommonSubtab", None, guiSeqCommonButton, None, guiBaseResize)
	guiSeqCommonSubtab.fade_mode = 1
	guiSeqCommonSubtab.enabled, guiSeqCommonSubtab.visible = False, False
	guiSeqActSubtab = Common_Gui.TabContainer("guiSeqActSubtab", None, guiSeqActButton, None, guiBaseResize)
	guiSeqActSubtab.fade_mode = 1
	guiSeqActSubtab.enabled, guiSeqActSubtab.visible = True, True
	guiSequenceIFLSubtab = Common_Gui.TabContainer("guiSequenceIFLSubtab", None, guiSequenceIFLButton, None, guiBaseResize)
	guiSequenceIFLSubtab.fade_mode = 1
	guiSequenceIFLSubtab.enabled, guiSequenceIFLSubtab.visible = False, False
	guiSequenceVisibilitySubtab = Common_Gui.TabContainer("guiSequenceVisibilitySubtab", None, guiSequenceVisibilityButton, None, guiBaseResize)
	guiSequenceVisibilitySubtab.fade_mode = 1
	guiSequenceVisibilitySubtab.enabled, guiSequenceVisibilitySubtab.visible = False, False
	guiSequenceUVSubtab = Common_Gui.TabContainer("guiSequenceUVSubtab", None, guiSequenceUVButton, None, guiBaseResize)
	guiSequenceUVSubtab.fade_mode = 1
	guiSequenceUVSubtab.enabled, guiSequenceUVSubtab.visible = False, False
	guiSequenceMorphSubtab = Common_Gui.TabContainer("guiSequenceMorphSubtab", None, guiSequenceMorphButton, None, guiBaseResize)
	guiSequenceMorphSubtab.fade_mode = 1
	guiSequenceMorphSubtab.enabled, guiSequenceMorphSubtab.visible = False, False
	guiMaterialsSubtab = Common_Gui.BasicContainer("guiMaterialsSubtab", None, None, guiBaseResize)
	guiMaterialsSubtab.fade_mode = 1
	guiMaterialsSubtab.borderColor = [0,0,0,0]
	guiMaterialsSubtab.enabled, guiMaterialsSubtab.visible = True, True

	
	guiGeneralSubtab = Common_Gui.BasicContainer("guiGeneralSubtab", None, None, guiBaseResize)
	guiGeneralSubtab.fade_mode = 1
	guiArmatureSubtab = Common_Gui.BasicContainer("guiArmatureSubtab", None, None, guiBaseResize)
	guiArmatureSubtab.fade_mode = 1
	guiAboutSubtab = Common_Gui.BasicContainer("guiAboutSubtab", None, None, guiBaseResize)
	guiAboutSubtab.fade_mode = 1
	
	# Add all controls to respective containers
	
	guiHeaderBar.addControl(guiHeaderText)
	guiHeaderBar.addControl(guiVersionText)
	
	Common_Gui.addGuiControl(guiTabBar)
	guiTabBar.addControl(guiHeaderBar)
	guiTabBar.addControl(guiSequenceButton)
	guiTabBar.addControl(guiArmatureButton)
	guiTabBar.addControl(guiMaterialsButton)
	guiTabBar.addControl(guiMeshButton)
	
	guiTabBar.addControl(guiAboutButton)
	guiTabBar.addControl(guiExportButton)
	
		
	Common_Gui.addGuiControl(guiSequenceTab)
	guiSequenceTab.borderColor = [0,0,0,0]
	guiSequenceTab.addControl(guiSeqCommonSubtab)
	guiSequenceTab.addControl(guiSeqActSubtab)
	guiSequenceTab.addControl(guiSequenceIFLSubtab)
	guiSequenceTab.addControl(guiSequenceVisibilitySubtab)
	guiSequenceTab.addControl(guiSequenceUVSubtab)
	guiSequenceTab.addControl(guiSequenceMorphSubtab)
	
	guiMaterialsTab.addControl(guiMaterialsSubtab)
	
	guiSequenceTab.addControl(guiSequencesTabBar)
	guiSequencesTabBar.addControl(guiSeqCommonButton)
	guiSequencesTabBar.addControl(guiSeqActButton)
	guiSequencesTabBar.addControl(guiSequenceIFLButton)
	guiSequencesTabBar.addControl(guiSequenceVisibilityButton)
	guiSequencesTabBar.addControl(guiSequenceUVButton)
	guiSequencesTabBar.addControl(guiSequenceMorphButton)


	guiSeqCommonSubtab.borderColor = [0,0,0,0]
	guiSeqActSubtab.borderColor = [0,0,0,0]
	guiSequenceIFLSubtab.borderColor = [0,0,0,0]
	guiSequenceVisibilitySubtab.borderColor = [0,0,0,0]
	guiSequenceUVSubtab.borderColor = [0,0,0,0]
	guiSequenceMorphSubtab.borderColor = [0,0,0,0]

	
	Common_Gui.addGuiControl(guiArmatureTab)
	guiArmatureTab.borderColor = [0,0,0,0]
	guiArmatureTab.addControl(guiArmatureSubtab)
	guiArmatureSubtab.borderColor = [0,0,0,0]
	
	
	Common_Gui.addGuiControl(guiMaterialsTab)
	
	Common_Gui.addGuiControl(guiGeneralTab)
	guiGeneralTab.borderColor = [0,0,0,0]
	guiGeneralTab.addControl(guiGeneralSubtab)
	guiGeneralSubtab.borderColor = [0,0,0,0]
	
	Common_Gui.addGuiControl(guiAboutTab)
	guiAboutTab.borderColor = [0,0,0,0]
	guiAboutTab.addControl(guiAboutSubtab)
	guiAboutSubtab.borderColor = [0,0,0,0]
	

	# Initialize all tab pages
	SeqCommonControls = SeqCommonControlsClass()
	ActionControls = ActionControlsClass()
	IFLControls = IFLControlsClass()
	VisControls = VisControlsClass()
	MaterialControls = MaterialControlsClass()
	ArmatureControls = ArmatureControlsClass()
	GeneralControls = GeneralControlsClass()
	AboutControls = AboutControlsClass()
	
	# Restore last tab selection
	restoreLastActivePanel()

# Called when gui exits
def exit_callback():
	global SeqCommonControls, IFLControls, ActionControls, MaterialControls, ArmatureControls, GeneralControls, AboutControls
	Torque_Util.dump_setout("stdout")
	ActionControls.clearSequenceList()
	ArmatureControls.clearBoneGrid()
	# todo - clear lists on other panels before cleaning up.	
	IFLControls.cleanup()
	ActionControls.cleanup()
	VisControls.cleanup()
	MaterialControls.cleanup()
	ArmatureControls.cleanup()
	GeneralControls.cleanup()
	AboutControls.cleanup()
	savePrefs()

'''
	Entry Point
'''
#-------------------------------------------------------------------------------------------------

if Profiling:
	try:
		import profile
		import __main__
		import pstats
	except:
		Profiling = False
	
def entryPoint(a):
	global Prefs
	getPathSeperator(Blender.Get("filename"))
	
	loadPrefs()
	
	if Debug:
		Torque_Util.dump_setout("stdout")
	else:
		try: x = Prefs['LogToOutputFolder']
		except KeyError: Prefs['LogToOutputFolder'] = True
		if Prefs['LogToOutputFolder']:
			getPathSeperator(Prefs['exportBasepath'])
			Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSeperator, noext(Prefs['exportBasename'])) )
		else:
			Torque_Util.dump_setout("%s.log" % noext(Blender.Get("filename")))
		
		
	
	Torque_Util.dump_writeln("Torque Exporter %s " % Version)
	Torque_Util.dump_writeln("Using blender, version %s" % Blender.Get('version'))
	
	#if Torque_Util.Torque_Math.accelerator != None:
	#	Torque_Util.dump_writeln("Using accelerated math interface '%s'" % Torque_Util.Torque_Math.accelerator)
	#else:
	#	Torque_Util.dump_writeln("Using unaccelerated math code, performance may be suboptimal")
	#Torque_Util.dump_writeln("**************************")
	
	
	
	if (a == 'quick'):
		handleScene()
		# Use the profiler, if enabled.
		if Profiling:
			# make the entry point available from __main__
			__main__.export = export
			profile.run('export(),', 'exporterProfilelog.txt')
		else:
			export()
		
		# dump out profiler stats if enabled
		if Profiling:
			# print out the profiler stats.
			p = pstats.Stats('exporterProfilelog.txt')
			p.strip_dirs().sort_stats('cumulative').print_stats(60)
			p.strip_dirs().sort_stats('time').print_stats(60)
			p.strip_dirs().print_callers('__getitem__', 20)
	elif a == 'normal' or (a == None):
		# Process scene and load configuration gui
		handleScene()
		initGui()
	


# Main entrypoint
if __name__ == "__main__":
	entryPoint('normal')
