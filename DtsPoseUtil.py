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


import gc

gc.enable()
'''
	Utility class for dealing with Blender's pose module and armature system,
	and the many memory leaks therein.
'''
#-------------------------------------------------------------------------------------------------

class nodeInfoClass:
	'''
	NodeInfoClass
	
	This class stores static node information for a node, and provides a standard interface
	for getting dynamic node transform data from blender whether the node was created from a
	Blender object or Blender bone.
	'''
	def __init__(self, nodeName, blenderType, blenderObj, parentNI, armParentNI, initPose=None):
		self.nodeName = nodeName
		self.blenderType = blenderType
		self.blenderObj = blenderObj # either a blender bone or blender object depending on blenderType
		self.parentNodeInfo = parentNI		
		if parentNI != None: self.parentName = parentNI.nodeName
		else: self.parentName = None
		if parentNI != None: self.parentBlenderType = parentNI.blenderType
		else: self.parentBlenderType = None
		
		self.parentNI = parentNI
		self.armParentNI = armParentNI
		#self.parentScale = parentScale
		
		if blenderType == "object":
			mat = blenderObj.getMatrix('worldspace')
			# Note: Blender quaternions must be inverted since torque uses column vectors
			self.restRotWS = toTorqueQuat(mat.rotationPart().toQuat().inverse())
			self.restPosWS = toTorqueVec(mat.translationPart())

			self.defPosPS = self.__calcNodeDefPosPS(nodeName)
			self.defRotPS = self.__calcNodeDefRotPS(nodeName)

		elif blenderType == "bone":			
			bone = blenderObj.getData().bones[nodeName]
			bMat = bone.matrix['ARMATURESPACE']
			self.restPosWS = self.__calcBoneRestPosWS(bMat)
			self.restRotWS = self.__calcBoneRestRotWS(bMat)

			self.defPosPS = self.__calcNodeDefPosPS(bone.name)
			self.defRotPS = self.__calcNodeDefRotPS(bone.name)
			
			
	
	# methods used to calculate static node tranform data
	# ***********************
	# these next four functions should not be called by any other functions, only in init

	# Determine a bone's default position for the current pose in the parent bone's space.
	# This is where the bone should be if it has not been explicitly moved or
	# effected by a constraint.
	# 
	# todo - what happens if parent armature node is collapsed?
	def __calcNodeDefPosPS(self, bName):
		# early out if we've got no parent
		if self.parentNI == None:
			boneLocWS = self.restPosWS
			return boneLocWS			
		# get the bone's default position in worldspace
		boneLocWS = self.restPosWS
		# get the parent bone's default position in worldspace
		parentBoneLocWS = self.parentNI.restPosWS
		# subtract out the parent bone's position, this gives us the offset of the child in worldspace
		offsetWS = boneLocWS - parentBoneLocWS
		# scale the offset by armature's scale
		# todo - this wasn't doing anything?
		#armSize = self.armInfo[armName][ARMSIZE]
		# rotate the offset into the parent bone's default local space		
		offsetPS = self.parentNI.restRotWS.inverse().apply(offsetWS)
		return offsetPS

	# determine a bone's default rotation in parent space
	# This is what the bone's rotation should be, relative to the parent bone,
	# if it has not been directly rotated or affected by a constraint.
	# 
	# todo - what happens if parent armature node is collapsed?
	def __calcNodeDefRotPS(self, bName):
		# early out if we've got no parent
		if self.parentNI == None:
			boneRotWS = self.restRotWS
			return boneRotWS			
		# get the bone's default rotation in worldspace
		boneRotWS = self.restRotWS
		# get the parent bone's default rotation in worldspace
		parentBoneRotWS = self.parentNI.restRotWS
		# get the difference
		bDefRotPS = boneRotWS * parentBoneRotWS.inverse()
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
	def __getBoneLocWS(self, armName, pose):
		# get the armature's rotation
		armRot = self.armParentNI.getNodeRotWS(armName, pose)
		# and it's inverse
		# get the pose location
		bTrans = armRot.apply(toTorqueVec(pose.bones[self.nodeName].poseMatrix.translationPart()))
		# Scale by armature's scale
		armSize = toTorqueVec([1,1,1])
		bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
		# add on armature pivot to translate into worldspace
		bTrans = bTrans + self.armParentNI.getNodeLocWS(armName, pose)
		return bTrans

	# determine the rotation of any bone in worldspace
	# TESTED
	def __getBoneRotWS(self, armName, pose):
		# get the armature's rotation
		armRot = self.armParentNI.getNodeRotWS(armName, pose)
		# get the pose rotation and rotate into worldspace
		bRot = ( toTorqueQuat(pose.bones[self.nodeName].poseMatrix.rotationPart().toQuat().inverse()) * armRot)
		return bRot



	def __getObjectLocWS(self):
		bLoc = toTorqueVec(Blender.Object.Get(self.nodeName).getMatrix('worldspace').translationPart())
		return bLoc
	
	def __getObjectRotWS(self):
		bRot = toTorqueQuat(Blender.Object.Get(self.nodeName).getMatrix('worldspace').rotationPart().toQuat()).inverse()
		return bRot
		
	def getNodeLocWS(self, armName, pose):
		if self.blenderType == "object":
			retVal = self.__getObjectLocWS()
		elif self.blenderType == "bone":
			retVal = self.__getBoneLocWS(armName, pose)
		return retVal
		
	def getNodeRotWS(self, armName, pose):
		if self.blenderType == "object":
			retVal = self.__getObjectRotWS()
		elif self.blenderType == "bone":
			retVal = self.__getBoneRotWS(armName, pose)
		return retVal



