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
Dts_Blender.py

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
import Blender_Gui
import string
import math
import copy # For copying details


'''
  Blender Exporter For Torque
-------------------------------
  Blender Dts Classes for Python
'''

Version = "0.87"
Prefs = None
export_tree = None

'''
Utility Functions
'''
#-------------------------------------------------------------------------------------------------

# Convert Bone pos to a MatrixF
def blender_bone2matrixf(head, tail, roll):
	'''
		Convert bone rest state (defined by bone.head, bone.tail and bone.roll)
		to a matrix (the more standard notation).
		Taken from blenkernel/intern/armature.c in Blender source.
		See also DNA_armature_types.h:47.
	'''
	target = Vector(0.0, 1.0, 0.0)
	delta  = Vector(tail[0] - head[0], tail[1] - head[1], tail[2] - head[2])
	nor    = delta.normalize()

	# Find Axis & Amount for bone matrix
	axis   = target.cross(nor)

	if axis.dot(axis) > 0.0000000000001:
		# if nor is *not* a multiple of target ...
		axis    = axis.normalize()
		theta   = math.acos(target.dot(nor))
		# Make Bone matrix
		bMatrix = MatrixF().rotate(axis, theta)
	else:
		# if nor is a multiple of target ...
		# point same direction, or opposite?
		if target.dot(nor) > 0.0:
			updown =  1.0
		else:
			updown = -1.0

		# I think this should work ...
		dMatrix = [
		updown, 0.0, 0.0, 0.0,
		0.0, updown, 0.0, 0.0,
		0.0, 0.0, 1.0, 0.0,
		0.0, 0.0, 0.0, 1.0,
		]
		bMatrix = MatrixF(dMatrix)

	# Make Roll matrix
	rMatrix = MatrixF().rotate(nor, roll)
	# Combine and output result
	return (rMatrix * bMatrix)

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

# Helpful function to make a map of curve names
def BuildCurveMap(ipo):
	curvemap = {}
	ipocurves = ipo.getCurves()
	for i in range(ipo.getNcurves()):
		curvemap[ipocurves[i].getName()] = i

	if Blender.Get('version') == 234:
		# HACKHACK! 2.34 doesn't give us the correct quat values
		try:
			# X=Y, Y=Z, Z=W, W=X
			curvemap['QuatX'],curvemap['QuatY'],curvemap['QuatZ'],curvemap['QuatW'] = curvemap['QuatY'],curvemap['QuatZ'],curvemap['QuatW'],curvemap['QuatX']
		except:
			pass

	return curvemap

# Function to determine what animation is present in a curveMap
def getCMapSupports(curveMap):
	try:
		foo = curveMap['LocX']
		has_loc = True
	except KeyError: has_loc = False
	try:
		foo = curveMap['QuatX']
		has_rot = True
	except KeyError: has_rot = False
	try:
		foo = curveMap['SizeX']
		has_scale = True
	except KeyError: has_scale = False
	return has_loc,has_rot,has_scale

# Tells us how many frames are in an Action
def getNumActionFrames(action, use_ipo):
	numFrames = 0
	if not use_ipo:
		for channel_name in action.getAllChannelIpos():
			i = action.getAllChannelIpos()[channel_name]
			# This basically gets the furthest frame in blender this sequence has a keyframe at
			if i.getCurveBeztriple(0, i.getNBezPoints(0)-1)[3] > numFrames:
				numFrames = int(i.getCurveBeztriple(0, i.getNBezPoints(0)-1)[3])
	else:
		for channel_name in action.getAllChannelIpos():
			i = action.getAllChannelIpos()[channel_name]
			# This simply counts the keyframes assigned by users
			if i.getNBezPoints(0) > numFrames:
				numFrames = i.getNBezPoints(0)
	return numFrames

