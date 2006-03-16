'''
poseUtil.py

Copyright (c) 2006 Joseph Greenawalt(jsgreenawalt@gmail.com)

Permission is hereby granted, free of charge, to any person obtainingTorque_Util.dump_write
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial poTorque_Util.dump_writelnrtions of the Software.

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

import gc

gc.enable()
'''
	Utility functions for dealing with Blender's pose module.
	these functions allow us to move between the different
	spaces involved
'''
#-------------------------------------------------------------------------------------------------


# --------- some constants used by the below class ----------
# indicies into armInfo's lists
ARMOB = 0
ARMDATA = 1
ARMMAT = 2
ARMROT = 3
ARMROTINV = 4
ARMLOC = 5
ARMSIZE = 6

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
	
	Insert documentation here.
	
	'''
	def __init__(self):	
		gc.enable()
		self.armBones = {}
		self.armInfo = {}	
		self.__populateData()
	
	def __populateData(self):
		# go through each armature object
		for armOb in Blender.Object.Get():
			if (armOb.getType() != 'Armature') or (armOb.name == "DTS-EXP-GHOST-OB"): continue
			
			# add a dictionary entry for it, and store all data reguarding the
			# armature in a list
			armDb = armOb.getData()
			armMat = bMath.Matrix(armOb.getMatrix())
			armRot = bMath.Matrix(armMat).rotationPart()
			armRotInv = bMath.Matrix(armRot).invert()
			armLoc = armMat.translationPart()
			armSize = bMath.Vector(armOb.getSize())
			self.armInfo[armOb.name] = [ armOb, armDb, armMat, armRot, armRotInv, armLoc, armSize ]
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
				self.armBones[armOb.name][bName][BONERESTPOSWS] = self.__getBoneRestPosWS(armOb.name, bName)
				self.armBones[armOb.name][bName][BONERESTROTWS] = self.__getBoneRestRotWS(armOb.name, bName)

			# second pass for calculated static bone data
			for bone in armDb.bones.values():
				bName = bone.name				
				if bone.hasParent():
					self.armBones[armOb.name][bName][BONEDEFPOSPS] = self.__getBoneDefPosPS(armOb.name, bName)
					self.armBones[armOb.name][bName][BONEDEFROTPS] = self.__getBoneDefRotPS(armOb.name, bName)

				


	# --------- Localspace getters ----------------


	# *****
	# This is our only exposed public function.
	def getBoneLocRotLS(self, armName, bName, pose):
		loc = None
		rot = None
		if self.armBones[armName][bName][PARENTNAME] == None:
			loc = self.__getOrphanBoneLocLS(armName, bName, pose)
			rot = self.__getOrphanBoneRotLS(armName, bName, pose)
		else:
			loc = self.__getBoneLocLS(armName, bName, pose)
			rot = self.__getBoneRotLS(armName, bName, pose)
		return loc, rot
	# *****
	
	# ********  everything below this point is private
	
	# TESTED
	def __getBoneLocLS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's location in parent space
		whereIsBonePS = self.__getBonePosPS(armName, bName, pose)
		# get the bone's default location in parent space
		# ( This is where the bone should be if it has not been explicitly moved or
		# effected by a constraint.)
		whereShouldBoneBePS = self.armBones[armName][bName][BONEDEFPOSPS]
		#whereShouldBoneBePS = __getBoneDefPosPS(armName, bName, parentName)
		# subtract out the position that the bone will end up in due to FK transforms
		# from the parent bone, as these are already taken care of due to the nodes being
		# in the parent's local space.
		whereIsBonePS = whereIsBonePS - whereShouldBoneBePS
		return whereIsBonePS


	# Get the rotation from rest of a connected bone in the bone's local space.
	# TESTED
	def __getBoneRotLS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the default rotation of the bone in parent space, this
		# is what the bone's rotation should be if it has not been
		# explicitly rotated or affected by a constraint.
		bDefRotPS = self.armBones[armName][bName][BONEDEFROTPS]
		# get the current rotation of the bone in parent space.
		bCurRotPS = self.__getBoneRotPS(armName, bName, pose)
		bRotLS = ( bCurRotPS.toMatrix().invert() * bDefRotPS.toMatrix()).toQuat()
		return bRotLS


	# orphan bone translations are defined in worldspace
	# relative to the default postion of the bone.
	# TESTED
	# MAY NEED TO TAKE ANOTHER LOOK AT THIS.
	def __getOrphanBoneLocLS(self, armName, bName, pose):
		# get the rest position of the bone
		bRestPos = self.armBones[armName][bName][BONERESTPOSWS]
		# get the bone's current position
		bCurPos = self.__getBoneLocWS(armName, bName, pose)
		# subtract the rest postion from the current position to get
		# the bone's local movement
		bMovement = bCurPos - bRestPos
		return bMovement


	# get the difference between an orphan bone's rest rotation
	# and it's current rotation; this is the bone's localspace
	# rotation.
	# TESTED
	def __getOrphanBoneRotLS(self, armName, bName, pose):
		# get the bone's rest rotation in worldspace
		bRestRot = bMath.Matrix(self.armBones[armName][bName][BONERESTROTWS])
		# get the bone's worldspace rotation
		bCurRot = self.__getBoneRotWS(armName, bName, pose)
		# get the differnce between the two, worldspace factors out
		bRotDelta = bMath.DifferenceQuats(bRestRot.toQuat(), bCurRot.toQuat())
		return bRotDelta

	# --------- (private) Parentspace getters ----------------

	# determine the position of the bone in parentSpace
	# (absolute parent space position, not relative to default position of the bone)
	# TESTED
	def __getBonePosPS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# find the parent's location in worldspace
		whereIsParentWS = self.__getBoneLocWS(armName, parentName, pose)
		# find the child's location in worldspace
		whereIsChildWS = self.__getBoneLocWS(armName, bName, pose)
		# subtract out the parent's location
		whereIsBonePS = whereIsChildWS - whereIsParentWS
		# add on armature scale
		armSize = self.armInfo[armName][ARMSIZE]
		whereIsBonePS = bMath.Vector(whereIsBonePS[0] * armSize[0], whereIsBonePS[1] * armSize[1], whereIsBonePS[2]  * armSize[2])
		# determine the transform needed to get to the same point in the parent's space.
		whereIsBonePS = whereIsBonePS * self.__getBoneRotWS(armName, parentName, pose).invert()
		return whereIsBonePS

	# Get a non-orphan bone's rotation in parent space
	# TESTED
	def __getBoneRotPS(self, armName, bName, pose):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's default rotation in worldspace
		boneRotWS = self.__getBoneRotWS(armName, bName, pose)
		# get the parent bone's default rotation in worldspace
		parentBoneRotWS = self.__getBoneRotWS(armName, parentName, pose)
		bRotPS = bMath.DifferenceQuats(boneRotWS.toQuat(), parentBoneRotWS.toQuat())
		return bRotPS


	# Determine a bone's default position for the current pose in the parent bone's space.
	# This is where the bone should be if it has not been explicitly moved or
	# effected by a constraint.
	# TESTED
	def __getBoneDefPosPS(self, armName, bName):
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
		offsetWS = bMath.Vector(offsetWS[0] * armSize[0], offsetWS[1] * armSize[1], offsetWS[2]  * armSize[2])
		# rotate the offset into the parent bone's default local space		
		offsetPS = offsetWS * bMath.Matrix(self.armBones[armName][parentName][BONERESTROTWS]).invert()

		return offsetPS


	# determine a bone's default rotation in parent space
	# This is what the bone's rotation should be, relative to the parent bone,
	# if it has not been directly rotated or affected by a constraint.
	# TESTED
	def __getBoneDefRotPS(self, armName, bName):
		parentName = self.armBones[armName][bName][PARENTNAME]
		if parentName == None: raise ValueError
		# get the bone's default rotation in worldspace
		boneRotWS = bMath.Matrix(self.armBones[armName][bName][BONERESTROTWS])
		# get the parent bone's default rotation in worldspace
		parentBoneRotWS = self.armBones[armName][parentName][BONERESTROTWS]
		bDefRotPS = bMath.DifferenceQuats(boneRotWS.toQuat(), parentBoneRotWS.toQuat())
		return bDefRotPS

			
	# --------- (private) Worldspace getters ----------------

	# determine the position of any bone in worldspace
	# TESTED
	def __getBoneLocWS(self, armName, bName, pose):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# and it's inverse
		armRotInv = self.armInfo[armName][ARMROTINV]
		# get the pose location
		bTrans = armRotInv * pose.bones[bName].poseMatrix.translationPart()
		# Scale by armature's scale
		armSize = bMath.Vector(self.armInfo[armName][ARMSIZE])
		# have to square the scale  - this is stupid, but it works
		armSize = armSize[0] * armSize[0], armSize[1] * armSize[1],  armSize[2] * armSize[2]
		bTrans = bMath.Vector(bTrans[0] * armSize[0], bTrans[1] * armSize[1], bTrans[2]  * armSize[2])
		# add on armature pivot to translate into worldspace
		bTrans = bTrans + self.armInfo[armName][ARMLOC]
		return bTrans

	# determine the rotation of any bone in worldspace
	# TESTED
	def __getBoneRotWS(self, armName, bName, pose):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# get the pose rotation
		bRot = pose.bones[bName].poseMatrix.rotationPart() * armRot
		return bMath.Matrix(bRot).rotationPart()

	# determine a bone's rest position in worldspace (scaling is free)
	# TESTED
	def __getBoneRestPosWS(self, armName, bName):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# get the bone's location in armaturespace
		bLoc = self.armBones[armName][bName][BONEMAT].translationPart()
		# rotate out of armature space
		bLoc = bLoc * armRot
		# add on armature's location
		bLoc = bLoc + self.armInfo[armName][ARMLOC]
		#bLoc = bLoc + arm.getMatrix().translationPart()
		return bLoc



	# determine a bone's rest rotation in worldspace
	# TESTED
	def __getBoneRestRotWS(self, armName, bName):
		# get the armature's rotation
		armRot = self.armInfo[armName][ARMROT]
		# get the bone's rotation in armaturespace
		bRot = self.armBones[armName][bName][BONEMAT].rotationPart()
		# rotate out of armature space
		bRot = bRot * armRot
		return bMath.Matrix(bRot).rotationPart()

		

	


