#!BPY

"""
Name: 'Torque Shape (.dts)...'
Blender: 233
Group: 'Export'
Submenu: 'Export' export
Submenu: 'Configure' config
Tooltip: 'Export to Torque (.dts) format.'
"""

'''
Dts_Blender.pyguiMeshTab

Copyright (c) 2003 - 2005 James Urquhart(j_urquhart@btinternet.com)

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

import DtsShape_Blender
from DtsShape_Blender import *


'''
  Blender Exporter For Torque
-------------------------------
  Blender Dts Classes for Python
'''

Version = "0.9"
Prefs = None
export_tree = None
Debug = True

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
	return string.join(words[:-1], sep) + sep

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
	for child in obj_children:
		obj_children += getAllChildren(child)
	return obj_children

'''
	Preferences Code
'''
#-------------------------------------------------------------------------------------------------

# Saves preferences
def savePrefs():
	global Prefs
	Registry.SetKey('TORQUEEXPORTER', Prefs)
	saveTextPrefs()

# Saves preferences to a text buffer
def saveTextPrefs():
	global Prefs
	# We need a blank buffer
	try: text_doc = Text.Get("TORQUEEXPORTER_CONF")
	except: text_doc = Text.New("TORQUEEXPORTER_CONF")
	text_doc.clear()

	text_doc.write("Version %f\n" % Prefs['Version'])
	text_doc.write("{\n")
	text_doc.write("DTSVersion %d\n" % Prefs['DTSVersion'])
	text_doc.write("WriteShapeScript %d\n" % Prefs['WriteShapeScript'])
	for seq in Prefs['Sequences'].keys():
		text_doc.write("Sequence \"%s\"\n" % seq)
		text_doc.write("{\n")
		text_doc.write("Dsq %d\n" % Prefs['Sequences'][seq]['Dsq'])
		text_doc.write("Cyclic %d\n" % Prefs['Sequences'][seq]['Cyclic'])
		text_doc.write("Blend %d\n" % Prefs['Sequences'][seq]['Blend'])
		text_doc.write("NoExport %d\n" % Prefs['Sequences'][seq]['NoExport'])
		text_doc.write("Interpolate %d\n" % Prefs['Sequences'][seq]['Interpolate'])
		text_doc.write("NumGroundFrames %d\n" % Prefs['Sequences'][seq]['NumGroundFrames'])
		text_doc.write("Triggers %d\n" % len(Prefs['Sequences'][seq]['Triggers']))
		text_doc.write("{\n")
		for trig in Prefs['Sequences'][seq]['Triggers']:
			text_doc.write("Value %d\n" % trig[0])
			text_doc.write("Time %f\n" % trig[1])
		text_doc.write("}\n")
		text_doc.write("}\n")
	text_doc.write("StripMeshes %d\n" % Prefs['StripMeshes'])
	text_doc.write("MaxStripSize %d\n" % Prefs['MaxStripSize'])
	text_doc.write("WriteSequences %d\n" % Prefs['WriteSequences'])
	text_doc.write("ClusterDepth %d\n" % Prefs['ClusterDepth'])
	text_doc.write("AlwaysWriteDepth %d\n" % Prefs['AlwaysWriteDepth'])
	text_doc.write("Billboard %d\n" % Prefs['Billboard']['Enabled'])
	if Prefs['Billboard']['Enabled']:
		text_doc.write("{\n")
		text_doc.write("Equator %d\n" % Prefs['Billboard']['Equator'])
		text_doc.write("Polar %d\n" % Prefs['Billboard']['Polar'])
		text_doc.write("PolarAngle %f\n" % Prefs['Billboard']['PolarAngle'])
		text_doc.write("Dim %d\n" % Prefs['Billboard']['Dim'])
		text_doc.write("IncludePoles %d\n" % Prefs['Billboard']['IncludePoles'])
		text_doc.write("Size %d\n" % Prefs['Billboard']['Size'])
		text_doc.write("}\n")
	text_doc.write("}\n")

# Loads preferences from a text buffer
def loadTextPrefs(Prefs):
	try: text_doc = Text.Get("TORQUEEXPORTER_CONF")
	except: return Prefs

	cur_parse = 0

	text_arr = array('c')
	txt = ""
	lines = text_doc.asLines()
	for l in lines: txt += "%s\n" % l
	text_arr.fromstring(txt)

	tok = Tokenizer(text_arr)
	while tok.advanceToken(True):
		cur_token = tok.getToken()
		if cur_token == "Version":
			tok.advanceToken(False)
			if float(tok.getToken()) > 0.2:
				Torque_Util.dump_writeln("   Warning : Loading different version config file than is supported")
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
				elif cur_token == "StripMeshes":
					tok.advanceToken(False)
					Prefs['StripMeshes'] = int(tok.getToken())
				elif cur_token == "MaxStripSize":
					tok.advanceToken(False)
					Prefs['MaxStripSize'] = int(tok.getToken())
				elif cur_token == "UseStickyCoords": tok.advanceToken(False)
				elif cur_token == "WriteSequences":
					tok.advanceToken(False)
					Prefs['WriteSequences'] = int(tok.getToken())
				elif cur_token == "ClusterDepth":
					tok.advanceToken(False)
					Prefs['ClusterDepth'] = int(tok.getToken())
				elif cur_token == "AlwaysWriteDepth":
					tok.advanceToken(False)
					Prefs['AlwaysWriteDepth"'] = int(tok.getToken())
				elif cur_token == "Billboard":
					tok.advanceToken(False)
					Prefs['Billboard']['Enabled'] = int(tok.getToken())
					if int(tok.getToken()):
						cur_parse = 2
				elif cur_token == "Sequence":
					tok.advanceToken(False)
					seq_name = tok.getToken()
					Prefs['Sequences'][seq_name] = {'Dsq' : False, 'Cyclic' : False, 'Blend' : False, 'Triggers' : [], 'Interpolate' : 0, 'NoExport' : False, 'NumGroundFrames' : 0}
					cur_parse = 3
				elif cur_token == "NoExport":
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
							Prefs['Billboard']['IncludePoles'] = int(tok.getToken())
						elif cur_token == "Size":
							tok.advanceToken(False)
							Prefs['Billboard']['Size'] = int(tok.getToken())
						elif cur_token == "}":
							break
						else:
							Torque_Util.dump_writeln("   Unrecognised Billboard token : %s" % cur_token)
					cur_parse = 1
				elif (cur_token == "{") and (cur_parse == 3):
					# Parse Sequence Section
					while tok.advanceToken(True):
						cur_token = tok.getToken()
						if cur_token == "Dsq":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['Dsq'] = int(tok.getToken())
						elif cur_token == "Cyclic":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['Cyclic'] = int(tok.getToken())
						elif cur_token == "Blend":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['Blend'] = int(tok.getToken())
						elif (cur_token == "Interpolate_Count") or (cur_token == "Interpolate"):
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['Interpolate'] = int(tok.getToken())
						elif cur_token == "NoExport":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['NoExport'] = int(tok.getToken())
						elif cur_token == "NumGroundFrames":
							tok.advanceToken(False)
							Prefs['Sequences'][seq_name]['NumGroundFrames'] = int(tok.getToken())
						elif cur_token == "Triggers":
							tok.advanceToken(False)
							triggers_left = int(tok.getToken())
							for t in range(0, triggers_left): Prefs['Sequences'][seq_name]['Triggers'].append([0,0.0])
							while tok.advanceToken(True):
								cur_token = tok.getToken()
								if cur_token == "Value":
									tok.advanceToken(False)
									Prefs['Sequences'][seq_name]['Triggers'][-triggers_left][0] = int(tok.getToken())
								elif cur_token == "Time":
									tok.advanceToken(False)
									Prefs['Sequences'][seq_name]['Triggers'][-triggers_left][1] = float(tok.getToken())
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
				elif cur_token == "}":
					cur_parse = 0
					break
				else:
					Torque_Util.dump_writeln("   Unrecognised token : %s" % cur_token)
		else:
			Torque_Util.dump_writeln("   Warning : Unexpected token %s!" % cur_token)
	return Prefs

def initPrefs():
	Prefs = {}
	Prefs['Version'] = 0.2 # NOTE: change version if anything *major* is changed.
	Prefs['DTSVersion'] = 24
	Prefs['WriteShapeScript'] = False
	Prefs['Sequences'] = {}
	Prefs['StripMeshes'] = False
	Prefs['MaxStripSize'] = 6
	Prefs['WriteSequences'] = True
	Prefs['ClusterDepth'] = 1
	Prefs['AlwaysWriteDepth'] = False
	Prefs['Billboard'] = {'Enabled' : False,'Equator' : 10,'Polar' : 10,'PolarAngle' : 25,'Dim' : 64,'IncludePoles' : True, 'Size' : 20.0}
	Prefs['BannedBones'] = []
	return Prefs

# Loads preferences
def loadPrefs():
	global Prefs
	Prefs = Registry.GetKey('TORQUEEXPORTER%s' % basename(Blender.Get("filename")))
	if not Prefs:
		# Could be saved?
		Prefs = loadTextPrefs(initPrefs())
		Torque_Util.dump_writeln("Loaded Preferences.")
		# Save prefs
		savePrefs()

dummySequence = {'Dsq' : False, 'Cyclic' : False, 'Blend' : False, 'Triggers' : [], 'Interpolate' : 0, 'NoExport' : False, 'NumGroundFrames' : 0}

# Gets a sequence key from the preferences
# Creates default if key does not exist
def getSequenceKey(value):
	global Prefs, dummySequence
	if value == "N/A": return dummySequence
	try:
		return Prefs['Sequences'][value]
	except KeyError:
		Prefs['Sequences'][value] = {'Dsq' : False, 'Cyclic' : False, 'Blend' : False, 'Triggers' : [], 'Interpolate' : 0, 'NoExport' : False, 'NumGroundFrames' : 0}
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
		if tname.upper() == "SHAPE":
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
		elif (tname[0:3].upper() == "LOS") or (tname[0:20].upper() == "LINEOFSIGHTCOLLISION"):
			self.losCollisionMeshes.append(obj)
			if tname[0:20].upper() == "LINEOFSIGHTCOLLISION":
				Torque_Util.dump_writeln("Warning: 'LOS' designation for los collision node deprecated, use 'LINEOFSIGHTCOLLISION' instead.")
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
		
			Stream = DtsStream(Prefs['exportBasepath'] + Prefs['exportBasename'] + ".dts", False, Prefs['DTSVersion'])
			Torque_Util.dump_writeln("Writing shape to  '%s'." % (Prefs['exportBasepath'] + Prefs['exportBasename'] + ".dts"))
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
									if arm.getData().getName() == child.getData().getName():
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
								print "Unhandled: %s" % child.getType()
								progressBar.update()
								continue
								
						meshDetails.append(meshList)
					
					# Now we can add it in order
					for arm in armatures:
						self.Shape.addArmature(arm)
						progressBar.update()
						
					for n in nodes:
						self.Shape.addNode(n)
						progressBar.update()
						
					for i in range(0, len(self.normalDetails)):
						self.Shape.addDetailLevel(meshDetails[i], self.normalDetails[i][0])
						progressBar.update()
					for marker in self.collisionMeshes:
						meshes = getAllChildren(marker)
						for mesh in meshes: self.Shape.addCollisionMesh(mesh, False)
						progressBar.update()					
					for marker in self.losCollisionMeshes:
						meshes = getAllChildren(marker)
						for mesh in meshes: self.Shape.addCollisionMesh(mesh, True)
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
						self.Shape.detaillevels.insert(self.numDetails,detail)
					
					progressBar.popTask()
					
				# Finalize static meshes, do triangle strips
				self.Shape.finalizeObjects()
				if Prefs['StripMeshes']:
					self.Shape.stripMeshes(Prefs['MaxStripSize'])

				# Add all actions (will ignore ones not belonging to shape)
				if Prefs['WriteSequences']:
					scene = Blender.Scene.getCurrent()
					context = scene.getRenderingContext()
					actions = Armature.NLA.GetActions()
					
					if len(actions.keys()) > 0:
						progressBar.pushTask("Adding Actions..." , len(actions.keys()), 0.6)
						for action_name in actions.keys():
							if getSequenceKey(action_name)['NoExport']:
								progressBar.update()
								continue # Skip
							
							self.Shape.addAction(actions[action_name], scene, context, getSequenceKey(action_name))
							progressBar.update()
						
						progressBar.popTask()

				# Final stuff
				progressBar.pushTask("Finalizing shape..." , 2, 0.8)
				self.Shape.finalize()
				progressBar.update()
				
				Torque_Util.dump_writeln("> Shape Details")
				self.Shape.dumpShapeInfo()
				progressBar.update()
				progressBar.popTask()

				# Now we've finished, we can save shape and burn it.
				progressBar.pushTask("Writing out DTS...", 1, 0.9)
				Torque_Util.dump_writeln("Writing out DTS...")
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
			Torque_Util.dump_setout("stdout")
			if self.Shape: del self.Shape
			progressBar.popTask()
			if Debug: raise

	# Handles the whole branch
	def handleObject(self):
		global Prefs
		self.clear() # clear just in case we already have children

		# Firstly, it would be nice to know all the paths and filenames (for reuse later)
		Prefs['exportBasename'] = basename(Blender.Get("filename"))
		Prefs['exportBasepath'] = basepath(Blender.Get("filename"))

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
	export_tree = SceneTree(None,Blender.Scene.getCurrent())
	Torque_Util.dump_writeln("Cleaning Preference Keys")
	cleanKeys()

def export():
	Torque_Util.dump_writeln("Exporting...")
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

'''
	Gui Handling Code
