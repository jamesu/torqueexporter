'''
DtsSceneInfo.py

Copyright (c) 2008 Joseph Greenawalt(jsgreenawalt@gmail.com)

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

import Blender
from Blender import Modifier
import string, gc
from DtsPrefs import *
import DtsGlobals
from DTSPython import stripPath
from DTSPython import dump_write, dump_writeln, dump_writeWarning, dump_writeErr
noGeometryTypes = ['Empty', 'Curve', 'Camera', 'Lamp', 'Lattice', 'Armature']

'''
NodeInfoClass

This class stores static node information for a node and provides a standard interface
for getting dynamic node transform data from Blender whether the node was created from a
Blender object or Blender bone.
'''
class nodeInfoClass:
	def __init__(self, nodeName, blenderType, blenderObj, parentNI, armParentNI=None):
		self.dtsNodeName = nodeName  # <- name of the (exported) dts node
		self.dtsObjName = None # <- name of the dts object (for meshes)
		self.blenderObjName = blenderObj.name # either a blender bone or blender object depending on blenderType
		self.blenderType = blenderType		
		self.hasGeometry = not (blenderObj.getType() in noGeometryTypes)
		self.detailLevels = []		
		self.armParentNI = armParentNI
		#self.isBannedNode = self.isBanned() # <- whether or not the node is in the banned nodes list
		self.isExportable = self.__isInExportLayer() # <- whether or not the node is in a layer that is being exported
		self.layers = [layer for layer in blenderObj.layers] # make sure we're not keeping a reference to a blender-owned object
		self.parentNI = parentNI

		if blenderType == "bone":
			self.originalBoneName = nodeName
		else:
			originalBoneName = None

		#if blenderType == "object":
		#	pass
		
		if self.hasGeometry:
			self.dtsObjName = SceneInfoClass.getStrippedMeshName(nodeName)
			self.dtsNodeName = SceneInfoClass.getStrippedMeshName(nodeName)


	# find a non-excluded node to use as a parent for a dts object
	# Returns the object's own generated node if it's valid.
	def getGoodMeshParentNI(self):
		pNI = self
		while (pNI != None) and ((not pNI.isExportable) or pNI.isBanned()):
			pNI = pNI.parentNI
		return pNI

	# find a non-excluded node to use as a parent for another node
	# never returns the object's own generated node
	def getGoodNodeParentNI(self, debug=False):
		pNI = self.parentNI
		while (pNI != None) and ((not pNI.isExportable) or pNI.isBanned()):
			pNI = pNI.parentNI
		
		# return whatever we found.
		return pNI

	def isBanned(self):
		# is the node on the banned nodes list?
		banned = (self.dtsNodeName.upper() in DtsGlobals.Prefs['BannedNodes'])
		return banned
	
		
	def __isInExportLayer(self):
		# is the node in a layer that is exported?
		goodLayer = False
		obj = self.getBlenderObj()
		for dlName in DtsGlobals.Prefs['DetailLevels'].keys():
			dl = DtsGlobals.Prefs['DetailLevels'][dlName]			
			for layer in obj.layers:
				if layer in dl:
					goodLayer = True
					break
		retval = goodLayer
		return retval
	
	def getBlenderObj(self):
		try: retval = Blender.Object.Get(self.blenderObjName)
		except: retval = None
		return retval

#-------------------------------------------------------------------------------------------------			
'''
Replacement for SceneTree class, stores metadata and parent child relationships for all scene
objects for easy access.

