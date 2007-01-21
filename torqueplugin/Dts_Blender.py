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
import string
import math
import re

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

Version = "0.93"
Prefs = None
Prefs_keyname = ""
export_tree = None
Debug = False
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
#-------------------------------------------------------------------------------------------------
	
# Loads preferences from a text buffer (old version)
def loadOldTextPrefs(text_doc):
	global Prefs, dummySequence

	cur_parse = 0

	text_arr = array('c')
	txt = ""
	lines = text_doc.asLines()
	for l in lines: txt += "%s\n" % l
	text_arr.fromstring(txt)
	seq_name = None
	tok = Tokenizer(text_arr)
	while tok.advanceToken(True):
		cur_token = tok.getToken()
		if cur_token == "Version":
			tok.advanceToken(False)
			if not ( (float(tok.getToken())) > 0.0 and (float(tok.getToken()) <= 0.2) ):
				Torque_Util.dump_writeln("   Error: Loading different version config file than is supported")
				return False
		elif cur_token == "{":
			cur_parse = 1
			while tok.advanceToken(True):
				cur_token = tok.getToken()
				# Parse Main Section
				if cur_token == "WriteShapeScript":
					tok.advanceToken(False)
					Prefs['WriteShapeScript'] = int(tok.getToken())
				elif cur_token == "DTSVersion":
					tok.advanceToken(False)
					Prefs['DTSVersion'] = int(tok.getToken())
				#elif cur_token == "PrimType":
				#	tok.advanceToken(False)
				#	Prefs['PrimType'] = (tok.getToken())
				elif cur_token == "StripMeshes":
					tok.advanceToken(False)
					Prefs['StripMeshes'] = int(tok.getToken())
				elif cur_token == "MaxStripSize":
					tok.advanceToken(False)
					Prefs['MaxStripSize'] = int(tok.getToken())
				elif cur_token == "UseStickyCoords": tok.advanceToken(False)
				elif cur_token == "WriteSequences":
					tok.advanceToken(False)
					#Prefs['WriteSequences'] = int(tok.getToken())
				elif cur_token == "ClusterDepth":
					tok.advanceToken(False)
					Prefs['ClusterDepth'] = int(tok.getToken())
				elif cur_token == "AlwaysWriteDepth":
					tok.advanceToken(False)
					Prefs['AlwaysWriteDepth"'] = int(tok.getToken())
				elif cur_token == "Billboard":
					tok.advanceToken(False)
					Prefs['Billboard']['Enabled'] = bool(int(tok.getToken()))
					if int(tok.getToken()):
						cur_parse = 2
				elif cur_token == "Sequence":
					tok.advanceToken(False)
					seq_name = tok.getToken()
					Prefs['Sequences'][seq_name] = dummySequence.copy()
					Prefs['Sequences'][seq_name]['Triggers'] = []
					# set defaults for ref pose stuff
					# Get number of frames for this sequence
					#try:
					action = Blender.Armature.NLA.GetActions()[seq_name]
					Prefs['Sequences'][seq_name]['InterpolateFrames'] = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
					Prefs['Sequences'][seq_name]['BlendRefPoseAction'] = seq_name
					blendRefPoseFrame = Prefs['Sequences'][seq_name]['InterpolateFrames']/2
					if blendRefPoseFrame < 1: blendRefPoseFrame = 1
					Prefs['Sequences'][seq_name]['BlendRefPoseFrame'] = blendRefPoseFrame
					Prefs['Sequences'][seq_name]['Priority'] = 0

					cur_parse = 3
				elif cur_token == "BannedBones":
					tok.advanceToken(False)
					Prefs['BannedBones'].append("%s" % tok.getToken())
				elif (cur_token == "{") and (cur_parse == 2):
					# Parse Billboard Section
					while tok.advanceToken(True):
						cur_token = tok.getToken()
						if cur_token == "Equator":
							tok.advanceToken(False)
							Prefs['Billboard']['Equator'] = int(tok.getToken())
						elif cur_token == "Polar":
							tok.advanceToken(False)
							Prefs['Billboard']['Polar'] = int(tok.getToken())
						elif cur_token == "PolarAngle":
							tok.advanceToken(False)
							Prefs['Billboard']['PolarAngle'] = float(tok.getToken())
						elif cur_token == "Dim":
							tok.advanceToken(False)
							Prefs['Billboard']['Dim'] = int(tok.getToken())
						elif cur_token == "IncludePoles":
							tok.advanceToken(False)
							Prefs['Billboard']['IncludePoles'] = bool(int(tok.getToken()))
						elif cur_token == "Size":
							tok.advanceToken(False)
							Prefs['Billboard']['Size'] = int(tok.getToken())
						elif cur_token == "}":
							break
						else:
							Torque_Util.dump_writeln("   Unrecognised Billboard token : %s" % cur_token)
					cur_parse = 1
				elif (cur_token == "{") and (cur_parse == 3):
					useKeyframes = True
					# Parse Sequence Section
					while tok.advanceToken(True):
						cur_token = tok.getToken()
						if cur_token == "Dsq":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['Dsq'] = bool(int(tok.getToken()))
						elif cur_token == "Cyclic":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['Cyclic'] = bool(int(tok.getToken()))
						elif cur_token == "Blend":
							tok.advanceToken(False)
							# Lets always set the actions to not be blends when loading style old prefs.
							# This hopefully forces the user to look at how blend anims are handled now.
							#Prefs['Sequences'][seq_name]['Blend'] = bool(int(tok.getToken()))
							Prefs['Sequences'][seq_name]['Blend'] = False
						elif (cur_token == "Interpolate_Count") or (cur_token == "Interpolate"):
							tok.advanceToken(False)
							useKeyframes = True
						elif cur_token == "NoExport":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['NoExport'] = bool(int(tok.getToken()))
						elif cur_token == "NumGroundFrames":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['NumGroundFrames'] = int(tok.getToken())
						elif cur_token == "Triggers":
							tok.advanceToken(False)
							triggers_left = int(tok.getToken())
							for t in range(0, triggers_left): Prefs['Sequences'][seq_name]['Triggers'].append([0,0, True])
							while tok.advanceToken(True):
								cur_token = tok.getToken()
								if cur_token == "Value":
									tok.advanceToken(False)
									stValue = int(tok.getToken())
									if stValue < 0:
										stValue += 32
										Prefs['Sequences'][seq_name]['Triggers'][-triggers_left][2] = False
									Prefs['Sequences'][seq_name]['Triggers'][-triggers_left][0] = stValue
								elif cur_token == "Time":
									tok.advanceToken(False)
									Prefs['Sequences'][seq_name]['Triggers'][-triggers_left][1] = 0
									triggers_left -= 1
								elif cur_token == "}":
									break
								elif cur_token == "{":
									pass
								else:
									Torque_Util.dump_writeln("   Unrecognised Sequence Trigger token : %s" % cur_token)
						elif cur_token == "}":
							cur_parse = 1
							seq_name = None
							break
						else:
							Torque_Util.dump_writeln("   Unrecognised Sequence token : %s" % cur_token)

					cur_parse = 1
					# Get number of frames for this sequence
					if seq_name != None:
						try:
							action = Blender.NLA.Action.Get(seq_name)
							Prefs['Sequences'][seq_name]['InterpolateFrames'] = DtsShape_Blender.getNumFrames(None, action.getAllChannelIpos().values(), useKeyframes)
						except:
							Torque_Util.dump_writeln("   Warning : sequence '%s' doesn't exist!" % seq_name)
							Prefs['Sequences'][seq_name]['InterpolateFrames'] = 0
				elif cur_token == "}":
					cur_parse = 0
					break
				else:
					Torque_Util.dump_writeln("   Unrecognised token : %s" % cur_token)
		else:
			Torque_Util.dump_writeln("   Warning : Unexpected token %s!" % cur_token)

	return True

