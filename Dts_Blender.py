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
	Prefs['Version'] = 0.95 # NOTE: change version if anything *major* is changed.
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
	pass
	'''
	# Sequences
	#delKeys = []
	for key in Prefs['Sequences'].keys():
		Found = False
		for action_key in Armature.NLA.GetActions().keys():
			if action_key == key:
				Found = True
				break
		if not Found:
			ifl = None
			try: ifl = Prefs['Sequences'][key]['IFL']['Enabled']
			except: pass
			if ifl == None or ifl == False:	del Prefs['Sequences'][key]

	#for key in delKeys:
	#	del Prefs['Sequences'][key]
	'''

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
						Blender.Draw.PupMenu("Warning%t|One or more of your armatures is locked into rest position. This can cause problems with exported animations.")
						break

				# The ice be dammed, it's time to take action
				if len(actions.keys()) > 0:
					progressBar.pushTask("Adding Actions..." , len(actions.keys()*4), 0.8)
					for action_name in actions.keys():
						# skip the fake action (workaround for a blender bug)
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
						
						try: x = sequenceKey['IFL']['Enabled']
						except: sequenceKey['IFL']['Enabled'] = False
						if sequenceKey['IFL']['Enabled']:
							self.Shape.addSequenceIFL(sequence, sequenceKey)
						
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
IFLControls = None

guiSeqActOpts = None
guiSeqActList = None
guiBoneList = None

# Global control event table.  Containers have their own event tables for child controls
globalEvents = Common_Gui.EventTable(1)


def guiBoneListItemCallback(control):
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





# new
def createBoneListitem(bone1, bone2, bone3, bone4, bone5, startEvent):
	#sequencePrefs = getSequenceKey(seq_name)
	# Note on positions:
	# It quicker to assign these here, as there is no realistic chance scaling being required.
	guiContainer = Common_Gui.BasicContainer("", None, None)
	guiContainer.fade_mode = 0
	guiContainer.borderColor = None
	if bone1 != None:
		guiBone1 = Common_Gui.ToggleButton("guiBone_" + bone1, bone1, "Toggle Status of " + bone1, startEvent, guiBoneListItemCallback, None)
		guiBone1.x, guiBone1.y = 1, 0
		guiBone1.width, guiBone1.height = 90, 19
		guiBone1.state = True
		guiContainer.addControl(guiBone1)
	if bone2 != None:
		guiBone2 = Common_Gui.ToggleButton("guiBone_" + bone2, bone2, "Toggle Status of " + bone2, startEvent+1, guiBoneListItemCallback, None)
		guiBone2.x, guiBone2.y = 92, 0
		guiBone2.width, guiBone2.height = 90, 19
		guiBone2.state = True
		guiContainer.addControl(guiBone2)
	if bone3 != None:
		guiBone3 = Common_Gui.ToggleButton("guiBone_" + bone3, bone3, "Toggle Status of " + bone3, startEvent+3, guiBoneListItemCallback, None)
		guiBone3.x, guiBone3.y = 183, 0
		guiBone3.width, guiBone3.height = 90, 19
		guiBone3.state = True
		guiContainer.addControl(guiBone3)
	if bone4 != None:
		guiBone4 = Common_Gui.ToggleButton("guiBone_" + bone4, bone4, "Toggle Status of " + bone4, startEvent+4, guiBoneListItemCallback, None)
		guiBone4.x, guiBone4.y = 274, 0
		guiBone4.width, guiBone4.height = 89, 19
		guiBone4.state = True
		guiContainer.addControl(guiBone4)	
	if bone5 != None:
		guiBone5 = Common_Gui.ToggleButton("guiBone_" + bone5, bone5, "Toggle Status of " + bone5, startEvent+5, guiBoneListItemCallback, None)
		guiBone5.x, guiBone5.y = 364, 0
		guiBone5.width, guiBone5.height = 89, 19
		guiBone5.state = True
		guiContainer.addControl(guiBone5)
	return guiContainer





