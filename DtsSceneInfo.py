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
import string, gc
from DtsPrefs import *
import DtsGlobals
from DTSPython import stripPath




'''
NodeInfoClass

This class stores static node information for a node and provides a standard interface
for getting dynamic node transform data from Blender whether the node was created from a
Blender object or Blender bone.
'''
class nodeInfoClass:
	def __init__(self, nodeName, blenderType, blenderObj, parentNI, prefs):
		self.preferences = prefs
		self.nodeName = nodeName
		self.blenderType = blenderType
		self.blenderObj = blenderObj # either a blender bone or blender object depending on blenderType
		self.parentNodeInfo = parentNI
		
		self.isBannedNode = nodeName in self.preferences['BannedNodes']
		self.layers = blenderObj.layers
		
		if parentNI != None: self.parentName = parentNI.nodeName
		else: self.parentName = None
		if parentNI != None: self.parentBlenderType = parentNI.blenderType
		else: self.parentBlenderType = None
		
		self.parentNI = parentNI
		
		if blenderType == "object":
			pass
		elif blenderType == "bone":
			pass

	# find a non-excluded node to use as a parent for another node/object
	# don't call this until the tree is completely built.
	def getGoodParentNI(self):
		pNI = self
		while (pNI != None) and (pNI.nodeName.upper() in self.preferences['BannedNodes']):
			pNI = pNI.parentNI
		return pNI



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

	def __init__(self, prefs):	
		gc.enable()
		self.preferences = prefs
		self.nodes = {}
		self.armatures = {}
		self.meshes = {}
		self.detailLevels = {}
		self.DTSObjects = {}
		self.__populateData()

	def refreshAll(self):
		self.nodes = {}
		self.armatures = {}
		self.meshes = {}
		self.detailLevels = {}
		self.DTSObjects = {}
		self.__populateData()

	# recursive, for internal use only
	def __addTree(self, obj, parentNI):
			#   "obj" is a blender object of any type
			#   "parentNI" is the parent object (NodeInfo object) of obj
			
			nodeName = obj.name
			blenderType = "object"
			blenderObj = obj


			# create a new nodeInfo object for the Blender object
			n = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, self.preferences)

			# the new node to the nodes dictionary
			self.nodes[nodeName] = n

			# add the node to other dictionaries as needed
			bObjType = obj.getType()
			if (bObjType == 'Armature'):
				self.armatures[nodeName] = n		
			
			# don't add object to detail levels if it has no visible geometry
			elif not (bObjType in ['Empty', 'Curve', 'Camera', 'Lamp', 'Lattice']):
				self.meshes[nodeName] = n			
				# add mesh node info to detail levels
				for dlName in self.preferences['DetailLevels'].keys():
					dl = self.preferences['DetailLevels'][dlName]
					for layer in obj.layers:
						if layer in dl:
							self.detailLevels[dlName].append(n)
				'''
				# add to DTSObjects
				dtsObjName = getStrippedMeshName(obj.name)
				try: dtsObj = self.DTSObjects[dtsObjName]
				except: self.DTSObjects[dtsObjName] = []
				self.DTSObjects[dtsObjName].append
				'''

			# add armature bones if needed
			if (bObjType == 'Armature'):
				# get blender armature datablock
				armDb = obj.getData()
				for bone in filter(lambda x: x.parent==None, armDb.bones.values()):					
					self.__addBoneTree(obj, n, bone, armDb)

					
			# add child trees
			for child in filter(lambda x: x.parent==obj, Blender.Object.Get()):
				parentBoneName = child.getParentBoneName()
				if (obj.getType() == 'Armature') and (parentBoneName != None):					
					parentNode = self.nodes[parentBoneName]					
					self.__addTree(child, parentNode)
				else:
					self.__addTree(child, n)
		

	
	# adds a bone tree recursively, for internal use only
	def __addBoneTree(self, obj, parentNI, boneOb, armDb):
		nodeName = boneOb.name
		blenderType = "bone"
		blenderObj = obj

		# add it to the nodes dict
		n = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, self.preferences)
		self.nodes[nodeName] = n

		# add child trees
		for bone in filter(lambda x: x.parent==boneOb, armDb.bones.values()):					
			self.__addBoneTree(obj, n, bone, armDb)

	# for debugging
	def __printTree(self, ni, indent=0):
		pad = ""
		for i in range(0, indent):
			pad += " "
		print pad+"|"
		print pad+"Node:", ni.nodeName
		try:
			nn = ni.parentNI.nodeName
			print pad+"Parent:", nn
		except: print pad+"No Parent."
		indent += 3
		for nic in filter(lambda x: x.parentNI==ni, self.nodes.values()):			
			self.__printTree(nic, indent)
			

	def __populateData(self):
		startTime = Blender.sys.time()
		
		# create empty detail levels based on prefs
		for dlName in self.preferences['DetailLevels'].keys():
			self.detailLevels[dlName] = []
		
		# go through each object and bone and add subtrees		
		for obj in filter(lambda x: x.parent==None, Blender.Object.Get()):
			if obj.parent == None:
				self.__addTree(obj, None)
		#print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
		#for ni in filter(lambda x: x.parentNI==None, self.nodes.values()):
		#	self.__printTree(ni)
		#print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
		endTime = Blender.sys.time()
		print "__populateData finished in", endTime - startTime


	#################################################
	#  File name and path methods
	#################################################


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
	def __stripImageExtension(imagename, filename=""):
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

	__stripImageExtension = staticmethod(__stripImageExtension)

	# not static because it needs to know about detail levels.
	def getDtsMaterials(self):
		# loop through all faces of all meshes in visible detail levels and compile a list
		# of unique images that are UV mapped to the faces.
		imageList = []	
		for dlName in self.detailLevels:
			dl = self.detailLevels[dlName]
			for ni in dl:
				obj = ni.blenderObj
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
							imageName = SceneInfoClass.__stripImageExtension(objData.materials[face.mat].name)
							if not (imageName in imageList):
								imageList.append(imageName)

					# Otherwise we do have an image assigned to the face, so add it to the imageList.
					else:
						imageName = SceneInfoClass.__stripImageExtension(face.image.getName(), face.image.getFilename())
						if not (imageName in imageList):
							imageList.append(imageName)



		return imageList
	
	# gets a dts material name for a given Blender mesh primitive
	def getFaceDtsMatName(face, msh):
		imageName = None
		try: imageName = SceneInfoClass.__stripImageExtension(face.image.getName(), face.image.getFilename())
		#except AttributeError:
		except (ValueError, AttributeError):
			# there isn't an image assigned to the face...
			# do we have a material index?
			try: mat = msh.materials[face.mat]
			except IndexError: mat = None
			if mat != None:
				# we have a material index, so get the name of the material
				imageName = SceneInfoClass.__stripImageExtension(mat.name)

		return imageName
		
	getFaceDtsMatName = staticmethod(getFaceDtsMatName)
	
	# gets the names of all Blender images with extensions stripped
	def getAllBlenderImages():
		imageNames = []
		for img in Blender.Image.Get():
			imageNames.append( SceneInfoClass.__stripImageExtension(img.getName(), img.getFilename()) )
		return imageNames
	
	getAllBlenderImages = staticmethod(getAllBlenderImages)
	

	#################################################
	#  Nodes
	#################################################


	# get the names of all nodes in the scene
	def getAllNodeNames(self):
		nameList = []
		for ni in self.nodes.values():
			nameList.append(ni.nodeName)
		return nameList


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
				dtsObjName = SceneInfoClass.getStrippedMeshName(meshNI.nodeName)
				uniqueNames[dtsObjName] = 0
		return uniqueNames


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
