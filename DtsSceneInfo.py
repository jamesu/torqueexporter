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
			self.originalBoneName = None

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
		self.armatures = {} # <- indexed by actual blender object name
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
			if n.armParentNI != None:
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
		for child in filter(lambda x: x.parent==obj, Blender.Scene.GetCurrent().objects):
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


	# adds parent stacks to armature nodes for later lookup (used when tranforming bones from
	# armature space to world space)
	def __addArmatureParentStacks(self):
		for armNI in self.armatures.values():
			armNI.parentStack = []
			armNIParent = armNI.parentNI
			while armNIParent != None:
				armNI.parentStack.append(armNIParent)
				armNIParent = armNIParent.parentNI
			

	def __populateData(self):
		#startTime = Blender.sys.time()
		
		# go through each Blender object and bone and add subtrees (construct allThings list)
		for obj in filter(lambda x: x.parent==None, Blender.Scene.GetCurrent().objects):
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

	
		# construct nodes dictionary, fixing node names if dups exist
		# and flattening the lod hierarchy as we go.
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
				if highest != ni:
					continue
				
				# flatten hierarcy, reparent to highest LOD version of parent
				pNI = ni.getGoodNodeParentNI()
				if pNI != None and pNI.blenderType == 'object' and pNI.dtsObjName != None:
					# find highest lod version of parent object
					dtsObj = self.DTSObjects[pNI.dtsObjName]
					for dlName in sortedDLs:
						highest = dtsObj[dlName]
						if highest != None: break
					if highest != None and highest != pNI:
						# reparent to highest
						ni.parentNI = highest

			self.__safeAddToNodesDict(ni)
		
		
		# create armature parent stacks for use in DtsPoseUtil
		self.__addArmatureParentStacks()

		'''
		print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
		for ni in filter(lambda x: x.getGoodNodeParentNI()==None, self.nodes.values()):
			self.__printTree(ni)
		print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
		'''

		

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
		#endTime = Blender.sys.time()
		#print "__populateData finished in", endTime - startTime


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
		retVal = SceneInfoClass.__noext(string.join(words[0:len(words)], "."))
		if retVal == "": retVal = "UNTITLED"
		return retVal
	
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

	imageExts = ['jpg', 'jpeg', 'gif', 'png', 
		     'tif', 'tiff', 'mpg', 'mpeg',
		     'tga', 'pcx', 'xcf', 'pix',
		     'eps', 'fit', 'fits', 'jpe',
		     'ico', 'pgm', 'psd', 'ps',
		     'ppm', 'bmp', 'pcc', 'xbm',
		     'xpm', 'xwd', 'bitmap']


	# Strip image names of trailing extension
	def stripImageExtension(imagename, filename=""):
		
		imageExts = SceneInfoClass.imageExts		
		temp = ""
		
		# strip the path from the filename
		if filename != "": filename = stripPath(filename)
		
		# determine whether to use the image name or file name
		if len(imagename) < len(filename) and imagename == filename[0:len(imagename)]:
			temp = string.split(filename,".")
		else:
			temp = string.split(imagename,".")
		
		# early out if there's only one segment (no extension)
		if len(temp)==1: return temp[0]
		
		# add on the first segment.
		retVal = temp[0] + "."		
		
		# add each segment, ignoring any segment that matches an image extension
		for i in range(1, len(temp)):
			if not temp[i].lower() in imageExts:
				retVal += (temp[i] + ".")
		
		# remove trailing "."
		retVal = retVal[0:len(retVal)-1] 
		
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
				matName = SceneInfoClass.getFaceDtsMatName(face, objData)
				if matName != None: imageList.append(matName)

		retVal = list(set(imageList))		
		return retVal

	
	# gets a dts material name for a given Blender mesh primitive
	def getFaceDtsMatName(face, msh):
		imageName = None
		try: image = face.image
		except ValueError: image = None
		if image == None:
			# there isn't an image assigned to the face...
			# do we have a material index?
			if face.mat != None:
				try: mat = msh.materials[face.mat]
				except: return None
				if mat == None: return None
				# we have a material index, so get the name of the material
				imageName = SceneInfoClass.stripImageExtension(mat.name)
				#imageName = mat.name
				return imageName

		else:
			# we have an image
			imageName = SceneInfoClass.stripImageExtension(face.image.getName(), face.image.getFilename())
			#imageName = face.image.getName()
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

	
	# gets the length of an action
	def __getActionLength(actName):
		act = Blender.Armature.NLA.GetActions()[actName]
		min = 65535
		max = 1
		for frNum in act.getFrameNumbers():
			if frNum > max: max = int(round(frNum))
			if frNum < min: min = int(round(frNum))
		retVal = int(max-min)
		return max
	
	__getActionLength = staticmethod(__getActionLength)
	
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

	# find a named marker on the timeline
	def findMarker(markerName):
		markedList = Blender.Scene.GetCurrent().getTimeLine().getMarked()
		for frameNum in markedList:
			markerNames = markedList[frameNum]
			for mn in markerNames:
				if mn.upper() == markerName.upper():
					return frameNum
		return None

	findMarker = staticmethod(findMarker)
	
	# returns true if the given frame number has multiple markers
	def hasMultipleMarkers(frameNum):
		markedList = Blender.Scene.GetCurrent().getTimeLine().getMarked()
		retVal = False
		try: markerNames = markedList[frameNum]
		except: markerNames = []
		if len(markerNames) > 1:
			retVal = True
		return retVal
	
	hasMultipleMarkers = staticmethod(hasMultipleMarkers)
	
	# returns True if a frame on the timeline has no markers.
	def isNotMarked(frameNum):
		retVal = True
		markedList = Blender.Scene.GetCurrent().getTimeLine().getMarked()
		try: x = markedList[frameNum]
		except: retVal = False
		return retVal
		
	isNotMarked = staticmethod(isNotMarked)
	
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

		# look for animation triggers within each frame range
		for seqName in sequences.keys():
			startFrame, endFrame = sequences[seqName][0], sequences[seqName][1]
			# check all frames in range
			for fr in range(startFrame, endFrame + 1):				
				try: markerNames = markedList[fr]
				except: continue
				for markerName in markerNames:
					# is it a trigger marker?
					if markerName[0:7].lower() == "trigger":
						# parse out the trigger info
						settings = markerName.split(':')
						# do we have the correct number of segments?
						if len(settings) == 3:
							# todo - warn when trigger names are invalid?
							try: trigNum = int(settings[1])
							except: continue
							if settings[2].lower() == "on": trigState = True
							elif settigns[2].lower() == "off": trigState = False
							else: continue						
							sequences[seqName].append([trigNum, int(round(fr-startFrame)), trigState])

		return sequences
	
	getSequenceInfo = staticmethod(getSequenceInfo)

	# deletes a named marker
	# fails silently if the marker name does not exist.
	# Warns user with a popup if the marker could not be deleted
	def delMarker(markerName):
		frameNum = SceneInfoClass.findMarker(markerName)
		if frameNum == None: return
		if SceneInfoClass.hasMultipleMarkers(frameNum):
			message = "Could not delete sequence marker \'"\
			+ markerName + "\' on frame " + str(frameNum)\
			+ " because there is more than one marker on the frame!%t|Cancel"
			x = Blender.Draw.PupMenu(message)
			del x
			return False
		else:
			Blender.Scene.GetCurrent().getTimeLine().delete(frameNum)
		return True
	
	delMarker = staticmethod(delMarker)
		
	# Deletes all sequence markers that match the given name
	def delSeqMarkers(seqName):
		startName = seqName + ":start"
		endName = seqName + ":end"		
		# see if both markers are alone on their respective frames.
		startFrame = SceneInfoClass.findMarker(startName)
		endFrame = SceneInfoClass.findMarker(endName)
		smm = SceneInfoClass.hasMultipleMarkers(startFrame)
		emm = SceneInfoClass.hasMultipleMarkers(endFrame)		
		if smm:			
			message = "Could not delete sequence marker \'"+startName+"\' on frame "+str(startFrame)+" because there is more than one marker on the frame!%t|OK"
			x = Blender.Draw.PupMenu(message)
			del x
		if emm:
			message = "Could not delete sequence marker \'"+endName+"\' on frame "+str(endFrame)+" because there is more than one marker on the frame!%t|OK"
			x = Blender.Draw.PupMenu(message)
			del x
		
		if not (smm or emm):
			# delete the markers.
			SceneInfoClass.delMarker(startName)
			SceneInfoClass.delMarker(endName)
		else:
			message = "Could not delete sequence  \'"+seqName+"\'!%t|Cancel"
			x = Blender.Draw.PupMenu(message)
			del x

	delSeqMarkers = staticmethod(delSeqMarkers)

		
	# Renames sequence markers that match the given name
	def renameSeqMarkers(oldName, newName):
		startName = oldName + ":start"
		endName = oldName + ":end"
		newStartName = newName + ":start"
		newEndName = newName + ":end"
		# see if both markers are alone on their respective frames.
		startFrame = SceneInfoClass.findMarker(startName)
		endFrame = SceneInfoClass.findMarker(endName)
		smm = SceneInfoClass.hasMultipleMarkers(startFrame)
		emm = SceneInfoClass.hasMultipleMarkers(endFrame)

		if smm:			
			message = "Could not rename sequence marker \'"+startName+"\' on frame "+str(startFrame)+" because there is more than one marker on the frame!%t|OK"
			x = Blender.Draw.PupMenu(message)
			del x
		if emm:
			message = "Could not rename sequence marker \'"+endName+"\' on frame "+str(endFrame)+" because there is more than one marker on the frame!%t|OK"
			x = Blender.Draw.PupMenu(message)
			del x
		
		if not (smm or emm):
			# rename the markers.
			Blender.Scene.GetCurrent().getTimeLine().setName(startFrame, newStartName)
			Blender.Scene.GetCurrent().getTimeLine().setName(endFrame, newEndName)
		else:
			message = "Could not rename sequence  \'"+oldName+"\'!%t|Cancel"
			x = Blender.Draw.PupMenu(message)
			del x

	
	renameSeqMarkers = staticmethod(renameSeqMarkers)

	# create a marker on the timeline
	# returns true if marker was successfully created, otherwise returns false
	def createMarker(markerName, frameNum):
		# check to make sure the frame isn't out of range, if it is,
		# increase the range :-)
		context = Blender.Scene.GetCurrent().getRenderingContext()
		eFrame = context.endFrame()
		if frameNum > eFrame:
			context.endFrame(frameNum)
			Blender.Scene.GetCurrent().update(1)

		isNotMarked = SceneInfoClass.isNotMarked(frameNum)
		if SceneInfoClass.findMarker(markerName) == frameNum: alreadyThere = True
		else: alreadyThere = False
		if isNotMarked and not alreadyThere:
			message = "Could not create sequence marker \'"+markerName+"\' on frame "+str(frameNum)+" because there is already a marker on the frame!%t|OK"
			x = Blender.Draw.PupMenu(message)
			del x
			return False
		else:
			timeline = Blender.Scene.GetCurrent().getTimeLine()
			timeline.add(frameNum)
			timeline.setName(frameNum, markerName)
			return True
		
	createMarker = staticmethod(createMarker)

	# returns true if the sequence was successfully created, otherwise returns false.
	def createSequenceMarkers(seqName, startFrame, endFrame):		
		if startFrame >= endFrame:
			message = "Start frame must come before end frame!%t|Cancel sequence creation"
			x = Blender.Draw.PupMenu(message)
			del x
			return False

		startName = seqName + ":start"
		endName = seqName + ":end"

		startExists = (SceneInfoClass.findMarker(startName) != None)
		endExists = (SceneInfoClass.findMarker(endName) != None)
		if startExists and endExists:
			message = "Sequence \'"+seqName+"\' already exists!%t|Cancel sequence creation"
			x = Blender.Draw.PupMenu(message)
			del x
			return False
		
		# clean up any stray start or end frames that may already exist
		if startExists:
			SceneInfoClass.delMarker(startName)
		elif endExists:
			SceneInfoClass.delMarker(endName)
		
		# try to create the markers
		ss = SceneInfoClass.createMarker(startName, startFrame)
		es = SceneInfoClass.createMarker(endName, endFrame)
		
		# warn if we failed, and delete any markers that were created
		if not (ss and es):
			message = "Could not create sequence  \'"+seqName+"\'!%t|OK"
			x = Blender.Draw.PupMenu(message)
			del x
			if ss: SceneInfoClass.delMarker(startName)
			if es: SceneInfoClass.delMarker(endName)

			return False
		else: return True
	
	createSequenceMarkers = staticmethod(createSequenceMarkers)
		

	# gets the action strips for all objects in the scene
	# and returns a list of tuples in the form [(stripName, startFrame, endFrame), ...]
	def getAllActionStrips(self):
		# get all exportable objects
		objNodeNames = self.getObjectNodeNames()
		bObjs = []
		for objNodeName in objNodeNames:
			bObjs.append(self.nodes[objNodeName].getBlenderObj())
		# get all action strips
		aStrips = []
		for bObj in bObjs:
			if bObj == None: continue
			strips = bObj.actionStrips
			for strip in strips:
				aStrips.append(strip)
		
		# build a temp dictionary of tupples for all strips
		allStrips = {}
		for strip in aStrips:
			stripName = strip.action.name
			startFrame = int(round(strip.stripStart))
			endFrame = int(round(strip.stripEnd))
			if startFrame < endFrame:
				# just take the last one that we found.
				allStrips[stripName] = (startFrame, endFrame)
		
		# build retval
		retVal = []
		for stripName in allStrips.keys():
			startFrame, endFrame = allStrips[stripName]
			retVal.append((stripName, startFrame, endFrame))
		
		return retVal
			
	# create sequence markers from action strips
	def markersFromActionStrips(self):
		stripTuples = self.getAllActionStrips()
		for t in stripTuples:
			stripName, startFrame, endFrame = t
			# create the markers
			SceneInfoClass.createSequenceMarkers(stripName, startFrame, endFrame)
			
	# create action strips from actions
	def actionStripsFromActions(self):
		# get a list of all actions
		actions = Blender.Armature.NLA.GetActions()

		# no way to tell "what's what" using the python API, so
		# we just create the action strips for every armature in the scene
		# and hope to God that there aren't any "object actions" present.
		
		bObjs = []
		objNodeNames = self.getObjectNodeNames()
		nextFrame = 2
		for objNodeName in objNodeNames:
			bObjs.append(self.nodes[objNodeName].getBlenderObj())
		for action in actions.values():
			# calculate strip parameters
			sf = nextFrame
			ef = sf + self.__getActionLength(action.name)
			nextFrame = ef + 1			
			for bObj in bObjs:
				if bObj.getType() != 'Armature': continue
				objStrips = bObj.actionStrips
				objStrips.append(action)
				strip = objStrips[len(objStrips)-1]
				strip.stripEnd = ef
				strip.stripStart = sf
				bObj.enableNLAOverride = True
		
		# refresh everything.
		Blender.Scene.GetCurrent().update(1)

	
	# create sequence markers from actions, first converting actions to action strips
	def createFromActions(self):
		# todo - bail if action strips already exist
		self.actionStripsFromActions()
		self.markersFromActionStrips()
		


	#################################################
	#  Meshes and DTS objects
	#################################################


	# strips the last '.' and everything following it from the mesh name.
	def getStrippedMeshName(meshName):
		#names = meshName.split("_")
		detail_name_dot_index = meshName.rfind(".")
		if detail_name_dot_index != -1:
			detail_name = meshName[0:detail_name_dot_index]
		else:
			detail_name = meshName.split(".")[0]
		return detail_name

	getStrippedMeshName = staticmethod(getStrippedMeshName)
	
	# gets dts object names (unique mesh names across all detail levels, minus trailing extension)
	def getDtsObjectNames(self):
		retval = self.DTSObjects.keys()
		retval.sort()
		return retval
		'''
		uniqueNames = {}
		for dl in self.detailLevels.values():
			for meshNI in dl:
				dtsObjName = meshNI.dtsObjName
				uniqueNames[dtsObjName] = 0
		return uniqueNames
		'''

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



	def getVGroupTransDict(self):
		retVal = {}
		# find all exportable bone nodes
		for ni in self.nodes.values():
			if ni.blenderType != "bone" or ni.isBanned(): continue
			retVal[ni.originalBoneName] = ni.dtsNodeName
		return retVal
			
			

	#################################################
	#  Misc
	#################################################


	# Gets the children of an object
	def getChildren(self, obj):
		return filter(lambda x: x.parent==obj, Blender.Scene.GetCurrent().objects)

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
						
			