Note: Prefs object must be initialized before the SceneInfo object.
'''

class SceneInfoClass:


	#################################################
	#  Initialization/Refresh
	#################################################

	def __init__(self, prefs, issueWarnings=False):	
		gc.enable()
		DtsGlobals.Prefs = prefs		
		self.refreshAll(issueWarnings)

	def refreshAll(self, issueWarnings=False):
		# node lists and indicies
		self.allThings = [] # <- contains info for all objects and bones in the blender scene.
		self.meshExportList = [] # <- contains all exportable meshes, even those with banned object-nodes.
		self.nodes = {} # <- indexed by dtsNodeName, contains all nodes in exportable layers after init (including banned nodes)
		self.armatures = {} # <- indexed by actual blender object name(?)		
		self.DTSObjects = {} # <- indexed by dtsObjName (final dts object name)
		self.issueWarnings = issueWarnings #<- so we don't have to pass this around
		
		# translation lookup dictionary for vertex group names
		self.boneNameChanges = {}
		
		# take out the trash
		gc.collect()
		
		# build the tree		
		self.__populateData()
		self.issueWarnings = False #<- make sure we don't somehow issue warnings when we shouldn't.

	def __alreadyExists(self, n, getTest=False):
		# see if we've got a naming conflict		
		alreadyExists = False
		try:
			test = self.nodes[n.dtsNodeName]
			alreadyExists = True
		except: test = None
		if getTest: return alreadyExists, test
		else: return alreadyExists

	# gets the highest LOD for a given node (nodeInfo)
	def getHighestLodNI(self, n):
		highestSize = -1
		for dlName in n.detailLevels:
			dlSize = DtsGlobals.getTrailingNumber(dlName)
			if dlSize > highest: highest = dlSize
		return highestSize

	# utility method used in __safeAddToNodesDict below
	# returns the nodeInfo struct with the highest lod assignment.
	def getHighestLodNI(self, n1, n2):
		if self.getHighestLodNI(n1) > self.getHighestLodNI(n2):
			return n1
		else:
			return n2

	# add a nodes to the (good, exported) nodes dictionary
	# does not change dts object names, only node names
	def __safeAddToNodesDict(self, n):		
		alreadyExists, existing = self.__alreadyExists(n, True)
		if alreadyExists:
			finalName = n.dtsNodeName
			if self.issueWarnings:
				warnString = "  ****************************************************************************\n"\
					   + "   Warning: " + n.blenderType + " node \"" + finalName + "\" (Blender Object:"+n.blenderObjName+") conflicts\n"\
					   + "    with existing " + existing.blenderType + " node name \"" + finalName + "\" (Blender Object:" + existing.blenderObjName + ") !"
				dump_writeWarning(warnString)
			i = 1
			newName = finalName + ("(%s)" % str(i))
			n.dtsNodeName = newName			
			while(self.__alreadyExists(n)):
				i += 1
				newName = finalName + ("(%s)" % str(i))
				n.dtsNodeName = newName
				
				
			if self.issueWarnings:
				message = "     Changed name of " + n.blenderType + " node to: \"" + newName + "\"\n"\
				        + "   ****************************************************************************\n"
				dump_writeln(message)
				
			n.dtsNodeName = newName
			try: x = self.boneNameChanges[n.armParentNI.blenderObjName]
			except: self.boneNameChanges[n.armParentNI.blenderObjName] = {}
			self.boneNameChanges[n.armParentNI.blenderObjName][n.originalBoneName] = newName
			self.nodes[newName] = n
		else:
			self.nodes[n.dtsNodeName] = n			
			if n.armParentNI != None:
				try: x = self.boneNameChanges[n.armParentNI.blenderObjName]
				except: self.boneNameChanges[n.armParentNI.blenderObjName] = {}
				self.boneNameChanges[n.armParentNI.blenderObjName][n.originalBoneName] = n.originalBoneName



	# recursive, for internal use only
	# adds a blender object (sub) tree to the allThings list recursively.
	def __addTree(self, obj, parentNI):
		#   "obj" is a blender object of any type
		#   "parentNI" is the parent object (NodeInfo object) of obj

		# skip temp objects
		if obj.name == "DTSExpObj_Tmp": return

		#nodeName = obj.name
		blenderType = "object"
		blenderObj = obj


		# create a new nodeInfo object for the Blender object
		n = nodeInfoClass(obj.name, blenderType, blenderObj, parentNI)

		# always keep track of armatures, even if they're not exported at all.
		bObjType = obj.getType()
		if (bObjType == 'Armature'):
			# add the node to the armatures dictionary if needed
			self.armatures[n.blenderObjName] = n

		# add the new node to the allThings list
		self.allThings.append(n)
		
		# set up detail levels
		if n.isExportable and n.hasGeometry:
			# add mesh node info to detail levels
			for dlName in DtsGlobals.Prefs['DetailLevels'].keys():
				dl = DtsGlobals.Prefs['DetailLevels'][dlName]
				for layer in obj.layers:
					if layer in dl:
						# single meshes *can* exist in multiple detail levels
						n.detailLevels.append(dlName)
						break

		
		
		
		# always add bone nodes
		if (bObjType == 'Armature'):
			tempBones = {}
			# add armature bones if needed
			armDb = obj.getData()
			for bone in filter(lambda x: x.parent==None, armDb.bones.values()):
				self.__addBoneTree(obj, n, bone, armDb, n, tempBones)

		# add child trees
		for child in filter(lambda x: x.parent==obj, Blender.Object.Get()):
			parentBoneName = child.getParentBoneName()
			if (obj.getType() == 'Armature') and (parentBoneName != None):					
				parentNode = tempBones[parentBoneName]
				self.__addTree(child, parentNode)
			else:
				self.__addTree(child, n)
		

	
	# adds a bone tree to the allThings list recursively, for internal use only
	def __addBoneTree(self, blenderObj, parentNI, boneOb, armDb, armParentNI, boneDictionary):
		n = nodeInfoClass(boneOb.name, 'bone', blenderObj, parentNI, armParentNI)
		boneDictionary[boneOb.name] = n
		self.allThings.append(n)
		# add child trees
		for bone in filter(lambda x: x.parent==boneOb, armDb.bones.values()):					
			self.__addBoneTree(blenderObj, n, bone, armDb, armParentNI, boneDictionary)

	# for debugging
	def __printTree(self, ni, indent=0):
		pad = ""
		for i in range(0, indent):
			pad += " "
		print pad+"|"
		print pad+"Node:", ni.dtsNodeName, "(",ni.blenderObjName,")"
		try:
			nn = ni.getGoodNodeParentNI().dtsNodeName
			print pad+"Parent:", nn,"(",ni.getGoodNodeParentNI().blenderObjName,")"
		except: print pad+"No Parent."
		indent += 3
		for nic in filter(lambda x: x.getGoodNodeParentNI()==ni, self.nodes.values()):
			self.__printTree(nic, indent)
			

	def __populateData(self):
		startTime = Blender.sys.time()
		
		# go through each Blender object and bone and add subtrees (construct allThings list)
		for obj in filter(lambda x: x.parent==None, Blender.Object.Get()):
			if obj.parent == None:
				self.__addTree(obj, None)
		
		# nodes that should be exported
		nodeExportList = filter(lambda x: x.isExportable, self.allThings)

		# meshes that should be exported
		meshExportList = filter(lambda x: (x.hasGeometry==True) and (x.isExportable==True), self.allThings)
		self.meshExportList = meshExportList
		
		# construct dts objects
		
		dlNames = DtsGlobals.Prefs['DetailLevels'].keys()

		# check that every mesh within a given detail level has a unique dts object name
		for dlName in dlNames:
			dlMeshes = filter(lambda x: dlName in x.detailLevels, meshExportList)
			found = {}
			for meshNI in dlMeshes:
				dtsObjName = meshNI.dtsObjName
				try: x = found[dtsObjName]
				except:
					# new dts object
					found[dtsObjName] = []
				found[dtsObjName].append(meshNI)
			
			for dtsObjName in found.keys():
				foundList = found[dtsObjName]
				if len(foundList) > 1:
					dtsObjName = foundList[0].dtsObjName
					nameList = []
					for ni in foundList: nameList.append(ni.blenderObjName)
					
					if self.issueWarnings:
						warnString = "  ****************************************************************************\n"\
						           + "   Warning: Multiple Blender mesh names in "+dlName+" all reduce to the same DTS\n"\
						           + "    Object name: \""+dtsObjName + "\"\n"\
						           + "     The exporter will use the original names for these meshes and any nodes\n"\
						           + "     generated from them.  This may result in duplicate or unneccesary nodes,\n"\
						           + "     extra animation tracks, and inefficent mesh packing in the exported dts\n"\
						           + "     file."
						dump_writeWarning(warnString)
					
					# fix dtsObject names.
					for ni in foundList:
						if self.issueWarnings:
							dump_writeln("      Changed dts object and node name for Blender mesh \""+ni.blenderObjName+"\"")
							dump_writeln("        from \""+ni.dtsObjName+"\" to \""+ni.blenderObjName+"\".")
						ni.dtsObjName = ni.blenderObjName
						ni.dtsNodeName = ni.dtsObjName

					if self.issueWarnings:
						dump_writeln("  ****************************************************************************\n")


				
		# build DTSObjects index
		# create 'None' lists for DTS Objects
		for ni in meshExportList:
			# create a dts object if it doesn't already exist.
			try: test = self.DTSObjects[ni.dtsObjName]
			except:
				# populate dts object with "None" entries for each dl
				self.DTSObjects[ni.dtsObjName] = {}
				for dl in dlNames:
					self.DTSObjects[ni.dtsObjName][dl] = None
		
		sortedDLs = DtsGlobals.Prefs.getSortedDLNames()

		# insert meshes into correct slots in dts object lists.
		for ni in meshExportList:
			# insert meshes into the correct detail levels
			for dl in ni.detailLevels:
				self.DTSObjects[ni.dtsObjName][dl] = ni

		# construct nodes dictionary, fixing node names if dups exist.
		for ni in nodeExportList:
			# skip object nodes that need skippin'
			if ni.blenderType == 'object' and ni.dtsObjName != None:
				# don't add nodes for skinned meshes
				if self.isSkinnedMesh(ni.getBlenderObj()): continue
				# only add nodes for the highest lod version of a mesh
				dtsObj = self.DTSObjects[ni.dtsObjName]
				for dlName in sortedDLs:
					highest = dtsObj[dlName]
					if highest != None: break
				if highest != ni: continue
			
			self.__safeAddToNodesDict(ni)
		
		#print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
		#for ni in filter(lambda x: x.getGoodNodeParentNI()==None, self.nodes.values()):
		#	self.__printTree(ni)
		#print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++"


		

		'''

		# ----------------
		# debug prints
		sortedKeys = self.detailLevels.keys()
		sortedKeys.sort( lambda x,y: cmp(DtsGlobals.Prefs.getTrailingNumber(x), DtsGlobals.Prefs.getTrailingNumber(y)) )
		sortedKeys.reverse()

		# print header row
		fieldWidth = 20
		tempString = "DtsObject".ljust(18) + "| "
		for dlName in sortedKeys:
			tempString += dlName.ljust(20)
		print tempString

		
		for obName in self.DTSObjects.keys():
			tempString = ""
			tempString += obName.ljust(18) + "| "
			for dlName in sortedKeys:				
				c = self.DTSObjects[obName][dlName]
				if c == None: tempString += "None".ljust(20)
				else: tempString += c.blenderObjName.ljust(20)
			print tempString

		# ----------------
		'''
		endTime = Blender.sys.time()
		print "__populateData finished in", endTime - startTime


	#################################################
	#  File name and path methods
	#################################################

	# Gets the base file name from a full file path (no extension)
	def fileNameFromPath(filepath):
		if "\\" in filepath:
			words = string.split(filepath, "\\")
		else:
			words = string.split(filepath, "/")
		words = string.split(words[-1], ".")
		return SceneInfoClass.__noext(string.join(words[0:len(words)], "."))
	
	fileNameFromPath = staticmethod(fileNameFromPath)

	# Gets base path from a full file path, with trailing slash
	def pathPortion(filepath):
		if "\\" in filepath: sep = "\\"
		else: sep = "/"
		words = string.split(filepath, sep)
		return string.join(words[:-1], sep)
	
	pathPortion = staticmethod(pathPortion)


	# Gets the Base Name from the File Path
	def getDefaultBaseName():
		filepath = Blender.Get("filename")
		if "\\" in filepath:
			words = string.split(filepath, "\\")
		else:
			words = string.split(filepath, "/")
		words = string.split(words[-1], ".")
		return SceneInfoClass.__noext(string.join(words[0:len(words)], "."))
	
	getDefaultBaseName = staticmethod(getDefaultBaseName)

	# Gets base path with trailing /
	def getDefaultBasePath():
		filepath = Blender.Get("filename")
		if "\\" in filepath: sep = "\\"
		else: sep = "/"
		words = string.split(filepath, sep)
		return string.join(words[:-1], sep)
	
	getDefaultBasePath = staticmethod(getDefaultBasePath)

	def getPathSeparator():
		pathSeparator = DtsGlobals.pathSeparator
		filepath = Blender.Get("filename")
		if "\\" in filepath: pathSeparator = "\\"
		else: pathSeparator = "/"
		DtsGlobals.pathSeparator = pathSeparator
		return pathSeparator
	
	getPathSeparator = staticmethod(getPathSeparator)

	# Strips the extension from a file name
	def __noext(filepath):
		words = string.split(filepath, ".")
		if len(words)==1: return filepath
		return string.join(words[:-1], ".")
	
	__noext = staticmethod(__noext)


	#################################################
	#  Images and materials
	#################################################


	# Strip image names of trailing extension
	def stripImageExtension(imagename, filename=""):
		imageExts = ['jpg', 'jpeg', 'gif', 'png', 
			     'tif', 'tiff', 'mpg', 'mpeg',
			     'tga', 'pcx', 'xcf', 'pix',
			     'eps', 'fit', 'fits', 'jpe',
			     'ico', 'pgm', 'psd', 'ps',
			     'ppm', 'bmp', 'pcc', 'xbm',
			     'xpm', 'xwd', 'bitmap']
		temp = ""
		if filename != "": filename = stripPath(filename)
		if len(imagename) < len(filename) and imagename == filename[0:len(imagename)]:
			temp = string.split(filename,".")
		else:
			temp = string.split(imagename,".")
		if len(temp)==1: return temp[0]
		retVal = ""
		for i in range(0, len(temp)):
			if not temp[i].lower() in imageExts:
				retVal += (temp[i] + ".")
		retVal = retVal[0:len(retVal)-1] # remove trailing "."
		return retVal

	stripImageExtension = staticmethod(stripImageExtension)

	# not static because it needs to know about detail levels.
	def getDtsMaterials(self):
		# loop through all faces of all meshes in visible detail levels and compile a list
		# of unique images that are UV mapped to the faces.
		imageList = []	
		for ni in self.meshExportList:
			obj = ni.getBlenderObj()
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
						imageName = SceneInfoClass.stripImageExtension(objData.materials[face.mat].name)
						if not (imageName in imageList):
							imageList.append(imageName)

				# Otherwise we do have an image assigned to the face, so add it to the imageList.
				else:
					imageName = SceneInfoClass.stripImageExtension(face.image.getName(), face.image.getFilename())
					if not (imageName in imageList):
						imageList.append(imageName)



		return imageList
	
	# gets a dts material name for a given Blender mesh primitive
	def getFaceDtsMatName(face, msh):
		imageName = None
		try: imageName = SceneInfoClass.stripImageExtension(face.image.getName(), face.image.getFilename())
		#except AttributeError:
		except (ValueError, AttributeError):
			# there isn't an image assigned to the face...
			# do we have a material index?
			try: mat = msh.materials[face.mat]
			except IndexError: mat = None
			if mat != None:
				# we have a material index, so get the name of the material
				imageName = SceneInfoClass.stripImageExtension(mat.name)

		return imageName
		
	getFaceDtsMatName = staticmethod(getFaceDtsMatName)
	
	# gets the names of all Blender images with extensions stripped
	def getAllBlenderImages():
		imageNames = []
		for img in Blender.Image.Get():
			imageNames.append( SceneInfoClass.stripImageExtension(img.getName(), img.getFilename()) )
		return imageNames
	
	getAllBlenderImages = staticmethod(getAllBlenderImages)
	

	#################################################
	#  Nodes
	#################################################


	# get the names of nodes in all exported layers
	def getAllNodeNames(self):
		temp = []
		for ni in self.nodes.values():
			temp.append(ni.dtsNodeName)
		temp.sort()
		return temp

	# get the names of all object generated nodes
	def getObjectNodeNames(self):
		temp = []
		nodes = filter(lambda x: (x.blenderType=='object'), self.nodes.values())
		for ni in nodes:
			temp.append(ni.dtsNodeName)
		temp.sort()
		return temp

	# get the names of all bone generated nodes
	def getBoneNodeNames(self):
		temp = []
		nodes = filter(lambda x: (x.blenderType=='bone'), self.nodes.values())
		for ni in nodes:
			temp.append(ni.dtsNodeName)
		temp.sort()
		return temp

	#################################################
	#  Sequences
	#################################################

	
	# gets the name portion of a sequence marker string
	def __getSeqMarkerName(string):
		strings = string.split(':')
		if len(strings) >= 2:
			return strings[0]
		else:
			return None
	
	__getSeqMarkerName = staticmethod(__getSeqMarkerName)
			
	# gets the start/end flag from a sequence marker string.
	# returns a (lowercase) string, either "start" or "end"
	def __getSeqMarkerType(string):
		strings = string.split(':')
		if len(strings) >= 2:
			return strings[1].lower()
		else:
			return None
	
	__getSeqMarkerType = staticmethod(__getSeqMarkerType)
	
	# called by prefs refreshSequencePrefs
	# returns a dictionary containing sequence names, start and end frames
	# in the form {'mySequence':[0,10], ...}
	def getSequenceInfo():
		foundSequences = []
		markedList = Blender.Scene.GetCurrent().getTimeLine().getMarked()
		
		sequences = {}
		
				
		# look for start frames
		for frameNum in markedList:
			markerNames = markedList[frameNum]
			for markerName in markerNames:
				seqName = SceneInfoClass.__getSeqMarkerName(markerName)
				seqMarkerType = SceneInfoClass.__getSeqMarkerType(markerName)
				# do we have a valid start sequence marker?
				if seqName != None and seqMarkerType == 'start':
					# create our key
					sequences[seqName] = [frameNum]


		# look for the end frames
		for frameNum in markedList:
			markerNames = markedList[frameNum]
			for markerName in markerNames:
				seqName = SceneInfoClass.__getSeqMarkerName(markerName)
				seqMarkerType = SceneInfoClass.__getSeqMarkerType(markerName)
				# do we have a valid start sequence marker?
				if seqName != None and seqMarkerType == 'end':
					# try to get the key
					try: x = sequences[seqName]
					except: continue
					# add the end frame
					sequences[seqName].append(frameNum)
		
		# discard sequences without both a start and end frame
		# and trim extra end frames if the user is being snarky :-)
		for seqName in sequences.keys():
			if len(sequences[seqName]) < 2:
				del sequences[seqName]
				continue
			sequences[seqName] = sequences[seqName][0:2]
		
		# discard sequences with zero or negative frames
		for seqName in sequences.keys():
			if sequences[seqName][1] - sequences[seqName][0] < 1:
				del sequences[seqName]
					
		return sequences
	
	getSequenceInfo = staticmethod(getSequenceInfo)


	#################################################
	#  Meshes and DTS objects
	#################################################


	# strips the last '.' and everything following it from the mesh name.
	def getStrippedMeshName(meshName):
		names = meshName.split("_")
		detail_name_dot_index = names[0].rfind(".")
		if detail_name_dot_index != -1:
			detail_name = names[0][0:detail_name_dot_index]
		else:
			detail_name = names[0].split(".")[0]
		return detail_name

	getStrippedMeshName = staticmethod(getStrippedMeshName)
	
	# gets dts object names (unique mesh names across all detail levels, minus trailing extension)
	def getDtsObjectNames(self):
		uniqueNames = {}
		for dl in self.detailLevels.values():
			for meshNI in dl:
				dtsObjName = meshNI.dtsObjName
				uniqueNames[dtsObjName] = 0
		return uniqueNames

	# test whether or not a mesh object is skinned
	def isSkinnedMesh(o):
		hasArmatureDeform = False
		for mod in o.modifiers:
			if mod.type == Blender.Modifier.Types.ARMATURE:
				hasArmatureDeform = True
		# Check for an armature parent
		if (o.parentType == Blender.Object.ParentTypes['ARMATURE']) and (o.parentbonename == None) :
			hasArmatureDeform = True

		return hasArmatureDeform
		
	isSkinnedMesh = staticmethod(isSkinnedMesh)

	def getSkinArmTargets(self, o):
		targets = []
		hasArmatureDeform = False
		for mod in o.modifiers:
			if mod.type == Blender.Modifier.Types.ARMATURE:
				targetObj = mod[Modifier.Settings.OBJECT]
				if targetObj != None and targetObj.getType() == 'Armature':
					targets.append(self.armatures[targetObj.name])
		# Check for an armature deform parent
		if (o.parentType == Blender.Object.ParentTypes['ARMATURE']) and (o.parentbonename == None) :
			targetObj = o.getParent()
			if targetObj != None and targetObj.getType() == 'Armature':
				if not (self.armatures[targetObj.name] in targets):
					targets.append(self.armatures[targetObj.name])
		return targets



	def translateVertGroupNames(self, meshName, names, armNIList):
		# issue warnings if mesh is multi-skinned and bone matching vgroup
		# name exists in more than one of the target armatures
		for name in names:
			foundList = []
			for armNI in armNIList:
				try: newName = self.boneNameChanges[armNI.blenderObjName][name]
				except: newName = None
				if newName != None: foundList.append(name)
			if len(foundList) > 1:
				warnString = "\n  ****************************************************************************\n"\
				+ "  Warning: Vertex group \"" + name + "\" in multi-skinned mesh \"" + meshName +"\"\n"\
				+ "   could not be resolved because a bone matching the name of the vertex group\n"\
				+ "   exists in more than one of the target armatures.\n"\
				+ "  ****************************************************************************\n"
				dump_writeWarning(warnString)

		output = []
		for name in names:
			for armNI in armNIList:
				try:
					output.append(self.boneNameChanges[armNI.blenderObjName][name])
					break
				except: continue
				
		return output
			

	#################################################
	#  Misc
	#################################################


	# Gets the children of an object
	def getChildren(self, obj):
		return filter(lambda x: x.parent==obj, Blender.Object.Get())

	# Gets all the children of an object (recursive)
	def getAllChildren(self, obj):
		obj_children = getChildren(obj)
		for child in obj_children[:]:
			obj_children += getAllChildren(child)
		return obj_children

	#################################################
	#  These methods are used to detect and warn
	#   on a certain condition that causes skinned mesh
	#   animations to go wonky.  See long note/explanation
	#   in Dts_Blender.py.
	#################################################
	
	# todo - what happens if parent is a different armature?
	
	# gets a list of meshes that have an armature modifier but not
	# an armature parent.
	def __getMeshesOfConcern(self):
		foundList = []
		for ni in self.meshExportList:
			hasExplicitModifier = False
			hasArmDeformParent = False
			hasArmObjParent = False
			# Check for an armature modifier
			o = ni.getBlenderObj()
			for mod in o.modifiers:
				if mod.type == Blender.Modifier.Types.ARMATURE:
					hasExplicitModifier = True
			# Check for an armature parent
			try:				
				if (o.parentType == Blender.Object.ParentTypes['ARMATURE']) and (o.parentbonename == None):
					hasArmDeformParent = True
				if (o.parentType == Blender.Object.ParentTypes['OBJECT']) and (o.parentbonename == None):
					hasArmObjParent = True
				
			except: pass
			# add mesh to the list if we've got a modifier, but no armature parent.
			if hasExplicitModifier and not hasArmDeformParent:
				foundList.append(ni)
			
		return foundList
	
	
	# Gets a list of armatures ni structs that are exportable
	# and are targets of an armature modifier without an armature parent
	# for the mesh with the modifier.
	def getArmaturesOfConcern(self):
		concernList = []
		# first make a list of "armature modifier" target armatures
		for ni in self.__getMeshesOfConcern():
			o = ni.getBlenderObj()
			# find the armature modifier(s)
			for mod in o.modifiers:
				if mod.type == Blender.Modifier.Types.ARMATURE:
					concernList.append(mod[Modifier.Settings.OBJECT].name)
		retval = [self.armatures[armName] for armName in concernList]
		return retval

	# get meshes that need the warning
	def getWarnMeshes(self, badArmNIList):
		warnings = []
		badArmNameList = [armNI.blenderObjName for armNI in badArmNIList]
		for meshNI in self.__getMeshesOfConcern():
			o = meshNI.getBlenderObj()
			# find the armature modifier(s)
			for mod in o.modifiers:
				if mod.type == Blender.Modifier.Types.ARMATURE:
					if mod[Modifier.Settings.OBJECT].name in badArmNameList:
						warnings.append([o.name, mod[Modifier.Settings.OBJECT].name])
		return warnings
						
			