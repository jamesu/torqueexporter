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
import math as pMath

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
	
	This class provides one stop access to armature and bone data through the armInfo and
	armBones dictionaries.  The rational behind this is to centralize all access to Blender's
	armature and pose system to avoid some nasty memory leaks in the Blender Python API.  Basically
	we store off all the static spatial data concerning armatures and bones and use them as needed.
	
	
	
	'''
	def __init__(self, prefs):	
		gc.enable()
		self.armBones = {}
		self.armInfo = {}	
		self.__populateData(prefs)
	
	def __populateData(self, prefs):
		# go through each armature object
		for armOb in Blender.Object.Get():
			if (armOb.getType() != 'Armature'): continue
			# add a dictionary entry for the armature, and store all it's static data in a list
			armDb = armOb.getData()
			armMat = bMath.Matrix(armOb.getMatrix('worldspace'))
			armRot = self.toTorqueQuat(armMat.rotationPart().toQuat().normalize())
			armRotInv = armRot.inverse()
			armLoc = self.toTorqueVec(armMat.translationPart())
			armSize = self.toTorqueVec(armOb.getSize('worldspace'))
			try: exportScale = prefs['ExportScale']
			except: exportScale = 1.0
			armSize[0], armSize[1], armSize[2] = armSize[0]*exportScale, armSize[1]*exportScale, armSize[2]*exportScale
			armLoc[0], armLoc[1], armLoc[2] = armLoc[0]*exportScale, armLoc[1]*exportScale, armLoc[2]*exportScale
			self.armInfo[armOb.name] = [ armOb, armDb, armRot, armRotInv, armLoc, armSize ]
			self.armBones[armOb.name] = {}			

			# loop through the armature's bones
			for bone in armDb.bones.values():
				bName = bone.name				
				# store off all static values for each bone
				# leaks memory in blender 2.41
				bMat = bone.matrix['ARMATURESPACE']				
				if bone.hasParent():
					parentName = bone.parent.name
				else:
					parentName = None				
				self.armBones[armOb.name][bName] = [ bone, bMat, None, None, parentName, None, None ]
				self.armBones[armOb.name][bName][BONERESTPOSWS] = self.getBoneRestPosWS(armOb.name, bName)
				self.armBones[armOb.name][bName][BONERESTROTWS] = self.getBoneRestRotWS(armOb.name, bName)

			# second pass for calculated static bone data
			for bone in armDb.bones.values():
				bName = bone.name				
				if bone.hasParent():
					self.armBones[armOb.name][bName][BONEDEFPOSPS] = self.getBoneDefPosPS(armOb.name, bName)
					self.armBones[armOb.name][bName][BONEDEFROTPS] = self.getBoneDefRotPS(armOb.name, bName)

				


	# --------- Localspace getters ----------------


	# *****
	# This is our only exposed public method.
	def getBoneLocRotLS(self, armName, bName, pose):
		loc = None
		rot = None
		if self.armBones[armName][bName][PARENTNAME] == None:
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
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's location in parent space
		whereIsBonePS = self.getBonePosPS(armName, bName, pose)
		# get the bone's default location in parent space
		# ( This is where the bone should be if it has not been explicitly moved or
		# effected by a constraint.)
		whereShouldBoneBePS = self.armBones[armName][bName][BONEDEFPOSPS]		
		# subtract out the position that the bone will end up in due to FK transforms
		# from the parent bone, as these are already taken care of due to the nodes being
		# in the parent's local space.
		whereIsBonePS = whereIsBonePS - whereShouldBoneBePS
		return whereIsBonePS

	# Get the rotation from rest of a connected bone in the bone's local space.
	# TESTED
	def getBoneRotLS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the default rotation of the bone in parent space, this
		# is what the bone's rotation should be if it has not been
		# explicitly rotated or affected by a constraint.
		bDefRotPS = self.armBones[armName][bName][BONEDEFROTPS].inverse()
		# get the current rotation of the bone in parent space.
		bCurRotPS = self.getBoneRotPS(armName, bName, pose)
		bRotLS =   bCurRotPS.inverse() * bDefRotPS
		return bRotLS.inverse()

	# orphan bone translations are defined in worldspace
	# relative to the default postion of the bone.
	# TESTED
	def getOrphanBoneLocLS(self, armName, bName, pose):
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


	# --------- (private) Parentspace getters ----------------

	# determine the position of the bone in parentSpace
	# (absolute parent space position, not relative to default position of the bone)
	# TESTED
	def getBonePosPS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# find the parent's location in worldspace
		whereIsParentWS = self.getBoneLocWS(armName, parentName, pose)
		# find the child's location in worldspace
		whereIsChildWS = self.getBoneLocWS(armName, bName, pose)
		# subtract out the parent's location
		offsetFromParent = whereIsChildWS - whereIsParentWS		
		# remove scale from the offset, as best we can.
		offsetScaleRemoved = self.correctScaledOffset(offsetFromParent, armName, bName, pose)
		# Rotate the offset into the parent's space
		offsetFromParent = self.getBoneRotWS(armName, parentName, pose).apply(offsetScaleRemoved)		
		return offsetFromParent

	# walk back up the node tree and build a list of scales and transforms for each bone
	# that has it's scale explicitly set to a non (1,1,1) value.  We then rotate the passed in
	# offset into each space and apply the corresponding inverted scale.  The end result is
	# an offset that has all scale and most importantly, worldspace skew effects removed.
	def correctScaledOffset(self, offsetIn, armName, bName, pose):
		# inverse scales
		scaleListLS = []
		# rotations (not inverse)
		rotListWS = []

		# set initial parent
		parentName = self.armBones[armName][bName][PARENTNAME]
		# go backwards through the hierarchy and build a list of scale and rotation operations (both inverse)
		while parentName != None:
			rot = self.getBoneRotWS(armName, parentName, pose)
			scaleRaw = self.toTorqueVec(pose.bones[parentName].size)
			scaleInv = Vector(1.0/scaleRaw[0], 1.0/scaleRaw[1], 1.0/scaleRaw[2])
			# check to see if all members are within delta of one, if so, don't
			# even bother adding them to the list since it'll only throw off accuracy
			if scaleRaw.eqDelta( Vector(1.0,1.0,1.0), 0.008 ):
				try: parentName = self.armBones[armName][parentName][PARENTNAME]
				except: parentName = None
				continue
			scaleListLS.append(scaleInv)
			rotListWS.append(rot)
			try: parentName = self.armBones[armName][parentName][PARENTNAME]
			except: parentName = None


			
		# reverse both lists so inverse scales are applied in correct order
		# note - this *does* matter since scales are applied in parent space
		scaleListLS.reverse()
		rotListWS.reverse()
		
		# apply the inverse scales in the correct space
		offsetAccum = offsetIn		
		for i in range(0, len(scaleListLS)):
			scaleInv = scaleListLS[i]
			rot = rotListWS[i]
			rotInv = rot.inverse()
			# rotate the offset into parent bone's space 
			offsetAccum = rot.apply(offsetAccum)
			# remove the parent bone's scale from the offset.
			offsetAccum = Vector(offsetAccum[0] * scaleInv[0], offsetAccum[1] * scaleInv[1], offsetAccum[2] * scaleInv[2])
			# rotate back into worldspace for next iteration :-)
			offsetAccum = rotInv.apply(offsetAccum)

		# return the calculated offset		
		offsetOut = offsetAccum
		return offsetOut




	# Get a non-orphan bone's rotation in parent space
	# TESTED
	def getBoneRotPS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's default rotation in worldspace
		boneRotWS = self.getBoneRotWS(armName, bName, pose)
		# get the parent bone's default rotation in worldspace
		parentBoneRotWS = self.getBoneRotWS(armName, parentName, pose)
		# get the difference
		bRotPS = parentBoneRotWS.inverse() * boneRotWS
		return bRotPS


	# ***********************
	# these next four functions are used to populate the armBones database, they should
	# not be called by any other functions, only in init

	# Determine a bone's default position for the current pose in the parent bone's space.
	# This is where the bone should be if it has not been explicitly moved or
	# effected by a constraint.
	# TESTED
	def getBoneDefPosPS(self, armName, bName):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's default position in worldspace
		boneLocWS = self.armBones[armName][bName][BONERESTPOSWS]
		# get the parent bone's default position in worldspace
		parentBoneLocWS = self.armBones[armName][parentName][BONERESTPOSWS]
		# subtract out the parent bone's position, this gives us the offset of the child in worldspace
		offsetWS = boneLocWS - parentBoneLocWS
		# scale the offset by armature's scale
		armSize = self.armInfo[armName][ARMSIZE]
		# rotate the offset into the parent bone's default local space		
		offsetPS = self.armBones[armName][parentName][BONERESTROTWS].inverse().apply(offsetWS)
		return offsetPS

	# determine a bone's default rotation in parent space
	# This is what the bone's rotation should be, relative to the parent bone,
	# if it has not been directly rotated or affected by a constraint.
	# TESTED
	def getBoneDefRotPS(self, armName, bName):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's default rotation in worldspace
		boneRotWS = self.armBones[armName][bName][BONERESTROTWS]
		# get the parent bone's default rotation in worldspace
		parentBoneRotWS = self.armBones[armName][parentName][BONERESTROTWS]
		# get the difference (why backwards? because it works)
		bDefRotPS = boneRotWS * parentBoneRotWS.inverse()
		return bDefRotPS

			
	# --------- Worldspace getters ----------------

	# determine a bone's rest position in worldspace
	# TESTED
	def getBoneRestPosWS(self, armName, bName):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# get the bone's location in armaturespace
		bLoc = self.toTorqueVec(self.armBones[armName][bName][BONEMAT].translationPart())
		# add on armature's scale
		armSize = self.armInfo[armName][ARMSIZE]
		bLoc = Vector( bLoc[0] * armSize[0], bLoc[1] * armSize[1], bLoc[2] * armSize[2] )
		# rotate out of armature space
		bLoc = armRot.apply(bLoc)
		# add on armature's location
		bLoc = bLoc + self.armInfo[armName][ARMLOC]
		return bLoc

	# determine a bone's rest rotation in worldspace
	# TESTED
	def getBoneRestRotWS(self, armName, bName):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# get the bone's rotation in armaturespace
		bRot = self.toTorqueQuat(self.armBones[armName][bName][BONEMAT].rotationPart().toQuat())
		# rotate out of armature space
		bRot = (bRot * armRot)
		return bRot

	# ***********************


	# determine the position of any bone in worldspace
	# TESTED
	def getBoneLocWS(self, armName, bName, pose):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# and it's inverse
		armRotInv = self.armInfo[armName][ARMROTINV]
		# get the pose location
		bTrans = armRot.apply(self.toTorqueVec(pose.bones[bName].poseMatrix.translationPart()))
		# Scale by armature's scale
		armSize = self.armInfo[armName][ARMSIZE]
		#bTrans = Vector(bTrans[0] * armSize[0], bTrans[1] * armSize[1], bTrans[2]  * armSize[2])
		bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
		# add on armature pivot to translate into worldspace
		bTrans = bTrans + self.armInfo[armName][ARMLOC]
		return bTrans

	# determine the rotation of any bone in worldspace
	# TESTED - but is fairly innacurate when anisotropic scale is persent on parent bones.
	def getBoneRotWS(self, armName, bName, pose):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT].inverse()
		# get the pose rotation and rotate into worldspace
		bRot = ( armRot * self.toTorqueQuat(pose.bones[bName].poseMatrix.rotationPart().toQuat().inverse()) )
		return bRot

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
	arm = Blender.Object.Get('Armature')
	armName = arm.name
	scene = Blender.Scene.GetCurrent()
	scene.getRenderingContext().currentFrame(40)
	scene.update(1)
	# get the pose
	pose = arm.getPose()

	PoseUtil = DtsPoseUtilClass(None)

	bName = 'Bone.001'
	#bName = 'Pelvis.L'
	#bName = 'FollowMe'
	parentName = PoseUtil.armBones[armName][bName][PARENTNAME]

	#PoseUtil.getBoneLocWS(armName, bName, pose)
	#POSWSFromPS = (PoseUtil.armBones[armName][bName][BONEDEFPOSPS] * bMath.Matrix(PoseUtil.armBones[armName][parentName][BONERESTROTWS])) + PoseUtil.armBones[armName][parentName][BONERESTPOSWS]
	
	#setEmptyRot(PoseUtil.armBones[armName][bName][BONERESTROTWS])
	#putEmptyAt(PoseUtil.armBones[armName][bName][BONERESTPOSWS])
	
	
	setEmptyRot(PoseUtil.getBoneRotWS(armName, bName, pose))
	putEmptyAt(PoseUtil.getBoneLocWS(armName, bName, pose))
	

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