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
	def __init__(self):	
		gc.enable()
		self.armBones = {}
		self.armInfo = {}	
		self.__populateData()
	
	def __populateData(self):
		# go through each armature object
		for armOb in Blender.Object.Get():
			if (armOb.getType() != 'Armature'): continue
			# add a dictionary entry for the armature, and store all it's static data in a list
			armDb = armOb.getData()
			armMat = bMath.Matrix(armOb.getMatrix())
			armRot = self.toTorqueQuat(armMat.rotationPart().toQuat().normalize())
			armRotInv = armRot.inverse()
			armLoc = self.toTorqueVec(armMat.translationPart())
			armSize = self.toTorqueVec(armOb.getSize())
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
	'''
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
	'''
	# Optimized version of the above
	# There is more optimization to be done here, but I thought I'd stop
	# before I mess something up.  After inlining most of the math code,
	# it seems as if of some of the inverse() calls may not be needed, perhaps
	# someone more knowledgable about quaternion math will fix it some day - Joe G. :P
	def getBoneLocRotLS(self, armName, bName, pose):
		armRot = self.armInfo[armName][ARMROT]
		armRotInv = self.armInfo[armName][ARMROTINV]
		armLoc = self.armInfo[armName][ARMLOC]
		parentName = self.armBones[armName][bName][PARENTNAME]
		loc = None
		rot = None
		if parentName == None:
			# for orphan bones
			bRestPos = self.armBones[armName][bName][BONERESTPOSWS]			
			bRestRot = self.armBones[armName][bName][BONERESTROTWS]
			armSize = self.armInfo[armName][ARMSIZE]
			
			bTrans = armRot.apply(self.toTorqueVec(pose.bones[bName].poseMatrix.translationPart()))
			bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
			bTrans = bTrans + armLoc
			loc = bTrans - bRestPos

			bRot = ( armRotInv * self.toTorqueQuat(pose.bones[bName].poseMatrix.rotationPart().toQuat().inverse()) )
			rot = (bRot.inverse() * bRestRot.inverse()).inverse()

		else:
			# for bones with a parent			
			armSize = self.armInfo[armName][ARMSIZE]
			whereShouldBoneBePS = self.armBones[armName][bName][BONEDEFPOSPS]
			bDefRotPS = self.armBones[armName][bName][BONEDEFROTPS].inverse()

			#bTrans = armRot.apply(self.toTorqueVec(pose.bones[parentName].poseMatrix.translationPart()))
			v = self.toTorqueVec(pose.bones[parentName].poseMatrix.translationPart())
			v0 = v.members[0]
			v1 = v.members[1]
			v2 = v.members[2]
			v3 = 0.0
			c0 = -armRot.members[0]
			c1 = -armRot.members[1]
			c2 = -armRot.members[2]
			c3 = armRot.members[3]
			s0 = armRot.members[0]
			s1 = armRot.members[1]
			s2 = armRot.members[2]
			s3 = armRot.members[3]
			ir0 = +c0*v3 +c1*v2 -c2*v1 +c3*v0
			ir1 = -c0*v2 +c1*v3 +c2*v0 +c3*v1
			ir2 = +c0*v1 -c1*v0 +c2*v3 +c3*v2
			ir3 = -c0*v0 -c1*v1 -c2*v2 +c3*v3
			r0 = +ir0*s3 +ir1*s2 -ir2*s1 +ir3*s0
			r1 = -ir0*s2 +ir1*s3 +ir2*s0 +ir3*s1
			r2 = +ir0*s1 -ir1*s0 +ir2*s3 +ir3*s2
			#r3 = -ir0*s0 -ir1*s1 -ir2*s2 +ir3*s3
			#return Vector(r0, r1, r2)
			
			#bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
			#bTrans = bTrans + armLoc
			r0 += armLoc.members[0]
			r1 += armLoc.members[1]
			r2 += armLoc.members[2]
			#whereIsParentWS = bTrans
			#whereIsParentWS = Vector(r0, r1, r2)
			whereIsParentWS0 = r0
			whereIsParentWS1 = r1
			whereIsParentWS2 = r2
			
			#bTrans = armRot.apply(self.toTorqueVec(pose.bones[bName].poseMatrix.translationPart()))
			v = self.toTorqueVec(pose.bones[bName].poseMatrix.translationPart())
			v0 = v.members[0]
			v1 = v.members[1]
			v2 = v.members[2]
			v3 = 0.0
			c0 = -armRot.members[0]
			c1 = -armRot.members[1]
			c2 = -armRot.members[2]
			c3 = armRot.members[3]
			s0 = armRot.members[0]
			s1 = armRot.members[1]
			s2 = armRot.members[2]
			s3 = armRot.members[3]
			ir0 = +c0*v3 +c1*v2 -c2*v1 +c3*v0
			ir1 = -c0*v2 +c1*v3 +c2*v0 +c3*v1
			ir2 = +c0*v1 -c1*v0 +c2*v3 +c3*v2
			ir3 = -c0*v0 -c1*v1 -c2*v2 +c3*v3
			r0 = +ir0*s3 +ir1*s2 -ir2*s1 +ir3*s0
			r1 = -ir0*s2 +ir1*s3 +ir2*s0 +ir3*s1
			r2 = +ir0*s1 -ir1*s0 +ir2*s3 +ir3*s2
			#r3 = -ir0*s0 -ir1*s1 -ir2*s2 +ir3*s3
			#return Vector(r0, r1, r2)
			
			#bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
			r0 = r0 * armSize.members[0]
			r1 = r1 * armSize.members[1]
			r2 = r2 * armSize.members[2]
			
			#bTrans = bTrans + armLoc
			r0 += armLoc.members[0]
			r1 += armLoc.members[1]
			r2 += armLoc.members[2]			
			
			#whereIsChildWS = bTrans
			#whereIsChildWS = Vector(r0, r1, r2)
			#whereIsBonePS = whereIsChildWS - whereIsParentWS
			r0 -= whereIsParentWS0
			r1 -= whereIsParentWS1
			r2 -= whereIsParentWS2			
			bRot = ( armRotInv * self.toTorqueQuat(pose.bones[parentName].poseMatrix.rotationPart().toQuat().inverse()) )
			#whereIsBonePS = Vector(r0, r1, r2)
			#whereIsBonePS = bRot.apply(whereIsBonePS)
			r3 = 0.0
			c0 = -bRot.members[0]
			c1 = -bRot.members[1]
			c2 = -bRot.members[2]
			c3 = bRot.members[3]
			s0 = bRot.members[0]
			s1 = bRot.members[1]
			s2 = bRot.members[2]
			s3 = bRot.members[3]
			ir0 = +c0*r3 +c1*r2 -c2*r1 +c3*r0
			ir1 = -c0*r2 +c1*r3 +c2*r0 +c3*r1
			ir2 = +c0*r1 -c1*r0 +c2*r3 +c3*r2
			ir3 = -c0*r0 -c1*r1 -c2*r2 +c3*r3
			r1_0 = +ir0*s3 +ir1*s2 -ir2*s1 +ir3*s0
			r1_1 = -ir0*s2 +ir1*s3 +ir2*s0 +ir3*s1
			r1_2 = +ir0*s1 -ir1*s0 +ir2*s3 +ir3*s2
			#r1_3 = -ir0*s0 -ir1*s1 -ir2*s2 +ir3*s3
			#return vector(r1_0, r1_1, r1_2)
			
			#whereIsBonePS = whereIsBonePS - whereShouldBoneBePS
			r1_0 -= whereShouldBoneBePS.members[0]
			r1_1 -= whereShouldBoneBePS.members[1]
			r1_2 -= whereShouldBoneBePS.members[2]
			
			#loc = whereIsBonePS
			loc = Vector(r1_0, r1_1, r1_2)

			
			boneRotWS = ( armRotInv * self.toTorqueQuat(pose.bones[bName].poseMatrix.rotationPart().toQuat().inverse()) )
			parentBoneRotWS = ( armRotInv * self.toTorqueQuat(pose.bones[parentName].poseMatrix.rotationPart().toQuat().inverse()) )
			bCurRotPS = parentBoneRotWS.inverse() * boneRotWS
			bRotLS =   bCurRotPS.inverse() * bDefRotPS
			rot = bRotLS.inverse()

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
		whereIsBonePS = whereIsChildWS - whereIsParentWS
		# determine the transform needed to get to the same point in the parent's space.
		whereIsBonePS = self.getBoneRotWS(armName, parentName, pose).apply(whereIsBonePS)
		return whereIsBonePS

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
		bTrans = Vector(bTrans.members[0] * armSize.members[0], bTrans.members[1] * armSize.members[1], bTrans.members[2]  * armSize.members[2])
		# add on armature pivot to translate into worldspace
		bTrans = bTrans + self.armInfo[armName][ARMLOC]
		return bTrans

	# determine the rotation of any bone in worldspace
	# TESTED
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


'''
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


'''		


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