# --------- some constants used by the below class ----------
# indicies into armInfo's lists
ARMOB = 0
ARMDATA = 1
ARMROT = 2
ARMROTINV = 3
ARMLOC = 4
ARMSIZE = 5

# indicies into armBone's lists
BONE = 0
BONEMAT = 1
BONERESTPOSWS = 2
BONERESTROTWS = 3
PARENTNAME = 4
BONEDEFPOSPS = 5
BONEDEFROTPS = 6

# --------- Class that stores all static data internally so we only have to get it once ----------
class DtsPoseUtilClass:
	'''
	
	DtsPoseUtilClass
	
	todo - description	
	
	
	'''
	def __init__(self, prefs):	
		gc.enable()
		self.nodes = {}
		self.armatures = {}
		self.__populateData(prefs)
	

	# recursive, for internal use only
	def __addTree(self, obj, parentNI):
			#   "obj" is a blender object of any type
			#   "parentNI" is the parent object (NodeInfo object) of obj

			nodeName = obj.name
			blenderType = "object"
			blenderObj = obj

			if (obj.getType() == 'Armature'): armParentNI = parentNI
			else: armParentNI = None

			# create a new nodeInfo object for the Blender object
			n = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, armParentNI)
			# add it to the nodes dict
			self.nodes[nodeName] = n
			
			if (obj.getType() == 'Armature'):
				# Armature transforms are needed even if the node for the armature object is
				# collapsed to compute bone transforms in worldspace, so we keep these in a separate list
				self.armatures[nodeName] = n
				# get blender armature datablock
				armDb = obj.getData()
				pose = obj.getPose()

				# loop through the armature's bones
				for bone in filter(lambda x: x.parent==None, armDb.bones.values()):					
					self.__addBoneTree(obj, n, bone, armDb, n, pose)
						
					
			# add child trees
			for child in filter(lambda x: x.parent==obj, Blender.Object.Get()):
				if (obj.getType() == 'Armature') and (child.getParentBoneName() != None):
					self.__addTree(child, self.nodes[child.getParentBoneName()])
				else:
					self.__addTree(child, n)
		

	
	# adds a bone tree recursively, for internal use only
	def __addBoneTree(self, obj, parentNI, boneOb, armDb, armParentNI, initPose):
		nodeName = boneOb.name
		blenderType = "bone"
		blenderObj = obj

		# create a new nodeInfo object for the Blender bone
		n = nodeInfoClass(nodeName, blenderType, blenderObj, parentNI, armParentNI, initPose)
		# add it to the nodes dict
		self.nodes[nodeName] = n

		# add child trees
		for bone in filter(lambda x: x.parent==boneOb, armDb.bones.values()):					
			self.__addBoneTree(obj, n, bone, armDb, armParentNI, initPose)

	# for debugging
	def __printTree(self, ni, indent=0):
		for nic in filter(lambda x: x.parentNI==ni, self.nodes.values()):			
			self.__printTree(nic, indent)
			

	def __populateData(self, prefs):
		# go through each object		
		for obj in filter(lambda x: x.parent==None, Blender.Object.Get()):
			if obj.parent == None:
				self.__addTree(obj, None)
		for ni in filter(lambda x: x.parentNI==None, self.nodes.values()):
			self.__printTree(ni)


	# --------- Localspace getters ----------------


	# *****
	# This is our only exposed public method.
	def getBoneLocRotLS(self, armName, bName, pose):
		loc = None
		rot = None
		#if self.armBones[armName][bName][PARENTNAME] == None:
		if self.nodes[bName].parentNI == None:
			loc = self.getOrphanBoneLocLS(armName, bName, pose)
			rot = self.getOrphanBoneRotLS(armName, bName, pose)
		else:
			loc = self.getBoneLocLS(armName, bName, pose)
			rot = self.getBoneRotLS(armName, bName, pose)
		return loc, rot
	# *****
	
	# -----  everything below this point is private
	
	# TESTED
	def getBoneLocLS(self, armName, bName, pose):
		#parentName = self.armBones[armName][bName][PARENTNAME]
		#if parentName == None: raise ValueError
		node = self.nodes[bName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# get the bone's location in parent space
		whereIsBonePS = self.getBonePosPS(armName, bName, pose)
		# get the bone's default location in parent space
		# ( This is where the bone should be if it has not been explicitly moved or
		# effected by a constraint.)
		#whereShouldBoneBePS = self.armBones[armName][bName][BONEDEFPOSPS]
		whereShouldBoneBePS = node.defPosPS
		
		# subtract out the position that the bone will end up in due to FK transforms
		# from the parent bone, as these are already taken care of due to the nodes being
		# in the parent's local space.
		whereIsBonePS = whereIsBonePS - whereShouldBoneBePS
		return whereIsBonePS

	# Get the rotation from rest of a connected bone in the bone's local space.
	# TESTED
	def getBoneRotLS(self, armName, bName, pose):
		#parentName = self.armBones[armName][bName][PARENTNAME]
		#if parentName == None: raise ValueError
		node = self.nodes[bName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# get the default rotation of the bone in parent space, this
		# is what the bone's rotation should be if it has not been
		# explicitly rotated or affected by a constraint.
		#bDefRotPS = self.armBones[armName][bName][BONEDEFROTPS].inverse()
		bDefRotPS = node.defRotPS.inverse()
		
		# get the current rotation of the bone in parent space.
		bCurRotPS = self.getBoneRotPS(armName, bName, pose)
		bRotLS = bCurRotPS.inverse() * bDefRotPS
		return bRotLS.inverse()

	'''
	# orphan bone translations are defined in worldspace
	# relative to the default postion of the bone.
	# TESTED
	def getOrphanBoneLocLS(self, armName, bName, pose):
		print "getOrphanBoneLocLS called..."
		# get the rest position of the bone
		bRestPos = self.armBones[armName][bName][BONERESTPOSWS]
		# get the bone's current position
		bCurPos = self.getBoneLocWS(armName, bName, pose)
		# subtract the rest postion from the current position to get
		# the bone's local movement
		bMovement = bCurPos - bRestPos
		return bMovement

	# get the difference between an orphan bone's rest rotation
	# and it's current rotation; this is the bone's localspace
	# rotation.
	# TESTED

	def getOrphanBoneRotLS(self, armName, bName, pose):
		# get the bone's rest rotation in worldspace
		bRestRot = self.armBones[armName][bName][BONERESTROTWS]
		# get the bone's worldspace rotation
		bCurRot = self.getBoneRotWS(armName, bName, pose)
		# get the differnce between the two, worldspace factors out
		bRotDelta = (bCurRot.inverse() * bRestRot.inverse()).inverse()
		return bRotDelta
	'''

	# --------- (private) Parentspace getters ----------------

	# determine the position of the bone in parentSpace
	# (absolute parent space position, not relative to default position of the bone)
	# TESTED
	def getBonePosPS(self, armName, bName, pose):
		node = self.nodes[bName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# find the parent's location in worldspace
		whereIsParentWS = parent.getNodeLocWS(armName, pose)
		
		# find the child's location in worldspace
		whereIsChildWS = node.getNodeLocWS(armName, pose)
		
		# subtract out the parent's location
		whereIsBonePS = whereIsChildWS - whereIsParentWS
		
		# determine the transform needed to get to the same point in the parent's space.
		whereIsBonePS = parent.getNodeRotWS(armName, pose).inverse().apply(whereIsBonePS)
		return whereIsBonePS

	# Get a non-orphan bone's rotation in parent space
	# TESTED
	def getBoneRotPS(self, armName, bName, pose):
		node = self.nodes[bName]
		parent = node.parentNI
		if parent == None: raise ValueError
		# get the bone's rotation in worldspace
		boneRotWS = node.getNodeRotWS(armName, pose)
		# get the parent bone's rotation in worldspace
		parentBoneRotWS = parent.getNodeRotWS(armName, pose)
		
		# get the difference
		bRotPS = boneRotWS * parentBoneRotWS.inverse()
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





# *** entry point for getBoneLocWS testing ***
if __name__ == "__main__":
	arm = Blender.Object.Get('ArmatureObj')
	armName = arm.name
	scene = Blender.Scene.GetCurrent()
	scene.getRenderingContext().currentFrame(40)
	scene.update(1)
	# get the pose
	pose = arm.getPose()

	PoseUtil = DtsPoseUtilClass()

	bName = 'Thigh.L'
	#bName = 'Pelvis.L'
	#bName = 'FollowMe'
	parentName = PoseUtil.armBones[armName][bName][PARENTNAME]

	#PoseUtil.getBoneLocWS(armName, bName, pose)
	#POSWSFromPS = (PoseUtil.armBones[armName][bName][BONEDEFPOSPS] * bMath.Matrix(PoseUtil.armBones[armName][parentName][BONERESTROTWS])) + PoseUtil.armBones[armName][parentName][BONERESTPOSWS]
	
	#setEmptyRot(PoseUtil.armBones[armName][bName][BONERESTROTWS])
	#putEmptyAt(PoseUtil.armBones[armName][bName][BONERESTPOSWS])
	
	setEmptyRot(PoseUtil.getBoneRestRotWS(armName, bName))
	putEmptyAt(PoseUtil.getBoneRestPosWS(armName, bName))

	#setEmptyRot(PoseUtil.getBoneRotWS(armName, bName, pose))
	#putEmptyAt(PoseUtil.getBoneLocWS(armName, bName, pose))

	#getBoneDefPosPS(self, armName, bName)
	#dif = toBlenderQuat(PoseUtil.getBoneRotLS(armName, bName, pose)).toEuler()
	#print "((((((((("
	#print toBlenderVec(PoseUtil.getBoneDefPosPS(armName, bName))
	#print toBlenderVec(PoseUtil.getBonePosPS(armName, bName, pose))

	#print toBlenderQuat(PoseUtil.armBones[armName][bName][BONEDEFROTPS].normalize()).toEuler()
	#print toBlenderQuat(PoseUtil.getBoneRotPS(armName, bName, pose).normalize()).toEuler()
	#print "differnce = ", dif
	#print "((((((((("
	
	#getBoneRotLS(self, armName, bName, pose)
	#print "((((((((("
	#print toBlenderVec(PoseUtil.getBoneDefPosPS(armName, bName))
	#print toBlenderVec(PoseUtil.getBonePosPS(armName, bName, pose))

	#print toBlenderQuat(PoseUtil.getBoneDefRotPS(armName, bName)).toEuler()
	#print toBlenderQuat(PoseUtil.getBoneRotLS(armName, bName, pose)).toEuler()
	#print "((((((((("
	
	
	#PoseUtil.getBoneRotLS(armName, bName, pose)
	#locWS = PoseUtil.armBones[armName][parentName][BONERESTROTWS].inverse().apply(PoseUtil.getBoneDefPosPS(armName, bName) + PoseUtil.armBones[armName][parentName][BONERESTPOSWS]) 
	#rotWS = PoseUtil.getBoneDefRotPS(armName, bName) * PoseUtil.armBones[armName][parentName][BONERESTROTWS]
	#setEmptyRot(rotWS)
	#putEmptyAt(locWS)


	print "Done!"