# --------- test functions ----------------

def putEmptyAt(loc):
	try: Blender.Object.Get('Empty')
	except:
		Blender.Object.New('Empty', 'Empty')
	empty = Blender.Object.Get('Empty')
	if not (empty in scene.getChildren()): scene.link(empty)
	empty.setLocation(loc.x, loc.y, loc.z)
	scene.update(1)
	Blender.Window.RedrawAll()
	
def setEmptyRot(rot):
	try: Blender.Object.Get('Empty')
	except:
		Blender.Object.New('Empty', 'Empty')
	empty = Blender.Object.Get('Empty')
	if not (empty in scene.getChildren()): scene.link(empty)
	#print rot
	#print rot
	empty.setMatrix(bMath.Matrix(rot))
	scene.update(1)
	Blender.Window.RedrawAll()
		


# *** entry point for getBoneLocWS testing ***
if __name__ == "__main__":
	arm = Blender.Object.Get('Armature')
	armName = arm.name
	scene = Blender.Scene.GetCurrent()
	scene.getRenderingContext().currentFrame(1)
	scene.update(1)
	# get the pose
	pose = arm.getPose()

	PoseUtil = DtsPoseUtilClass()

	bName = 'Bone.002'
	parentName = PoseUtil.armBones[armName][bName][PARENTNAME]

	#PoseUtil.getBoneLocWS(armName, bName, pose)
	POSWSFromPS = (PoseUtil.armBones[armName][bName][BONEDEFPOSPS] * bMath.Matrix(PoseUtil.armBones[armName][parentName][BONERESTROTWS])) + PoseUtil.armBones[armName][parentName][BONERESTPOSWS]

	setEmptyRot(PoseUtil.armBones[armName][bName][BONERESTROTWS])
	putEmptyAt(POSWSFromPS)

	print "Done!"