'''
#-------------------------------------------------------------------------------------------------

'''
	Menu Handlers
'''
def getDetailMenu():
	details = []
	for o in export_tree.children:
		if o.__class__ == ShapeTree:
			for c in o.children:
				if c.getName()[0:6] == "Detail": details.append(c.getName())
			break
	return Blender_Gui.makeMenu("Details",details)

def getSequenceMenu():
	sequences = []
	for a in Armature.NLA.GetActions().keys():
		sequences.append(a)
	if len(sequences) == 0: sequences.append("N/A")
	return Blender_Gui.makeMenu("Sequences",sequences)

def getSequenceTriggers(sequence):
	global Prefs
	try:
		trigger_list = []
		for t in getSequenceKey(sequence)['Triggers']:
			trigger_list.append("(%d,%f)" % (t[0],t[1]))
		if len(trigger_list) == 0: return ["N/A"]
		return trigger_list
	except KeyError:
		return ["N/A"]

def getSequenceTriggerMenu():
	global Sequence_ID
	seq_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][0]['items'][1]['instance'].val
	if len(Armature.NLA.GetActions().keys()) > seq_val:
		seq_id = Armature.NLA.GetActions().keys()[seq_val]
		return Blender_Gui.makeMenu("Triggers",getSequenceTriggers(seq_id))
	else: return Blender_Gui.makeMenu("Triggers",["N/A"])

'''
	Gui Init Code
