'''
poseUtil.py

Copyright (c) 2006 Joseph Greenawalt(jsgreenawalt@gmail.com)

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
from Blender import Mathutils as bMath

import DTSPython
from DTSPython import *
from DTSPython import Torque_Math

from DtsGlobals import *
from DtsSceneInfo import *

import new
import gc

gc.enable()
#-------------------------------------------------------------------------------------------------
def initWSTransformData(self, initPose=None):
	if self.blenderType == "object":
		mat = self.getBlenderObj().getMatrix('worldspace')
		# Note: Blender quaternions must be inverted since torque uses column vectors
		self.restRotWS = toTorqueQuat(mat.rotationPart().toQuat().inverse())
		self.restPosWS = toTorqueVec(mat.translationPart())

	elif self.blenderType == "bone":			
		bone = self.getBlenderObj().getData().bones[self.nodeName]
		bMat = bone.matrix['ARMATURESPACE']
		self.restPosWS = self.__calcBoneRestPosWS(bMat)
		self.restRotWS = self.__calcBoneRestRotWS(bMat)

def initPSTransformData(self, initPose=None):
	if self.blenderType == "object":
		self.defPosPS = self.__calcNodeDefPosPS(self.dtsObjName)
		self.defRotPS = self.__calcNodeDefRotPS(self.dtsObjName)

	elif self.blenderType == "bone":			
		bone = self.getBlenderObj().getData().bones[self.nodeName]
		self.defPosPS = self.__calcNodeDefPosPS(bone.name)
		self.defRotPS = self.__calcNodeDefRotPS(bone.name)


# methods used to calculate static node tranform data
# ***********************
# these next four functions should not be called by any other functions, only in init

# Determine a node's default position for the current pose in the parent node's space.
# This is where the node should be if it has not been explicitly moved or
# effected by a constraint.
# 
def __calcNodeDefPosPS(self, nodeName):
	# early out if we've got no parent
	if self.parentNI == None:
		nodeLocWS = self.restPosWS
		return nodeLocWS			
	# get the node's default position in worldspace
	nodeLocWS = self.restPosWS
	# get the parent node's default position in worldspace
	parentnodeLocWS = self.parentNI.restPosWS
	# subtract out the parent node's position, this gives us the offset of the child in worldspace
	offsetWS = nodeLocWS - parentnodeLocWS
	# scale the offset by armature's scale
	# todo - this wasn't doing anything?
	# rotate the offset into the parent node's default local space		
	offsetPS = self.parentNI.restRotWS.inverse().apply(offsetWS)
	return offsetPS

# determine a node's default rotation in parent space
# This is what the node's rotation should be, relative to the parent node,
# if it has not been directly rotated or affected by a constraint.
# 
def __calcNodeDefRotPS(self, nodeName):
	# early out if we've got no parent
	if self.parentNI == None:
		nodeRotWS = self.restRotWS
		return nodeRotWS			
	# get the node's default rotation in worldspace
	nodeRotWS = self.restRotWS
	# get the parent node's default rotation in worldspace
	parentNodeRotWS = self.parentNI.restRotWS
	# get the difference
	bDefRotPS = nodeRotWS * parentNodeRotWS.inverse()
	return bDefRotPS


# --------- Worldspace getters ----------------

# determine a bone's rest position in worldspace
#
# todo - what happens if parent armature node is collapsed?
def __calcBoneRestPosWS(self, bMat):
	# get the armature's rotation
	armRot = self.armParentNI.restRotWS
	# get the bone's location in armaturespace
	bLoc = toTorqueVec(bMat.translationPart())
	# rotate out of armature space
	bLoc = armRot.apply(bLoc)
	# add on armature's scale
	armSize = [1,1,1]
	bLoc = Vector( bLoc[0] * armSize[0], bLoc[1] * armSize[1], bLoc[2] * armSize[2] )
	# add on armature's location
	bLoc = bLoc + self.armParentNI.restPosWS
	return bLoc

# determine a bone's rest rotation in worldspace
#
# todo - what happens if parent armature node is collapsed
def __calcBoneRestRotWS(self, bMat):
	# get the armature's rotation		
	armRot = self.armParentNI.restRotWS
	# get the bone's rotation in armaturespace
	bRot = toTorqueQuat(bMat.rotationPart().toQuat().inverse())
	# rotate out of armature space
	bRot = (bRot * armRot)
	return bRot



# ***********************
# determine the position of any bone in worldspace
# TESTED
def __getBoneLocWS(self, pose):
	# get the armature's rotation
	armRot = self.armParentNI.getNodeRotWS(pose)
	# and it's inverse
	# get the pose location
	bTrans = armRot.apply(toTorqueVec(pose.bones[self.nodeName].poseMatrix.translationPart()))
	# Scale by armature's scale
	armSize = toTorqueVec([1,1,1])
	bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
	# add on armature pivot to translate into worldspace
	bTrans = bTrans + self.armParentNI.getNodeLocWS(pose)
	return bTrans

# determine the rotation of any bone in worldspace
# TESTED
def __getBoneRotWS(self, pose):
	# get the armature's rotation
	armRot = self.armParentNI.getNodeRotWS(pose)
	# get the pose rotation and rotate into worldspace
	bRot = ( toTorqueQuat(pose.bones[self.nodeName].poseMatrix.rotationPart().toQuat().inverse()) * armRot)
	return bRot


# determine the location of an object node in worldspace
# TESTED
def __getObjectLocWS(self):
	bLoc = toTorqueVec(Blender.Object.Get(self.nodeName).getMatrix('worldspace').translationPart())
	return bLoc

# determine the rotation of an object node in worldspace
# TESTED
def __getObjectRotWS(self):
	bRot = toTorqueQuat(Blender.Object.Get(self.nodeName).getMatrix('worldspace').rotationPart().toQuat()).inverse()
	return bRot

def getNodeLocWS(self, pose):
	if self.blenderType == "object":
		retVal = self.__getObjectLocWS()
	elif self.blenderType == "bone":
		retVal = self.__getBoneLocWS(pose)
	return retVal

def getNodeRotWS(self, pose):
	if self.blenderType == "object":
		retVal = self.__getObjectRotWS()
	elif self.blenderType == "bone":
		retVal = self.__getBoneRotWS(pose)
	return retVal


# binds the above methods to the nodeInfo class imported from DtsSceneInfo.py.
def bindDynamicMethods():
	new.instancemethod(initWSTransformData, None, initWSTransformData)
	nodeInfoClass.__dict__['initWSTransformData'] = initWSTransformData
	new.instancemethod(initPSTransformData, None, initPSTransformData)
	nodeInfoClass.__dict__['initPSTransformData'] = initPSTransformData
	new.instancemethod(__calcNodeDefPosPS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__calcNodeDefPosPS'] = __calcNodeDefPosPS
	new.instancemethod(__calcNodeDefRotPS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__calcNodeDefRotPS'] = __calcNodeDefRotPS
	new.instancemethod(__calcBoneRestPosWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__calcBoneRestPosWS'] = __calcBoneRestPosWS
	new.instancemethod(__calcBoneRestRotWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__calcBoneRestRotWS'] = __calcBoneRestRotWS
	new.instancemethod(__getBoneLocWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getBoneLocWS'] = __getBoneLocWS
	new.instancemethod(__getBoneRotWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getBoneRotWS'] = __getBoneRotWS
	new.instancemethod(__getObjectLocWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getObjectLocWS'] = __getObjectLocWS
	new.instancemethod(__getObjectRotWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getObjectRotWS'] = __getObjectRotWS
	new.instancemethod(getNodeLocWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['getNodeLocWS'] = getNodeLocWS
	new.instancemethod(getNodeRotWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['getNodeRotWS'] = getNodeRotWS



# --------- Class that stores all static data internally so we only have to get it once ----------
class DtsPoseUtilClass:
	'''
	
	DtsPoseUtilClass
	
	todo - description	
	
	
	'''
	def __init__(self, prefs):
		gc.enable()
		# bind dynamic methods to nodeInfoClass
		bindDynamicMethods()
		# get dictionaries
		self.nodes = DtsGlobals.SceneInfo.nodes
		self.armatures = DtsGlobals.SceneInfo.armatures
		self.__initTransforms()
		'''
		# first init armatures
		for node in self.armatures.values():
			node.initWSTransformData()
		for node in self.armatures.values():
			node.initPSTransformData()
		# now the rest (there's some overlap, but not much unless a scene has a crap-ton of armatures)
		for node in self.nodes.values():
			node.initWSTransformData()
		for node in self.nodes.values():
			node.initPSTransformData()
		#self.__populateData(prefs)
		'''
	
	def __initTransforms(self):
		# start with nodes at the root of the tree
		for node in filter(lambda x: x.parentNI == None, self.nodes.values()):
			node.initWSTransformData()
			# add child trees
			self.__walkTreeInitTransforms(None)
			# finally init PS transform data
			node.initPSTransformData()
		

	def __walkTreeInitTransforms(self, node):
		for node in filter(lambda x: x.parentNI == node, self.nodes.values()):
			node.initWSTransformData()
			# add child trees
			self.__walkTreeInitTransforms(node)
			# finally init PS transform data
			node.initPSTransformData()

	# recursive, for internal use only
	def __addTree(self, obj, parentNI, prefs):
			#   "obj" is a blender object of any type
			#   "parentNI" is the parent object (NodeInfo object) of obj

			# skip temp objects
			if obj.name == "DTSExpObj_Tmp": return

			nodeName = obj.name
			blenderType = "object"
			blenderObj = obj


			# create a new nodeInfo object for the Blender object
			

			armDb = None
			nnu = nodeName.upper()
			if (obj.getType() == 'Armature'):
				# Armature transforms are needed even if the node for the armature object is
				# collapsed to compute bone transforms in worldspace, so we keep these in a separate list
				ai = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, None)
				self.armatures[nodeName] = ai

			if nodeName.upper() in prefs['BannedNodes']:
				n = parentNI
			else:
				# add it to the nodes dict
				ni = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, None)
				self.nodes[nodeName] = ni
				n = ni

			if (obj.getType() == 'Armature'):
				# get blender armature datablock
				armDb = obj.getData()
				pose = obj.getPose()

				# loop through the armature's bones
				for bone in filter(lambda x: x.parent==None, armDb.bones.values()):					
					self.__addBoneTree(obj, n, bone, armDb, ai, pose, prefs)
					
			# add child trees
			for child in filter(lambda x: x.parent==obj, Blender.Object.Get()):
				parentBoneName = child.getParentBoneName()
				if (obj.getType() == 'Armature') and (parentBoneName != None):					
					# find a good parent bone if possible
					while parentBoneName.upper() in prefs['BannedNodes']:
						if armDb.bones[parentBoneName].parent != None:
							parentBoneName = armDb.bones[parentBoneName].parent.name
						else:
							parentBoneName = obj.name
							if parentBoneName.upper() in prefs['BannedNodes']:
								parentBoneName = parentNI
						if parentBoneName == None: break
					if parentBoneName == None: parentNode = None
					else: parentNode = self.nodes[parentBoneName]
					
					self.__addTree(child, parentNode, prefs)
				else:
					self.__addTree(child, n, prefs)
		

	
	# adds a bone tree recursively, for internal use only
	def __addBoneTree(self, obj, parentNI, boneOb, armDb, armParentNI, initPose, prefs):
		nodeName = boneOb.name
		blenderType = "bone"
		blenderObj = obj

		# create a new nodeInfo object for the Blender bone
		if nodeName.upper() in prefs['BannedNodes']:
			n = parentNI
		else:
			n = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, armParentNI, initPose)
			# add it to the nodes dict
			self.nodes[nodeName] = n

		# add child trees
		for bone in filter(lambda x: x.parent==boneOb, armDb.bones.values()):					
			self.__addBoneTree(obj, n, bone, armDb, armParentNI, initPose, prefs)

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
			

	# Build the node tree.
	# Nodes in this tree are representative of actual exported nodes; The tree
	# does not include banned nodes.
	def __populateData(self, prefs):
		# Build armatures dictionary
		for ni in self.nodes.values():
			if ni.getBlenderObj().getType == "Armature":
				pass
				#self.armatures[ni.]
		'''
		# go through each object		
		for obj in filter(lambda x: x.parent==None, Blender.Object.Get()):
			if obj.parent == None:
				self.__addTree(obj, None, prefs)
		for ni in filter(lambda x: x.parentNI==None, self.nodes.values()):
			self.__printTree(ni)
		'''


	# --------- Localspace getters ----------------


	# *****
	# This is our only exposed public method.
	def getNodeLocRotLS(self, nodeName, pose):
		loc = None
		rot = None
		if self.nodes[nodeName].parentNI == None:
			loc = self.getOrphanNodeLocLS(nodeName, pose)
			rot = self.getOrphanNodeRotLS(nodeName, pose)
		else:
			loc = self.getNodeLocLS(nodeName, pose)
			rot = self.getNodeRotLS(nodeName, pose)
		return loc, rot
	# *****
	
	# -----  everything below this point is private (pretend it is, anyway)
	
	# TESTED
	def getNodeLocLS(self, nodeName, pose):
		node = self.nodes[nodeName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# get the bone's location in parent space
		whereIsBonePS = self.getNodePosPS(nodeName, pose)
		# get the bone's default location in parent space
		# ( This is where the bone should be if it has not been explicitly moved or
		# effected by a constraint.)
		whereShouldNodeBePS = node.defPosPS
		# subtract out the position that the bone will end up in due to FK transforms
		# from the parent bone, as these are already taken care of due to the nodes being
		# in the parent's local space.
		whereIsBonePS = whereIsBonePS - whereShouldNodeBePS
		return whereIsBonePS

	# Get the rotation from rest of a connected bone in the bone's local space.
	# TESTED
	def getNodeRotLS(self, nodeName, pose):
		node = self.nodes[nodeName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# get the default rotation of the bone in parent space, this
		# is what the bone's rotation should be if it has not been
		# explicitly rotated or affected by a constraint.
		bDefRotPS = node.defRotPS.inverse()
		# get the current rotation of the bone in parent space.
		bCurRotPS = self.getNodeRotPS(nodeName, pose)
		bRotLS = bCurRotPS.inverse() * bDefRotPS
		return bRotLS.inverse()


	# orphan bone translations are defined in worldspace
	# relative to the default postion of the bone.
	# TESTED
	def getOrphanNodeLocLS(self, nodeName, pose):
		node = self.nodes[nodeName]
		# get the rest position of the bone
		bRestPos = node.restPosWS
		# get the bone's current position
		bCurPos = node.getNodeLocWS(pose)
		# subtract the rest postion from the current position to get
		# the bone's local movement
		bMovement = bCurPos - bRestPos
		return bMovement

	# get the difference between an orphan bone's rest rotation
	# and it's current rotation; this is the bone's localspace
	# rotation.
	# TESTED
	def getOrphanNodeRotLS(self, nodeName, pose):
		node = self.nodes[nodeName]
		# get the bone's rest rotation in worldspace
		bRestRot = node.restRotWS
		# get the bone's worldspace rotation
		bCurRot = node.getNodeRotWS(pose)
		# get the differnce between the two, worldspace factors out
		bRotDelta = (bRestRot.inverse() * bCurRot).inverse()
		return bRotDelta


	# --------- Parentspace getters ----------------

	# determine the position of the bone in parentSpace
	# (absolute parent space position, not relative to default position of the bone)
	# TESTED
	def getNodePosPS(self, nodeName, pose):
		node = self.nodes[nodeName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# find the parent's location in worldspace
		whereIsParentWS = parent.getNodeLocWS(pose)
		# find the child's location in worldspace
		whereIsChildWS = node.getNodeLocWS(pose)
		# subtract out the parent's location
		whereIsBonePS = whereIsChildWS - whereIsParentWS
		# determine the transform needed to get to the same point in the parent's space.
		whereIsBonePS = parent.getNodeRotWS(pose).inverse().apply(whereIsBonePS)
		return whereIsBonePS

	# Get a non-orphan Node's rotation in parent space
	# TESTED
	def getNodeRotPS(self, nodeName, pose):
		node = self.nodes[nodeName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# get the node's rotation in worldspace
		nodeRotWS = node.getNodeRotWS(pose)
		# get the parent node's rotation in worldspace
		parentNodeRotWS = parent.getNodeRotWS(pose)
		# get the difference
		bRotPS = nodeRotWS * parentNodeRotWS.inverse()
		return bRotPS.inverse()






		
	def toTorqueVec(self, v):
		return Vector(v[0], v[1], v[2])

	def toBlenderVec(self, v):
		return bMath.Vector(v[0], v[1], v[2])

	def toTorqueQuat(self, q):
		q = q.inverse().normalize()
		return Quaternion(q[1],q[2],q[3],q[0])

	def toBlenderQuat(self, q):
		q = q.inverse().normalize()		
		return bMath.Quaternion(q[3],q[0],q[1],q[2])

	


# --------- test functions ----------------



def toTorqueVec(v):
	return Vector(v[0], v[1], v[2])
	
def toBlenderVec(v):
	return bMath.Vector(v[0], v[1], v[2])
	
def toTorqueQuat(q):
	return Quaternion(q[1],q[2],q[3],q[0])
	
def toBlenderQuat(q):
	#print "\nq = ", q
	return bMath.Quaternion(q[3],q[0],q[1],q[2])



def putEmptyAt(loc):
	scene = Blender.Scene.GetCurrent()
	loc = toBlenderVec(loc)
	try: Blender.Object.Get('Empty')
	except:
		Blender.Object.New('Empty', 'Empty')
	empty = Blender.Object.Get('Empty')
	if not (empty in scene.getChildren()): scene.link(empty)
	empty.setLocation(loc.x, loc.y, loc.z)
	scene.update(1)
	Blender.Window.RedrawAll()
	
def setEmptyRot(rot):
	scene = Blender.Scene.GetCurrent()
	rot = toBlenderQuat(rot)
	try: Blender.Object.Get('Empty')
	except:
		Blender.Object.New('Empty', 'Empty')
	empty = Blender.Object.Get('Empty')
	if not (empty in scene.getChildren()): scene.link(empty)
	#print rot
	#print rot.toMatrix()
	rot = rot.toMatrix().resize4x4()
	empty.setMatrix(rot)
	scene.update(1)
	Blender.Window.RedrawAll()





# *** entry point for getBoneLoc/Rot WS testing ***
if __name__ == "__main__":
	arm = Blender.Object.Get('Armature')
	armName = arm.name
	scene = Blender.Scene.GetCurrent()
	scene.getRenderingContext().currentFrame(40)
	scene.update(1)
	# get the pose
	pose = arm.getPose()

	PoseUtil = DtsPoseUtilClass()

	bName = 'Bone'
	#parentName = PoseUtil.armBones[armName][bName][PARENTNAME]

	
	#setEmptyRot(PoseUtil.getBoneRestRotWS(armName, bName))
	#putEmptyAt(PoseUtil.getBoneRestPosWS(armName, bName))

	
	print "Done!"