def initPrefs():
	Prefs = {}
	Prefs['Version'] = 0.9 # NOTE: change version if anything *major* is changed.
	Prefs['DTSVersion'] = 24
	Prefs['WriteShapeScript'] = False
	Prefs['Sequences'] = {}
	#Prefs['StripMeshes'] = False
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
				if not loadOldTextPrefs(text_doc):
					print "Error: failed to load old preferences!"
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

dummySequence = {'Dsq' : False,
'Cyclic' : False,
'Blend' : False,
'Triggers' : [], # [State, Time, On]
'AnimateMaterial' : False,
'MaterialIpoStartFrame' : 1,
'InterpolateFrames' : 0,
'NoExport' : False,
'NumGroundFrames' : 0,
'Priority' : 0}

# Gets a sequence key from the preferences
# Creates default if key does not exist
def getSequenceKey(value):
	global Prefs, dummySequence
	if value == "N/A":
		return dummySequence
	try:
		return Prefs['Sequences'][value]	
	except KeyError:
		Prefs['Sequences'][value] = dummySequence.copy()
		# Create anything that cannot be copied (reference objects like lists),
		# and set everything that needs a default
		Prefs['Sequences'][value]['Triggers'] = []
		try:
			action = Blender.Armature.NLA.GetActions()[value]
			maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
		except:
			maxNumFrames = 0
		Prefs['Sequences'][value]['InterpolateFrames'] = maxNumFrames			
		# added for ref pose of blend animations
		# default reference pose for blends is in the middle of the same action
		Prefs['Sequences'][value]['BlendRefPoseAction'] = value			
		Prefs['Sequences'][value]['BlendRefPoseFrame'] = maxNumFrames/2
		Prefs['Sequences'][value]['Priority'] = 0
		return getSequenceKey(value)

# Cleans up extra keys that may not be used anymore (e.g. action deleted)
def cleanKeys():
	# Sequences
	delKeys = []
	for key in Prefs['Sequences'].keys():
		Found = False
		for action_key in Armature.NLA.GetActions().keys():
			if action_key == key:
				Found = True
				break
		if not Found: del Prefs['Sequences'][key]

	for key in delKeys:
		del Prefs['Sequences'][key]

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
		for c in self.children:
			if c == None: continue
			c.process(progressBar)

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
		Scene.getCurrent().getRenderingContext().currentFrame(1)
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
								# Joe : hey neat :)
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
				progressBar.update()
				if Prefs['PrimType'] == "TriStrips":
					self.Shape.stripMeshes(Prefs['MaxStripSize'])
				progressBar.update()
				
				# Add all actions (will ignore ones not belonging to shape)
				if True:
					scene = Blender.Scene.GetCurrent()
					context = scene.getRenderingContext()
					actions = Armature.NLA.GetActions()

					# check the armatures to see if any are locked in rest position
					for armOb in Blender.Object.Get():
						if (armOb.getType() != 'Armature'): continue
						if armOb.getData().restPosition:
							Blender.Draw.PupMenu("Warning%t|One or more of your armatures is locked into rest position. This can cause problems with exported animations.")
							break

					# The ice be dammed, it's time to take action
					if len(actions.keys()) > 0:
						progressBar.pushTask("Adding Actions..." , len(actions.keys()*4), 0.8)
						for action_name in actions.keys():
							# skip the fake action (workaround for a blender bug)
							# TODO: surround this w/ version check when bug is fixed.
							if action_name == "DTSEXPFAKEACT": continue
							
							sequenceKey = getSequenceKey(action_name)
							if (sequenceKey['NoExport']) or (sequenceKey['InterpolateFrames'] == 0):
								progressBar.update()
								progressBar.update()
								progressBar.update()
								progressBar.update()
								continue
							
							# Sequence the Action
							sequence = self.Shape.addAction(actions[action_name], scene, context, getSequenceKey(action_name))
							if sequence == None:
								Torque_Util.dump_writeln("Warning : Couldn't add action '%s' to shape!" % action_name)
								progressBar.update()
								progressBar.update()
								progressBar.update()
								progressBar.update()
								continue
							progressBar.update()
							
							# Pull the triggers
							if len(sequenceKey['Triggers']) != 0:
								self.Shape.addSequenceTriggers(sequence, sequenceKey['Triggers'], DtsShape_Blender.getNumFrames(actions[action_name].getAllChannelIpos().values(), False))
							progressBar.update()
							
							# Materialize
							if sequenceKey['AnimateMaterial']:
								self.Shape.addSequenceMaterialIpos(sequence, DtsShape_Blender.getNumFrames(actions[action_name].getAllChannelIpos().values(), False), sequenceKey['MaterialIpoStartFrame'])
							progressBar.update()
							
							# Hey you, DSQ!
							if sequenceKey['Dsq']:
								self.Shape.convertAndDumpSequenceToDSQ(sequence, "%s/%s.dsq" % (Prefs['exportBasepath'], action_name), Stream.DTSVersion)
								Torque_Util.dump_writeln("Loaded and dumped sequence '%s' to '%s/%s.dsq'." % (action_name, Prefs['exportBasepath'], action_name))
							else:
								Torque_Util.dump_writeln("Loaded sequence '%s'." % action_name)
								
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
					for bone in c.getData().bones.values():
						armBoneList.append(bone.name)
					# sort each armature's bone list before
					# appending it to the main list.
					armBoneList.sort()
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
	Torque_Util.dump_writeln("Cleaning Preference Keys")
	cleanKeys()

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

guiSequenceOptions = None
guiSequenceList = None
guiBoneList = None

def guiSequenceListItemCallback(control):
	global Prefs, guiSequenceList
	
	# Determine sequence name
	
	if control.evt == 40:
		calcIdx = 0
	else:
		calcIdx = (control.evt - 40) / 4

	sequenceName = guiSequenceList.controls[calcIdx].controls[0].label
	realItem = control.evt - 40 - (calcIdx*4)
	sequencePrefs = getSequenceKey(sequenceName)
	
	if realItem == 0:
		sequencePrefs['NoExport'] = not control.state
	elif realItem == 1:
		sequencePrefs['Dsq'] = control.state
	elif realItem == 2:
		sequencePrefs['Blend'] = control.state
		# if blend is true, show the ref pose controls
		if sequencePrefs['Blend'] == True:
			guiSequenceOptions.controls[12].visible = True
			guiSequenceOptions.controls[13].visible = True
			guiSequenceOptions.controls[14].visible = True
		else:
			guiSequenceOptions.controls[12].visible = False
			guiSequenceOptions.controls[13].visible = False
			guiSequenceOptions.controls[14].visible = False
	elif realItem == 3:
		sequencePrefs['Cyclic'] = control.state

# New
def guiBoneListItemCallback(control):
	global Prefs, guiSequenceList
	
	# Determine id of clicked button
	
	if control.evt == 40:
		calcIdx = 0
	else:
		calcIdx = (control.evt - 40) #/ 4
	real_name = control.name.upper()
	if control.state:
		# Remove entry from BannedBones
		for i in range(0, len(Prefs['BannedBones'])):
			if Prefs['BannedBones'][i] == real_name:
				del Prefs['BannedBones'][i]
				break
	else:
		Prefs['BannedBones'].append(real_name)