'''

'''
	The Gui code needs to alter the following preferences:
		Dts Version (Prefs['DTSVersion']) 24-25
		Prefs['Sequences']: (One tab)
			Seq['DSQ'] (bool)
			Seq['Cyclic'] (bool)
			Seq['Blend'] (bool)
			Seq['NoExport'] (bool)
			Seq['Interpolate'] (bool)
			Seq['NumGroundFrames'] (0-numFrames)
			Seq['Triggers']:
				Value (-30-30)
				Time (0-endTime)
		Global Properties: (one tab)
			Prefs['StripMeshes']
			Prefs['MaxStripSize']
			Prefs['WriteSequences']
			Sort options: (grouped)
				Prefs['ClusterDepth']
				Prefs['AlwaysWriteDepth']
			Prefs['Billboard']: (hidden, bool)
				Billboard['Equator'] (2-64)
				Billboard['Polar'] (3-64)
				Billboard['PolarAngle'] (0-0.45)
				Billboard['Dim'] (16-128)
				Billboard['IncludePoles'] (bool)
				Billboard['Size'] (1.0-128.0)
		Prefs[''] (One tab)
	It also needs the following extra things:
		About Button
		Exit Button
		Title
		Version (Prefs['Version'])
'''

# Controls referenced in functions
guiSequenceTab, guiMeshTab, guiAboutTab, guiTabBar, guiHeaderTab = None, None, None, None, None

def guiBaseCallback(control):
	global guiSequenceTab, guiMeshTab, guiAboutTab
	if control.evt == 1:
		guiSequenceTab.visible = True
		guiMeshTab.visible = False
		guiAboutTab.visible = False
		guiSequenceTab.enabled = True
		guiMeshTab.enabled = False
		guiAboutTab.enabled = False
	elif control.evt == 2:
		guiSequenceTab.visible = False
		guiMeshTab.visible = True
		guiAboutTab.visible = False
		guiSequenceTab.enabled = False
		guiMeshTab.enabled = True
		guiAboutTab.enabled = False
	elif control.evt == 3:
		export()
	elif control.evt == 4:
		guiSequenceTab.visible = False
		guiMeshTab.visible = False
		guiAboutTab.visible = True
		guiSequenceTab.enabled = False
		guiMeshTab.enabled = False
		guiAboutTab.enabled = True
		
def guiSequenceCallback(control):
	pass

def guiMeshCallback(control):
	pass

def guiAboutCallback(control):
	pass

def guiBaseResize(control, newwidth, newheight):
	global guiSequenceTab, guiMeshTab, guiAboutTab, guiTabBar, guiHeaderTab
	
	if control.evt == None:
		if control.name == "tabs":
			control.x = 0
			control.y = 335
			control.width = 490
			control.height = 35
		elif (control.name == "content.sequence") or (control.name == "content.shape") or (control.name == "content.about"):
			control.x = 0
			control.y = 0
			control.width = 490
			control.height = 335
		elif control.name == "header":
			control.x = 0
			control.y = 370
			control.width = 490
			control.height = 20
		elif control.name == "tabs.version":
			control.x = newwidth-80
			control.y = 10
	elif control.evt == 1:
		control.x = 10
		control.y = 5
		control.width = 70
		control.height = 20
	elif control.evt == 2:
		control.x = 85
		control.y = 5
		control.width = 70
		control.height = 20
	elif control.evt == 3:
		control.x = 160
		control.y = 5
		control.width = 70
		control.height = 20
	elif control.evt == 4:
		control.x = 235
		control.y = 5
		control.width = 70
		control.height = 20

def guiSequenceResize(control, newwidth, newheight):
	if control.evt == None:
		pass
	elif control.evt == 9:
		control.x = 10
		control.width = 110
		control.y = newheight - 140 - control.height
	pass

def guiMeshResize(control, newwidth, newheight):
	if control.evt == None:
		if control.name == "shape.strip":
			control.x = 10
			control.y = newheight - 20
		elif control.name == "shape.cluster":
			control.x = 10
			control.y = newheight - 70
	elif control.evt == 5:
		control.x = 10
		control.y = newheight - 30 - control.height
		control.width = 50
	elif control.evt == 6:
		control.x = 62
		control.y = newheight - 30 - control.height
		control.width = 180
	elif control.evt == 7:
		control.x = 10
		control.y = newheight - 80 - control.height
		control.width = 80
	elif control.evt == 8:
		control.x = 92
		control.y = newheight - 80 - control.height
		control.width = 180
	pass

def guiAboutResize(control, newwidth, newheight):
	if control.evt == None:
		if control.name == "about.text":
			control.x = 10
			control.y = 100
	pass

def initGui():
	global Version
	global guiSequenceTab, guiMeshTab, guiAboutTab, guiTabBar, guiHeaderTab
	global Prefs
		
	Common_Gui.initGui(exit_callback)
	
	# Main tab controls
	guiSequenceButton = Common_Gui.BasicButton("Sequence", "Sequence Options", 1, guiBaseCallback, guiBaseResize)
	guiMeshButton = Common_Gui.BasicButton("Mesh", "Mesh Options", 2, guiBaseCallback, guiBaseResize)
	guiExportButton = Common_Gui.BasicButton("Export", "Export .dts shape", 3, guiBaseCallback, guiBaseResize)
	guiAboutButton = Common_Gui.BasicButton("About", "About", 4, guiBaseCallback, guiBaseResize)
	guiVersionText = Common_Gui.SimpleText("tabs.version", "Version %s" % Version, None, guiBaseResize)

	# Sequence tabe controls
	guiWriteSequencesButton = Common_Gui.ToggleButton("Export Sequences", "Allow export of sequences", 5, guiSequenceCallback, guiSequenceResize)
	guiWriteSequencesButton.state = Prefs['WriteSequences']
	
	# Shape tab controls
	guiStripText = Common_Gui.SimpleText("shape.strip", "Triangle Stripping", None, guiMeshResize)
	guiStripMeshesButton = Common_Gui.ToggleButton("Enable", "Generate triangle strips for meshes", 5, guiMeshCallback, guiMeshResize)
	guiStripMeshesButton.state = Prefs['StripMeshes']
	guiMaxStripSizeSlider = Common_Gui.NumberSlider("Strip Size ", "Maximum size of generated triangle strips", 6, guiMeshCallback, guiMeshResize)
	guiMaxStripSizeSlider.min, guiMaxStripSizeSlider.max = 3, 30
	guiMaxStripSizeSlider.value = Prefs['MaxStripSize']
	guiClusterText = Common_Gui.SimpleText("shape.cluster", "Cluster Mesh", None, guiMeshResize)
	guiClusterDepthButton = Common_Gui.ToggleButton("Write Depth ", "Always Write the Depth on Cluster meshes", 7, guiMeshCallback, guiMeshResize)
	guiClusterDepthSlider = Common_Gui.NumberSlider("Depth", "Maximum depth Clusters meshes should be calculated to", 8, guiMeshCallback, guiMeshResize)
	guiClusterDepthSlider.min, guiClusterDepthSlider.max = 3, 30
	guiClusterDepthButton.state = Prefs['AlwaysWriteDepth']
	
	# About tab controls
	guiAboutText = Common_Gui.SimpleText("about.text", "Foo\nGoo\nWoo", None, guiAboutResize)
	
	# Container Controls
	guiHeaderBar = Common_Gui.BasicContainer("header", None, guiBaseResize)
	guiTabBar = Common_Gui.BasicContainer("tabs", None, guiBaseResize)
	guiTabBar.fade_mode = 2
	guiTabBar.borderColor = None
	guiSequenceTab = Common_Gui.BasicContainer("content.sequence", None, guiBaseResize)
	guiSequenceTab.borderColor = None
	guiSequenceTab.enabled, guiSequenceTab.visible = True, True
	guiMeshTab = Common_Gui.BasicContainer("content.shape", None, guiBaseResize)
	guiMeshTab.borderColor = None
	guiMeshTab.enabled, guiMeshTab.visible = False, False
	guiAboutTab = Common_Gui.BasicContainer("content.about", None, guiBaseResize)
	guiAboutTab.borderColor = None
	guiAboutTab.enabled, guiAboutTab.visible = False, False
	
	# Add all controls to respective containers
	
	Common_Gui.addGuiControl(guiHeaderBar)
	
	Common_Gui.addGuiControl(guiTabBar)
	guiTabBar.addControl(guiSequenceButton)
	guiTabBar.addControl(guiMeshButton)
	guiTabBar.addControl(guiExportButton)
	guiTabBar.addControl(guiAboutButton)
	guiTabBar.addControl(guiVersionText)
	
	Common_Gui.addGuiControl(guiSequenceTab)
	guiSequenceTab.addControl(guiWriteSequencesButton)
	
	Common_Gui.addGuiControl(guiMeshTab)
	guiMeshTab.addControl(guiStripText)
	guiMeshTab.addControl(guiStripMeshesButton)
	guiMeshTab.addControl(guiMaxStripSizeSlider)
	guiMeshTab.addControl(guiClusterText)
	guiMeshTab.addControl(guiClusterDepthSlider)
	guiMeshTab.addControl(guiClusterDepthButton)
	
	#Prefs['Billboard']: (hidden, bool)
	#	Billboard['Equator'] (2-64)
	#	Billboard['Polar'] (3-64)
	#	Billboard['PolarAngle'] (0-0.45)
	#	Billboard['Dim'] (16-128)
	#	Billboard['IncludePoles'] (bool)
	#	Billboard['Size'] (1.0-128.0)

	Common_Gui.addGuiControl(guiAboutTab)
	guiAboutTab.addControl(guiAboutText)
	
	'''
	TopSharedBar=[	{
							'type' : 'CONTAINER',
							'x' : 0, 'y' : 200, 'w' : 490, 'h' : 20,
							'color_in' : shared_bar_end, 'color_out' : shared_bar_int, 'fade_mode' : 2,
							'color_border' : shared_border_col, 'visible' : True,
							'items' : [
								{
									'type' : 'TEXT',
									'x' : 10, 'y' : 5, 'color' : [1.,1.,1.],
									'value' : "Torque Exporter", 'size' : "normal", 'visible' : True,
								}
							]
						}
					]

	SequenceSheet = SharedBar + TopSharedBar + [
						{
							'type' : 'CONTAINER',
							'x' : 0, 'y' : 30, 'w' : 490, 'h' : 170,
							'color_in' : [0.75,0.75,0.75], 'color_out' : [0.5,0.5,0.5], 'fade_mode' : 0,
							'color_border' : shared_border_col, 'visible' : True,
							'items' : [
								# Per-Sequence options
								{
								'type' : 'CONTAINER',
								'x' : 0, 'y' : 110, 'w' : 350, 'h' : 60,
								'color_in' : shared_bar_int, 'fade_mode' : 0,
								'color_border' : shared_border_col, 'visible' : True,
								'items' : [
									{
										'type' : 'TEXT',
										'x' : 10, 'y' : 40, 'color' : [1.,1.,1.],
										'value' : "Sequences", 'size' : "normal", 'visible' : True,
									},
									{
										'type' : 'MENU', 'event' : 50,
										'x' : 10, 'y' : 10, 'w' : 152 , 'h' : 20,
										'items' : getSequenceMenu, 'value' : 0, 'visible' : True, 'instance' : None,
									},
									]
								},
								{
								'type' : 'CONTAINER',
								'x' : 10, 'y' : 0, 'w' : 180, 'h' : 109,
								'color_in' : shared_bar_int, 'color_out' : shared_bar_end,'fade_mode' : 0,
								'color_border' : None, 'visible' : True,
								'items' : [
									{
										'type' : 'TOGGLE', 'event' : 6,
										'x' : 0, 'y' : 42, 'w' : 86, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "DSQ", 'tooltip' : "Write DSQ instead of storing sequence in Shape", 'value' : 1
									},
									{
										'type' : 'TOGGLE', 'event' : 7,
										'x' : 88, 'y' : 42, 'w' : 86, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "Cyclic", 'tooltip' : "Make animation cyclic. Will also ignore duplicate start-end frames.", 'value' : 2
									},
									{
										'type' : 'TOGGLE', 'event' : 16,
										'x' : 88, 'y' : 25, 'w' : 86, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "Blend", 'tooltip' : "Make animation a blend (relative to root)", 'value' : 3
									},
									# Additional Sequence Options (Ground Frames, Interpolation)
									{
										'type' : 'SLIDER', 'event' : 18,
										'x' : 0, 'y' : 86, 'w' : 175 , 'h' : 20, 'tooltip' : "Amount of ground frames to export. 0 if no ground frames",
										'name' : "#GRND Fr ", 'min' : 0, 'max' : 50, 'value' : 10, 'visible' : True, 'instance' : None,
									},
									{
										'type' : 'TOGGLE', 'event' : 20,
										'x' : 0, 'y' : 64, 'w' : 175 , 'h' : 20, 'tooltip' : "Should we grab the whole set of frames for the animation, or just the keyframes?",
										'name' : "Interpolate Frames", 'min' : 0, 'max' : 100, 'value' : 12, 'visible' : True, 'instance' : None,
									},
									{
										'type' : 'TOGGLE', 'event' : 21,
										'x' : 0, 'y' : 25, 'w' : 86, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "No Export", 'tooltip' : "Don't Export this Sequence", 'value' : 13
									},
									]
								},
								# Sequence Trigger Options
								{
								'type' : 'CONTAINER',
								'x' : 207, 'y' : 0, 'w' : 131, 'h' : 109,
								'color_in' : shared_bar_int, 'color_out' : shared_bar_end, 'fade_mode' : 0,
								'color_border' : None, 'visible' : True,
								'items' : [
									{
										'type' : 'TEXT',
										'x' : 0, 'y' : 94, 'color' : [1.,1.,1.],
										'value' : "Triggers", 'size' : "normal", 'visible' : True,
									},
									{
										'type' : 'MENU', 'event' : 60,
										'x' : 0, 'y' : 64, 'w' : 130 , 'h' : 20,
										'items' : getSequenceTriggerMenu, 'value' : 0, 'visible' : True, 'instance' : None,
									},
									{
									'type' : 'BUTTON', 'event' : 10,
									'x' : 66, 'y' : 86, 'w' : 32, 'h' : 20,
									'name' : "Add", 'tooltip' : "Add new Trigger", 'visible' : True, 'instance' : None,
									},
									{
									'type' : 'BUTTON', 'event' : 11,
									'x' : 98, 'y' : 86, 'w' : 32, 'h' : 20,
									'name' : "Del", 'tooltip' : "Remove Trigger", 'visible' : True, 'instance' : None,
									},
									{
										'type' : 'SLIDER', 'event' : 12,
										'x' : 0, 'y' : 49, 'w' : 130 , 'h' : 15, 'tooltip' : "Value when triggered",
										'name' : "Value ", 'min' : -30, 'max' : 30, 'value' : 5, 'visible' : True, 'instance' : None,
									},
									{
										'type' : 'NUMBER', 'event' : 13,
										'x' : 0, 'y' : 34, 'w' : 130 , 'h' : 15, 'tooltip' : "Time Triggered",
										'name' : "Time ", 'min' : 0.0, 'max' : 120.0, 'value' : 6, 'visible' : True, 'instance' : None,
									},
									]
								},
								# General Sequence Options
								{
								'type' : 'CONTAINER',
								'x' : 350, 'y' : 0, 'w' : 140, 'h' : 170,
								'color_in' : shared_bar_int, 'color_out' : shared_bar_end, 'fade_mode' : 2,
								'color_border' : shared_border_col, 'visible' : True,
								'items' : [
									{
										'type' : 'TEXT',
										'x' : 10, 'y' : 150, 'color' : [1.,1.,1.],
										'value' : "Sequence Options", 'size' : "normal", 'visible' : True,
									},
									{
										'type' : 'TOGGLE', 'event' : 14,
										'x' : 10, 'y' : 120, 'w' : 120, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "Export Sequences", 'tooltip' : "Export Sequences", 'value' : 7
									},
									{
										'type' : 'TOGGLE', 'event' : 15,
										'x' : 10, 'y' : 103, 'w' : 120, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "Write Shape Script", 'tooltip' : "Write a shape script (.cs) for DSQ's", 'value' : 8
									},
									]
								},
							]
						}
					]
	Sequence_ID = Blender_Gui.addSheet(SequenceSheet,sequence_val,sequence_evt)

	# Mesh Sheet
	MeshSheet = SharedBar + TopSharedBar + [
						{
							'type' : 'CONTAINER',
							'x' : 0, 'y' : 30, 'w' : 490, 'h' : 170,
							'color_in' : [0.75,0.75,0.75], 'color_out' : [0.5,0.5,0.5], 'fade_mode' : 0,
							'color_border' : shared_border_col, 'visible' : True,
							'items' : [
								{
								'type' : 'CONTAINER',
								'x' : 0, 'y' : 0, 'w' : 350, 'h' : 170,
								'color_in' : shared_bar_int, 'fade_mode' : 0,
								'color_border' : shared_border_col, 'visible' : True,
								'items' : [
									# Detail Options (flags, etc)
									{
										'type' : 'TEXT',
										'x' : 10, 'y' : 150, 'color' : [1.,1.,1.],
										'value' : "Detail Options", 'size' : "normal", 'visible' : True,
									},
									# Billboards
									{
										'type' : 'TOGGLE', 'event' : 6,
										'x' : 10, 'y' : 122, 'w' : 60, 'h' : 20, 'visible' : True, 'instance' : None,
										'name' : "Billboard", 'tooltip' : "Generate Billboard for this detail level", 'value' : 1
									},
									{
										'type' : 'NUMBER', 'event' : 7,
										'x' : 10, 'y' : 104, 'w' : 110 , 'h' : 15, 'tooltip' : "Equator Step",
										'name' : "Equator", 'min' : 2, 'max' : 64, 'value' : 2, 'visible' : Prefs['Billboard']['Enabled'], 'instance' : None,
									},
									{
										'type' : 'NUMBER', 'event' : 8,
										'x' : 10, 'y' : 87, 'w' : 110 , 'h' : 15, 'tooltip' : "Polar Step",
										'name' : "Polar", 'min' : 3, 'max' : 64, 'value' : 3, 'visible' : Prefs['Billboard']['Enabled'], 'instance' : None,
									},
									{
										'type' : 'NUMBER', 'event' : 9,
										'x' : 10, 'y' : 70, 'w' : 110 , 'h' : 15, 'tooltip' : "Polar Angle",
										'name' : "Polar Angle", 'min' : .0, 'max' : 45.0, 'value' : 4, 'visible' : Prefs['Billboard']['Enabled'], 'instance' : None,
									},
									{
										'type' : 'NUMBER', 'event' : 10,
										'x' : 10, 'y' : 53, 'w' : 110 , 'h' : 15, 'tooltip' : "Image Size (pixels)",
										'name' : "Image Size", 'min' : 16, 'max' : 128, 'value' : 5, 'visible' : Prefs['Billboard']['Enabled'], 'instance' : None,
									},
									{
										'type' : 'TOGGLE', 'event' : 11,
										'x' : 10, 'y' : 36, 'w' : 110, 'h' : 15, 'visible' : Prefs['Billboard']['Enabled'], 'instance' : None,
										'name' : "Include Poles", 'tooltip' : "Take polar snapshots?", 'value' : 6
									},
									{
										'type' : 'NUMBER', 'event' : 12,
										'x' : 10, 'y' : 19, 'w' : 110 , 'h' : 15, 'tooltip' : "Size of the billboard detail",
										'name' : "Detail Size", 'min' : 1, 'max' : 128, 'value' : 7, 'visible' : Prefs['Billboard']['Enabled'], 'instance' : None,
									},
									{
										'type' : 'TOGGLE', 'event' : 13,
										'x' : 72, 'y' : 122, 'w' : 100, 'h' : 20, 'visible' : True, 'instance' : None,
										'name' : "Generate Details", 'tooltip' : "Generate missing detail level meshes", 'value' : 8
									},
									]
								},
								# Mesh Export Options
								{
								'type' : 'CONTAINER',
								'x' : 350, 'y' : 0, 'w' : 140, 'h' : 170,
								'color_in' : shared_bar_int, 'color_out' : shared_bar_end, 'fade_mode' : 2,
								'color_border' : shared_border_col, 'visible' : True,
								'items' : [
									{
										'type' : 'TEXT',
										'x' : 10, 'y' : 150, 'color' : [1.,1.,1.],
										'value' : "Mesh Options", 'size' : "normal", 'visible' : True,
									},
									{
										'type' : 'TOGGLE', 'event' : 14,
										'x' : 10, 'y' : 120, 'w' : 120, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "Triangle Strips", 'tooltip' : "Generate Triangle Strips for Meshes", 'value' : 9
									},
									{
										'type' : 'NUMBER', 'event' : 15,
										'x' : 10, 'y' : 103, 'w' : 120 , 'h' : 15, 'tooltip' : "Maximum strip size",
										'name' : "Max Strip Size", 'min' : -30, 'max' : 30, 'value' : 10, 'visible' : Prefs['StripMeshes'], 'instance' : None,
									},
									{
										'type' : 'NUMBER', 'event' : 16,
										'x' : 10, 'y' : 70, 'w' : 120 , 'h' : 15, 'tooltip' : "Maximum cluster depth on Sorted Meshes",
										'name' : "Cluster Depth", 'min' : -30, 'max' : 30, 'value' : 11, 'visible' : True, 'instance' : None,
									},
									{
										'type' : 'TEXT',
										'x' : 10, 'y' : 90, 'color' : [1.,1.,1.],
										'value' : "Sorted Mesh Options", 'size' : "normal", 'visible' : True,
									},
									{
										'type' : 'TOGGLE', 'event' : 17,
										'x' : 10, 'y' : 53, 'w' : 120, 'h' : 15, 'visible' : True, 'instance' : None,
										'name' : "Write Depth", 'tooltip' : "Always Write Depth on Sorted Meshes", 'value' : 12
									},
									]
								}
							]
						}
					]
	Mesh_ID = Blender_Gui.addSheet(MeshSheet,mesh_val,mesh_evt)

	# About Sheet
	aboutText = ["DTS Exporter for the Torque Game Engine",
	"Written by James Urquhart, with assistance from Tim Gift, Clark Fagot, Wes Beary,",
	"Ben Garney, Joshua Ritter, Emanuel Greisen, Todd Koeckeritz, Xavier Amado,",
	"Ryan J. Parker, and Walter Yoon.",
	"Additional thanks goes to the testers.",
	"",
	"Visit GarageGames at http://www.garagegames.com"]
	AboutSheet = SharedBar + TopSharedBar + [
						{
							'type' : 'CONTAINER',
							'x' : 0, 'y' : 30, 'w' : 490, 'h' : 170,
							'color_in' : [0.75,0.75,0.75], 'color_out' : [0.5,0.5,0.5], 'fade_mode' : 0,
							'color_border' : shared_border_col, 'visible' : True,
							'items' : [
								{
									'type' : 'TEXTLINES',
									'x' : 1, 'y' : 151, 'color' : [1.,1.,1.],
									'value' : aboutText, 'size' : "normal", 'visible' : True,
								},
							]
						}
					]
	About_ID = Blender_Gui.addSheet(AboutSheet,about_val,about_evt)
	'''


'''
	Shared Event Handler