# Imports a material into a Dts Shape
def importBlenderMaterial(shape, bmat):
	global dump
	if bmat == None: return None
	material = dMaterial(bmat.getName(), dMaterial.SWrap | dMaterial.TWrap,shape.materials.size(),-1,-1,1.0,bmat.getRef())
	material.sticky = False

	# If we are emitting light, we must be self illuminating
	if bmat.getEmit() > 0.0: material.flags |= dMaterial.SelfIlluminating
	material.flags |= dMaterial.NeverEnvMap

	# Look at the texture channels if they exist
	textures = bmat.getTextures()
	if len(textures) > 0:
		if (textures[0] != None) and (textures[0].tex.type == Texture.Types.IMAGE):
			# Translucency?
			if textures[0].mapto & Texture.MapTo.ALPHA:
				material.flags |= dMaterial.Translucent
				if bmat.getAlpha() < 1.0: material.flags |= dMaterial.Additive

			# Sticky coords?
			if textures[0].texco & Texture.TexCo.STICK:
				material.sticky = True

			# Disable mipmaps?
			if not (textures[0].tex.imageFlags & Texture.ImageFlags.MIPMAP):
				material.flags |= dMaterial.NoMipMap

		for i in range(1, len(textures)):
			texture_obj = textures[i]
			if texture_obj == None: continue

			# Figure out if we have an Image
			if texture_obj.tex.type != Texture.Types.IMAGE:
				dump.writeln("      Warning: Material(%s,%d) Only Image textures are supported. Skipped." % (bmat.getName(),i))
				continue

			# Determine what this texture is used for
			# A) We have a reflectance map
			if (material.reflectance == -1) and (texture_obj.mapto & Texture.MapTo.REF):
				# We have a reflectance map
				reflectance_map = dMaterial(texture_obj.tex.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
				reflectance_map.flags |= dMaterial.ReflectanceMap
				material.flags &= ~dMaterial.NeverEnvMap
				material.reflectance = self.Shape.materials.add(reflectance_map)
			# B) We have a normal map (basically a 3d bump map)
			elif (material.bump == -1) and (texture_obj.mapto & Texture.MapTo.NOR):
				bump_map = dMaterial(texture_obj.tex.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
				bump_map.flags |= dMaterial.BumpMap
				material.bump = shape.materials.add(bump_map)
			# C) We have a texture; Lets presume its a detail map (since its laid on top after all)
			elif material.detail == -1:
				detail_map = dMaterial(texture_obj.tex.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
				detail_map.flags |= dMaterial.DetailMap
				material.detail = shape.materials.add(detail_map)
	else:
		dump.writeln("      Warning: Material(%s) does not have any textures assigned!" % bmat.getName())
	return shape.materials.add(material)

# Calculates mesh flags
def generateMeshFlags(names):
	genFlags = 0

	# Look through elements in names
	for n in names:
		if n == "BB":
			genFlags |= DtsMesh.Billboard
		elif n == "BBZ":
			genFlags |= DtsMesh.Billboard | DtsMesh.BillboardZ

	# Returns the Generated Flags
	return genFlags

# Converts a blender matrix to a Torque_Util.MatrixF
def toTorqueUtilMatrix(blendermatrix):
	return MatrixF([blendermatrix[0][0],blendermatrix[0][1],blendermatrix[0][2],blendermatrix[0][3],
						 blendermatrix[1][0],blendermatrix[1][1],blendermatrix[1][2],blendermatrix[1][3],
						 blendermatrix[2][0],blendermatrix[2][1],blendermatrix[2][2],blendermatrix[2][3],
						 blendermatrix[3][0],blendermatrix[3][1],blendermatrix[3][2],blendermatrix[3][3]])

# Creates a matrix that transforms to shape space
def collapseBlenderTransform(object):
	# In blender 2.33 and before, getMatrix() returned the worldspace matrix.
	# In blender 2.33+, it seems to return the local matrix
	if Blender.Get('version') > 233:
		cmat = toTorqueUtilMatrix(object.getMatrix("worldspace"))
	else:
		cmat = toTorqueUtilMatrix(object.getMatrix())
	return cmat

# Creates a cumilative scaling ratio for an object
def collapseBlenderScale(object):
	csize = object.getSize()
	csize = [csize[0], csize[1], csize[2]]
	parent = object.getParent()
	while parent != None:
		nsize = parent.getSize()
		csize[0],csize[1],csize[2] = csize[0]*nsize[0],csize[1]*nsize[1],csize[2]*nsize[2]
		parent = parent.getParent()
	return csize



'''
	Progress Management Code
'''
cur_progress = None

'''
	The progress management is quite simple.
	Create an instance of the Progress class, then use pushTask() to assign new tasks,
	which tell the user what we are currently doing.

	To update the status of a task, use update(). This will also update the progress bar in blender.

	When you are finished with a task, simply use popTask().

	e.g :
		myCounter = Progress()
		myCounter.pushTask("Done", 1, 1.0)

		myCounter.pushTask("Doing something in between...", 2, 0.5)
		myCounter.update()
		myCounter.update()
		myCounter.popTask()

		myCounter.pushTask("Doing something else in between...", 2, 0.5)
		myCounter.update()
		myCounter.update()
		myCounter.popTask()

		myCounter.update()
		myCounter.popTask()

'''
class Progress:
	def __init__(self):
		self.stack = []		# [name, increment, max]
		self.cProgress = 0.0

	def __del__(self):
		del self.stack

	def pushTask(self, name, maxItems, maxProgress):
		self.stack.append([name, (maxProgress - self.cProgress) / maxItems, maxProgress])
		Window.DrawProgressBar(self.cProgress, self.stack[-1][0])

	def popTask(self):
		#print "DBG: Popping", self.stack[-1]
		del self.stack[-1]

	def curMax(self):
		return self.stack[-1][2]

	def curInc(self):
		return self.stack[-1][-1]

	def update(self):
		self.cProgress += self.stack[-1][1]
		if self.cProgress > self.stack[-1][2]:
			self.cProgress = self.stack[-1][2]

		#print "Updated Progress, Task '%s', %f/%f" % (self.stack[-1][0],self.cProgress,self.stack[-1][2])
		Window.DrawProgressBar(self.cProgress, self.stack[-1][0])

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
	text_doc.write("AutoDetail %d\n" % Prefs['AutoDetail'])
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
	global Version, dump
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
				dump.writeln("   Warning : Loading different version config file than is supported")
		elif cur_token == "{":
			cur_parse = 1
			while tok.advanceToken(True):
				cur_token = tok.getToken()
				# Parse Main Section
				if cur_token == "WriteShapeScript":
					tok.advanceToken(False)
					Prefs['WriteShapeScript'] = int(tok.getToken())
				elif cur_token == "AutoDetail":
					tok.advanceToken(False)
					Prefs['AutoDetail'] = int(tok.getToken())
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
							dump.writeln("   Unrecognised Billboard token : %s" % cur_token)
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
									dump.writeln("   Unrecognised Sequence Trigger token : %s" % cur_token)
						elif cur_token == "}":
							cur_parse = 1
							seq_name = None
							break
						else:
							dump.writeln("   Unrecognised Sequence token : %s" % cur_token)
					cur_parse = 1
				elif cur_token == "}":
					cur_parse = 0
					break
				else:
					dump.writeln("   Unrecognised token : %s" % cur_token)
		else:
			dump.writeln("   Warning : Unexpected token %s!" % cur_token)
	return Prefs

def initPrefs():
	Prefs = {}
	Prefs['Version'] = 0.2 # NOTE: change version if anything *major* is changed.
	Prefs['WriteShapeScript'] = False
	Prefs['Sequences'] = {}
	Prefs['AutoDetail'] = False
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
	global Prefs, dump
	Prefs = Registry.GetKey('TORQUEEXPORTER%s' % basename(Blender.Get("filename")))
	if not Prefs:
		# Could be saved?
		Prefs = loadTextPrefs(initPrefs())
		dump.writeln("Loaded Preferences.")
		# Save prefs
		savePrefs()

dummySequence = {'Dsq' : False, 'Cyclic' : False, 'Blend' : False, 'Triggers' : [], 'Interpolate' : 0, 'NoExport' : False, 'NumGroundFrames' : 0}

# Gets a sequence key from the preferences
# Creates default if key does not exist
def getSequenceKey(value):
	global Prefs, dump, dummySequence
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
	Dump print class
'''

class DumpPrint:
	def __init__(self, filename):
		if filename == "stdout":
			self.useFile = False
			print "Dumping output to console"
		else:
			self.fs = open(filename, "w")
			if not self.fs:
				print "Warning : could not open dump file '%s'!" % filename
				self.useFile = False
			else:
				print "Dumping output to file '%s'" % filename
				self.useFile = True

	def __del__(self):
		if self.useFile:
			del self.fs

	def write(self, string):
		if self.useFile:
			self.fs.write(string)
		else:
			print string
	def writeln(self, string):
		self.write("%s\n" % string)

'''
   Mesh Class
'''
#-------------------------------------------------------------------------------------------------

class BlenderMesh(DtsMesh):
	def __init__(self, shape, msh,  rootBone, scaleFactor, matrix, Sorted=False):
		global dump
		DtsMesh.__init__(self)
		self.vertsIndexMap = []

		# Insert Polygons
		for face in msh.faces:
			if len(face.v) < 3:
				continue # skip to next face
			# Insert primitive strips
			pr = Primitive()
			pr.firstElement = len(self.indices)
			pr.numElements = 3
			pr.matindex = pr.Strip | pr.Indexed

			useSticky = False
			# Find the image associated with the face on the mesh, if any
			if len(msh.materials) > 0:
				# Also, use sticky coords if we were asked to
				matIndex = shape.materials.findMaterial(msh.materials[face.materialIndex].getName())
				if matIndex == None: matIndex = importBlenderMaterial(shape, msh.materials[face.materialIndex])
				if matIndex == None: matIndex = pr.NoMaterial
				useSticky = shape.materials.get(matIndex).sticky
				pr.matindex |= matIndex
			else:
				pr.matindex |= pr.NoMaterial # Nope, no material

			self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
			self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky))
			self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))

			# Finally add primitive
			self.primitives.append(pr)
			# If double sided, add this face again in reverse order
			if (msh.mode & NMesh.Modes.TWOSIDED) or (face.mode & NMesh.FaceModes.TWOSIDE):
				print "you are here 1"
				print "self.indices:"
				print self.indices
				self.indices.append(self.indices[-1])
				self.indices.append(self.indices[-2])
				self.indices.append(self.indices[-3])
				self.primitives.append(Primitive(pr.firstElement+pr.numElements,3,pr.matindex))
				print "self.indices:"
				print self.indices

			# Add a second triangle if the face has 4 verts
			if len(face.v) == 4:
				pr2 = Primitive()
				pr2.firstElement = len(self.indices)
				pr2.numElements = 3
				pr2.matindex = pr.matindex
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,3, useSticky))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))
				self.primitives.append(pr2)
				if (msh.mode & NMesh.Modes.TWOSIDED) or (face.mode & NMesh.FaceModes.TWOSIDE):
					print "you are here 2"
					print "self.indices:"
					print self.indices
					# If double sided, add this face again in reverse order
					self.indices.append(self.indices[-1])
					self.indices.append(self.indices[-2])
					self.indices.append(self.indices[-3])
					self.primitives.append(Primitive(pr2.firstElement+pr2.numElements,3,pr2.matindex))
					print "self.indices:"
					print self.indices


		if Sorted: self.mtype = self.T_Sorted

		# Determine shape type based on vertex weights
		if len(self.bindex) <= 1:
			if not self.mtype == self.T_Sorted: self.mtype = self.T_Standard
		else:
			if not self.mtype == self.T_Sorted:
				self.mtype = self.T_Standard # default
				for v in self.bindex:
					if v != self.bindex[0]:
						self.mtype = self.T_Skin
						break

		# Print informative message describing type
		if self.mtype == self.T_Standard:
			dump.writeln("      Type: Standard")
		elif self.mtype == self.T_Skin:
			dump.writeln("      Type: Skin")
		elif self.mtype == self.T_Sorted:
			dump.writeln("      Type: Sorted")

		# vertsPerFrame is related to the vertex animation code
		self.vertsPerFrame = len(self.verts) # set verts in a frame

		# Final stuff...
		# Total number of frames. For a non animated mesh, this will always be 1
		self.numFrames = len(self.verts) / self.vertsPerFrame

		# Mesh parent
		self.parent = -1

		# Calculate Limits
		self.calculateBounds()
		self.calculateCenter()
		self.calculateRadius()

		del self.vertsIndexMap

	def appendVertex(self, shape, msh, rootBone, matrix, scaleFactor, face, faceIndex, useSticky):
		# Use Face coords if requested
		if not useSticky:
			# The face may not have texture coordinate, in which case we assign 0,0
			if len(face.uv) < faceIndex + 1:
				texture = Vector2(float(0.0),float(0.0))
			else:
				texture = Vector2(face.uv[faceIndex][0], 1.0 - face.uv[faceIndex][1])
		# Add sticky coords *if* they are available
		elif msh.hasVertexUV():
			texture = Vector2(msh.verts[face.v[faceIndex].index].uvco[0],msh.verts[face.v[faceIndex].index].uvco[1])
		# We were supposed to use sticky coords, but none were found
		else:
			texture = Vector2(float(0.0),float(0.0))

		# See if the vertex/texture combo already exists..
		bvIndex = face.v[faceIndex].index
		for vi in range(0,len(self.vertsIndexMap)):
			if bvIndex == self.vertsIndexMap[vi]:
				# See if the texture coordinates match up.
				tx = self.tverts[vi]
				if tx[0] == texture[0] and tx[1] == texture[1]:
					return vi

		'''
			Add new mesh vert and texture
			Get Vert in world coordinates using object matrix
			Texture needs to be flipped to work in torque
		'''
		vert = msh.verts[face.v[faceIndex].index]
		nvert = matrix.passPoint(Vector(vert.co[0], vert.co[1], vert.co[2])) * scaleFactor
		vindex = len(self.verts)
		self.verts.append(nvert)
		self.tverts.append(texture)
		self.vertsIndexMap.append(bvIndex)

		# Add vert Normals
		normal = Vector(vert.no[0], vert.no[1], vert.no[2])
                #normal = matrix.passPoint(Vector(vert.no[0], vert.no[1], vert.no[2]))
		self.normals.append(normal)
		self.enormals.append(self.encodeNormal(normal))

		# Add bone weights
		bone, weight = -1, 1.0
		influences = msh.getVertexInfluences(vert.index)
		if len(influences) > 0:
			# Total weights should add up to one, so we need
			# to normalize the weights assigned in blender.
			total = 0
			for inf in influences:
				total += inf[1]

			for inf in influences:
				# Add the vertex influence. Any number can be added,
				# but they must be ordered by vertex.
				self.vindex.append(vindex)
				bone, weight = shape.getNodeIndex(inf[0]), inf[1]
				if bone >= 0:
					self.bindex.append(self.getVertexBone(bone))
				else:
					self.bindex.append(self.getVertexBone(rootBone))
				# getVertexBone() also adds the nodeTransform(matrixF),
				# and node Index (if not already on list)
				self.vweight.append(weight / total)
		return vindex

'''
	Class to handle the 'World' branch
'''
#-------------------------------------------------------------------------------------------------
class SceneTree:
	# Creates trees to handle children
	def handleChild(self,obj):
		tname = string.split(obj.getName(), ":")[0]
		if tname == "Shape":
			handle = ShapeTree(self, obj)
		else:
			#dump.writeln("Warning: could not handle child '%s'" % obj.getName())
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

	def process(self):
		# Process children
		for c in self.children:
			if c == None: continue
			c.process()

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

# Simple store of objects for later adding to detail levels
class DetailInfo:
	def __init__(self):
		self.objects = []
		self.sz = 0
		self.name = ""
	def clear(self):
		clearArray(self.objects)
	def __del__(self):
		self.clear()

class ShapeTree(SceneTree):
	def __init__(self,parent=None,obj=None):
		self.Shape = None

		# Used in metrics
		self.numDetails = 0
		self.numCollision = 0
		self.numLOSCollision = 0

		self.detailInfos = []
		self.detailSizes = []

		SceneTree.__init__(self,parent,obj)

	def getDetail(self, size):
		for d in self.detailInfos:
			if d.sz == size:
				return d
		return None

	def handleChild(self, obj):
		global dump
		tname = obj.getName()
		if tname[0:6] == "Detail":
			self.numDetails += 1
			self.detailSizes.append(int(tname[6:]))
		elif tname[0:3] == "Col":
			self.numCollision += 1
		elif tname[0:3] == "Los":
			self.numLOSCollision += 1
		else:
			# Now handle general purpose objects like armatures
			if obj.getType() != "Armature":
				dump.writeln("     Warning: Could not accept child %s on shape %s" % (obj.getName(),self.obj.getName()))
				return None
		return obj

	# Handles shape children; Can generate statistics by setting the "Metrics" option.
	def processChild(self,obj):
		global dump
		tname = obj.getName()
		if tname[0:6] == "Detail":
			num = int(tname[6:])
			self.processDetail(obj)
		elif tname[0:3] == "Col":
			self.processCollision(obj)
		elif tname[0:3] == "Los":
			self.processCollision(obj,True)
		else:
			# Now handle general purpose objects like armatures
			if obj.getType() == "Armature":
				self.addArmature(obj)
			else:
				dump.writeln("     Warning: Could not accept child %s on shape %s" % (obj.getName(),self.obj.getName()))

	# Processes Detail# nodes
	def processDetail(self, obj):
		global Prefs, dump, cur_progress
		info = self.getDetail(int(obj.getName()[6:]))
		dump.writeln("   >Detail (size %d)" % info.sz)

		# Get everything parented to this object
		objects = getAllChildren(obj)

		if len(objects) != 0:
			cur_progress.pushTask("Adding Detail (%d)" % info.sz, len(objects), cur_progress.cProgress+cur_progress.curInc())

			# Firstly, we need armatures and cameras
			for o in objects:
				if o.getType() == "Armature":
					self.addArmature(o)
					cur_progress.update()
				elif o.getType() == "Camera":
					self.addCamera(o)
					cur_progress.update()

			# Then we can add everything else
			for o in objects:
				if o.getType() == "Mesh":
					if o.getName() == "Bounds": continue # Skip objects named "Bounds"

					# Get Object's Matrix
					mat = collapseBlenderTransform(o)

					# Split name up
					names = string.split(o.getName(),"_")
					obj = dObject(self.Shape.addName(names[0]), 1, -1, 0)
					dump.writeln("     Mesh Object: %s" % names[0])
					sorted = False
					if len(names) > 1:
						for flg in names[1:]:
							if flg == "Sort": sorted = True

					mesh_data = o.getData()
					# Convert the mesh to a regular mesh if its SubSurf'd
					if mesh_data.getMode() & NMesh.Modes.SUBSURF:
						dump.writeln("      SubSurf : Yes, Converting...")
						mesh_data = NMesh.GetRawFromObject(o.getName())
						mesh_data.update()

					# Import Mesh, process flags
					tmsh = BlenderMesh(self.Shape, mesh_data, 0 , 1.0, mat, sorted)
					if len(names) > 1:
						tmsh.flags |= generateMeshFlags(names[1:])

					# If we ended up being a Sorted Mesh, sort the faces
					if sorted:
						tmsh.mtype = tmsh.T_Sorted
						tmsh.sortMesh(Prefs['AlwaysWriteDepth'], Prefs['ClusterDepth'])

					info.objects.append([obj,tmsh])

					cur_progress.update()
				elif (o.getType() != "Armature") and (o.getType() != "Camera") and (o.getType() != "Empty"):
					dump.writeln("     Warning: could not handle child %s with type %s" % (o.getName(),o.getType()))

			cur_progress.popTask()

	# Processes Col# and Los# nodes
	def processCollision(self, obj,LOS=False):
		global dump
		if LOS: info = self.detailInfos[self.numDetails + self.numCollision + int(obj.getName()[3:])]
		else: info = self.detailInfos[self.numDetails + int(obj.getName()[3:])]
		dump.writeln("   >Collision Level")

		# Get everything parented to this object
		objects = getAllChildren(obj)

		if len(objects) != 0:
			cur_progress.pushTask("Adding Collision Detail" , len(objects), cur_progress.cProgress+cur_progress.curInc())

			# Firstly, we need armatures and cameras
			for o in objects:
				if o.getType() == "Armature":
					self.addArmature(o)
					cur_progress.update()
				elif o.getType() == "Camera":
					self.addCamera(o)
					cur_progress.update()

			# Then we can add everything else
			for o in objects:
				if o.getType() == "Mesh":
					if o.getName() == "Bounds": continue # Skip objects named "Bounds"

					dump.writeln("     Mesh Object: %s" % o.getName())
					# Add the Mesh
					# Get Object's Matrix
					mat = collapseBlenderTransform(o)
					tmsh = BlenderMesh(self.Shape, o.getData(), 0 , 1.0, mat)
					obj = dObject(self.Shape.addName(o.getName()), 1, -1, 0)
					info.objects.append([obj,tmsh])

					cur_progress.update()

				elif (o.getType() != "Armature") and (o.getType() != "Camera"):
					dump.writeln("     Warning: could not handle child %s with type %s" % (o.getName(),o.getType()))

			cur_progress.popTask()

	# Tells us how many frames are in a sequence
	# NOTE: must contain a member variable "ipo", which is a list of ipo curves used in the sequence.
	def getNumFrames(self, sequence):
		numFrames = 0
		if getSequenceKey(self.Shape.sTable.get(sequence.nameIndex))['Interpolate']:
			for i in sequence.ipo:
				if i != 0:
					# This basically gets the furthest frame in blender this sequence has a keyframe at
					if i.getCurveBeztriple(0, i.getNBezPoints(0)-1)[3] > numFrames:
						numFrames = int(i.getCurveBeztriple(0, i.getNBezPoints(0)-1)[3])
		else:
			for i in sequence.ipo:
				if i != 0:
					# This simply counts the keyframes assigned by users
					if i.getNBezPoints(0) > numFrames:
						numFrames = i.getNBezPoints(0)
		return numFrames

	# Handles all the sequences in the scene
	def processActions(self):
		global Prefs, dump, cur_progress
		scene = Blender.Scene.getCurrent()
		context = scene.getRenderingContext()
		actions = Armature.NLA.GetActions()

		if len(actions.keys()) == 0: # No actions
			return

		cur_progress.pushTask("Adding Actions..." , len(actions.keys()*2), 0.6)

		# Go through actions and add the ipo's.
		for action_name in actions.keys():
			if getSequenceKey(action_name)['NoExport']: continue # Skip

			a = actions[action_name]
			sequence = Sequence(self.Shape.sTable.addString(action_name))

			sequence.has_ground = getSequenceKey(action_name)['NumGroundFrames'] != 0

			# Make set of blank ipos and matters for current node
			sequence.ipo = []
			sequence.frames = []
			for n in self.Shape.nodes:
				sequence.ipo.append(0)
				sequence.matters_translation.append(False)
				sequence.matters_rotation.append(False)
				sequence.matters_scale.append(False)
				sequence.frames.append(0)

			nodeFound = False
			# Figure out which nodes are animated
			channels = a.getAllChannelIpos()
			for channel_name in a.getAllChannelIpos():
				if channels[channel_name].getNcurves() == 0:
					continue
				nodeIndex = self.Shape.getNodeIndex(channel_name)

				# Determine if this node is in the shape
				if nodeIndex == None: continue
				else:
					# Print informative sequence name if we found a node in the shape (first time only)
					if not nodeFound:
						dump.writeln("   >Sequence:  %s" % action_name)
					nodeFound = True
					# Print informative track message
					dump.writeln("      Track: %s (node %d)" % (channel_name,nodeIndex))

				sequence.ipo[nodeIndex] = channels[channel_name]

			# If *none* of the nodes in this Action were present in the shape, abandon importing this action.
			if nodeFound == False:
				del sequence
				continue

			# Get any triggers used in this sequence
			sequence.triggers = getSequenceKey(action_name)['Triggers'] # note: will also create seq prefs if non existant

			# Add additional flags, e.g. cyclic
			if getSequenceKey(action_name)['Cyclic']: sequence.flags |= sequence.Cyclic
			if getSequenceKey(action_name)['Blend']:  sequence.flags |= sequence.Blend
			if sequence.has_ground: sequence.flags |= sequence.MakePath
			sequence.fps = context.framesPerSec()

			# Assign temp flags
			sequence.has_loc = False
			sequence.has_rot = False
			sequence.has_scale = False
			sequence.has_dsq = False

			# Determine the number of key frames
			sequence.numKeyFrames = self.getNumFrames(sequence)

			# Print different messages depending if we used interpolate or not
			if getSequenceKey(self.Shape.sTable.get(sequence.nameIndex))['Interpolate']:
				dump.writeln("      Interpolated KeyFrames: %d " % sequence.numKeyFrames)
			else:
				dump.writeln("      KeyFrames: %d " % sequence.numKeyFrames)

			self.Shape.sequences.append(sequence)

			cur_progress.update()

		'''
			Now we have the sequences, we can now determine what they animate
			We also need to create the matters_* arrays for the nodes in the shape
		'''
		dump.writeln("   >Sequence Info")
		for sequence in self.Shape.sequences:
			for ipo in sequence.ipo:
				if ipo == 0: continue # No ipo, no play
				curveMap = BuildCurveMap(ipo)
				has_loc, has_rot, has_scale = getCMapSupports(curveMap)
				if (not sequence.has_loc) and (has_loc): sequence.has_loc = True
				if (not sequence.has_rot) and (has_rot): sequence.has_rot = True
				if (not sequence.has_scale) and (has_scale):
					sequence.has_scale = True
					sequence.flags |= sequence.AlignedScale # scale is aligned in blender

			dump.write("      %s Animates:" % (self.Shape.sTable.get(sequence.nameIndex)))
			if sequence.has_loc: dump.write("loc ")
			if sequence.has_rot: dump.write("rot ")
			if sequence.has_scale: dump.write("scale ")
			if sequence.has_ground: dump.write("ground")
			dump.write("\n")

		dump.writeln("   >Processing Sequences")
		'''
			To top everything off, we need to import all the animation frames.
			Loop through all the sequences and the IPO blocks in nodeIndex order so that
			the animation node and rotation tables will be correctly compressed.
		'''
		count = 0
		for sequence in self.Shape.sequences:
			# Depending on what we have, set the bases accordingly
			if sequence.has_ground: sequence.firstGroundFrame = len(self.Shape.groundTranslations)
			else: sequence.firstGroundFrame = -1

			remove_last = False

			# Loop through the ipo list
			for nodeIndex in range(len(self.Shape.nodes)):
				ipo = sequence.ipo[nodeIndex]
				if ipo == 0: # No ipo for this node, so its not animated
					continue
				sequence.frames[nodeIndex] = []

				# Build curveMap for this ipo
				curveMap = BuildCurveMap(ipo)

				# Determine which bone attributes are modified by *this* IPO block
				has_loc, has_rot, has_scale = getCMapSupports(curveMap)

				# If we are adding rotation or translation nodes, make sure the
				# sequence matters is properly set..
				if sequence.has_loc: sequence.matters_translation[nodeIndex] = has_loc
				if sequence.has_rot: sequence.matters_rotation[nodeIndex] = has_rot
				if sequence.has_scale: sequence.matters_scale[nodeIndex] = has_scale

				if getSequenceKey(self.Shape.sTable.get(sequence.nameIndex))['Interpolate']:
					for bez in range(0, sequence.numKeyFrames):
						loc, rot, scale = self.getTransformAtFrame(scene, context, sequence, curveMap, nodeIndex, bez+1, False)
						sequence.frames[nodeIndex].append([loc,rot,scale])
				else:
					for bez in range(0, sequence.numKeyFrames):
						loc, rot, scale = self.getTransformAtFrame(scene, context, sequence, curveMap, nodeIndex, bez, True)
						sequence.frames[nodeIndex].append([loc,rot,scale])

				if sequence.flags & sequence.Cyclic:
					'''
						If we added any new translations, and the first frame is equal to the last, allow the next pass of nodes to happen, to remove the last frame.
						(This fixes the "dead-space" issue)
					'''
					remove_translation, remove_rotation, remove_scale = False, False, False

					if len(sequence.frames[nodeIndex]) != 0:
						'''
						if (sequence.frames[nodeIndex][0][0] != None) and (sequence.frames[nodeIndex][-1][0] != None):
							dump.writeln("LOC: %f %f %f == %f %f %f?" % (sequence.frames[nodeIndex][0][0][0],
							sequence.frames[nodeIndex][0][0][1],
							sequence.frames[nodeIndex][0][0][2],
							sequence.frames[nodeIndex][-1][0][0],
							sequence.frames[nodeIndex][-1][0][1],
							sequence.frames[nodeIndex][-1][0][2]))
						if (sequence.frames[nodeIndex][0][1] != None) and (sequence.frames[nodeIndex][-1][1] != None):
							dump.writeln("ROT: %f %f %f %f == %f %f %f %f?" % (sequence.frames[nodeIndex][0][1][0],
							sequence.frames[nodeIndex][0][1][1],
							sequence.frames[nodeIndex][0][1][2],
							sequence.frames[nodeIndex][0][1][3],
							sequence.frames[nodeIndex][-1][1][0],
							sequence.frames[nodeIndex][-1][1][1],
							sequence.frames[nodeIndex][-1][1][2],
							sequence.frames[nodeIndex][-1][1][3]))
						if (sequence.frames[nodeIndex][0][2] != None) and (sequence.frames[nodeIndex][-1][2] != None):
							dump.writeln("SCA: %f %f %f == %f %f %f?" % (sequence.frames[nodeIndex][0][2][0],
							sequence.frames[nodeIndex][0][2][1],
							sequence.frames[nodeIndex][0][2][2],
							sequence.frames[nodeIndex][-1][2][0],
							sequence.frames[nodeIndex][-1][2][1],
							sequence.frames[nodeIndex][-1][2][2]))
						'''

						if (sequence.frames[nodeIndex][0][0] != None) and (sequence.frames[nodeIndex][-1][0] != None) and (sequence.frames[nodeIndex][0][0] == sequence.frames[nodeIndex][-1][0]):
							remove_translation = True
						if (sequence.frames[nodeIndex][0][1] != None) and (sequence.frames[nodeIndex][-1][1] != None) and (sequence.frames[nodeIndex][0][1] == sequence.frames[nodeIndex][-1][1]):
							remove_rotation = True
						if (sequence.frames[nodeIndex][0][2] != None) and (sequence.frames[nodeIndex][-1][2] != None) and (sequence.frames[nodeIndex][0][2] == sequence.frames[nodeIndex][-1][2]):
							remove_scale = True

					# Determine if the change has affected all that we animate
					'''
					dump.writeln("%d %d" % (has_loc,remove_translation))
					dump.writeln("%d %d" % (has_rot,remove_rotation))
					dump.writeln("%d %d" % (has_scale,remove_scale))
					'''
					if (has_loc == remove_translation) and (has_rot == remove_rotation) and (has_scale == remove_scale):
						remove_last = True

			# Do a second pass on the nodes to remove the last frame for cyclic anims
			if remove_last:
				# Go through list of frames for nodes animated in sequence and delete the last frame from all of them
				for nodeIndex in range(len(self.Shape.nodes)):
					ipo = sequence.ipo[nodeIndex]
					if ipo != 0:
						#dump.writeln("Deleting last frame for node %s" % (self.Shape.sTable.get(self.Shape.nodes[nodeIndex].name)))
						del sequence.frames[nodeIndex][-1]
				dump.writeln("         Sequence '%s' frames now %d, decremented from %d" % (self.Shape.sTable.get(sequence.nameIndex),sequence.numKeyFrames-1,sequence.numKeyFrames))
				sequence.numKeyFrames -= 1

			# Triggers:
			# Add any triggers the sequence may have
			if len(sequence.triggers) != 0:
				dump.writeln("      '%s' Triggers: %d" % (self.Shape.sTable.get(sequence.nameIndex),len(sequence.triggers)))
				sequence.firstTrigger = len(self.Shape.triggers)
				sequence.numTriggers = len(sequence.triggers)
				# First check for triggers with both on and off states
				triggerState = []
				for t in sequence.triggers:
					triggerState.append(False)
					for comp in sequence.triggers:
						if t == -comp[0]:
							triggerState[-1] = True
							break

				count = 0
				for t in sequence.triggers:
					self.Shape.triggers.append(Trigger(t[0], t[1],triggerState[count]))
					count += 1
				del triggerState
			else:
				sequence.numTriggers = 0
				sequence.firstTrigger = -1

			# Calculate Bases
			if sequence.has_loc: sequence.baseTranslation = len(self.Shape.nodeTranslations)
			else: sequence.baseTranslation = -1
			if sequence.has_rot: sequence.baseRotation = len(self.Shape.nodeRotations)
			else: sequence.baseRotation = -1
			if sequence.has_scale: sequence.baseScale = len(self.Shape.nodeAlignedScales)
			else: sequence.baseScale = -1

			'''
				DSQ Support:
				Write the current sequence, then clear it out - This means 1 sequence per dsq.
				We could write several sequences, but we'll just leave it 1 to file.

				INTERNAL Sequence :
				Just dump the frames into the dts.
			'''
			if getSequenceKey(self.Shape.sTable.get(sequence.nameIndex))['Dsq']:
				dsq_format = self.dts_basepath + self.dts_basename + "_%s.dsq"
				dump.writeln("      DSQ: %s" % (dsq_format % self.Shape.sTable.get(sequence.nameIndex)))
				sequence_name = self.Shape.sTable.get(sequence.nameIndex)
				dsq_file = open(dsq_format % sequence_name, "wb")
				if Prefs['WriteShapeScript']:
					# Write entry for this in shape script
					self.shapeScript.write("   sequence%d = \"./%s_%s.dsq %s\";\n" % (count,self.dts_basename,sequence_name,sequence_name))

				# Dump Frames
				for node in sequence.frames:
					if node == 0: continue
					for frame in node:
						if frame[0]:
							self.Shape.nodeTranslations.append(frame[0])
						if frame[1]:
							self.Shape.nodeRotations.append(frame[1])
						if frame[2]:
							self.Shape.nodeAlignedScales.append(frame[2])

				self.Shape.writeDSQSequence(dsq_file, sequence) # Write only current sequence data
				dsq_file.close()

				# Remove anything we added to the main list
				if sequence.baseTranslation != -1: del self.Shape.nodeTranslations[sequence.baseTranslation:]
				if sequence.baseRotation != -1:    del self.Shape.nodeRotations[sequence.baseRotation:]
				if sequence.baseScale != -1:       del self.Shape.nodeAlignedScales[sequence.baseScale:]
				if sequence.firstTrigger != -1:    del self.Shape.triggers[sequence.firstTrigger:]
				if sequence.firstGroundFrame != -1:
					del self.Shape.groundTranslations[sequence.firstGroundFrame:]
					del self.Shape.groundRotations[sequence.firstGroundFrame:]
				# ^^ Add other data here once exporter has support for it.

				sequence.has_dsq = True
				count += 1
			else:
				dump.writeln("      INTERNAL: %s" % self.Shape.sTable.get(sequence.nameIndex))

				# Dump Frames
				for node in sequence.frames:
					if node == 0: continue
					for frame in node:
						if frame[0]:
							self.Shape.nodeTranslations.append(frame[0])
						if frame[1]:
							self.Shape.nodeRotations.append(frame[1])
						if frame[2]:
							self.Shape.nodeAlignedScales.append(frame[2])

			cur_progress.update()

		# Final pass
		count = 0
		while count != len(self.Shape.sequences):
			# Remove sequences with dsq's
			if self.Shape.sequences[count].has_dsq:
				del self.Shape.sequences[count]
				continue
			# Clear out matters if we don't need them
			if not self.Shape.sequences[count].has_loc: sequence.matters_translation = []
			if not self.Shape.sequences[count].has_rot: sequence.matters_rotation = []
			if not self.Shape.sequences[count].has_scale: sequence.matters_scale = []
			count += 1

		cur_progress.popTask()

	# Gets loc, rot, scale at time frame_idx
	def getTransformAtFrame(self, scene, context, sequence, curveMap, nodeIndex, frame_idx, use_ipo=False):
		global dump
		# Get the node's ipo...
		ipo = sequence.ipo[nodeIndex]
		if ipo == 0: # No ipo for this node, so its not animated
			return None

		loc, rot, scale = None, None, None

		# Determine which bone attributes are modified by *this* IPO block
		has_loc, has_rot, has_scale = sequence.matters_translation[nodeIndex], sequence.matters_rotation[nodeIndex], sequence.matters_scale[nodeIndex]

		if use_ipo:
			# Grab frame number from ipo according to frame_idx
			try:
				frame = ipo.getCurveBeztriple(0, frame_idx)[3]
				#print "DBG: Using keyframe at frame %d" % frame
			except:
				# Frame is missing, so duplicate last
				frame = ipo.getCurveBeztriple(0, ipo.getNBezPoints(0)-1)[3]
				#print "DBG: Using keyframe at frame %d (Duplicated)" % frame
		else:
			# Just switch to frame frame_idx in blender
			frame = frame_idx
			#print "DBG: Using frame %d" % frame

		# Set the current frame in blender to the frame the ipo keyframe is at
		context.currentFrame(int(frame))

		# Update the ipo's current value
		scene.update(1)

		# Add ground frames if enabled
		if sequence.has_ground:
			# Check if we have any more ground frames to add
			targetNumber = getSequenceKey(self.Shape.sTable.get(sequence.nameIndex))['NumGroundFrames']
			if targetNumber != sequence.numGroundFrames:
				# Ok, we can add a ground frame, but do we add it now?
				duration = sequence.numKeyFrames / targetNumber
				if frame >= (duration * (sequence.numGroundFrames+1)):
					# We are ready, lets stomp!
					try:
						bound_obj = Blender.Object.Get("Bounds")
						matf = collapseBlenderTransform(bound_obj)
						rot = Quaternion().fromMatrix(matf).inverse()
						pos = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2))
						self.Shape.groundTranslations.append(pos)
						self.Shape.groundRotations.append(rot)
						sequence.numGroundFrames += 1
					except:
						dump.writeln("Warning: Error getting ground frame %d" % sequence.numGroundFrames)

		# Convert time units from Blender's frame (starting at 1) to second
		# (using sequence FPS)
		time = (frame - 1.0) / sequence.fps
		if sequence.duration < time:
			sequence.duration = time

		if sequence.flags & sequence.Blend:
			# Blended animation, so find the difference between
			# frames and store this

			# If we have loc values...
			if has_loc:
				loc = Vector(
				ipo.getCurveCurval(curveMap['LocX']),
				ipo.getCurveCurval(curveMap['LocY']),
				ipo.getCurveCurval(curveMap['LocZ']))
				#print "BLEND  loc: %f %f %f" % (loc[0],loc[1],loc[2])

			# If we have rot values...
			if has_rot:
				ipo_rot = Quaternion(
				ipo.getCurveCurval(curveMap['QuatX']),
				ipo.getCurveCurval(curveMap['QuatY']),
				ipo.getCurveCurval(curveMap['QuatZ']),
				ipo.getCurveCurval(curveMap['QuatW']))
				#print "BLEND rot: %f %f %f %f" % (ipo_rot[0],ipo_rot[1],ipo_rot[2],ipo_rot[3])
				rot = ipo_rot.inverse()

			# If we have scale values...
			if has_scale:
				# Size is a ratio of the original
				scale = Vector(
				ipo.getCurveCurval(curveMap['SizeX']),
				ipo.getCurveCurval(curveMap['SizeY']),
				ipo.getCurveCurval(curveMap['SizeZ']))
				#print "BLEND scale: %f %f %f" % (scale[0],scale[1],scale[2])
		else:
			# Standard animations, so store total translations
			# If we have loc values...
			if has_loc:
				loc = Vector(
				ipo.getCurveCurval(curveMap['LocX']),
				ipo.getCurveCurval(curveMap['LocY']),
				ipo.getCurveCurval(curveMap['LocZ']))
				#print "REG  loc: %f %f %f" % (loc[0],loc[1],loc[2])
				loc += self.Shape.defaultTranslations[nodeIndex]

			# If we have rot values...
			if has_rot:
				ipo_rot = Quaternion(
				ipo.getCurveCurval(curveMap['QuatX']),
				ipo.getCurveCurval(curveMap['QuatY']),
				ipo.getCurveCurval(curveMap['QuatZ']),
				ipo.getCurveCurval(curveMap['QuatW']))
				#print "REG rot: %f %f %f %f" % (ipo_rot[0],ipo_rot[1],ipo_rot[2],ipo_rot[3])
				rot = ipo_rot.inverse() * self.Shape.defaultRotations[nodeIndex]

			# If we have scale values...
			if has_scale:
				# Size is a ratio of the original
				scale = Vector(
				ipo.getCurveCurval(curveMap['SizeX']),
				ipo.getCurveCurval(curveMap['SizeY']),
				ipo.getCurveCurval(curveMap['SizeZ']))
				#print "REG scale: %f %f %f" % (scale[0],scale[1],scale[2])

		return loc, rot, scale

	# Adds a camera; Treated just like an armature except obviously there are no children.
	def addCamera(self, obj):
		global dump
		dump.writeln("     Camera: %s" % obj.getName())

		# Get the camera's pos and rotation
		matf = collapseBlenderTransform(obj)
		rot = Quaternion().fromMatrix(matf).inverse()
		pos = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2))

		parentId = len(self.Shape.nodes)
		b = Node(self.Shape.sTable.addString(obj.getName()), -1)
		self.Shape.defaultTranslations.append(pos)
		self.Shape.defaultRotations.append(rot)
		self.Shape.nodes.append(b)

	def addArmature(self, obj):
		global dump
		arm = obj.getData()
		dump.writeln("     Armature: %s" % obj.getName())

		startNode = len(self.Shape.nodes)
		# Get the armature's pos and rotation
		matf = collapseBlenderTransform(obj)
		# Add each bone tree
		pos, rot = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2)), Quaternion().fromMatrix(matf).inverse()
		scale = collapseBlenderScale(obj)
		for bone in arm.getBones():
			if bone.getParent() == None: self.addBlenderChildren(bone,MatrixF().identity(), -1, scale)

		# Now collapse the transform if the parent == -1
		for node in range(startNode, len(self.Shape.nodes)):
			if self.Shape.nodes[node].parent == -1:
				self.Shape.defaultTranslations[node] += pos
				self.Shape.defaultRotations[node] = rot * self.Shape.defaultRotations[node]

	def addBlenderChildren(self, bone, matrix, parentId, scale, indent = 0):
		global Prefs, dump
		real_name = bone.getName()
		# Do not add bones on the "BannedBones" list
		for expt in Prefs['BannedBones']:
			if expt == real_name: return

		# Blender bones are defined in their parent's rotational
		# space, but relative to the parent's tail.
		dump.write(" " * (indent+4))
		dump.writeln("^^ Bone [%s] (parent %d)" % (real_name,parentId))

		# Convert to vector
		bhead = Vector(bone.head[0],bone.head[1],bone.head[2])
		btail = Vector(bone.tail[0],bone.tail[1],bone.tail[2])

		# Move into parent space & build rotation
		head = matrix.passPoint(bhead)
		tail = matrix.passPoint(btail)
		# ... and add on scale
		head[0], head[1], head[2] = scale[0]*head[0], scale[1]*head[1], scale[2]*head[2]
		tail[0], tail[1], tail[2] = scale[0]*tail[0], scale[1]*tail[1], scale[2]*tail[2]
		rot = Quaternion().fromMatrix(matrix * blender_bone2matrixf(head, tail, bone.getRoll())).inverse()

		# Add a DTS bone to the shape
		b = Node(self.Shape.sTable.addString(real_name), parentId)

		self.Shape.defaultTranslations.append(head)
		self.Shape.defaultRotations.append(rot)
		self.Shape.nodes.append(b)

		# Add any children this bone may have
		# Child nodes are always translated along the Y axis
		nmat = matrix.identity()
		nmat.setRow(3,Vector(0,(btail - bhead).length(),0)) # Translation matrix
		parentId = len(self.Shape.nodes)-1
		for bChild in bone.getChildren():
			self.addBlenderChildren(bChild, nmat, parentId, scale, indent + 1)

	def process(self):
		global dump, cur_progress
		# Set scene frame to 1 in case we have any problems
		Scene.getCurrent().getRenderingContext().currentFrame(1)
		try:
			cur_progress.pushTask("Initializing Shape...", 2, 0.1)

			Stream = DtsStream(self.dts_basepath+self.dts_filename)
			dump.writeln("> Shape %s" % (self.dts_basepath+self.dts_filename))
			# Now, start the shape export process if the Stream loaded
			if Stream.fs:
				cur_progress.update()

				self.Shape = DtsShape()
				# Create Shape Script (.cs) if requested
				if Prefs['WriteShapeScript']:
					dump.writeln("   Writing script %s" % (self.dts_basepath+self.dts_basename+".cs"))
					self.shapeScript = open(self.dts_basepath+self.dts_basename+".cs", "w")
					self.shapeScript.write("datablock TSShapeConstructor(%sDts)\n" % self.dts_basename)
					self.shapeScript.write("{\n")
					self.shapeScript.write("   baseShape = \"./%s\";\n" % self.dts_filename)

				# Add Root Node to catch meshes and vertices not assigned to the armature
				n = Node(self.Shape.addName("Root"), -1)
				# Add default translations and rotations for this bone
				self.Shape.defaultTranslations.append(Vector(0,0,0))
				self.Shape.defaultRotations.append(Quaternion(0,0,0,1))
				self.Shape.nodes.append(n)

				# Clear any existing objects from detailInfos
				for d in self.detailInfos:
					d.clear()

				cur_progress.update()
				cur_progress.popTask()

				# Import child objects
				if len(self.children) != 0:
					cur_progress.pushTask("Importing Objects...", len(self.children), 0.3)
					for c in self.children:
						if c == None: continue
						self.processChild(c)

						cur_progress.update()
					cur_progress.popTask()

				# Add all actions (will ignore ones not belonging to shape)
				if Prefs['WriteSequences']:
					self.processActions()

				cur_progress.pushTask("Processing Detail Levels...", (len(self.detailInfos)*2) +1, 0.8)
				# Now we have gotten all the detail level info's, store them in the dts
				for info in self.detailInfos:
					# Firstly, don't do anything if we have no objects in this level
					if len(info.objects) == 0:
						if Prefs['AutoDetail']:
							# However, do something if we have automatic detail levels on
							orig_info = self.detailInfos[0]
							if len(info) != 0:
								# Clone mesh and object and decimate, then insert into detail level
								for inf in orig_info:
									clone_obj, clone_msh = inf[0].duplicate(), inf[1].duplicate()
									clone_msh.collapsePrims(info.sz / orig_info.size)
									info.append(clone_obj, clone_msh)
							else: dump.writeln("   Error in decimate : First Detail has no objects!!")
						else: continue
					# Now, construct detail level info
					detail = DetailLevel(self.Shape.addName(info.name), len(self.Shape.subshapes), 0, info.sz, -1, -1, 0)
					subshape = SubShape(0,len(self.Shape.objects),0,len(self.Shape.nodes),len(info.objects),0)
					# Add the objects
					startob = len(self.Shape.objects)
					for o in info.objects:
						object, mesh = o[0], o[1]
						object.firstMesh = startob + (len(self.Shape.objects) - startob)
						detail.polyCount += mesh.getPolyCount()
						self.Shape.objects.append(object)
						self.Shape.meshes.append(mesh)
					# Store constructed detail level info into shape
					self.Shape.subshapes.append(subshape)
					self.Shape.detaillevels.append(detail)

					cur_progress.update()

				# We have finished adding the regular detail levels. Now add the billboard if required.
				if Prefs['Billboard']['Enabled']:
					detail = DetailLevel(self.Shape.addName("BILLBOARD-%d" % (self.numDetails)),-1,
					encodeBillBoard(
						Prefs['Billboard']['Equator'],
						Prefs['Billboard']['Polar'],
						Prefs['Billboard']['PolarAngle'],
						0,
						Prefs['Billboard']['Dim'],
						Prefs['Billboard']['IncludePoles']),
						Prefs['Billboard']['Size'],-1,-1,0)
					self.Shape.detaillevels.insert(self.numDetails,detail)

				dump.writeln("   >Materials added")
				for m in self.Shape.materials.materials:
					dump.writeln("      %s" % m.name)

				# Frame 0
				# (We would add other frames here for visibility / material / vertex animation)
				for o in self.Shape.objects:
					# Note: These are the states for all the objects,
					# in ALL of the detail levels.
					os = ObjectState(1.0, 0, 0)
					self.Shape.objectstates.append(os)

				self.Shape.calcSmallestSize() # Get smallest size where shape is visible

				dump.writeln("   >Detail Levels")
				# Fix up nodes in all the meshes in all the detail levels
				# Also print out final order of detail levels
				for detail in self.Shape.detaillevels:
					dump.writeln("      %s" % (self.Shape.sTable.get(detail.name)))
					if detail.subshape < 0: continue # Skip billboard
					subshape = self.Shape.subshapes[detail.subshape]
					for obj in self.Shape.objects[subshape.firstObject:subshape.firstObject+subshape.numObjects]:
						for tmsh in self.Shape.meshes[obj.firstMesh:obj.firstMesh+obj.numMeshes]:
							'''
								We need to assign nodes to objects and set transforms.
								Rigid meshes can be attached to a single node, in which
								case we need to transform the vertices into the node's
								local space.
							'''
							if tmsh.mtype != tmsh.T_Skin:
								obj.node = tmsh.getNodeIndex(0)
								if obj.node == None:
									# Collision Meshes have to have nodes assigned to them
									# In addition, all orphaned meshes need to be attatched to a root bone
									obj.node = 0 # Root is the first bone
								#dump.writeln("MESH %s node %d" % (self.Shape.sTable.get(obj.name),obj.node))

								# Transform the mesh into node space. The Mesh vertices
								# must all be relative to the bone their attached to
								world_trans, world_rot = self.Shape.getNodeWorldPosRot(obj.node)
								tmsh.translate(-world_trans)
								tmsh.rotate(world_rot.inverse())
							else:
								for n in range(0, tmsh.getNodeIndexCount()):
									# The node transform must take us from shape space to bone space
									world_trans, world_rot = self.Shape.getNodeWorldPosRot(tmsh.getNodeIndex(n))
									tmsh.setNodeTransform(n, world_trans, world_rot)
					cur_progress.update()

				if len(self.Shape.detaillevels) != 0:
					dump.writeln("      Smallest : %s (size : %d)" % (self.Shape.sTable.get(self.Shape.detaillevels[self.Shape.mSmallestVisibleDL].name), self.Shape.mSmallestVisibleSize))
				else:
					dump.writeln("      Warning : Shape contains no detail levels!")

				# Final Mesh Processing
				if Prefs['StripMeshes']:
					dump.writeln("   > Stripping Meshes (max size : %d)" % Prefs['MaxStripSize'])
					# Take into account triangle strips ONLY on non-collision meshes
					for d in self.Shape.detaillevels:
						if (d.size < 0) or (d.subshape < 0): continue
						subshape = self.Shape.subshapes[d.subshape]
						for obj in self.Shape.objects[subshape.firstObject:subshape.firstObject+subshape.numObjects]:
							for tmsh in self.Shape.meshes[obj.firstMesh:obj.firstMesh+obj.numMeshes]:
								tmsh.windStrip(Prefs['MaxStripSize'])
					dump.writeln("     Done.")

				# Finish writing the .cs
				if Prefs['WriteShapeScript']:
					self.shapeScript.write("};\n")
					self.shapeScript.close()

				# Calculate the bounds,
				# If we have an object in blender called "Bounds" of type "Mesh", use that.
				try:
					bound_obj = Blender.Object.Get("Bounds")
					matf = collapseBlenderTransform(bound_obj)
					if bound_obj.getType() == "Mesh":
						bmesh = bound_obj.getData()
						self.Shape.bounds.max = Vector(-10e30, -10e30, -10e30)
						self.Shape.bounds.min = Vector(10e30, 10e30, 10e30)
						for v in bmesh.verts:
							real_vert = matf.passPoint(v)
							self.Shape.bounds.min[0] = min(self.Shape.bounds.min.x(), real_vert[0])
							self.Shape.bounds.min[1] = min(self.Shape.bounds.min.y(), real_vert[1])
							self.Shape.bounds.min[2] = min(self.Shape.bounds.min.z(), real_vert[2])
							self.Shape.bounds.max[0] = max(self.Shape.bounds.max.x(), real_vert[0])
							self.Shape.bounds.max[1] = max(self.Shape.bounds.max.y(), real_vert[1])
							self.Shape.bounds.max[2] = max(self.Shape.bounds.max.z(), real_vert[2])
						# The center...
						self.Shape.center = self.Shape.bounds.max.midpoint(self.Shape.bounds.min)
						# Tube Radius.
                                                dist = self.Shape.bounds.max - self.Shape.center
						self.tubeRadius = Vector2(dist[0], dist[1]).length()
						# Radius...
						self.radius = (self.Shape.bounds.max - self.Shape.center).length()
					else:
						self.Shape.calculateBounds()
						self.Shape.calculateCenter()
						self.Shape.calculateRadius()
						self.Shape.calculateTubeRadius()
				except:
						self.Shape.calculateBounds()
						self.Shape.calculateCenter()
						self.Shape.calculateRadius()
						self.Shape.calculateTubeRadius()

				cur_progress.update()
				cur_progress.popTask()

				# Now we've finished, we can save shape and burn it.
				cur_progress.pushTask("Writing out DTS...", 1, 0.9)
				dump.writeln("Writing out DTS...")
				self.Shape.write(Stream)
				cur_progress.update()
				cur_progress.popTask()

				del Stream
				del self.Shape
			else:
				dump.writeln("   Warning: failed to open shape stream!")
				del self.Shape
				cur_progress.popTask()
				return None
		except Exception, msg:
			dump.writeln("Exception encountered, bailing out.")
			#dump.writeln(Exception)
			del dump
			if self.Shape: del self.Shape
			cur_progress.popTask()
			raise

	# Handles the whole branch
	def handleObject(self):
		global Prefs
		self.clear() # clear just in case we already have children

		# Firstly, it would be nice to know all the paths and filenames (for reuse later)
		self.dts_filename = basename(Blender.Get("filename")) + ".dts"
		self.dts_basepath = basepath(Blender.Get("filename"))
		self.dts_basename = noext(self.dts_filename)

		self.numDetails = 0
		self.numCollision = 0
		self.numLOSCollision = 0

		if len(self.children) > 0: self.clear()

		if len(self.detailSizes) > 0: del self.detailSizes[0:-1]
		if len(self.detailInfos) > 0: del self.detailInfos[0:-1]
		# Gather metrics on children so we have a better idea of what we are dealing with
		for c in getChildren(self.obj):
			self.children.append(self.handleChild(c))

		# Sort detailSizes
		self.detailSizes.sort()
		self.detailSizes.reverse()

		self.detailInfos = [None]*(self.numDetails + self.numCollision + self.numLOSCollision)
		# Create a store of DetailInfo's
		for i in range(0,self.numDetails + self.numCollision + self.numLOSCollision):
			self.detailInfos[i] = DetailInfo()
			if i > (self.numDetails+self.numCollision-1):
				self.detailInfos[i].name = "LOS-%d" % (i-self.numDetails-self.numCollision+9)
				self.detailInfos[i].sz = -1
			elif i > (self.numDetails-1):
				self.detailInfos[i].name = "Collision-%d" % (i-self.numDetails+1)
				self.detailInfos[i].sz = -1
			else:
				self.detailInfos[i].name = "Detail-%d" % i
				self.detailInfos[i].sz = self.detailSizes[i]

'''
	Functions to export shape and load script
'''
#-------------------------------------------------------------------------------------------------
def handleScene():
	global export_tree, dump
	dump.writeln("Processing Scene...")
	# What we do here is clear any existing export tree, then create a brand new one.
	# This is useful if things have changed.
	if export_tree != None: export_tree.clear()
	export_tree = SceneTree(None,Blender.Scene.getCurrent())
	dump.writeln("Cleaning Preference Keys")
	cleanKeys()

def export():
	global dump, cur_progress
	dump.writeln("Exporting...")
	savePrefs()

	cur_progress = Progress()
	cur_progress.pushTask("Done", 1, 1.0)

	if export_tree != None:
		export_tree.process()
		dump.writeln("Finished.")
	else:
		dump.writeln("Error. Not processed scene yet!")

	cur_progress.update()
	cur_progress.popTask()
	del cur_progress

'''
	Gui Handling Code
'''
#-------------------------------------------------------------------------------------------------
# ID's for menu's
Sequence_ID = -1
Mesh_ID = -1
About_ID = -1

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
def initGui():
	global Sequence_ID
	global Mesh_ID
	global About_ID
	global Version
	Blender_Gui.initGui(exit_callback)

	# Colour constants
	shared_border_col = [0.5,0.5,0.5]
	shared_bar_int = [0.75,0.75,0.75]
	shared_bar_end = [0.45,0.45,0.45]

	# Shared Bar - Appears on all sheets
	SharedBar=[	{
						'type' : 'CONTAINER',
						'x' : 0, 'y' : 0, 'w' : 490, 'h' : 35,
						'color_in' : shared_bar_int, 'color_out' : shared_bar_end, 'fade_mode' : 2,
						'color_border' : shared_border_col, 'visible' : True,
						'items' : [
							{
								'type' : 'TEXT',
								'x' : 266, 'y' : 10, 'color' : [1.,1.,1.],
								'value' : "Version %s" % Version, 'size' : "normal", 'visible' : True,
							},
							{
								'type' : 'BUTTON', 'event' : 1,
								'x' : 10, 'y' : 5, 'w' : 60, 'h' : 20,
								'name' : "Sequence", 'tooltip' : "Alter Sequence Options", 'visible' : True, 'instance' : None,
							},
							{
								'type' : 'BUTTON', 'event' : 2,
								'x' : 72, 'y' : 5, 'w' : 60, 'h' : 20,
								'name' : "Mesh", 'tooltip' : "Alter Mesh and Detail Options", 'visible' : True, 'instance' : None,
							},
							{
								'type' : 'BUTTON', 'event' : 3,
								'x' : 134, 'y' : 5, 'w' : 60, 'h' : 20,
								'name' : "Export", 'tooltip' : "Export Model to DTS Format", 'visible' : True, 'instance' : None,
							},
							{
								'type' : 'BUTTON', 'event' : 4,
								'x' : 196, 'y' : 5, 'w' : 60, 'h' : 20,
								'name' : "About", 'tooltip' : "Show Credits", 'visible' : True, 'instance' : None,
							}
						]
					}
				]

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
	global dump
	del dump

'''
	Entry Point
'''
#-------------------------------------------------------------------------------------------------

# Export model
if __name__ == "__main__":
	dump = DumpPrint("%s.log" % noext(Blender.Get("filename")))
	dump.writeln("Torque Exporter %s " % Version)
	dump.writeln("Using blender, version %s" % Blender.Get('version'))
	dump.writeln("**************************")
	loadPrefs()
	# Determine the best course of action
	a = __script__['arg']
	if (a == 'export') or (a == None):
		# Process scene and export (default)
		handleScene()
		export()
		del dump
	elif a == 'config':
		# Process scene and launch config panel
		handleScene()
		initGui()
	else:
		# Something bad happened
		dump.writeln("Error: invalid script arguement '%s'" % a)