def createSequenceListitem(seq_name, startEvent):
	sequencePrefs = getSequenceKey(seq_name)
	# Note on positions:
	# It quicker to assign these here, as there is no realistic chance scaling being required.
	guiContainer = Common_Gui.BasicContainer("", None, None)
	
	# testing new fade modes for sequence list items
	guiContainer.fade_mode = 8  # same as 2 but with a brighter endcolor, easier on the eyes.
	guiName = Common_Gui.SimpleText("", seq_name, None, None)
	guiName.x, guiName.y = 5, 5
	guiExport = Common_Gui.ToggleButton("Export", "Export Sequence", startEvent, guiSequenceListItemCallback, None)
	guiExport.x, guiExport.y = 70, 5
	guiExport.width, guiExport.height = 50, 15
	guiExport.state = not sequencePrefs['NoExport']
	guiDSQ = Common_Gui.ToggleButton("Dsq", "Export Sequence as DSQ", startEvent+1, guiSequenceListItemCallback, None)
	guiDSQ.x, guiDSQ.y = 122, 5
	guiDSQ.width, guiDSQ.height = 50, 15
	guiDSQ.state = sequencePrefs['Dsq']
	guiBlend = Common_Gui.ToggleButton("Blend", "Export Sequence as Blend", startEvent+2, guiSequenceListItemCallback, None)
	guiBlend.x, guiBlend.y = 174, 5
	guiBlend.width, guiBlend.height = 50, 15
	guiBlend.state = sequencePrefs['Blend']
	guiCyclic = Common_Gui.ToggleButton("Cyclic", "Export Sequence as Cyclic", startEvent+3, guiSequenceListItemCallback, None)
	guiCyclic.x, guiCyclic.y = 226, 5
	guiCyclic.width, guiCyclic.height = 50, 15
	guiCyclic.state = sequencePrefs['Cyclic']
	
	# Add everything
	guiContainer.addControl(guiName)
	guiContainer.addControl(guiExport)
	guiContainer.addControl(guiDSQ)
	guiContainer.addControl(guiBlend)
	guiContainer.addControl(guiCyclic)
	
	return guiContainer

# new
def createBoneListitem(bone1, bone2, bone3, bone4, startEvent):
	#sequencePrefs = getSequenceKey(seq_name)
	# Note on positions:
	# It quicker to assign these here, as there is no realistic chance scaling being required.
	guiContainer = Common_Gui.BasicContainer("", None, None)
	
	# testing new fade modes for sequence list items
	guiContainer.fade_mode = 0  # same as 2 but with a brighter endcolor, easier on the eyes.
	guiContainer.borderColor = None
	#guiName = Common_Gui.SimpleText("", seq_name, None, None)
	#guiName.x, guiName.y = 5, 5
	if bone1 != None:
		guiBone1 = Common_Gui.ToggleButton(bone1, "Toggle Status of " + bone1, startEvent, guiBoneListItemCallback, None)
		guiBone1.x, guiBone1.y = 0, 0
		guiBone1.width, guiBone1.height = 70, 19
		guiBone1.state = True
		guiContainer.addControl(guiBone1)
	if bone2 != None:
		guiBone2 = Common_Gui.ToggleButton(bone2, "Toggle Status of " + bone2, startEvent+1, guiBoneListItemCallback, None)
		guiBone2.x, guiBone2.y = 71, 0
		guiBone2.width, guiBone2.height = 70, 19
		guiBone2.state = True
		guiContainer.addControl(guiBone2)
	if bone3 != None:
		guiBone3 = Common_Gui.ToggleButton(bone3, "Toggle Status of " + bone3, startEvent+3, guiBoneListItemCallback, None)
		guiBone3.x, guiBone3.y = 142, 0
		guiBone3.width, guiBone3.height = 70, 19
		guiBone3.state = True
		guiContainer.addControl(guiBone3)
	if bone4 != None:
		guiBone4 = Common_Gui.ToggleButton(bone4, "Toggle Status of " + bone4, startEvent+4, guiBoneListItemCallback, None)
		guiBone4.x, guiBone4.y = 213, 0
		guiBone4.width, guiBone4.height = 70, 19
		guiBone4.state = True
		guiContainer.addControl(guiBone4)	
	return guiContainer


def populateSequenceList():
	global guiSequenceList
	actions = Armature.NLA.GetActions()
	keys = actions.keys()
	keys.sort()
	
	#print "populateSequenceList: name of list : %s" % guiSequenceList.name
	# There are a finite number of events we can allocate in blender, so we need to
	# assign events in batches of the maximum number of visible list items.
	startEvent = 40
	for key in keys:
		# skip the fake action (hack for blender 2.41 bug)
		if key == "DTSEXPFAKEACT": continue		
		guiSequenceList.addControl(createSequenceListitem(key, startEvent))
		startEvent += 4
		# add any new animations to the ref pose combo box
		if not (key in guiSequenceOptions.controls[13].items):
			guiSequenceOptions.controls[13].items.append(key)
		
def clearSequenceList():
	global guiSequenceList
	
	for i in range(0, len(guiSequenceList.controls)):
		del guiSequenceList.controls[i].controls[:]
	del guiSequenceList.controls[:]
	
	guiSequenceList.itemIndex = -1
	guiSequenceList.scrollPosition = 0
	if guiSequenceList.callback: guiSequenceList.callback(guiSequenceList) # Bit of a hack, but works
		