def populateBoneGrid():
	global Prefs, export_tree, guiBoneList
	shapeTree = export_tree.find("SHAPE")
	if shapeTree == None: return
	evtNo = 40
	count = 0
	names = []
	for name in shapeTree.getShapeBoneNames():
		names.append(name)
		if len(names) == 5:
			guiBoneList.addControl(createBoneListitem(names[0],names[1],names[2],names[3],names[4], evtNo))			
			guiBoneList.controls[count].controls[0].state = not (guiBoneList.controls[count].controls[0].text.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[1].state = not (guiBoneList.controls[count].controls[1].text.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[2].state = not (guiBoneList.controls[count].controls[2].text.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[3].state = not (guiBoneList.controls[count].controls[3].text.upper() in Prefs['BannedBones'])
			guiBoneList.controls[count].controls[4].state = not (guiBoneList.controls[count].controls[4].text.upper() in Prefs['BannedBones'])
			
			evtNo += 6
			count += 1
			names = []
	# add leftovers in last row
	if len(names) > 0:
		for i in range(len(names)-1, 5):
			names.append(None)
		guiBoneList.addControl(createBoneListitem(names[0],names[1],names[2],names[3], names[4], evtNo))
		if names[0] != None: guiBoneList.controls[count].controls[0].state = not (guiBoneList.controls[count].controls[0].text.upper() in Prefs['BannedBones'])
		if names[1] != None: guiBoneList.controls[count].controls[1].state = not (guiBoneList.controls[count].controls[1].text.upper() in Prefs['BannedBones'])
		if names[2] != None: guiBoneList.controls[count].controls[2].state = not (guiBoneList.controls[count].controls[2].text.upper() in Prefs['BannedBones'])
		if names[3] != None: guiBoneList.controls[count].controls[3].state = not (guiBoneList.controls[count].controls[3].text.upper() in Prefs['BannedBones'])
		if names[4] != None: guiBoneList.controls[count].controls[4].state = not (guiBoneList.controls[count].controls[4].text.upper() in Prefs['BannedBones'])
			

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
	global guiSequenceTab, guiArmatureTab, guiMaterialsTab, guiGeneralTab, guiAboutTab, guiTabBar
	global guiSequenceButton, guiMeshButton, guiArmatureButton, guiMaterialsButton, guiAboutButton

	if control.name == "guiExportButton":
		export()
		return

	# Need to associate the button with it's corresponding tab container.
	ctrls = [[guiSequenceButton,guiSequenceTab], [guiMeshButton,guiGeneralTab], [guiMaterialsButton,guiMaterialsTab], [guiArmatureButton,guiArmatureTab], [guiAboutButton,guiAboutTab]]
	for ctrl in ctrls:
		if control.name == ctrl[0].name:
			# turn on the tab button, show and enable the tab container
			control.state = True
			ctrl[1].visible = True
			ctrl[1].enabled = True
			continue
		# disable all other tab containers and set tab button states to false.
		ctrl[0].state = False
		ctrl[1].visible = False
		ctrl[1].enabled = False
		
def guiSequenceTabsCallback(control):
	global guiSeqActButton, guiSequenceIFLButton, guiSequenceVisibilityButton, guiSequenceUVButton, guiSequenceMorphButton, guiSequenceTabBar
	global guiSeqActSubtab, guiSequenceIFLSubtab, guiSequenceVisibilitySubtab, guiSequenceUVSubtab, guiSequenceMorphSubtab
	#global guiSequenceTab, guiArmatureTab, guiMaterialsTab, guiGeneralTab, guiAboutTab, guiTabBar
	#global guiSequenceButton, guiMeshButton, guiArmatureButton, guiMaterialsButton, guiAboutButton
	
	# Need to associate the button with it's corresponding tab container.
	ctrls = [[guiSeqActButton,guiSeqActSubtab], [guiSequenceIFLButton,guiSequenceIFLSubtab], [guiSequenceVisibilityButton,guiSequenceVisibilitySubtab], [guiSequenceUVButton,guiSequenceUVSubtab], [guiSequenceMorphButton,guiSequenceMorphSubtab]]
	for ctrl in ctrls:
		if control.name == ctrl[0].name:
			# turn on the tab button, show and enable the tab container
			control.state = True
			ctrl[1].visible = True
			ctrl[1].enabled = True
			continue
		# disable all other tab containers and set tab button states to false.
		ctrl[0].state = False
		ctrl[1].visible = False
		ctrl[1].enabled = False


			
def guiArmatureCallback(control):
	global Prefs, export_tree, guiBoneList, guiBonePatternText
	if control.name == "guiBonePatternOnButton" or control.name == "guiBonePatternOffButton":
		userPattern = guiBonePatternText.value
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
					if control.name == "guiBonePatternOnButton":
						for i in range(len(Prefs['BannedBones'])-1, -1, -1):
							boneName = Prefs['BannedBones'][i].upper()
							if name == boneName:
								del Prefs['BannedBones'][i]
					elif control.name == "guiBonePatternOffButton":
						Prefs['BannedBones'].append(name)
		clearBoneGrid()
		populateBoneGrid()
	elif control.name == "guiBoneRefreshButton":
		clearBoneGrid()
		populateBoneGrid()
	


def guiGeneralSelectorCallback(filename):
	global guiGeneralSubtab
	if filename != "":
		Prefs['exportBasename'] = basename(filename)
		Prefs['exportBasepath'] = basepath(filename)
		
		pathSep = "/"
		if "\\" in Prefs['exportBasepath']: pathSep = "\\"

		guiGeneralSubtab.controls[18].value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']
		if guiGeneralSubtab.controls[18].value[len(guiGeneralSubtab.controls[18].value)-4:] != ".dts":
			guiGeneralSubtab.controls[18].value += ".dts"



def guiGeneralCallback(control):
	global Prefs
	global guiGeneralSubtab
	global guiTriListsButton
	global guiStripMeshesButton
	global guiTriMeshesButton
	if control.name == "guiTriMeshesButton":
		Prefs['PrimType'] = "Tris"
		guiTriListsButton.state = False
		guiStripMeshesButton.state = False
		guiTriMeshesButton.state = True
	elif control.name == "guiTriListsButton":
		Prefs['PrimType'] = "TriLists"
		guiTriListsButton.state = True
		guiStripMeshesButton.state = False
		guiTriMeshesButton.state = False
	elif control.name == "guiStripMeshesButton":
		Prefs['PrimType'] = "TriStrips"
		guiTriListsButton.state = False
		guiStripMeshesButton.state = True
		guiTriMeshesButton.state = False
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
		Blender.Window.FileSelector (guiGeneralSelectorCallback, 'Select destination and filename')
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
	elif control.name == "guiTSEMaterial":
		Prefs['TSEMaterial'] = control.state
		
	elif control.name == "guiLogToOutputFolder":
		Prefs['LogToOutputFolder'] = control.state
		if control.state:
			Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSeperator, noext(Prefs['exportBasename'])) )
		else:
			Torque_Util.dump_setout("%s.log" % noext(Blender.Get("filename")))
		Prefs['exportBasename']

def guiBaseResize(control, newwidth, newheight):
	tabContainers = ["guiSequenceTab", "guiGeneralTab", "guiArmatureTab", "guiAboutTab", "guiMaterialsTab"]
	tabSubContainers = ["guiSeqActSubtab", "guiSequenceIFLSubtab", "guiSequenceVisibilitySubtab","guiSequenceUVSubtab","guiSequenceMorphSubtab", "guiSequenceNLASubtab", "guiMaterialsSubtab", "guiGeneralSubtab", "guiArmatureSubtab", "guiAboutSubtab"]
	
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
	elif control.name == "guiSeqActButton":
		control.x, control.y = 15, 0
		control.width, control.height = 60, 25
	elif control.name == "guiSequenceIFLButton":
		control.x, control.y = 77, 0
		control.width, control.height = 35, 25
	elif control.name == "guiSequenceVisibilityButton":
		control.x, control.y = 114, 0
		control.width, control.height = 60, 25
	elif control.name == "guiSequenceUVButton":
		control.x, control.y = 176, 0
		control.width, control.height = 70, 25
	elif control.name == "guiSequenceMorphButton":
		control.x, control.y = 248, 0
		control.width, control.height = 65, 25


def guiArmatureResize(control, newwidth, newheight):

	if control.name == "guiBoneText":
		control.x = 10
		control.y = newheight-15
	elif control.name == "guiBoneList":
		control.x = 10
		control.y = 70
		control.width = 470
		control.height = 242
	elif control.name == "guiBoneMatchText":
		control.x = 10
		control.y = newheight-285
	elif control.name == "guiBonePatternText":
		control.width = 70
		control.x = 10
		control.y = newheight-315
	elif control.name == "guiBonePatternOnButton":
		control.width = 35
		control.x = 84
		control.y = newheight-315
	elif control.name == "guiBonePatternOffButton":
		control.width = 35
		control.x = 121
		control.y = newheight-315
	elif control.name == "guiBoneRefreshButton":
		control.width = 75
		control.x = 400
		control.y = newheight-315
	
	

def guiGeneralResize(control, newwidth, newheight):
	if control.name == "guiStripText":
		control.x = 10
		control.y = newheight - 20
	elif control.name == "guiClusterText":
		control.x = 10
		control.y = newheight - 70
	elif control.name == "guiBillboardText":
		control.x = 10
		control.y = newheight - 120
	elif control.name == "guiOutputText":
		control.x = 10
		control.y = newheight - 250
	elif control.name == "guiTriMeshesButton":
		control.x = 10
		control.y = newheight - 30 - control.height
		control.width = 90
	elif control.name == "guiTriListsButton":
		control.x = 102
		control.y = newheight - 30 - control.height
		control.width = 90
	elif control.name == "guiStripMeshesButton":
		control.x = 194
		control.y = newheight - 30 - control.height
		control.width = 90
	elif control.name == "guiMaxStripSizeSlider":
		control.x = 286
		control.y = newheight - 30 - control.height
		control.width = 180
	elif control.name == "guiClusterWriteDepth":
		control.x = 10
		control.y = newheight - 80 - control.height
		control.width = 80
	elif control.name == "guiClusterDepth":
		control.x = 92
		control.y = newheight - 80 - control.height
		control.width = 180
	elif control.name == "guiBillboardButton":
		control.x = 10
		control.y = newheight - 130 - control.height
		control.width = 50
	elif control.name == "guiBillboardEquator":
		control.x = 62
		control.y = newheight - 130 - control.height
		control.width = 100
	elif control.name == "guiBillboardPolar":
		control.x = 62
		control.y = newheight - 152 - control.height
		control.width = 100
	elif control.name == "guiBillboardPolarAngle":
		control.x = 164
		control.y = newheight - 152 - control.height
		control.width = 200
	elif control.name == "guiBillboardDim":
		control.x = 366
		control.y = newheight - 130 - control.height
		control.width = 100
	elif control.name == "guiBillboardPoles":
		control.x = 366
		control.y = newheight - 152 - control.height
		control.width = 100
	elif control.name == "guiBillboardSize":
		control.x = 164
		control.y = newheight - 130 - control.height
		control.width = 200
	elif control.name == "guiShapeScriptButton":
		control.x = 356
		control.y = newheight - 260 - control.height
		control.width = 122
	elif control.name == "guiCustomFilename":
		control.x = 10
		control.y = newheight - 260 - control.height
		control.width = 220
	elif control.name == "guiCustomFilenameSelect":
		control.x = 232
		control.y = newheight - 260 - control.height
		control.width = 50
	elif control.name == "guiCustomFilenameDefaults":
		control.x = 284
		control.y = newheight - 260 - control.height
		control.width = 70
	elif control.name == "guiTSEMaterial":
		control.x = 356
		control.y = newheight - 282 - control.height
		control.width = 122
	elif control.name == "guiLogToOutputFolder":
		control.x = 356
		control.y = newheight - 304 - control.height
		control.width = 122

def guiAboutResize(control, newwidth, newheight):
	if control.name == "guiAboutText":
		control.x = 10
		control.y = 120
			
def guiHeaderResize(control, newwidth, newheight):
	if control.name == "guiHeaderText":
		control.x = 5
		control.y = 5
	elif control.name == "guiVersionText":
		control.x = newwidth-80
		control.y = 5


'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Actions sub-panel of the Sequences panel.
*
***************************************************************************************************
'''
class ActionControlsClass:
	def __init__(self):
		global guiSequenceActionSubtab
		global globalEvents
		self.triggerMenuTemplate = "Frame:%d Trigger:%d "
		
		# initialize GUI controls
		self.guiSeqActTitle = Common_Gui.SimpleText("guiSeqActTitle", "Action Sequences :", None, self.resize)
		self.guiSeqActList = Common_Gui.ListContainer("guiSeqActList", "sequence.list", self.handleEvent, self.resize)		
		self.guiSeqActToggle = Common_Gui.ToggleButton("guiSeqActToggle", "Toggle All", "Toggle export of all sequences", 6, self.handleEvent, self.resize)		
		self.guiSeqActRefresh = Common_Gui.BasicButton("guiSeqActRefresh", "Refresh", "Refresh list of sequences", 7, self.handleEvent, self.resize)
		self.guiSeqActOpts = Common_Gui.BasicContainer("guiSeqActOpts", "sequence.prefs", None, self.resize)
		self.guiSeqActOptsTitle = Common_Gui.SimpleText("guiSeqActOptsTitle", "Sequence: None Selected", None, self.resize)
		self.guiSeqActOptsFramecount = Common_Gui.NumberPicker("guiSeqActOptsFramecount", "Frame Samples", "Amount of frames to export", 10, self.handleEvent, self.resize)
		self.guiSeqActOptsGroundFramecount = Common_Gui.NumberPicker("guiSeqActOptsGroundFramecount", "Ground Frames", "Amount of ground frames to export", 11, self.handleEvent, self.resize)
		self.guiSeqActOptsAnimateMaterials = Common_Gui.ToggleButton("guiSeqActOptsAnimateMaterials", "Mat Anim", "Animate Materials", 12, self.handleEvent, self.resize)
		self.guiSeqActOptsMatStartFrame = Common_Gui.NumberPicker("guiSeqActOptsMatStartFrame", "Start", "Frame to start exporting material track", 13, self.handleEvent, self.resize)
		self.guiSeqActOptsPriority = Common_Gui.NumberPicker("guiSeqActOptsPriority", "Priority", "Sequence playback priority", 23, self.handleEvent, self.resize)
		self.guiSeqActOptsRefposeTitle = Common_Gui.SimpleText("guiSeqActOptsRefposeTitle", "Ref Pose for ", None, self.resize)
		self.guiSeqActOptsRefposeMenu = Common_Gui.ComboBox("guiSeqActOptsRefposeMenu", "Use Action", "Select an action containing your refernce pose for this blend.", 20, self.handleEvent, self.resize)
		self.guiSeqActOptsRefposeFrame = Common_Gui.NumberPicker("guiSeqActOptsRefposeFrame", "Frame", "Frame to use for reference pose", 21, self.handleEvent, self.resize)
		self.guiSeqActOptsTriggerTitle = Common_Gui.SimpleText("guiSeqActOptsTriggerTitle", "Triggers", None, self.resize)
		self.guiSeqActOptsTriggerMenu = Common_Gui.ComboBox("guiSeqActOptsTriggerMenu", "Trigger List", "Select a trigger from this list to edit its properties", 14, self.handleTriggersEvent, self.resize)
		self.guiSeqActOptsTriggerState = Common_Gui.NumberPicker("guiSeqActOptsTriggerState", "Trigger", "Trigger state to alter", 15, self.handleTriggersEvent, self.resize)
		self.guiSeqActOptsTriggerStateOn = Common_Gui.ToggleButton("guiSeqActOptsTriggerStateOn", "On", "Determines if state will be activated or deactivated", 16, self.handleTriggersEvent, self.resize)
		self.guiSeqActOptsTriggerFrame = Common_Gui.NumberPicker("guiSeqActOptsTriggerFrame", "Frame", "Frame to activate trigger on", 17, self.handleTriggersEvent, self.resize)
		self.guiSeqActOptsTriggerAdd = Common_Gui.BasicButton("guiSeqActOptsTriggerAdd", "Add", "Add new trigger", 18, self.handleTriggersEvent, self.resize)
		self.guiSeqActOptsTriggerDel = Common_Gui.BasicButton("guiSeqActOptsTriggerDel", "Del", "Delete currently selected trigger", 19, self.handleTriggersEvent, self.resize)
		
		# set initial states
		self.guiSeqActList.fade_mode = 0
		self.guiSeqActToggle.state = False
		self.guiSeqActOpts.enabled = False
		self.guiSeqActOpts.fade_mode = 5
		self.guiSeqActOpts.borderColor = None
		self.guiSeqActOptsFramecount.min = 1
		self.guiSeqActOptsMatStartFrame.min = 1
		self.guiSeqActOptsMatStartFrame.max = Blender.Scene.GetCurrent().getRenderingContext().endFrame()	
		self.guiSeqActOptsPriority.min = 0
		self.guiSeqActOptsPriority.max = 64 # this seems resonable
		self.guiSeqActOptsRefposeTitle.visible = False
		self.guiSeqActOptsRefposeMenu.visible = False
		self.guiSeqActOptsRefposeFrame.visible = False
		self.guiSeqActOptsRefposeFrame.min = 1
		self.guiSeqActOptsTriggerState.min, self.guiSeqActOptsTriggerState.max = 1, 32
		self.guiSeqActOptsTriggerFrame.min = 1
		
		
		# add controls to containers
		guiSeqActSubtab.addControl(self.guiSeqActTitle)
		guiSeqActSubtab.addControl(self.guiSeqActList)
		guiSeqActSubtab.addControl(self.guiSeqActToggle)
		guiSeqActSubtab.addControl(self.guiSeqActRefresh)
		guiSeqActSubtab.addControl(self.guiSeqActOpts)

		self.guiSeqActOpts.addControl(self.guiSeqActOptsTitle)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsFramecount)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsGroundFramecount)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsAnimateMaterials)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsMatStartFrame)

		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerTitle)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerMenu)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerState)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerStateOn)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerFrame)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerAdd)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsTriggerDel)

		self.guiSeqActOpts.addControl(self.guiSeqActOptsRefposeTitle)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsRefposeMenu)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsRefposeFrame)
		self.guiSeqActOpts.addControl(self.guiSeqActOptsPriority)


		# populate actions list
		self.populateSequenceActionList()
		
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		pass
	
	def updateOldPrefs(self):
		pass

	def handleEvent(self, control):
		global guiSeqActOpts, guiSeqActList

		if control.name == "guiSeqActToggle":
			for child in self.guiSeqActList.controls:
				child.controls[1].state = control.state
				getSequenceKey(child.controls[0].label)['NoExport'] = not control.state
		elif control.name == "guiSeqActRefresh":
			self.clearSequenceActionList()
			self.populateSequenceActionList()
		elif control.name == "guiSeqActList":
			# Clear triggers menu
			del self.guiSeqActOpts.controls[6].items[:]
			if control.itemIndex != -1:
				sequenceName = control.controls[control.itemIndex].controls[0].label
				sequencePrefs = getSequenceKey(sequenceName)
				self.guiSeqActOpts.controls[0].label = "Sequence '%s'" % sequenceName

				try:
					action = Blender.Armature.NLA.GetActions()[sequenceName]
					maxNumFrames = DtsShape_Blender.getNumFrames(action.getAllChannelIpos().values(), False)
				except:
					maxNumFrames = 0

				# Update gui control states
				if sequencePrefs['InterpolateFrames'] > maxNumFrames:
					sequencePrefs['InterpolateFrames'] = maxNumFrames
				if sequencePrefs['NumGroundFrames'] > maxNumFrames:
					sequencePrefs['NumGroundFrames'] = maxNumFrames
				self.guiSeqActOpts.enabled = True
				self.guiSeqActOpts.controls[1].value = sequencePrefs['InterpolateFrames']
				self.guiSeqActOpts.controls[1].max = maxNumFrames
				self.guiSeqActOpts.controls[2].value = sequencePrefs['NumGroundFrames']
				self.guiSeqActOpts.controls[2].max = maxNumFrames
				self.guiSeqActOpts.controls[3].state = sequencePrefs['AnimateMaterial']
				self.guiSeqActOpts.controls[4].value = sequencePrefs['MaterialIpoStartFrame']

				# added for blend anim ref pose selection
				# make sure the user didn't delete the action containing the refrence pose
				# out from underneath us while we weren't looking.
				try: blah = Blender.Armature.NLA.GetActions()[sequencePrefs['BlendRefPoseAction']]
				except: sequencePrefs['BlendRefPoseAction'] = sequenceName
				self.guiSeqActOpts.controls[12].label = "Ref pose for '%s'" % sequenceName
				self.guiSeqActOpts.controls[13].setTextValue(sequencePrefs['BlendRefPoseAction'])
				self.guiSeqActOpts.controls[14].min = 1
				self.guiSeqActOpts.controls[14].max = DtsShape_Blender.getNumFrames(Blender.Armature.NLA.GetActions()[sequencePrefs['BlendRefPoseAction']].getAllChannelIpos().values(), False)
				self.guiSeqActOpts.controls[14].value = sequencePrefs['BlendRefPoseFrame']
				# hack, there must be a better way to handle this.
				try:
					self.guiSeqActOpts.controls[15].value = sequencePrefs['Priority']
				except KeyError:
					self.guiSeqActOpts.controls[15].value = 0


				# Triggers
				for t in sequencePrefs['Triggers']:
					if t[2]: stateStr = "(ON)"
					else: stateStr = "(OFF)"
					self.guiSeqActOpts.controls[6].items.append((self.triggerMenuTemplate % (t[1], t[0])) + stateStr)

				self.guiSeqActOpts.controls[6].itemIndex = 0
				self.guiSeqActOpts.controls[9].max = maxNumFrames
				self.guiSequenceUpdateTriggers(sequencePrefs['Triggers'], 0)
				# show/hide ref pose stuff.
				if sequencePrefs['Blend'] == True:
					self.guiSeqActOpts.controls[12].visible = True
					self.guiSeqActOpts.controls[13].visible = True
					self.guiSeqActOpts.controls[14].visible = True
				else:
					self.guiSeqActOpts.controls[12].visible = False
					self.guiSeqActOpts.controls[13].visible = False
					self.guiSeqActOpts.controls[14].visible = False

			else:
				self.guiSeqActOpts.enabled = False
				self.guiSeqActOpts.controls[0].label = "Sequence: None Selected"
		else:
			if self.guiSeqActList.itemIndex != -1:
				sequenceName = self.guiSeqActList.controls[self.guiSeqActList.itemIndex].controls[0].label
				sequencePrefs = getSequenceKey(sequenceName)
				if control.name == "guiSeqActOptsFramecount":
					sequencePrefs['InterpolateFrames'] = control.value
				elif control.name == "guiSeqActOptsGroundFramecount":
					sequencePrefs['NumGroundFrames'] = control.value
				elif control.name == "guiSeqActOptsAnimateMaterials":
					sequencePrefs['AnimateMaterial'] = control.state
				elif control.name == "guiSeqActOptsMatStartFrame":
					sequencePrefs['MaterialIpoStartFrame'] = control.value
				# added for blend ref pose selection
				elif control.name == "guiSeqActOptsRefposeMenu":
					sequencePrefs['BlendRefPoseAction'] = control.items[control.itemIndex]
					sequencePrefs['BlendRefPoseFrame'] = 1
					self.guiSeqActOpts.controls[14].value = sequencePrefs['BlendRefPoseFrame']
				elif control.name == "guiSeqActOptsRefposeFrame":
					sequencePrefs['BlendRefPoseFrame'] = control.value
				elif control.name == "guiSeqActOptsPriority":
					sequencePrefs['Priority'] = control.value

		pass

	def resize(self, control, newwidth, newheight):

		if control.name == "guiSeqActList":
			control.x = 10
			control.y = 30
			control.height = newheight - 70
			control.width = 300
		elif control.name == "guiSeqActTitle":
			control.x = 10
			control.y = newheight-20
		elif control.name == "guiSeqActOpts":
			control.x = newwidth - 180
			control.y = 0
			control.width = 180
			control.height = newheight
		elif control.name == "guiSeqActOptsTitle":
			control.x = 5
			control.y = newheight - 15
		# Joe - ?
		elif control.name == "sequence.opts.btitle":
			control.x = 5
			control.y = newheight - 110
		elif control.name == "guiSeqActOptsTriggerTitle":
			control.x = 5
			control.y = newheight - 215
		elif control.name == "guiSeqActOptsRefposeTitle":
			control.x = 5
			control.y = newheight - 140
		# Sequence list buttons
		elif control.name == "guiSeqActToggle":
			control.x = 10
			control.y = 5
			control.width = 100
		elif control.name == "guiSeqActRefresh":
			control.x = 112
			control.y = 5
			control.width = 100
		# Sequence options
		elif control.name == "guiSeqActOptsFramecount":
			control.x = 5
			control.y = newheight - 45
			control.width = newwidth - 10
		elif control.name == "guiSeqActOptsGroundFramecount":
			control.x = 5
			control.y = newheight - 70
			control.width = newwidth - 10
		elif control.name == "guiSeqActOptsAnimateMaterials":
			control.x = 5
			control.y = newheight - 95
			control.width = 65
		elif control.name == "guiSeqActOptsMatStartFrame":
			control.x = 72
			control.y = newheight - 95
			control.width = 102
		# Triggers
		elif control.name == "guiSeqActOptsTriggerMenu":
			control.x = 5
			control.y = newheight - 245
			control.width = newwidth - 10
		elif control.name == "guiSeqActOptsTriggerState":
			control.x = 5
			control.y = newheight - 267
			control.width = newwidth - 50
		elif control.name == "guiSeqActOptsTriggerStateOn":
			control.x = 137
			control.y = newheight - 267
			control.width = newwidth - 142
		elif control.name == "guiSeqActOptsTriggerFrame":
			control.x = 5
			control.y = newheight - 289
			control.width = newwidth - 10
		elif control.name == "guiSeqActOptsTriggerAdd":
			control.x = 5
			control.y = newheight - 311
			control.width = (newwidth / 2) - 6
		elif control.name == "guiSeqActOptsTriggerDel":
			control.x = (newwidth / 2)
			control.y = newheight - 311
			control.width = (newwidth / 2) - 6
		# reference pose controls
		elif control.name == "guiSeqActOptsRefposeMenu":
			control.x = 5
			control.y = newheight - 170
			control.width = (newwidth) - 10
		elif control.name == "guiSeqActOptsRefposeFrame":
			control.x = 5
			control.y = newheight - 195
			control.width = (newwidth) - 10
		# sequence priority
		elif control.name == "guiSeqActOptsPriority":
			control.x = 5
			control.y = newheight - 120
			control.width = newwidth - 10

	def guiSequenceUpdateTriggers(self, triggerList, itemIndex):
		if (len(triggerList) == 0) or (itemIndex >= len(triggerList)):
			self.guiSeqActOpts.controls[7].value = 0
			self.guiSeqActOpts.controls[8].state = False
			self.guiSeqActOpts.controls[9].value = 0
		else:
			self.guiSeqActOpts.controls[7].value = triggerList[itemIndex][0] # Trigger State
			self.guiSeqActOpts.controls[9].value = triggerList[itemIndex][1] # Time
			self.guiSeqActOpts.controls[8].state = triggerList[itemIndex][2] # On

	

	def handleTriggersEvent(self, control):
		if self.guiSeqActList.itemIndex == -1:
			return

		sequenceName = self.guiSeqActList.controls[self.guiSeqActList.itemIndex].controls[0].label
		sequencePrefs = getSequenceKey(sequenceName)
		itemIndex = self.guiSeqActOpts.controls[6].itemIndex

		if control.name == "guiSeqActOptsTriggerMenu":
			self.guiSequenceUpdateTriggers(sequencePrefs['Triggers'], itemIndex)
		elif control.name == "guiSeqActOptsTriggerAdd":
			# Add
			sequencePrefs['Triggers'].append([1, 1, True])
			self.guiSeqActOpts.controls[6].items.append((self.triggerMenuTemplate % (1, 1)) + "(ON)")
			self.guiSeqActOpts.controls[6].itemIndex = len(sequencePrefs['Triggers'])-1
			self.guiSequenceUpdateTriggers(sequencePrefs['Triggers'], self.guiSeqActOpts.controls[6].itemIndex)
		elif (len(self.guiSeqActOpts.controls[6].items) != 0):
			if control.name == "guiSeqActOptsTriggerState":
				sequencePrefs['Triggers'][itemIndex][0] = control.value
			elif control.name == "guiSeqActOptsTriggerStateOn":
				sequencePrefs['Triggers'][itemIndex][2] = control.state
			elif control.name == "guiSeqActOptsTriggerFrame":
				sequencePrefs['Triggers'][itemIndex][1] = control.value
			elif control.name == "guiSeqActOptsTriggerDel":
				# Remove
				del sequencePrefs['Triggers'][itemIndex]
				del self.guiSeqActOpts.controls[6].items[itemIndex]
				# Must decrement itemIndex if we are out of bounds
				if itemIndex <= len(sequencePrefs['Triggers']):
					self.guiSeqActOpts.controls[6].itemIndex = len(sequencePrefs['Triggers'])-1
					itemIndex = self.guiSeqActOpts.controls[6].itemIndex
				self.guiSequenceUpdateTriggers(sequencePrefs['Triggers'], itemIndex)

			# Update menu caption
			if itemIndex == -1:
				return
			if sequencePrefs['Triggers'][itemIndex][2]: stateStr = "(ON)"
			else: stateStr = "(OFF)"
			self.guiSeqActOpts.controls[6].items[itemIndex] = (self.triggerMenuTemplate % (sequencePrefs['Triggers'][itemIndex][1], sequencePrefs['Triggers'][itemIndex][0])) + stateStr
	def populateSequenceActionList(self):
		actions = Armature.NLA.GetActions()
		keys = actions.keys()
		keys.sort()

		#print "populateSequenceActionList: name of list : %s" % guiSeqActList.name
		# There are a finite number of events we can allocate in blender, so we need to
		# assign events in batches of the maximum number of visible list items.
		startEvent = 40
		for key in keys:
			# skip the fake action (hack for blender 2.41 bug)
			if key == "DTSEXPFAKEACT": continue		
			self.guiSeqActList.addControl(self.createSequenceActionListitem(key, startEvent))
			startEvent += 4
			# add any new animations to the ref pose combo box
			if not (key in self.guiSeqActOpts.controls[13].items):
				self.guiSeqActOpts.controls[13].items.append(key)

	def clearSequenceActionList(self):

		for i in range(0, len(self.guiSeqActList.controls)):
			del self.guiSeqActList.controls[i].controls[:]
		del self.guiSeqActList.controls[:]

		self.guiSeqActList.itemIndex = -1
		self.guiSeqActList.scrollPosition = 0
		if self.guiSeqActList.callback: self.guiSeqActList.callback(self.guiSeqActList) # Bit of a hack, but works

	def handleListItemEvent(self, control):
		global Prefs

		# Determine sequence name

		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / 4

		sequenceName = self.guiSeqActList.controls[calcIdx].controls[0].label
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
				self.guiSeqActOpts.controls[12].visible = True
				self.guiSeqActOpts.controls[13].visible = True
				self.guiSeqActOpts.controls[14].visible = True
			else:
				self.guiSeqActOpts.controls[12].visible = False
				self.guiSeqActOpts.controls[13].visible = False
				self.guiSeqActOpts.controls[14].visible = False
		elif realItem == 3:
			sequencePrefs['Cyclic'] = control.state

	def createSequenceActionListitem(self, seq_name, startEvent):
		sequencePrefs = getSequenceKey(seq_name)
		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)

		# testing new fade modes for sequence list items
		#guiContainer.fade_mode = 8  # same as 2 but with a brighter endcolor, easier on the eyes.
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", seq_name, None, None)
		guiName.x, guiName.y = 5, 5
		guiExport = Common_Gui.ToggleButton("guiExport", "Export", "Export Sequence", startEvent, self.handleListItemEvent, None)
		guiExport.x, guiExport.y = 70, 5
		guiExport.width, guiExport.height = 50, 15
		guiExport.state = not sequencePrefs['NoExport']
		guiDSQ = Common_Gui.ToggleButton("guiDSQ", "Dsq", "Export Sequence as DSQ", startEvent+1, self.handleListItemEvent, None)
		guiDSQ.x, guiDSQ.y = 122, 5
		guiDSQ.width, guiDSQ.height = 50, 15
		guiDSQ.state = sequencePrefs['Dsq']
		guiBlend = Common_Gui.ToggleButton("guiBlend", "Blend", "Export Sequence as Blend", startEvent+2, self.handleListItemEvent, None)
		guiBlend.x, guiBlend.y = 174, 5
		guiBlend.width, guiBlend.height = 50, 15
		guiBlend.state = sequencePrefs['Blend']
		guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+3, self.handleListItemEvent, None)
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

		# update old style prefs that don't have 'IFL' sequence keys
		self.updateOldPrefs()

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
		self.guiNumImages = Common_Gui.NumberPicker("guiNumImages", "Images", "Number of Images in the IFL animation", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiFramesListTxt = Common_Gui.SimpleText("guiFramesListTxt", "IFL Image Frames:", None, self.resize)
		self.guiFramesList = Common_Gui.ListContainer("guiFramesList", "", self.handleFrameListEvent, self.resize)
		self.guiFramesListSelectedTxt = Common_Gui.SimpleText("guiFramesListSelectedTxt", "Selected:", None, self.resize)
		self.guiNumFrames = Common_Gui.NumberPicker("guiNumFrames", "Frames", "Hold Selected image for n frames", globalEvents.getNewID(), self.handleEvent, self.resize)
		self.guiApplyToAll = Common_Gui.BasicButton("guiApplyToAll", "Apply to all", "Apply current frame display value to all IFL images", globalEvents.getNewID(), self.handleEvent, self.resize)

		# set initial states
		self.guiSeqOptsContainer.enabled = True
		self.guiSeqOptsContainer.fade_mode = 5
		self.guiSeqOptsContainer.borderColor = None
		self.guiSeqList.fade_mode = 0
		self.guiFramesList.enabled = True



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
		
		# populate the IFL sequence list
		self.populateIFLList(None)
		
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


	def updateOldPrefs(self):
		print " ****** Updating old IFL sequence preferences ****** "
		# loop through all actions in the preferences and add the 'IFL' key to them with some reasonable default values.
		global Prefs
		for seqName in Prefs['Sequences'].keys():
			seq = Prefs['Sequences'][seqName]
			try: x = seq['IFL']
			except KeyError:
				print "Resetting IFL Sequence:",seqName
				seq['IFL'] = {}
				seq['IFL']['Enabled'] = False
				seq['IFL']['Material'] = None
				seq['IFL']['NumImages'] = 0
				seq['IFL']['TotalFrames'] = 0
				seq['IFL']['IFLFrames'] = []

	
	def resize(self, control, newwidth, newheight):
		print "resize callback called..."
		# handle control resize events.
		#print control.name
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
			control.x, control.y, control.height, control.width = 280,310, 20,82
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
			control.x, control.y, control.height, control.width = 20,30, 195,223
		elif control.name == "guiFramesListSelectedTxt":
			control.x, control.y, control.height, control.width = 20,10, 20,120
		elif control.name == "guiNumFrames":
			control.x, control.y, control.height, control.width = 80,5, 20,80
		elif control.name == "guiApplyToAll":
			control.x, control.y, control.height, control.width = 164,5, 20,80
		#elif control.name == "guiSeqIFLImageCopy":
		#	control.x, control.y, control.height, control.width = 162,168, 20,80
		#elif control.name == "guiSeqIFLImagePasteA":
		#	control.x, control.y, control.height, control.width = 162,146, 20,80
		#elif control.name == "guiSeqIFLImagePasteB":
		#	control.x, control.y, control.height, control.width = 162,124, 20,80
		#elif control.name == "guiSeqIFLImageMoveUp":
		#	control.x, control.y, control.height, control.width = 162,102, 20,80
		#elif control.name == "guiSeqIFLImageMoveDown":
		#	control.x, control.y, control.height, control.width = 162,80, 20,80
		'''
		elif control.name == "guiSeqIFLDurationTxt":
			control.x = 10
			control.y = 256
			control.height = 20
			control.width = 120
		elif control.name == "guiSeqIFLDuration":
			control.x = 125
			control.y = 253
			control.height = 20
			control.width = 120
		'''

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
		#guiExport.state = not sequencePrefs['NoExport']
		guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+1, self.handleListItemEvent, None)
		guiCyclic.x, guiCyclic.y = 157, 5
		guiCyclic.width, guiCyclic.height = 50, 15
		#guiCyclic.state = sequencePrefs['Cyclic']

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
		# add sequence to prefs
		if not (seqName in Prefs['Sequences'].keys()):
			try: x = Prefs['Sequences'][seqName]
			except: Prefs['Sequences'][seqName] = {}
			seq = Prefs['Sequences'][seqName]
			# add action stuff here for now...
			seq['Triggers'] = []
			seq['NoExport'] = False
			seq['Dsq'] = False
			seq['Priority'] = 0
			seq['Cyclic'] = False
			seq['InterpolateFrames'] = 0
			seq['TotalFrames'] = 0
			seq['NumGroundFrames'] = 0
			seq['Blend'] = False
			seq['BlendRefPoseAction'] = None
			seq['BlendRefPoseFrame'] = 8
			seq['AnimateMaterial'] = False
			seq['MaterialIpoStartFrame'] = 0

			
			# add ifl stuff
			seq['IFL'] = {}
			seq['IFL']['Enabled'] = True
			seq['IFL']['Material'] = None
			seq['IFL']['NumImages'] = 0
			seq['IFL']['TotalFrames'] = 0
			seq['IFL']['IFLFrames'] = []

			# add sequence to GUI sequence list
			self.guiSeqList.addControl(self.createSequenceListItem(seqName))
	

	# add IFL to an existing sequence
	def AddIFLToExistingSeq(self, seqName):
		try: x = Prefs['Sequences'][seqName]
		except: Prefs['Sequences'][seqName] = {}
		seq = Prefs['Sequences'][seqName]
		# add ifl stuff
		seq['IFL'] = {}
		seq['IFL']['Enabled'] = True
		seq['IFL']['Material'] = None
		seq['IFL']['NumImages'] = 0
		seq['IFL']['TotalFrames'] = 0
		seq['IFL']['IFLFrames'] = []

		# add sequence to GUI sequence list
		self.guiSeqList.addControl(self.createSequenceListItem(seqName))

	def determineIFLMatStartNumber(self, matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		digitPortion = matName[i:len(matName)]
		print "Last", len(matName) - i, "characters of material name are digits."		
		if len(digitPortion) > 0:
			return int(digitPortion)
		else:
			return 0
	
	def determineIFLMatNumberPadding(self, matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		digitPortion = matName[i:len(matName)]
		print "Last", len(matName) - i, "characters of material name are digits."
		return len(matName) - i

	def numToPaddedString(self, num, padding):
		retVal = '0' * (padding - len(str(num)))
		retVal += str(num)
		print retVal
		return retVal

	def getIFLMatTextPortion(self, matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		textPortion = matName[0:i]
		print "first", i, "characters of material name are text."
		if len(textPortion) > 0:
			return textPortion
		else:
			return ""
	
	
	def handleEvent(self, control):
		print "handleEvent called..."
		if control.name == "guiSeqName":
			pass
		elif control.name == "guiSeqAdd":
			# todo - validate sequence name
			self.AddNewIFLSeq(self.guiSeqName.value)
			self.guiSeqName.value = ""
		elif control.name == "guiSeqDel":
			guiSeqList = self.guiSeqList
			if guiSeqList.itemIndex > -1 and guiSeqList.itemIndex < len(guiSeqList.controls):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				guiSeqList.removeItem(guiSeqList.itemIndex)
				Prefs['Sequences'][seqName]['IFL']['Enabled'] = False
				# todo - don't add back to list if only IFL is enabled for the sequence
				self.guiSeqExistingSequences.items.append(seqName)
		elif control.name == "guiSeqRename":
			guiSeqList = self.guiSeqList
			# todo - validate sequence name
			guiSeqList.controls[guiSeqList.itemIndex].controls[0].label = self.guiSeqName.value
		elif control.name == "guiSeqAddToExisting":
			existingSequences = self.guiSeqExistingSequences
			itemIndex = existingSequences.itemIndex
			if itemIndex >=0 and itemIndex < len(existingSequences.items):
				existingName = existingSequences.getSelectedItemString()
				self.AddIFLToExistingSeq(existingName)
				del existingSequences.items[itemIndex]
				existingSequences.selectStringItem("")
		elif control.name == "guiMat":
			guiSeqList = self.guiSeqList
			guiMat = self.guiMat
			itemIndex = guiMat.itemIndex
			# set the pref for the selected sequence
			if guiSeqList.itemIndex > -1 and itemIndex >=0 and itemIndex < len(guiMat.items):
				seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
				Prefs['Sequences'][seqName]['IFL']['Material'] = control.getSelectedItemString()
		elif control.name == "guiNumImages":
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
			print fr
			#print seqPrefs			
			i = len(guiFramesList.controls)
			while len(guiFramesList.controls) < control.value:
				newItemName = textPortion + self.numToPaddedString(startNum + i, numPadding)
				guiFramesList.addControl(self.createFramesListItem(newItemName))
				print "adding item to prefs:", newItemName
				Prefs['Sequences'][seqName]['IFL']['IFLFrames'].append([newItemName,1])
				i += 1
			print fr
		elif control.name == "guiNumFrames":
			guiSeqList = self.guiSeqList
			guiFramesList = self.guiFramesList
			seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			itemIndex = guiFramesList.itemIndex
			print "itemIndex=",itemIndex
			seqPrefs['IFL']['IFLFrames'][itemIndex][1] = control.value
			guiFramesList.controls[guiFramesList.itemIndex].controls[1].label = "fr:" + str(control.value)
			if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works
		elif control.name == "guiApplyToAll":
			guiSeqList = self.guiSeqList
			guiFramesList = self.guiFramesList
			seqName = guiSeqList.controls[guiSeqList.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			itemIndex = guiFramesList.itemIndex
			#print "itemIndex=",itemIndex
			for i in range(0, len(seqPrefs['IFL']['IFLFrames'])):				
				seqPrefs['IFL']['IFLFrames'][i][1] = self.guiNumFrames.value
				guiFramesList.controls[i].controls[1].label = "fr:" + str(self.guiNumFrames.value)
			if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works

		
	# called when an item is selected in the sequence list
	def handleListEvent(self, control):
		print "handleListEvent called..."
		if control.itemIndex < 0:
			self.guiSeqName.value = ""
			self.guiMat.selectStringItem("")
			self.guiNumImages.value = 0
			self.guiNumFrames.value = 1
		else:
			seqName = control.controls[control.itemIndex].controls[0].label
			seqPrefs = getSequenceKey(seqName)
			self.guiSeqName.value = seqName 
			self.guiMat.selectStringItem(seqPrefs['IFL']['Material'])
			self.guiNumImages.value = seqPrefs['IFL']['NumImages']
			print seqPrefs['IFL']['IFLFrames']
			try: self.guiNumFrames.value = seqPrefs['IFL']['IFLFrames'][1]
			except: self.guiNumFrames.value = 1
			self.populateImageFramesList(seqName)
	
	def handleListItemEvent(self, control):
		print "handleListItemEvent called..."
		print control
		print control.name
		# Determine sequence name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / 2

		print "calcIdx=",calcIdx
		seqName = self.guiSeqList.controls[calcIdx].controls[0].label
		print "seqName=",seqName
		realItem = control.evt - 40 - (calcIdx*2)
		sequencePrefs = getSequenceKey(seqName)

		if realItem == 0:
			sequencePrefs['NoExport'] = not control.state
		elif realItem == 1:
			sequencePrefs['Cyclic'] = control.state
		pass
	
	# called when an item is selected in the IFL image frames list
	def handleFrameListEvent(self, control):
		guiFramesList = self.guiFramesList
		guiNumFrames = self.guiNumFrames
		if control.itemIndex > -1:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			print "seqName=",seqName
			seqPrefs = getSequenceKey(seqName)
			print seqPrefs
			guiNumFrames.value = seqPrefs['IFL']['IFLFrames'][control.itemIndex][1]
		else:
			guiNumFrames.value = 1
		
	# this method assumes that the IFL list is empty prior to it being called.
	def populateIFLList(self, IFLSequences):
		print "Populating IFL Sequence list..."
		# loop through all actions in the preferences and check for IFL animations
		global Prefs
		for seqName in Prefs['Sequences'].keys():
			print "Checking",seqName,"..."
			seq = Prefs['Sequences'][seqName]
			if seq['IFL']['Enabled'] == True:
				print "  Creating IFL sequence:",seqName
				self.guiSeqList.addControl(self.createSequenceListItem(seqName))
			
			
		#self.guiSeqList.addControl(self.createSequenceListitem("Test 1", 40))
		pass

	def populateExistingSeqPulldown(self):
		print "Populating Existing Sequence list..."
		# loop through all actions in the preferences and check for sequences without IFL animations
		global Prefs
		for seqName in Prefs['Sequences'].keys():
			print "Checking",seqName,"..."
			seq = Prefs['Sequences'][seqName]
			if seq['IFL']['Enabled'] == False:
				print "  Adding sequence to existing sequence pulldown:",seqName
				self.guiSeqExistingSequences.items.append(seqName)
			
			
			'''
			seq['IFL']['Material'] = None
			seq['IFL']['NumImages'] = 0
			seq['IFL']['TotalFrames'] = 0
			seq['IFL']['IFLFrames'] = []
			'''

		#self.guiSeqList.addControl(self.createSequenceListitem("Test 1", 40))
		pass

	def populateIFLMatPulldown(self):
		print "Populating IFL Material pulldown"
		# loop through all materials in the preferences and check for IFL materials
		global Prefs
		try: x = Prefs['Materials'].keys()
		except: Prefs['Materials'] = {}
		for matName in Prefs['Materials'].keys():
			print "Checking",matName,"..."
			mat = Prefs['Materials'][matName]
			try: x = mat['IFLMaterial']
			except KeyError: mat['IFLMaterial'] = False
			if mat['IFLMaterial'] == True:
				print "  Adding material to IFL Material pulldown:",matName
				self.guiMat.items.append(matName)

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
			print "fr:",fr
			guiFramesList.addControl(self.createFramesListItem(fr[0], fr[1]))
			#print "Checking",matName,"..."
			
		
		guiFramesList
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

		self.guiMaterialList = Common_Gui.ListContainer("guiMaterialList", "material.list", self.handleEvent, self.resize)
		self.guiMaterialList.fade_mode = 0
		self.guiMaterialOptions = Common_Gui.BasicContainer("guiMaterialOptions", "", None, self.resize)
		self.guiMaterialTransFrame = Common_Gui.BasicFrame("guiMaterialTransFrame", "", None, 29, None, self.resize)
		self.guiMaterialAdvancedFrame = Common_Gui.BasicFrame("guiMaterialAdvancedFrame", "", None, 30, None, self.resize)
		self.guiMaterialImportRefreshButton = Common_Gui.BasicButton("guiMaterialImportRefreshButton", "Import / Refresh", "Import Blender materials and settings", 7, self.handleEvent, self.resize)
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
		guiMaterialsSubtab.addControl(self.guiMaterialList)
		guiMaterialsSubtab.addControl(self.guiMaterialOptions)
		guiMaterialsSubtab.addControl(self.guiMaterialImportRefreshButton)

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

		# update old style preferences
		self.updateOldPrefs()
		
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
		del self.guiMaterialList
		del self.guiMaterialOptions
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
		del self.guiMaterialShowAdvancedButton
		del self.guiMaterialRefMapButton
		del self.guiMaterialDetailMapMenu
		del self.guiMaterialBumpMapMenu
		del self.guiMaterialReflectanceMapMenu
		del self.guiMaterialReflectanceSlider
		del self.guiMaterialDetailScaleSlider

	
	def updateOldPrefs(self):
		# loop through all actions in the preferences and add the 'IFL' key to them with some reasonable default values.
		global Prefs
		for matName in Prefs['Materials'].keys():
			pmi = Prefs['Materials'][matName]
			try: x = pmi['IFLMaterial']
			except: pmi['IFLMaterial'] = False
	
	def resize(self, control, newwidth, newheight):
		# handle control resize events.
		if control.name == "guiMaterialList":
			control.x, control.y, control.height, control.width = 10,30, newheight - 70,150
		elif control.name == "guiMaterialOptions":
			control.x, control.y, control.height, control.width = 161,0, 335,328
		elif control.name == "guiMaterialTransFrame":
			control.x, control.y, control.height, control.width = 8,newheight-105, 50,170
		elif control.name == "guiMaterialAdvancedFrame":
			control.x, control.y, control.height, control.width = 8,newheight-325, 75,315
		elif control.name == "guiMaterialImportRefreshButton":
			control.x, control.y, control.width = 15,newheight-30, 100
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
		print "importMaterialList called..."
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


		print "Removing unused materials from the perfs..."
		# remove unused materials from the prefs
		for imageName in materials.keys()[:]:
			if not (imageName in imageList): del materials[imageName]

		if len(imageList)==0: return
		print "At least 1 material is in the imageList."


		# populate materials list with all blender materials
		for imageName in imageList:
			print "Current image is:", imageName
			bmat = None
			# Do we have a blender material that matches the image name?
			print "Do we have a blender material that matches the image name?"
			try: bmat = Blender.Material.Get(imageName)
			except NameError:
				# No blender material, do we have a prefs key for this material?
				print "No blender material, do we have a prefs key for this material?"
				try: x = Prefs['Materials'][imageName]
				except KeyError:
					# no corresponding blender material and no existing texture material, so use reasonable defaults.
					print "no corresponding blender material and no existing texture material, so use reasonable defaults."
					#print "Could not find a blender material that matches image (", imageName,") used on mesh, setting defaults."
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
					print "!!!!!!!!!!!!!!!!stuff!!!!!!!!!!!!!!!!!! (1)"
				continue

			# We have a blender material, do we have a prefs key for it?
			print "We have a blender material, do we have a prefs key for it?"
			print "Prefs['Materials'] = \n",Prefs['Materials']
			try: x = Prefs['Materials'][bmat.name]			
			except:
				# No prefs key, so create one.
				print "No prefs key, so create one."
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
				print "!!!!!!!!!!!!!!!!stuff!!!!!!!!!!!!!!!!!! (2)"
				#if bmat.getRef() > 0:
				#	pmb['NeverEnvMap'] = False
				#else: pmb['NeverEnvMap'] = True

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
							#print "Setting basetex to:", textures[0].tex.image.getName().split(".")[0]
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
								guiMaterialOptions.controlDict['guiMaterialReflectanceMapMenu'].selectStringItem(stripImageExtension(textures[i].tex.image.getName()))
							else:
								pmb['RefMapTex'] = None
						# B) We have a normal map (basically a 3d bump map)
						elif (texture_obj.mapto & Texture.MapTo.NOR):
							pmb['BumpMapFlag'] = True
							if textures[0].tex.image != None:
								pmb['BumpMapTex'] = stripImageExtension(textures[i].tex.image.getName())
								guiMaterialOptions.controlDict['guiMaterialBumpMapMenu'].selectStringItem(stripImageExtension(textures[i].tex.image.getName()))
							else:
								pmb['BumpMapTex'] = None
						# C) We have a texture; Lets presume its a detail map (since its laid on top after all)
						else:
							pmb['DetailMapFlag'] = True
							if textures[0].tex.image != None:
								pmb['DetailTex'] = stripImageExtension(textures[i].tex.image.getName())
								guiMaterialOptions.controlDict['guiMaterialDetailMapMenu'].selectStringItem(stripImageExtension(textures[i].tex.image.getName()))
							else:
								pmb['DetailTex'] = None

	def handleEvent(self, control):
		global Prefs
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
				#print "control.itemIndex =", control.itemIndex
				#print "len(controls) =", len(guiMaterialList.controls)
				materialName = guiMaterialList.controls[control.itemIndex].controls[0].label
				# referesh and repopulate the material option controls
				guiMaterialOptions.controlDict['guiMaterialSWrapButton'].state = matList[materialName]['SWrap']
				guiMaterialOptions.controlDict['guiMaterialTWrapButton'].state = matList[materialName]['TWrap']
				guiMaterialOptions.controlDict['guiMaterialTransButton'].state = matList[materialName]['Translucent']
				guiMaterialOptions.controlDict['guiMaterialAddButton'].state = matList[materialName]['Additive']
				guiMaterialOptions.controlDict['guiMaterialSubButton'].state = matList[materialName]['Subtractive']
				guiMaterialOptions.controlDict['guiMaterialSelfIllumButton'].state = matList[materialName]['SelfIlluminating']
				guiMaterialOptions.controlDict['guiMaterialEnvMapButton'].state = not matList[materialName]['NeverEnvMap']
				guiMaterialOptions.controlDict['guiMaterialMipMapButton'].state = not matList[materialName]['NoMipMap']
				guiMaterialOptions.controlDict['guiMaterialMipMapZBButton'].state = matList[materialName]['MipMapZeroBorder']
				guiMaterialOptions.controlDict['guiMaterialIFLMatButton'].state = matList[materialName]['IFLMaterial']
				guiMaterialOptions.controlDict['guiMaterialDetailMapButton'].state = matList[materialName]['DetailMapFlag']
				guiMaterialOptions.controlDict['guiMaterialBumpMapButton'].state = matList[materialName]['BumpMapFlag']
				guiMaterialOptions.controlDict['guiMaterialRefMapButton'].state = matList[materialName]['ReflectanceMapFlag']			
				guiMaterialOptions.controlDict['guiMaterialDetailMapMenu'].selectStringItem(matList[materialName]['DetailTex'])
				guiMaterialOptions.controlDict['guiMaterialBumpMapMenu'].selectStringItem(matList[materialName]['BumpMapTex'])
				guiMaterialOptions.controlDict['guiMaterialReflectanceMapMenu'].selectStringItem(matList[materialName]['RefMapTex'])
				guiMaterialOptions.controlDict['guiMaterialReflectanceSlider'].value = matList[materialName]['reflectance'] * 100.0
				guiMaterialOptions.controlDict['guiMaterialDetailScaleSlider'].value = matList[materialName]['detailScale'] * 100.0
			else:
				guiMaterialOptions.controlDict['guiMaterialSWrapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialTWrapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialTransButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialAddButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialSubButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialSelfIllumButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialEnvMapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialMipMapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialMipMapZBButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialIFLMatButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialDetailMapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialBumpMapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialRefMapButton'].state = False
				guiMaterialOptions.controlDict['guiMaterialDetailMapMenu'].selectStringItem("")
				guiMaterialOptions.controlDict['guiMaterialBumpMapMenu'].selectStringItem("")
				guiMaterialOptions.controlDict['guiMaterialReflectanceMapMenu'].selectStringItem("")
				guiMaterialOptions.controlDict['guiMaterialReflectanceSlider'].value = 0
				guiMaterialOptions.controlDict['guiMaterialDetailScaleSlider'].value = 100
				guiMaterialOptions.enabled = False


		if guiMaterialList.itemIndex == -1: return

		elif control.name == "guiMaterialSWrapButton":
			Prefs['Materials'][materialName]['SWrap'] = control.state
		elif control.name == "guiMaterialTWrapButton":
			Prefs['Materials'][materialName]['TWrap'] = control.state
		elif control.name == "guiMaterialTransButton":
			if not control.state:
				Prefs['Materials'][materialName]['Subtractive'] = False
				guiMaterialOptions.controlDict['guiMaterialSubButton'].state = False
				Prefs['Materials'][materialName]['Additive'] = False
				guiMaterialOptions.controlDict['guiMaterialAddButton'].state = False
			Prefs['Materials'][materialName]['Translucent'] = control.state
		elif control.name == "guiMaterialAddButton":
			if control.state:
				Prefs['Materials'][materialName]['Translucent'] = True
				guiMaterialOptions.controlDict['guiMaterialTransButton'].state = True
				Prefs['Materials'][materialName]['Subtractive'] = False
				guiMaterialOptions.controlDict['guiMaterialSubButton'].state = False
			Prefs['Materials'][materialName]['Additive'] = control.state
		elif control.name == "guiMaterialSubButton":
			if control.state:
				Prefs['Materials'][materialName]['Translucent'] = True
				guiMaterialOptions.controlDict['guiMaterialTransButton'].state = True
				Prefs['Materials'][materialName]['Additive'] = False
				guiMaterialOptions.controlDict['guiMaterialAddButton'].state = False
			Prefs['Materials'][materialName]['Subtractive'] = control.state
		elif control.name == "guiMaterialSelfIllumButton":
			Prefs['Materials'][materialName]['SelfIlluminating'] = control.state
		elif control.name == "guiMaterialEnvMapButton":
			if not control.state:
				Prefs['Materials'][materialName]['ReflectanceMapFlag'] = False
				guiMaterialOptions.controlDict['guiMaterialRefMapButton'].state = False
			Prefs['Materials'][materialName]['NeverEnvMap'] = not control.state
		elif control.name == "guiMaterialMipMapButton":
			if not control.state:
				Prefs['Materials'][materialName]['MipMapZeroBorder'] = False
				guiMaterialOptions.controlDict['guiMaterialMipMapZBButton'].state = False
			Prefs['Materials'][materialName]['NoMipMap'] = not control.state
		elif control.name == "guiMaterialMipMapZBButton":
			if control.state:
				Prefs['Materials'][materialName]['NoMipMap'] = False
				guiMaterialOptions.controlDict['guiMaterialMipMapButton'].state = True
			Prefs['Materials'][materialName]['MipMapZeroBorder'] = control.state
		elif control.name == "guiMaterialIFLMatButton":
			Prefs['Materials'][materialName]['IFLMaterial'] = control.state
		elif control.name == "guiMaterialDetailMapButton":
			Prefs['Materials'][materialName]['DetailMapFlag'] = control.state
		elif control.name == "guiMaterialBumpMapButton":
			Prefs['Materials'][materialName]['BumpMapFlag'] = control.state
		elif control.name == "guiMaterialRefMapButton":
			if control.state:
				Prefs['Materials'][materialName]['NeverEnvMap'] = False
				guiMaterialOptions.controlDict['guiMaterialEnvMapButton'].state = True
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
		#print "clearing material list..."
		for i in range(0, len(guiMaterialList.controls)):
			del guiMaterialList.controls[i].controls[:]
		del guiMaterialList.controls[:]

		guiMaterialList.itemIndex = -1
		guiMaterialList.scrollPosition = 0
		if guiMaterialList.callback: guiMaterialList.callback(guiMaterialList) # Bit of a hack, but works
		#print "Cleared material list."


	def populateMaterialList(self):
		global Prefs
		guiMaterialList = self.guiMaterialList
		guiMaterialOptions = self.guiMaterialOptions
		# clear texture pulldowns
		guiMaterialOptions.controlDict['guiMaterialDetailMapMenu'].items = []
		guiMaterialOptions.controlDict['guiMaterialBumpMapMenu'].items = []
		guiMaterialOptions.controlDict['guiMaterialReflectanceMapMenu'].items = []
		# populate the texture pulldowns
		for img in Blender.Image.Get():
			guiMaterialOptions.controlDict['guiMaterialDetailMapMenu'].items.append(stripImageExtension(img.getName()))
			guiMaterialOptions.controlDict['guiMaterialBumpMapMenu'].items.append(stripImageExtension(img.getName()))
			guiMaterialOptions.controlDict['guiMaterialReflectanceMapMenu'].items.append(stripImageExtension(img.getName()))


		# autoimport blender materials
		self.importMaterialList()
		try:
			materials = Prefs['Materials']
		except:

			toDo = 1
			importMaterialList()
			materials = Prefs['Materials']


		# add the materials to the list
		startEvent = 40
		for mat in materials.keys():
			#print "mat: ", mat
			self.guiMaterialList.addControl(self.createMaterialListItem(mat, startEvent))
			startEvent += 1




#IFLControls = IFLControlsClass
IFLControls = None
MaterialControls = None


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
	
	global IFLControls
	
	global guiTabBar, guiSequencesTabBar
	
	global guiSeqActButton, guiSequenceIFLButton, guiSequenceVisibilityButton, guiSequenceUVButton, guiSequenceMorphButton
	global guiSeqActSubtab, guiSequenceIFLSubtab, guiSequenceVisibilitySubtab, guiSequenceUVSubtab, guiSequenceMorphSubtab
	                                
	Common_Gui.initGui(exit_callback)
	
	# Main tab button controls
	guiSequenceButton = Common_Gui.TabButton("guiSequenceButton", "Sequences", "Sequence options", None, guiBaseCallback, guiBaseResize)
	guiSequenceButton.state = True
	guiArmatureButton = Common_Gui.TabButton("guiArmatureButton", "Armatures", "Armature options", None, guiBaseCallback, guiBaseResize)
	guiMaterialsButton = Common_Gui.TabButton("guiMaterialsButton", "Materials", "Material options", None, guiBaseCallback, guiBaseResize)
	guiMeshButton = Common_Gui.TabButton("guiMeshButton", "General", "Mesh and other options", None, guiBaseCallback, guiBaseResize)
	guiAboutButton = Common_Gui.TabButton("guiAboutButton", "About", "About", None, guiBaseCallback, guiBaseResize)
	
	guiExportButton = Common_Gui.BasicButton("guiExportButton", "Export", "Export .dts shape", globalEvents.getNewID("Export"), guiBaseCallback, guiBaseResize)

	
	# Subtab button controls
	guiSeqActButton = Common_Gui.TabButton("guiSeqActButton", "Actions", "Action Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSeqActButton.state = True
	guiSequenceIFLButton = Common_Gui.TabButton("guiSequenceIFLButton", "IFL", "IFL Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSequenceVisibilityButton = Common_Gui.TabButton("guiSequenceVisibilityButton", "Visibility", "Visibility Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSequenceUVButton = Common_Gui.TabButton("guiSequenceUVButton", "Texture UV", "Texture UV Coord Animations", None, guiSequenceTabsCallback, guiBaseResize)
	guiSequenceMorphButton = Common_Gui.TabButton("guiSequenceMorphButton", "Morph", "Mesh Morph Animations", None, guiSequenceTabsCallback, guiBaseResize)

	
	# Armature tab controls
	guiBoneText = Common_Gui.SimpleText("guiBoneText", "Bones that should be exported :", None, guiArmatureResize)
	guiBoneList = Common_Gui.BoneListContainer("guiBoneList", None, None, guiArmatureResize)
	guiBoneMatchText =  Common_Gui.SimpleText("guiBoneMatchText", "Match pattern", None, guiArmatureResize)
	guiBonePatternText = Common_Gui.TextBox("guiBonePatternText", "", "pattern to match bone names, asterix is wildcard", 6, guiArmatureCallback, guiArmatureResize)
	guiBonePatternText.value = "*"
	guiBonePatternOnButton = Common_Gui.BasicButton("guiBonePatternOnButton", "On", "Turn on export of bones matching pattern", 7, guiArmatureCallback, guiArmatureResize)
	guiBonePatternOffButton = Common_Gui.BasicButton("guiBonePatternOffButton", "Off", "Turn off export of bones matching pattern", 8, guiArmatureCallback, guiArmatureResize)
	guiBoneRefreshButton = Common_Gui.BasicButton("guiBoneRefreshButton", "Refresh", "Refresh bones list", 9, guiArmatureCallback, guiArmatureResize)
	
	# Material tab controls
	# Moved to class - Joe
	
	# General tab controls
	guiStripText = Common_Gui.SimpleText("guiStripText", "Geometry type", None, guiGeneralResize)
	# Joe - Ugly but effective
	try: x = Prefs['PrimType']
	except KeyError: Prefs['PrimType'] = "Tris"
	guiTriMeshesButton = Common_Gui.ToggleButton("guiTriMeshesButton", "Triangles", "Generate individual triangles for meshes", 6, guiGeneralCallback, guiGeneralResize)
	if Prefs['PrimType'] == "Tris": guiTriMeshesButton.state = True
	else: guiTriMeshesButton.state = False
	guiTriListsButton = Common_Gui.ToggleButton("guiTriListsButton", "Triangle Lists", "Generate triangle lists for meshes", 7, guiGeneralCallback, guiGeneralResize)
	if Prefs['PrimType'] == "TriLists": guiTriListsButton.state = True
	else: guiTriListsButton.state = False
	guiStripMeshesButton = Common_Gui.ToggleButton("guiStripMeshesButton", "Triangle Strips", "Generate triangle strips for meshes", 8, guiGeneralCallback, guiGeneralResize)
	if Prefs['PrimType'] == "TriStrips": guiStripMeshesButton.state = True
	else: guiStripMeshesButton.state = False
	guiMaxStripSizeSlider = Common_Gui.NumberSlider("guiMaxStripSizeSlider", "Strip Size ", "Maximum size of generated triangle strips", 9, guiGeneralCallback, guiGeneralResize)
	guiMaxStripSizeSlider.min, guiMaxStripSizeSlider.max = 3, 30
	guiMaxStripSizeSlider.value = Prefs['MaxStripSize']
	# --
	guiClusterText = Common_Gui.SimpleText("guiClusterText", "Cluster Mesh", None, guiGeneralResize)
	guiClusterWriteDepth = Common_Gui.ToggleButton("guiClusterWriteDepth", "Write Depth ", "Always Write the Depth on Cluster meshes", 10, guiGeneralCallback, guiGeneralResize)
	guiClusterWriteDepth.state = Prefs['AlwaysWriteDepth']
	guiClusterDepth = Common_Gui.NumberSlider("guiClusterDepth", "Depth", "Maximum depth Clusters meshes should be calculated to", 11, guiGeneralCallback, guiGeneralResize)
	guiClusterDepth.min, guiClusterDepth.max = 3, 30
	guiClusterDepth.value = Prefs['ClusterDepth']
	# --
	guiBillboardText = Common_Gui.SimpleText("guiBillboardText", "Billboard", None, guiGeneralResize)
	guiBillboardButton = Common_Gui.ToggleButton("guiBillboardButton", "Enable", "Add a billboard detail level to the shape", 12, guiGeneralCallback, guiGeneralResize)
	guiBillboardButton.state = Prefs['Billboard']['Enabled']
	guiBillboardEquator = Common_Gui.NumberPicker("guiBillboardEquator", "Equator", "Number of images around the equator", 13, guiGeneralCallback, guiGeneralResize)
	guiBillboardEquator.min, guiBillboardEquator.max = 2, 64
	guiBillboardEquator.value = Prefs['Billboard']['Equator']
	guiBillboardPolar = Common_Gui.NumberPicker("guiBillboardPolar", "Polar", "Number of images around the polar", 14, guiGeneralCallback, guiGeneralResize)
	guiBillboardPolar.min, guiBillboardPolar.max = 3, 64
	guiBillboardPolar.value = Prefs['Billboard']['Polar']
	guiBillboardPolarAngle = Common_Gui.NumberSlider("guiBillboardPolarAngle", "Polar Angle", "Angle to take polar images at", 15, guiGeneralCallback, guiGeneralResize)
	guiBillboardPolarAngle.min, guiBillboardPolarAngle.max = 0.0, 45.0
	guiBillboardPolarAngle.value = Prefs['Billboard']['PolarAngle']
	guiBillboardDim = Common_Gui.NumberPicker("guiBillboardDim", "Dim", "Dimensions of billboard images", 16, guiGeneralCallback, guiGeneralResize)
	guiBillboardDim.min, guiBillboardDim.max = 16, 128
	guiBillboardDim.value = Prefs['Billboard']['Dim']
	guiBillboardPoles = Common_Gui.ToggleButton("guiBillboardPoles", "Poles", "Take images at the poles", 17, guiGeneralCallback, guiGeneralResize)
	guiBillboardPoles.state = Prefs['Billboard']['IncludePoles']
	guiBillboardSize = Common_Gui.NumberSlider("guiBillboardSize", "Size", "Size of billboard's detail level", 18, guiGeneralCallback, guiGeneralResize)
	guiBillboardSize.min, guiBillboardSize.max = 0.0, 128.0
	guiBillboardSize.value = Prefs['Billboard']['Size']
	# --
	guiOutputText = Common_Gui.SimpleText("guiOutputText", "Output", None, guiGeneralResize)
	guiShapeScriptButton =  Common_Gui.ToggleButton("guiShapeScriptButton", "Write Shape Script", "Write .cs script that details the .dts and all .dsq sequences", 19, guiGeneralCallback, guiGeneralResize)
	guiCustomFilename = Common_Gui.TextBox("guiCustomFilename", "Filename: ", "Filename to write to", 20, guiGeneralCallback, guiGeneralResize)
	guiCustomFilename.length = 255
	if "\\" in Prefs['exportBasepath']:
		pathSep = "\\"
	else:
		pathSep = "/"
	guiCustomFilename.value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename'] + ".dts"
	guiCustomFilenameSelect = Common_Gui.BasicButton("guiCustomFilenameSelect", "Select...", "Select a filename and destination for export", 21, guiGeneralCallback, guiGeneralResize)
	guiCustomFilenameDefaults = Common_Gui.BasicButton("guiCustomFilenameDefaults", "Default", "Reset filename and destination to defaults", 22, guiGeneralCallback, guiGeneralResize)
	
	
	guiTSEMaterial = Common_Gui.ToggleButton("guiTSEMaterial", "Write TSE Materials", "Write materials and scripts geared for TSE", 24, guiGeneralCallback, guiGeneralResize)
	guiTSEMaterial.state = Prefs['TSEMaterial']
	guiLogToOutputFolder = Common_Gui.ToggleButton("guiLogToOutputFolder", "Log to Output Folder", "Write Log file to .DTS output folder", 25, guiGeneralCallback, guiGeneralResize)
	
	# About tab controls
	guiAboutText = Common_Gui.MultilineText("guiAboutText", 
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
	guiSeqActSubtab = Common_Gui.TabContainer("guiSeqActSubtab", None, guiSeqActButton, None, guiBaseResize)
	guiSeqActSubtab.fade_mode = 1
	guiSeqActSubtab.enabled, guiSeqActSubtab.visible = True, True
	guiSequenceIFLSubtab = Common_Gui.TabContainer("guiSequenceIFLSubtab", None, guiSequenceIFLButton, None, guiBaseResize)
	guiSequenceIFLSubtab.fade_mode = 1
	guiSequenceIFLSubtab.enabled, guiSequenceIFLSubtab.visible = False, False
	guiSequenceVisibilitySubtab = Common_Gui.TabContainer("guiSequenceVisibilitySubtab", None, guiSequenceVisibilityButton, None, guiBaseResize)
	guiSequenceVisibilitySubtab.fade_mode = 1
	guiSequenceUVSubtab = Common_Gui.TabContainer("guiSequenceUVSubtab", None, guiSequenceUVButton, None, guiBaseResize)
	guiSequenceUVSubtab.fade_mode = 1
	guiSequenceMorphSubtab = Common_Gui.TabContainer("guiSequenceMorphSubtab", None, guiSequenceMorphButton, None, guiBaseResize)
	guiSequenceMorphSubtab.fade_mode = 1
	guiMaterialsSubtab = Common_Gui.BasicContainer("guiMaterialsSubtab", None, None, guiBaseResize)
	guiMaterialsSubtab.fade_mode = 1
	guiMaterialsSubtab.borderColor = [0,0,0,0]

	
	guiGeneralSubtab = Common_Gui.BasicContainer("guiGeneralSubtab", None, None, guiBaseResize)
	guiGeneralSubtab.fade_mode = 1
	guiArmatureSubtab = Common_Gui.BasicContainer("guiArmatureSubtab", None, None, guiBaseResize)
	guiArmatureSubtab.fade_mode = 1
	guiAboutSubtab = Common_Gui.BasicContainer("guiAboutSubtab", None, None, guiBaseResize)
	guiAboutSubtab.fade_mode = 1
	#guiSequenceNLASubtab = Common_Gui.BasicContainer("guiSequenceNLASubtab", None, None, guiBaseResize)
	#guiSeqActSubtab.fade_mode = 1
	
	# Add all controls to respective containers
	
	guiHeaderBar.addControl(guiHeaderText)
	guiHeaderBar.addControl(guiVersionText)
	
	Common_Gui.addGuiControl(guiTabBar)
	guiTabBar.addControl(guiHeaderBar) # Here to get the blend from panel color
	guiTabBar.addControl(guiSequenceButton)
	guiTabBar.addControl(guiArmatureButton)
	guiTabBar.addControl(guiMaterialsButton)
	guiTabBar.addControl(guiMeshButton)
	
	guiTabBar.addControl(guiAboutButton)
	guiTabBar.addControl(guiExportButton)
	
		
	Common_Gui.addGuiControl(guiSequenceTab)
	guiSequenceTab.borderColor = [0,0,0,0]
	guiSequenceTab.addControl(guiSeqActSubtab)
	guiSequenceTab.addControl(guiSequenceIFLSubtab)
	guiSequenceTab.addControl(guiSequenceVisibilitySubtab)
	guiSequenceTab.addControl(guiSequenceUVSubtab)
	guiSequenceTab.addControl(guiSequenceMorphSubtab)
	
	guiMaterialsTab.addControl(guiMaterialsSubtab)
	
	guiSequenceTab.addControl(guiSequencesTabBar)
	guiSequencesTabBar.addControl(guiSeqActButton)
	guiSequencesTabBar.addControl(guiSequenceIFLButton)
	guiSequencesTabBar.addControl(guiSequenceVisibilityButton)
	guiSequencesTabBar.addControl(guiSequenceUVButton)
	guiSequencesTabBar.addControl(guiSequenceMorphButton)

	#guiSequenceVisibilityButton, guiSequenceUVButton, guiSequenceMorphButton

	guiSeqActSubtab.borderColor = [0,0,0,0]
	guiSequenceIFLSubtab.borderColor = [0,0,0,0]
	guiSequenceVisibilitySubtab.borderColor = [0,0,0,0]
	guiSequenceUVSubtab.borderColor = [0,0,0,0]
	guiSequenceMorphSubtab.borderColor = [0,0,0,0]

	
	Common_Gui.addGuiControl(guiArmatureTab)
	guiArmatureTab.borderColor = [0,0,0,0]
	guiArmatureTab.addControl(guiArmatureSubtab)
	guiArmatureSubtab.borderColor = [0,0,0,0]
	
	guiArmatureSubtab.addControl(guiBoneText)
	guiArmatureSubtab.addControl(guiBoneList)
	guiArmatureSubtab.addControl(guiBoneMatchText)
	guiArmatureSubtab.addControl(guiBonePatternText)
	guiArmatureSubtab.addControl(guiBonePatternOnButton)
	guiArmatureSubtab.addControl(guiBonePatternOffButton)
	guiArmatureSubtab.addControl(guiBoneRefreshButton)

	populateBoneGrid()
	
	Common_Gui.addGuiControl(guiMaterialsTab)
	
	#populateMaterialList()
	
	Common_Gui.addGuiControl(guiGeneralTab)
	guiGeneralTab.borderColor = [0,0,0,0]
	guiGeneralTab.addControl(guiGeneralSubtab)
	guiGeneralSubtab.borderColor = [0,0,0,0]
	
	guiGeneralSubtab.addControl(guiStripText)
	guiGeneralSubtab.addControl(guiTriMeshesButton)
	guiGeneralSubtab.addControl(guiTriListsButton)
	guiGeneralSubtab.addControl(guiStripMeshesButton)	
	guiGeneralSubtab.addControl(guiMaxStripSizeSlider)
	guiGeneralSubtab.addControl(guiClusterText)
	guiGeneralSubtab.addControl(guiClusterDepth)
	guiGeneralSubtab.addControl(guiClusterWriteDepth)
	guiGeneralSubtab.addControl(guiBillboardText)
	guiGeneralSubtab.addControl(guiBillboardButton)
	guiGeneralSubtab.addControl(guiBillboardEquator)
	guiGeneralSubtab.addControl(guiBillboardPolar)
	guiGeneralSubtab.addControl(guiBillboardPolarAngle)
	guiGeneralSubtab.addControl(guiBillboardDim)
	guiGeneralSubtab.addControl(guiBillboardPoles)
	guiGeneralSubtab.addControl(guiBillboardSize)
	guiGeneralSubtab.addControl(guiOutputText)
	guiGeneralSubtab.addControl(guiShapeScriptButton)
	guiGeneralSubtab.addControl(guiCustomFilename)
	guiGeneralSubtab.addControl(guiCustomFilenameSelect)
	guiGeneralSubtab.addControl(guiCustomFilenameDefaults)
	guiGeneralSubtab.addControl(guiTSEMaterial)
	guiGeneralSubtab.addControl(guiLogToOutputFolder)
	try: guiLogToOutputFolder.state = Prefs['LogToOutputFolder']
	except:
		Prefs['LogToOutputFolder'] = True
		guiLogToOutputFolder.state = True
	Common_Gui.addGuiControl(guiAboutTab)
	guiAboutTab.borderColor = [0,0,0,0]
	guiAboutTab.addControl(guiAboutSubtab)
	guiAboutSubtab.borderColor = [0,0,0,0]
	guiAboutSubtab.addControl(guiAboutText)

	# testing	
	IFLControls = IFLControlsClass()
	ActionControls = ActionControlsClass()
	MaterialControls = MaterialControlsClass()
	

# Called when gui exits
def exit_callback():
	global IFLControls
	Torque_Util.dump_setout("stdout")
	clearSequenceActionList()
	clearBoneGrid()
	print IFLControls
	IFLControls.cleanup()
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