'''
def shared_evt(evt):
	global Sequence_ID
	global Mesh_ID
	global About_ID

	if evt == 1: Blender_Gui.NewSheet = Sequence_ID
	elif evt == 2: Blender_Gui.NewSheet = Mesh_ID
	elif evt == 3: export()
	elif evt == 4: Blender_Gui.NewSheet = About_ID
	else: return False
	return True

'''
	About Sheet Handling
'''

def about_val(val):
	return 0

def about_evt(evt):
	if not shared_evt(evt):
		return False

'''
	Mesh Sheet Handling
'''

# Gets detail level from number
# Assumes same order as detail menu
def mesh_getDetail(num):
	real_number = num+1
	global export_tree
	for o in export_tree.children:
		if o.__class__ == ShapeTree:
			count = 0
			for c in o.children:
				if c.getName()[0:6] == "Detail":
					count += 1
				if count == real_number:
					return c.getName()
			break
def mesh_val(val):
	global Mesh_ID
	global Prefs
	if val == 1:
		# Billboard
		return Prefs['Billboard']['Enabled']
	elif val == 2:
		# Equator
		return Prefs['Billboard']['Equator']
	elif val == 3:
		# Polar
		return Prefs['Billboard']['Polar']
	elif val == 4:
		# Polar Angle
		return Prefs['Billboard']['PolarAngle']
	elif val == 5:
		# Image Size
		return Prefs['Billboard']['Dim']
	elif val == 6:
		# Polar Snapshots
		return Prefs['Billboard']['IncludePoles']
	elif val == 7:
		# Billboard size
		return Prefs['Billboard']['Size']
	elif val == 8:
		# Automagic Details
		return Prefs['AutoDetail']
	elif val == 9:
		# Triangle Strips
		return Prefs['StripMeshes']
	elif val == 10:
		# Triangle Strip Max Size
		return Prefs['MaxStripSize']
	elif val == 11:
		# Max Cluster Size
		return Prefs['ClusterDepth']
	elif val == 12:
		# Always write Depth?
		return Prefs['AlwaysWriteDepth']
	return 0

def mesh_evt(evt):
	global Mesh_ID
	global Prefs
	if shared_evt(evt): return True
	elif evt == 6:
		# Billboard
		if not Prefs['Billboard']['Enabled']:
			# Enable billboard
			Prefs['Billboard']['Enabled'] = True
			# Show controls
			for c in Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][2:8]:
				c['visible'] = True
		else:
			# Disable Billboard
			Prefs['Billboard']['Enabled'] = False
			# Hide Controls
			for c in Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][2:8]:
				c['visible'] = False
	elif evt == 7:
		# Equator
		new_val = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][2]['instance'].val
		Prefs['Billboard']['Equator'] = new_val
	elif evt == 8:
		# Polar
		new_val = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][3]['instance'].val
		Prefs['Billboard']['Polar'] = new_val
	elif evt == 9:
		# Polar Angle
		new_val = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][4]['instance'].val
		Prefs['Billboard']['PolarAngle'] = new_val
	elif evt == 10:
		# Image Size
		new_val = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][5]['instance'].val
		Prefs['Billboard']['Dim'] = new_val
	elif evt == 11:
		# Polar Snapshots
		Prefs['Billboard']['IncludePoles'] = not Prefs['Billboard']['IncludePoles']
	elif evt == 12:
		# Billboard size
		Prefs['Billboard']['Size'] = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][0]['items'][7]['instance'].val
	elif evt == 13:
		# Automagic Details
		Prefs['AutoDetail'] = not Prefs['AutoDetail']
	elif evt == 14:
		# Triangle Strips
		Prefs['StripMeshes'] = not Prefs['StripMeshes']
		Blender_Gui.Sheets[Mesh_ID][0][2]['items'][1]['items'][2]['visible'] = Prefs['StripMeshes']
	elif evt == 15:
		# Triangle Strip Max Size
		Prefs['MaxStripSize'] = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][1]['items'][2]['instance'].val
	elif evt == 16:
		# Max Cluster Size in Sorted Mesh Code
		Prefs['ClusterDepth'] = Blender_Gui.Sheets[Mesh_ID][0][2]['items'][1]['items'][3]['instance'].val
	elif evt == 17:
		Prefs['AlwaysWriteDepth'] = not Prefs['AlwaysWriteDepth']
	else: return False
	return True

'''
	Sequence Sheet Handling