def populateBoneGrid():
	global Prefs, export_tree, guiBoneList
	shapeTree = export_tree.find("SHAPE")
	if shapeTree == None: return
	evtNo = 40
	count = 0
	names = []
	for name in shapeTree.getShapeBoneNames():
		names.append(name)
		if len(names) == 4:
			guiBoneList.addControl(createBoneListitem(names[0],names[1],names[2],names[3], evtNo))			
			guiBoneList.controls[count].controls[0].state = not (guiBoneList.controls[count].controls[0].name.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[1].state = not (guiBoneList.controls[count].controls[1].name.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[2].state = not (guiBoneList.controls[count].controls[2].name.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[3].state = not (guiBoneList.controls[count].controls[3].name.upper() in Prefs['BannedBones'])
			evtNo += 5
			count += 1
			names = []
	# add leftovers in last row
	if len(names) > 0:
		for i in range(len(names)-1, 4):
			names.append(None)
		guiBoneList.addControl(createBoneListitem(names[0],names[1],names[2],names[3], evtNo))
		if names[0] != None: guiBoneList.controls[count].controls[0].state = not (guiBoneList.controls[count].controls[0].name.upper() in Prefs['BannedBones'])
		if names[1] != None: guiBoneList.controls[count].controls[1].state = not (guiBoneList.controls[count].controls[1].name.upper() in Prefs['BannedBones'])
		if names[2] != None: guiBoneList.controls[count].controls[2].state = not (guiBoneList.controls[count].controls[2].name.upper() in Prefs['BannedBones'])
		if names[3] != None: guiBoneList.controls[count].controls[3].state = not (guiBoneList.controls[count].controls[3].name.upper() in Prefs['BannedBones'])
			
			
		
def clearBoneGrid():
	global guiBoneList
	del guiBoneList.controls[:]
		
def guiBoneGridCallback(control):
	global Prefs
	
	real_name = control.name.upper()
	if control.state:
		# Remove entry from BannedBones
		for i in range(0, len(Prefs['BannedBones'])):
			if Prefs['BannedBones'][i] == real_name:
				#print "Removed banned bone %s" % real_name
				del Prefs['BannedBones'][i]
				break
	else:
		Prefs['BannedBones'].append(real_name)
		#print "Added banned bone %s" % real_name

def guiBaseCallback(control):
	global guiSequenceTab, guiArmatureTab, guiGeneralTab, guiAboutTab
	if control.evt == 1:
		guiSequenceTab.visible = True
		guiGeneralTab.visible = False
		guiAboutTab.visible = False
		guiArmatureTab.visible = False
		guiSequenceTab.enabled = True
		guiGeneralTab.enabled = False
		guiAboutTab.enabled = False
		guiArmatureTab.enabled = False
	elif control.evt == 2:
		guiSequenceTab.visible = False
		guiGeneralTab.visible = True
		guiAboutTab.visible = False
		guiArmatureTab.visible = False
		guiSequenceTab.enabled = False
		guiGeneralTab.enabled = True
		guiAboutTab.enabled = False
		guiArmatureTab.enabled = False
	elif control.evt == 3:
		guiSequenceTab.visible = False
		guiGeneralTab.visible = False
		guiAboutTab.visible = False
		guiArmatureTab.visible = True
		guiSequenceTab.enabled = False
		guiGeneralTab.enabled = False
		guiAboutTab.enabled = False
		guiArmatureTab.enabled = True
	elif control.evt == 4:
		guiSequenceTab.visible = False
		guiGeneralTab.visible = False
		guiAboutTab.visible = True
		guiArmatureTab.visible = False
		guiSequenceTab.enabled = False
		guiGeneralTab.enabled = False
		guiAboutTab.enabled = True
		guiArmatureTab.enabled = False
	elif control.evt == 5:
		export()
		
def guiSequenceUpdateTriggers(triggerList, itemIndex):
	global guiSequenceOptions, guiSequenceList
	if (len(triggerList) == 0) or (itemIndex >= len(triggerList)):
				guiSequenceOptions.controls[7].value = 0
				guiSequenceOptions.controls[8].state = False
				guiSequenceOptions.controls[9].value = 0
	else:
				guiSequenceOptions.controls[7].value = triggerList[itemIndex][0] # State
				guiSequenceOptions.controls[9].value = triggerList[itemIndex][1] # Time
				guiSequenceOptions.controls[8].state = triggerList[itemIndex][2] # On

triggerMenuTemplate = "[%d] state=%d"

def guiSequenceTriggersCallback(control):
	global guiSequenceOptions, guiSequenceList, triggerMenuTemplate
	if guiSequenceList.itemIndex == -1:
		return
	
	sequenceName = guiSequenceList.controls[guiSequenceList.itemIndex].controls[0].label
	sequencePrefs = getSequenceKey(sequenceName)
	itemIndex = guiSequenceOptions.controls[6].itemIndex
				
	if control.evt == 14:
		guiSequenceUpdateTriggers(sequencePrefs['Triggers'], itemIndex)
	elif control.evt == 18:
		# Add
		sequencePrefs['Triggers'].append([1, 1, True])
		guiSequenceOptions.controls[6].items.append((triggerMenuTemplate % (1, 1)) + "(ON)")
		guiSequenceOptions.controls[6].itemIndex = len(sequencePrefs['Triggers'])-1
		guiSequenceUpdateTriggers(sequencePrefs['Triggers'], guiSequenceOptions.controls[6].itemIndex)
	elif (len(guiSequenceOptions.controls[6].items) != 0):
		if control.evt == 15:
			sequencePrefs['Triggers'][itemIndex][0] = control.value
		elif control.evt == 16:
			sequencePrefs['Triggers'][itemIndex][2] = control.state
		elif control.evt == 17:
			sequencePrefs['Triggers'][itemIndex][1] = control.value
		elif control.evt == 19:
			# Remove
			del sequencePrefs['Triggers'][itemIndex]
			del guiSequenceOptions.controls[6].items[itemIndex]
			# Must decrement itemIndex if we are out of bounds
			if itemIndex <= len(sequencePrefs['Triggers']):
				guiSequenceOptions.controls[6].itemIndex = len(sequencePrefs['Triggers'])-1
				itemIndex = guiSequenceOptions.controls[6].itemIndex
			guiSequenceUpdateTriggers(sequencePrefs['Triggers'], itemIndex)
		
		# Update menu caption
		if itemIndex == -1:
			return
		if sequencePrefs['Triggers'][itemIndex][2]: stateStr = "(ON)"
		else: stateStr = "(OFF)"
		guiSequenceOptions.controls[6].items[itemIndex] = (triggerMenuTemplate % (sequencePrefs['Triggers'][itemIndex][1], sequencePrefs['Triggers'][itemIndex][0])) + stateStr
		
def guiSequenceCallback(control):
	global guiSequenceOptions, guiSequenceList
	
	if control.evt == None:
		if control.name == "sequence.list":
			# Clear triggers menu
			del guiSequenceOptions.controls[6].items[:]
			if control.itemIndex != -1:
				sequenceName = control.controls[control.itemIndex].controls[0].label
				sequencePrefs = getSequenceKey(sequenceName)
				guiSequenceOptions.controls[0].label = "Sequence '%s'" % sequenceName
				
				try:
					action = Blender.Armature.NLA.GetActions()[sequenceName]
					maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
				except:
					maxNumFrames = 0
				
				# Update gui control states
				guiSequenceOptions.enabled = True
				guiSequenceOptions.controls[1].value = sequencePrefs['InterpolateFrames']
				guiSequenceOptions.controls[1].max = maxNumFrames
				guiSequenceOptions.controls[2].value = sequencePrefs['NumGroundFrames']
				guiSequenceOptions.controls[2].max = maxNumFrames
				guiSequenceOptions.controls[3].state = sequencePrefs['AnimateMaterial']
				guiSequenceOptions.controls[4].value = sequencePrefs['MaterialIpoStartFrame']
				
				# added for blend anim ref pose selection
				# make sure the user didn't delete the action containing the refrence pose
				# out from underneath us while we weren't looking.
				try: blah = Blender.Armature.NLA.GetActions()[sequencePrefs['BlendRefPoseAction']]
				except: sequencePrefs['BlendRefPoseAction'] = sequenceName
				guiSequenceOptions.controls[12].label = "Ref pose for '%s'" % sequenceName
				guiSequenceOptions.controls[13].setTextValue(sequencePrefs['BlendRefPoseAction'])
				guiSequenceOptions.controls[14].min = 1
				guiSequenceOptions.controls[14].max = DtsShape_Blender.getNumFrames(Blender.Armature.NLA.GetActions()[sequencePrefs['BlendRefPoseAction']].getAllChannelIpos().values(), False)
				guiSequenceOptions.controls[14].value = sequencePrefs['BlendRefPoseFrame']
				# hack, there must be a better way to handle this.
				try:
					guiSequenceOptions.controls[15].value = sequencePrefs['Priority']
				except KeyError:
					guiSequenceOptions.controls[15].value = 0
				
				
				# Triggers
				for t in sequencePrefs['Triggers']:
					if t[2]: stateStr = "(ON)"
					else: stateStr = "(OFF)"
					guiSequenceOptions.controls[6].items.append((triggerMenuTemplate % (t[1], t[0])) + stateStr)
				
				guiSequenceOptions.controls[6].itemIndex = 0
				guiSequenceOptions.controls[9].max = maxNumFrames
				guiSequenceUpdateTriggers(sequencePrefs['Triggers'], 0)
				# show/hide ref pose stuff.
				if sequencePrefs['Blend'] == True:
					guiSequenceOptions.controls[12].visible = True
					guiSequenceOptions.controls[13].visible = True
					guiSequenceOptions.controls[14].visible = True
				else:
					guiSequenceOptions.controls[12].visible = False
					guiSequenceOptions.controls[13].visible = False
					guiSequenceOptions.controls[14].visible = False

			else:
				guiSequenceOptions.enabled = False
				guiSequenceOptions.controls[0].label = "Sequence"

	else:
		if control.evt >= 10:
			if guiSequenceList.itemIndex != -1:
				sequenceName = guiSequenceList.controls[guiSequenceList.itemIndex].controls[0].label
				sequencePrefs = getSequenceKey(sequenceName)
				if control.evt == 10:
					sequencePrefs['InterpolateFrames'] = control.value
				elif control.evt == 11:
					#print "setting number of ground frames to: %i" % control.value
					sequencePrefs['NumGroundFrames'] = control.value
				elif control.evt == 12:
					sequencePrefs['AnimateMaterial'] = control.state
				elif control.evt == 13:
					sequencePrefs['MaterialIpoStartFrame'] = control.value
				# added for blend ref pose selection
				elif control.evt == 20:
					#print "setting refernce pose action to: %s" % control.items[control.itemIndex]
					sequencePrefs['BlendRefPoseAction'] = control.items[control.itemIndex]
					sequencePrefs['BlendRefPoseFrame'] = 1
					guiSequenceOptions.controls[14].value = sequencePrefs['BlendRefPoseFrame']
				elif control.evt == 21:
					#print "setting refernce pose frame to: %i" % control.value
					sequencePrefs['BlendRefPoseFrame'] = control.value
				elif control.evt == 23:
					#print "setting priority"
					sequencePrefs['Priority'] = control.value
				
		else:
			if control.evt == 6:
				for child in guiSequenceList.controls:
					child.controls[1].state = control.state
					getSequenceKey(child.controls[0].label)['NoExport'] = not control.state
			elif control.evt == 7:
				clearSequenceList()
				populateSequenceList()
			
def guiArmatureCallback(control):
	global Prefs
	if control.evt == 6:
		Prefs['CollapseRootTransform'] = bool(control.state)

def guiGeneralSelectorCallback(filename):
	global guiGeneralTab
	if filename != "":
		Prefs['exportBasename'] = basename(filename)
		Prefs['exportBasepath'] = basepath(filename)
		
		pathSep = "/"
		if "\\" in Prefs['exportBasepath']: pathSep = "\\"
		guiGeneralTab.controls[16].value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']

def guiGeneralCallback(control):
	global Prefs
	global guiGeneralTab
	global guiTriListsButton
	global guiStripMeshesButton
	global guiTriMeshesButton
	if control.evt == 6:
		Prefs['PrimType'] = "Tris"
		guiTriListsButton.state = False
		guiStripMeshesButton.state = False
		guiTriMeshesButton.state = True
	if control.evt == 7:
		Prefs['PrimType'] = "TriLists"
		guiTriListsButton.state = True
		guiStripMeshesButton.state = False
		guiTriMeshesButton.state = False
	if control.evt == 8:
		Prefs['PrimType'] = "TriStrips"
		guiTriListsButton.state = False
		guiStripMeshesButton.state = True
		guiTriMeshesButton.state = False
	elif control.evt == 9:
		Prefs['MaxStripSize'] = control.value
	elif control.evt == 10:
		Prefs['AlwaysWriteDepth'] = control.state
	elif control.evt == 11:
		Prefs['ClusterDepth'] = control.value
	elif control.evt == 12:
		Prefs['Billboard']['Enabled'] = control.state
	elif control.evt == 13:
		Prefs['Billboard']['Equator'] = control.value
	elif control.evt == 14:
		Prefs['Billboard']['Polar'] = control.value
	elif control.evt == 15:
		Prefs['Billboard']['PolarAngle'] = control.value
	elif control.evt == 16:
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
	elif control.evt == 17:
		Prefs['Billboard']['IncludePoles'] = control.state
	elif control.evt == 18:
		Prefs['Billboard']['Size'] = control.value
	if control.evt == 19:
		Prefs['WriteShapeScript'] = control.state
	elif control.evt == 20:
		Prefs['exportBasename'] = basename(control.value)
		Prefs['exportBasepath'] = basepath(control.value)
	elif control.evt == 21:
		Blender.Window.FileSelector (guiGeneralSelectorCallback, 'Select destination and filename')
	elif control.evt == 22:
		Prefs['exportBasename'] = basename(Blender.Get("filename"))
		Prefs['exportBasepath'] = basepath(Blender.Get("filename"))
		
		pathSep = "/"
		if "\\" in Prefs['exportBasepath']:
			pathSep = "\\"
		else:
			pathSep = "/"
		guiGeneralTab.controls[16].value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']
	elif control.evt == 23:
		Prefs['DTSVersion'] = control.value
	elif control.evt == 24:
		Prefs['TSEMaterial'] = control.state

def guiBaseResize(control, newwidth, newheight):
	tabContainers = ["content.sequence", "content.general", "content.armature", "content.about"]
	if control.evt == None:
		if control.name == "tabs":
			control.x, control.y = 0, 335
			control.width, control.height = 490, 55
		elif control.name in tabContainers:
			control.x, control.y = 0, 0
			control.width, control.height = 490, 335
		elif control.name == "header":
			control.x, control.y = 0, newheight - 20
			control.width, control.height = 490, 20
		elif control.name == "tabs.version":
			# TODO : adjust this whenever the version text changes
			control.x, control.y = newwidth-80, 10
			#control.x, control.y = newwidth-100, 10
	elif control.evt == 1:
		control.x, control.y = 10, 5
		control.width, control.height = 70, 20
	elif control.evt == 2:
		control.x, control.y = 160, 5
		control.width, control.height = 70, 20
	elif control.evt == 3:
		control.x, control.y = 85, 5
		control.width, control.height = 70, 20
	elif control.evt == 4:
		control.x, control.y = 235, 5
		control.width, control.height = 70, 20
	elif control.evt == 5:
		control.x, control.y = 310, 5
		control.width, control.height = 70, 20

def guiSequenceResize(control, newwidth, newheight):
	if control.evt == None:
		if control.name == "sequence.list":
			control.x = 10
			control.y = 30
			control.height = newheight - 55
			control.width = 300
		elif control.name == "sequence.title":
			control.x = 10
			control.y = newheight-15
		elif control.name == "sequence.prefs":
			control.x = newwidth - 180
			control.y = 0
			control.width = 180
			control.height = newheight
		elif control.name == "sequence.opts.title":
			control.x = 5
			control.y = newheight - 15
		elif control.name == "sequence.opts.btitle":
			control.x = 5
			control.y = newheight - 110
		elif control.name == "sequence.opts.ttitle":
			control.x = 5
			control.y = newheight - 215
		elif control.name == "sequence.opts.rtitle":
			control.x = 5
			control.y = newheight - 140
	# Sequence list buttons
	elif control.evt == 6:
		control.x = 10
		control.y = 5
		control.width = 100
	elif control.evt == 7:
		control.x = 112
		control.y = 5
		control.width = 100
	# Sequence options
	elif control.evt == 10:
		control.x = 5
		control.y = newheight - 45
		control.width = newwidth - 10
	elif control.evt == 11:
		control.x = 5
		control.y = newheight - 70
		control.width = newwidth - 10
	elif control.evt == 12:
		control.x = 5
		control.y = newheight - 95
		control.width = 65
	elif control.evt == 13:
		control.x = 72
		control.y = newheight - 95
		control.width = 102
	# Triggers
	elif control.evt == 14:
		control.x = 5
		control.y = newheight - 245
		control.width = newwidth - 10
	elif control.evt == 15:
		control.x = 5
		control.y = newheight - 267
		control.width = newwidth - 50
	elif control.evt == 16:
		control.x = 137
		control.y = newheight - 267
		control.width = newwidth - 142
	elif control.evt == 17:
		control.x = 5
		control.y = newheight - 289
		control.width = newwidth - 10
	elif control.evt == 18:
		control.x = 5
		control.y = newheight - 311
		control.width = (newwidth / 2) - 6
	elif control.evt == 19:
		control.x = (newwidth / 2)
		control.y = newheight - 311
		control.width = (newwidth / 2) - 6
	# reference pose controls
	elif control.evt == 20:
		control.x = 5
		control.y = newheight - 170
		control.width = (newwidth) - 10
	elif control.evt == 21:
		control.x = 5
		control.y = newheight - 195
		control.width = (newwidth) - 10
	# sequence priority
	elif control.evt == 23:
		control.x = 5
		control.y = newheight - 120
		control.width = newwidth - 10
	

def guiArmatureResize(control, newwidth, newheight):
	if control.evt == None:
		if control.name == "armature.bantitle":
			control.x = 10
			control.y = newheight-15
		elif control.name == "armature.banlist":
			control.x = 10
			control.y = 10
			control.width = 300
			control.height = 300
	else:
		if control.evt == 6:
			control.x = 320
			control.y = newheight - 45
			control.width = 150

def guiGeneralResize(control, newwidth, newheight):
	if control.evt == None:
		if control.name == "shape.strip":
			control.x = 10
			control.y = newheight - 20
		elif control.name == "shape.cluster":
			control.x = 10
			control.y = newheight - 70
		elif control.name == "shape.billboard":
			control.x = 10
			control.y = newheight - 120
		elif control.name == "shape.output":
			control.x = 10
			control.y = newheight - 250
	elif control.evt == 6:
		control.x = 10
		control.y = newheight - 30 - control.height
		control.width = 90
	elif control.evt == 7:
		control.x = 102
		control.y = newheight - 30 - control.height
		control.width = 90
	elif control.evt == 8:
		control.x = 194
		control.y = newheight - 30 - control.height
		control.width = 90
	elif control.evt == 9:
		control.x = 286
		control.y = newheight - 30 - control.height
		control.width = 180
	elif control.evt == 10:
		control.x = 10
		control.y = newheight - 80 - control.height
		control.width = 80
	elif control.evt == 11:
		control.x = 92
		control.y = newheight - 80 - control.height
		control.width = 180
	elif control.evt == 12:
		control.x = 10
		control.y = newheight - 130 - control.height
		control.width = 50
	elif control.evt == 13:
		control.x = 62
		control.y = newheight - 130 - control.height
		control.width = 100
	elif control.evt == 14:
		control.x = 62
		control.y = newheight - 152 - control.height
		control.width = 100
	elif control.evt == 15:
		control.x = 164
		control.y = newheight - 152 - control.height
		control.width = 200
	elif control.evt == 16:
		control.x = 366
		control.y = newheight - 130 - control.height
		control.width = 100
	elif control.evt == 17:
		control.x = 366
		control.y = newheight - 152 - control.height
		control.width = 100
	elif control.evt == 18:
		control.x = 164
		control.y = newheight - 130 - control.height
		control.width = 200
	elif control.evt == 19:
		control.x = 356
		control.y = newheight - 260 - control.height
		control.width = 122
	elif control.evt == 20:
		control.x = 10
		control.y = newheight - 260 - control.height
		control.width = 220
	elif control.evt == 21:
		control.x = 232
		control.y = newheight - 260 - control.height
		control.width = 50
	elif control.evt == 22:
		control.x = 284
		control.y = newheight - 260 - control.height
		control.width = 70
	elif control.evt == 23:
		control.x = 356
		control.y = newheight - 304 - control.height
		control.width = 122
	elif control.evt == 24:
		control.x = 356
		control.y = newheight - 282 - control.height
		control.width = 122

def guiAboutResize(control, newwidth, newheight):
	if control.evt == None:
		if control.name == "about.text":
			control.x = 10
			control.y = 120
			
def guiHeaderResize(control, newwidth, newheight):
	if control.name == "header.title":
		control.x = 5
		control.y = 5

def initGui():
	global Version, Prefs
	global guiSequenceTab, guiArmatureTab, guiGeneralTab, guiAboutTab, guiTabBar, guiHeaderTab
	global guiSequenceList, guiSequenceOptions, guiBoneList
	global guiTriListsButton, guiStripMeshesButton, guiTriMeshesButton

	Common_Gui.initGui(exit_callback)
	
	# Main tab controls
	guiSequenceButton = Common_Gui.BasicButton("Sequences", "Sequence options", 1, guiBaseCallback, guiBaseResize)
	guiMeshButton = Common_Gui.BasicButton("General", "Mesh and other options", 2, guiBaseCallback, guiBaseResize)
	guiArmatureButton = Common_Gui.BasicButton("Armatures", "Armature options", 3, guiBaseCallback, guiBaseResize)
	guiAboutButton = Common_Gui.BasicButton("About", "About", 4, guiBaseCallback, guiBaseResize)
	guiExportButton = Common_Gui.BasicButton("Export", "Export .dts shape", 5, guiBaseCallback, guiBaseResize)
	guiVersionText = Common_Gui.SimpleText("tabs.version", "Version %s" % Version, None, guiBaseResize)

	# Sequence tab controls
	guiSequenceTitle = Common_Gui.SimpleText("sequence.title", "Action Sequences :", None, guiSequenceResize)
	guiSequenceList = Common_Gui.ListContainer("sequence.list", guiSequenceCallback, guiSequenceResize)
	guiSequenceList.fade_mode = 0
	guiSequenceToggle = Common_Gui.ToggleButton("Toggle All", "Toggle export of all sequences", 6, guiSequenceCallback, guiSequenceResize)
	guiSequenceToggle.state = False
	guiSequenceRefresh = Common_Gui.BasicButton("Refresh", "Refresh list of sequences", 7, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptions = Common_Gui.BasicContainer("sequence.prefs", None, guiSequenceResize)
	guiSequenceOptions.enabled = False
	guiSequenceOptions.fade_mode = 5
	guiSequenceOptions.borderColor = None
	
	# Sequence tab, list controls test
	#for i in range(0, 20):
		#guiSequenceList.addControl(Common_Gui.BasicContainer("l%d" % i, None, None))
	
	# Sequence tab, sequence options controls
	guiSequenceOptionsTitle = Common_Gui.SimpleText("sequence.opts.title", "Sequence", None, guiSequenceResize)
	guiSequenceOptionsFramecount = Common_Gui.NumberPicker("Frames", "Amount of frames to export", 10, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsFramecount.min = 1
	guiSequenceOptionsGroundFramecount = Common_Gui.NumberPicker("Ground Frames", "Amount of ground frames to export", 11, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsAnimateMaterials = Common_Gui.ToggleButton("Mat Anim", "Animate Materials", 12, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsMaterialStartFrame = Common_Gui.NumberPicker("Start", "Frame to start exporting material track", 13, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsMaterialStartFrame.min = 1
	guiSequenceOptionsMaterialStartFrame.max = Blender.Scene.GetCurrent().getRenderingContext().endFrame()	
	
	guiSequenceOptionsPriority = Common_Gui.NumberPicker("Priority", "Sequence playback priority", 23, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsPriority.min = 0
	guiSequenceOptionsPriority.max = 64 # this seems resonable
	
	# this allows the user to select an arbitrary frame from any action as the reference pose
	# for blend animations.
	guiSequenceOptionsRefposeTitle = Common_Gui.SimpleText("sequence.opts.rtitle", "Ref Pose for ", None, guiSequenceResize)
	guiSequenceOptionsRefposeTitle.visible = False
	guiSequenceOptionsRefposeMenu = Common_Gui.ComboBox("Use Action", "Select an action containing your refernce pose for this blend.", 20, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsRefposeMenu.visible = False
	guiSequenceOptionsRefposeFrame = Common_Gui.NumberPicker("Frame", "Frame to use for reference pose", 21, guiSequenceCallback, guiSequenceResize)
	guiSequenceOptionsRefposeFrame.visible = False
	guiSequenceOptionsRefposeFrame.min = 1
	
	
	guiSequenceOptionsTriggerTitle = Common_Gui.SimpleText("sequence.opts.ttitle", "Triggers", None, guiSequenceResize)
	guiSequenceOptionsTriggerMenu = Common_Gui.ComboBox("Trigger List", "Select a trigger from this list to edit its properties", 14, guiSequenceTriggersCallback, guiSequenceResize)
	guiSequenceOptionsTriggerState = Common_Gui.NumberPicker("State", "State of trigger to alter", 15, guiSequenceTriggersCallback, guiSequenceResize)
	guiSequenceOptionsTriggerState.min, guiSequenceOptionsTriggerState.max = 1, 32
	guiSequenceOptionsTriggerStateOn = Common_Gui.ToggleButton("On", "Determines if state will be activated or deactivated", 16, guiSequenceTriggersCallback, guiSequenceResize)
	guiSequenceOptionsTriggerFrame = Common_Gui.NumberPicker("Frame", "Frame to activate trigger on", 17, guiSequenceTriggersCallback, guiSequenceResize)
	guiSequenceOptionsTriggerFrame.min = 1
	guiSequenceOptionsTriggerAdd = Common_Gui.BasicButton("Add", "Add new trigger", 18, guiSequenceTriggersCallback, guiSequenceResize)
	guiSequenceOptionsTriggerDel = Common_Gui.BasicButton("Del", "Delete currently selected trigger", 19, guiSequenceTriggersCallback, guiSequenceResize)
	
	# Armature tab controls
	guiBoneText =  Common_Gui.SimpleText("armature.bantitle", "Bones that should be exported :", None, guiArmatureResize)
	#guiBoneList = Common_Gui.BasicGrid("armature.banlist", None, guiArmatureResize)
	guiBoneList = Common_Gui.BoneListContainer("armature.banlist", None, guiArmatureResize)
	guiArmatureRootToggle = Common_Gui.ToggleButton("Collapse Root Transform", "Collapse root transform when exporting Armature's", 6, guiArmatureCallback, guiArmatureResize)
	guiArmatureRootToggle.state = False # Prefs['CollapseRootTransform']
	guiArmatureRootToggle.visible = False # TODO: remove this control - Joe.
	
	# General tab controls
	guiStripText = Common_Gui.SimpleText("shape.strip", "Geometry type", None, guiGeneralResize)
	# Joe - Ugly but effective
	try: x = Prefs['PrimType']
	except KeyError: Prefs['PrimType'] = "Tris"
	guiTriMeshesButton = Common_Gui.ToggleButton("Triangles", "Generate individual triangles for meshes", 6, guiGeneralCallback, guiGeneralResize)
	if Prefs['PrimType'] == "Tris": guiTriMeshesButton.state = True
	else: guiTriMeshesButton.state = False
	guiTriListsButton = Common_Gui.ToggleButton("Triangle Lists", "Generate triangle lists for meshes", 7, guiGeneralCallback, guiGeneralResize)
	if Prefs['PrimType'] == "TriLists": guiTriListsButton.state = True
	else: guiTriListsButton.state = False
	guiStripMeshesButton = Common_Gui.ToggleButton("Triangle Strips", "Generate triangle strips for meshes", 8, guiGeneralCallback, guiGeneralResize)
	if Prefs['PrimType'] == "TriStrips": guiStripMeshesButton.state = True
	else: guiStripMeshesButton.state = False
	guiMaxStripSizeSlider = Common_Gui.NumberSlider("Strip Size ", "Maximum size of generated triangle strips", 9, guiGeneralCallback, guiGeneralResize)
	guiMaxStripSizeSlider.min, guiMaxStripSizeSlider.max = 3, 30
	guiMaxStripSizeSlider.value = Prefs['MaxStripSize']
	# --
	guiClusterText = Common_Gui.SimpleText("shape.cluster", "Cluster Mesh", None, guiGeneralResize)
	guiClusterWriteDepth = Common_Gui.ToggleButton("Write Depth ", "Always Write the Depth on Cluster meshes", 10, guiGeneralCallback, guiGeneralResize)
	guiClusterWriteDepth.state = Prefs['AlwaysWriteDepth']
	guiClusterDepth = Common_Gui.NumberSlider("Depth", "Maximum depth Clusters meshes should be calculated to", 11, guiGeneralCallback, guiGeneralResize)
	guiClusterDepth.min, guiClusterDepth.max = 3, 30
	guiClusterDepth.value = Prefs['ClusterDepth']
	# --
	guiBillboardText = Common_Gui.SimpleText("shape.billboard", "Billboard", None, guiGeneralResize)
	guiBillboardButton = Common_Gui.ToggleButton("Enable", "Add a billboard detail level to the shape", 12, guiGeneralCallback, guiGeneralResize)
	guiBillboardButton.state = Prefs['Billboard']['Enabled']
	guiBillboardEquator = Common_Gui.NumberPicker("Equator", "Number of images around the equator", 13, guiGeneralCallback, guiGeneralResize)
	guiBillboardEquator.min, guiBillboardEquator.max = 2, 64
	guiBillboardEquator.value = Prefs['Billboard']['Equator']
	guiBillboardPolar = Common_Gui.NumberPicker("Polar", "Number of images around the polar", 14, guiGeneralCallback, guiGeneralResize)
	guiBillboardPolar.min, guiBillboardPolar.max = 3, 64
	guiBillboardPolar.value = Prefs['Billboard']['Polar']
	guiBillboardPolarAngle = Common_Gui.NumberSlider("Polar Angle", "Angle to take polar images at", 15, guiGeneralCallback, guiGeneralResize)
	guiBillboardPolarAngle.min, guiBillboardPolarAngle.max = 0.0, 45.0
	guiBillboardPolarAngle.value = Prefs['Billboard']['PolarAngle']
	guiBillboardDim = Common_Gui.NumberPicker("Dim", "Dimensions of billboard images", 16, guiGeneralCallback, guiGeneralResize)
	guiBillboardDim.min, guiBillboardDim.max = 16, 128
	guiBillboardDim.value = Prefs['Billboard']['Dim']
	guiBillboardPoles = Common_Gui.ToggleButton("Poles", "Take images at the poles", 17, guiGeneralCallback, guiGeneralResize)
	guiBillboardPoles.state = Prefs['Billboard']['IncludePoles']
	guiBillboardSize = Common_Gui.NumberSlider("Size", "Size of billboard's detail level", 18, guiGeneralCallback, guiGeneralResize)
	guiBillboardSize.min, guiBillboardSize.max = 0.0, 128.0
	guiBillboardSize.value = Prefs['Billboard']['Size']
	# --
	guiOutputText = Common_Gui.SimpleText("shape.output", "Output", None, guiGeneralResize)
	guiShapeScriptButton =  Common_Gui.ToggleButton("Write Shape Script", "Write .cs script that details the .dts and all .dsq sequences", 19, guiGeneralCallback, guiGeneralResize)
	guiCustomFilename = Common_Gui.TextBox("Filename: ", "Filename to write to", 20, guiGeneralCallback, guiGeneralResize)
	guiCustomFilename.length = 255
	if "\\" in Prefs['exportBasepath']:
		pathSep = "\\"
	else:
		pathSep = "/"
	guiCustomFilename.value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename'] + ".dts"
	guiCustomFilenameSelect = Common_Gui.BasicButton("Select...", "Select a filename and destination for export", 21, guiGeneralCallback, guiGeneralResize)
	guiCustomFilenameDefaults = Common_Gui.BasicButton("Default", "Reset filename and destination to defaults", 22, guiGeneralCallback, guiGeneralResize)
	
	guiCustomDTSVersion = Common_Gui.NumberPicker("Dts Version", "Version of DTS file to export", 23, guiGeneralCallback, guiGeneralResize)
	guiCustomDTSVersion.min, guiCustomDTSVersion.max = 24, 25
	
	guiTSEMaterial = Common_Gui.ToggleButton("Write TSE Materials", "Write materials and scripts geared for TSE", 24, guiGeneralCallback, guiGeneralResize)
	guiTSEMaterial.state = Prefs['TSEMaterial']
	
	# About tab controls
	guiAboutText = Common_Gui.MultilineText("about.text", 
	"Torque Exporter Plugin for Blender\n" +
	"\n"
	"Written by James Urquhart, with assistance from Tim Gift, Clark Fagot, Wes Beary,\n" +
	"Ben Garney, Joshua Ritter, Emanuel Greisen, Todd Koeckeritz,\n" +
	"Ryan J. Parker, Walter Yoon, and Joseph Greenawalt.\n" +
	"GUI code written with assistance from Xen and Xavier Amado.\n" +
	"Additional thanks goes to the testers.\n" +
	"\n" +
	"Visit GarageGames at http://www.garagegames.com", None, guiAboutResize)
	
	# Header controls
	guiHeaderText = Common_Gui.SimpleText("header.title", "Torque Exporter Plugin", None, guiHeaderResize)
	headerTextColor = headerColor = Common_Gui.curTheme.get('buts').text_hi
	guiHeaderText.color = [headerTextColor[0]/255.0, headerTextColor[1]/255.0, headerTextColor[2]/255.0, headerTextColor[3]/255.0]
	
	# Container Controls
	guiHeaderBar = Common_Gui.BasicContainer("header", None, guiBaseResize)
	guiHeaderBar.borderColor = None
	headerColor = Common_Gui.curTheme.get('buts').header
	guiHeaderBar.color = [headerColor[0]/255.0, headerColor[1]/255.0, headerColor[2]/255.0, headerColor[3]/255.0]
	guiHeaderBar.fade_mode = 0
	guiTabBar = Common_Gui.BasicContainer("tabs", None, guiBaseResize)
	guiTabBar.fade_mode = 0
	#guiTabBar.borderColor = None
	guiSequenceTab = Common_Gui.BasicContainer("content.sequence", None, guiBaseResize)
	guiSequenceTab.fade_mode = 1
	guiSequenceTab.enabled, guiSequenceTab.visible = True, True
	guiGeneralTab = Common_Gui.BasicContainer("content.general", None, guiBaseResize)
	guiGeneralTab.fade_mode = 1
	guiGeneralTab.enabled, guiGeneralTab.visible = False, False
	guiArmatureTab = Common_Gui.BasicContainer("content.armature", None, guiBaseResize)
	guiArmatureTab.fade_mode = 1
	guiArmatureTab.enabled, guiArmatureTab.visible = False, False
	guiAboutTab = Common_Gui.BasicContainer("content.about", None, guiBaseResize)
	guiAboutTab.fade_mode = 1
	guiAboutTab.enabled, guiAboutTab.visible = False, False
	
	# Add all controls to respective containers
	
	guiHeaderBar.addControl(guiHeaderText)
	
	Common_Gui.addGuiControl(guiTabBar)
	guiTabBar.addControl(guiHeaderBar) # Here to get the blend from panel color
	guiTabBar.addControl(guiSequenceButton)
	guiTabBar.addControl(guiMeshButton)
	guiTabBar.addControl(guiArmatureButton)
	guiTabBar.addControl(guiAboutButton)
	guiTabBar.addControl(guiExportButton)
	guiTabBar.addControl(guiVersionText)
	
	Common_Gui.addGuiControl(guiSequenceTab)
	guiSequenceTab.addControl(guiSequenceTitle)
	guiSequenceTab.addControl(guiSequenceList)
	guiSequenceTab.addControl(guiSequenceToggle)
	guiSequenceTab.addControl(guiSequenceRefresh)
	guiSequenceTab.addControl(guiSequenceOptions)
	
	guiSequenceOptions.addControl(guiSequenceOptionsTitle)
	guiSequenceOptions.addControl(guiSequenceOptionsFramecount)
	guiSequenceOptions.addControl(guiSequenceOptionsGroundFramecount)
	guiSequenceOptions.addControl(guiSequenceOptionsAnimateMaterials)
	guiSequenceOptions.addControl(guiSequenceOptionsMaterialStartFrame)

	guiSequenceOptions.addControl(guiSequenceOptionsTriggerTitle)
	guiSequenceOptions.addControl(guiSequenceOptionsTriggerMenu)
	guiSequenceOptions.addControl(guiSequenceOptionsTriggerState)
	guiSequenceOptions.addControl(guiSequenceOptionsTriggerStateOn)
	guiSequenceOptions.addControl(guiSequenceOptionsTriggerFrame)
	guiSequenceOptions.addControl(guiSequenceOptionsTriggerAdd)
	guiSequenceOptions.addControl(guiSequenceOptionsTriggerDel)

	# added these for selection of blend ref pose.
	guiSequenceOptions.addControl(guiSequenceOptionsRefposeTitle)
	guiSequenceOptions.addControl(guiSequenceOptionsRefposeMenu)
	guiSequenceOptions.addControl(guiSequenceOptionsRefposeFrame)
	
	guiSequenceOptions.addControl(guiSequenceOptionsPriority)
	
	populateSequenceList()
	
	Common_Gui.addGuiControl(guiArmatureTab)
	guiArmatureTab.addControl(guiBoneText)
	guiArmatureTab.addControl(guiBoneList)
	populateBoneGrid()
	guiArmatureTab.addControl(guiArmatureRootToggle)
	
	Common_Gui.addGuiControl(guiGeneralTab)
	guiGeneralTab.addControl(guiStripText)
	guiGeneralTab.addControl(guiTriMeshesButton)
	guiGeneralTab.addControl(guiTriListsButton)
	guiGeneralTab.addControl(guiStripMeshesButton)	
	guiGeneralTab.addControl(guiMaxStripSizeSlider)
	guiGeneralTab.addControl(guiClusterText)
	guiGeneralTab.addControl(guiClusterDepth)
	guiGeneralTab.addControl(guiClusterWriteDepth)
	guiGeneralTab.addControl(guiBillboardText)
	guiGeneralTab.addControl(guiBillboardButton)
	guiGeneralTab.addControl(guiBillboardEquator)
	guiGeneralTab.addControl(guiBillboardPolar)
	guiGeneralTab.addControl(guiBillboardPolarAngle)
	guiGeneralTab.addControl(guiBillboardDim)
	guiGeneralTab.addControl(guiBillboardPoles)
	guiGeneralTab.addControl(guiBillboardSize)
	guiGeneralTab.addControl(guiOutputText)
	guiGeneralTab.addControl(guiShapeScriptButton)
	guiGeneralTab.addControl(guiCustomFilename)
	guiGeneralTab.addControl(guiCustomFilenameSelect)
	guiGeneralTab.addControl(guiCustomFilenameDefaults)
	guiGeneralTab.addControl(guiCustomDTSVersion)
	guiGeneralTab.addControl(guiTSEMaterial)

	Common_Gui.addGuiControl(guiAboutTab)
	guiAboutTab.addControl(guiAboutText)

# Called when gui exits
def exit_callback():
	Torque_Util.dump_setout("stdout")
	clearSequenceList()
	clearBoneGrid()
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
	getPathSeperator(Blender.Get("filename"))
	if Debug:
		Torque_Util.dump_setout("stdout")
	else:
		Torque_Util.dump_setout("%s.log" % noext(Blender.Get("filename")))
	Torque_Util.dump_writeln("Torque Exporter %s " % Version)
	Torque_Util.dump_writeln("Using blender, version %s" % Blender.Get('version'))
	
	#if Torque_Util.Torque_Math.accelerator != None:
	#	Torque_Util.dump_writeln("Using accelerated math interface '%s'" % Torque_Util.Torque_Math.accelerator)
	#else:
	#	Torque_Util.dump_writeln("Using unaccelerated math code, performance may be suboptimal")
	#Torque_Util.dump_writeln("**************************")
	
	loadPrefs()
	
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