'''

def sequence_val(val):
	global Sequence_ID
	global Prefs
	# Grab common stuff...
	try: seq_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][0]['items'][1]['instance'].val
	except: seq_val = -1
	try: trigger_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][2]['items'][1]['instance'].val
	except: pass
	if len(Armature.NLA.GetActions().keys()) > seq_val:
		seq_name = Armature.NLA.GetActions().keys()[seq_val]
	else:
		seq_name = None

	# Process events...
	if val == 1:
		# Write DSQ
		if seq_name != None:
			return getSequenceKey(seq_name)['Dsq']
	elif val == 2:
		# Cyclic
		if seq_name != None:
			return getSequenceKey(seq_name)['Cyclic']
	elif val == 3:
		# Blend
		if seq_name != None:
			return getSequenceKey(seq_name)['Blend']
	elif val == 5:
		# Value
		if seq_name != None:
			if trigger_val < len(getSequenceKey(seq_name)['Triggers']): return getSequenceKey(seq_name)['Triggers'][trigger_val][0]
	elif val == 6:
		# Time
		if seq_name != None:
			if trigger_val < len(getSequenceKey(seq_name)['Triggers']): return getSequenceKey(seq_name)['Triggers'][trigger_val][1]
	elif val == 7:
		# Export Sequences
		return Prefs['WriteSequences']
	elif val == 8:
		# Shape Script
		return Prefs['WriteShapeScript']
	elif val == 10:
		# Ground Frame Count
		if seq_name != None:
			return getSequenceKey(seq_name)['NumGroundFrames']
	elif val == 12:
		# No. Frames to export for interpolation
		if seq_name != None:
			return getSequenceKey(seq_name)['Interpolate']
	elif val == 13:
		# Don't export?
		if seq_name != None:
			return getSequenceKey(seq_name)['NoExport']
	return 0

def sequence_evt(evt):
	global Sequence_ID
	global Prefs
	# Grab common stuff...
	try:
		seq_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][0]['items'][1]['instance'].val
		trigger_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][2]['items'][1]['instance'].val
		if len(Armature.NLA.GetActions().keys()) > seq_val:
			seq_name = Armature.NLA.GetActions().keys()[seq_val]
		else:
			seq_name = None
	except:
		seq_name = None

	# Process events...
	if shared_evt(evt): return True
	elif evt == 50:
		# Sequence Menu

		# Re-calcuate max number of interpolation frames and ground frames
		maxFrames = getNumActionFrames(Armature.NLA.GetActions()[seq_name], False)
		# Ground frame control...
		Blender_Gui.Sheets[Sequence_ID][0][2]['items'][1]['items'][3]['max'] = maxFrames
		if Blender_Gui.Sheets[Sequence_ID][0][2]['items'][1]['items'][3]['instance'].val > maxFrames:
			getSequenceKey(seq_name)['NumGroundFrames'] = maxFrames

		Draw.Redraw(0)
	elif evt == 6:
		# DSQ
		if len(Armature.NLA.GetActions().keys()) > seq_val:
			getSequenceKey(seq_name)['Dsq'] = not getSequenceKey(seq_name)['Dsq']
	elif evt == 7:
		# Cyclic
		if seq_name != None:
			getSequenceKey(seq_name)['Cyclic'] = not getSequenceKey(seq_name)['Cyclic']
	elif evt == 16:
		# Blend
		if seq_name != None:
			getSequenceKey(seq_name)['Blend'] = not getSequenceKey(seq_name)['Blend']
	elif evt == 60:
		# Triggers Menu
		Draw.Redraw(0)
	elif evt == 10:
		# Add
		if seq_name != None:
			getSequenceKey(seq_name)['Triggers'].append([10,0.0])
	elif evt == 11:
		# Del
		if seq_name != None:
			if trigger_val < len(getSequenceKey(seq_name)['Triggers']): del getSequenceKey(seq_name)['Triggers'][trigger_val]
	elif evt == 12:
		# Value
		if seq_name != None:
			new_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][2]['items'][4]['instance'].val
			if trigger_val < len(getSequenceKey(seq_name)['Triggers']): getSequenceKey(seq_name)['Triggers'][trigger_val][0] = new_val
	elif evt == 13:
		# Time
		if seq_name != None:
			new_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][2]['items'][5]['instance'].val
			if trigger_val < len(getSequenceKey(seq_name)['Triggers']): getSequenceKey(seq_name)['Triggers'][trigger_val][1] = new_val
	elif evt == 14:
		# Export Sequences
		Prefs['WriteSequences'] = not Prefs['WriteSequences']
	elif evt == 15:
		# Shape Script
		Prefs['WriteShapeScript'] = not Prefs['WriteShapeScript']
	elif evt == 18:
		# Ground Frame Count
		if seq_name != None:
			new_val = Blender_Gui.Sheets[Sequence_ID][0][2]['items'][1]['items'][3]['instance'].val
			getSequenceKey(seq_name)['NumGroundFrames'] = new_val
	elif evt == 20:
		# Interpolate interval for keyframes
		if seq_name != None:
			getSequenceKey(seq_name)['Interpolate'] = not getSequenceKey(seq_name)['Interpolate']
	elif evt == 21:
		# Don't export?
		if seq_name != None:
			getSequenceKey(seq_name)['NoExport'] = not getSequenceKey(seq_name)['NoExport']

	else: return False
	return True

# Called when gui exits
def exit_callback():
	Torque_Util.dump_setout("stdout")

'''
	Entry Point
'''
#-------------------------------------------------------------------------------------------------

# Export model
if __name__ == "__main__":
	if Debug:
		Torque_Util.dump_setout("stdout")
	else:
		Torque_Util.dump_setout("%s.log" % noext(Blender.Get("filename")))
	Torque_Util.dump_writeln("Torque Exporter %s " % Version)
	Torque_Util.dump_writeln("Using blender, version %s" % Blender.Get('version'))
	if Torque_Util.Torque_Math.accelerator != None:
		Torque_Util.dump_writeln("Using accelerated math interface '%s'" % Torque_Util.Torque_Math.accelerator)
	else:
		Torque_Util.dump_writeln("Using unaccelerated math code, performance may be suboptimal")
	Torque_Util.dump_writeln("**************************")
	loadPrefs()
	# Determine the best course of action
	a = __script__['arg']
	if (a == 'export') or (a == None):
		# Process scene and export (default)
		handleScene()
		export()
		Torque_Util.dump_setout("stdout")
	elif a == 'config':
		# Process scene and launch config panel
		handleScene()
		initGui()
	else:
		# Something bad happened
		Torque_Util.dump_writeln("Error: invalid script arguement '%s'" % a)
