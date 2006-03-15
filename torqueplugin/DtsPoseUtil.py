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

'''
	Utility functions for dealing with Blender's pose module.
	these functions allow us to move between the different
	spaces involved
'''
#-------------------------------------------------------------------------------------------------

# --------- World Space getters ----------------

# determine the position of any bone in worldspace
# TESTED
def getBoneLocWS(arm, bName, pose):
	# get the armature's rotation
	armRot = arm.matrix.rotationPart()
	# and it's inverse
	armRotInv = bMath.Matrix(armRot).invert()
	# get the pose location
	bTrans = armRotInv * pose.bones[bName].poseMatrix.translationPart()

	# TESTING - scale by armature's scale - this is stupid, but it works
	armSize = bMath.Vector(arm.getSize())	
	armSize = armSize[0] * armSize[0], armSize[1] * armSize[1],  armSize[2] * armSize[2]
	bTrans = bMath.Vector(bTrans[0] * armSize[0], bTrans[1] * armSize[1], bTrans[2]  * armSize[2])
	# add on armature pivot to translate into worldspace
	bTrans = bTrans + arm.matrix.translationPart()
	return bTrans

# determine the rotation of any bone in worldspace
# TESTED
def getBoneRotWS(arm, bName, pose):
	# get the armature's rotation
	armRot = arm.matrix.rotationPart()
	# and it's inverse
	armRotInv = bMath.Matrix(armRot).invert()
	# get the pose rotation
	bRot = pose.bones[bName].poseMatrix.rotationPart() * armRot
	return bMath.Matrix(bRot).rotationPart()

# determine a bone's rest position in worldspace (scaling is free)
# TESTED
def getBoneRestPosWS(arm, bName):
	armDb = arm.getData()
	# get the armature's rotation
	armRot = arm.matrix.rotationPart()
	bone = armDb.bones[bName]
	# get the bone's location in armaturespace
	bLoc = bone.matrix['ARMATURESPACE'].translationPart() #+ arm.matrix.translationPart()
	# rotate out of armature space
	bLoc = bLoc * armRot
	# add on armature's location
	bLoc = bLoc + arm.matrix.translationPart()
	return bLoc

# determine a bone's rest rotation in worldspace
# TESTED
def getBoneRestRotWS(arm, bName):
	armDb = arm.getData()
	# get the armature's rotation
	armRot = arm.matrix.rotationPart()
	bone = armDb.bones[bName]
	# get the bone's rotation in armaturespace
	bRot = bone.matrix['ARMATURESPACE'].rotationPart() #+ arm.matrix.translationPart()
	# rotate out of armature space
	bRot = bRot * armRot
	return bMath.Matrix(bRot).rotationPart()

# --------- Parent Space getters ----------------

# determine the position of the bone in parentSpace
# (absolute parent space position, not relative to default position of the bone)
# TESTED
def getBonePosPS(arm, bName, parentName, pose):
	# find the parent's location in worldspace
	whereIsParentWS = getBoneLocWS(arm, parentName, pose)
	# find the child's location in worldspace
	whereIsChildWS = getBoneLocWS(arm, bName, pose)
	# subtract out the parent's location
	whereIsBonePS = whereIsChildWS - whereIsParentWS
	# add on armature scale
	armSize = bMath.Vector(arm.getSize())	
	whereIsBonePS = bMath.Vector(whereIsBonePS[0] * armSize[0], whereIsBonePS[1] * armSize[1], whereIsBonePS[2]  * armSize[2])
	# determine the transform needed to get to the same point in the parent's space.
	whereIsBonePS = whereIsBonePS * getBoneRotWS(arm, parentName, pose).invert()
	#print "whereIsBonePS = ", whereIsBonePS
	return whereIsBonePS

# Get a non-orphan bone's rotation in parent space
# TESTED
def getBoneRotPS(arm, bName, parentName, pose):
	# get the bone's default rotation in worldspace
	boneRotWS = getBoneRotWS(arm, bName, pose)
	# get the parent bone's default rotation in worldspace
	parentBoneRotWS = getBoneRotWS(arm, parentName, pose)
	bRotPS = bMath.DifferenceQuats(boneRotWS.toQuat(), parentBoneRotWS.toQuat())
	return bRotPS


# Determine a bone's default position for the current pose in the parent bone's space.
# This is where the bone should be if it has not been explicitly moved or
# effected by a constraint.
# TESTED
def getBoneDefPosPS(arm, bName, parentName):
	# get the bone's default position in worldspace
	boneLocWS = getBoneRestPosWS(arm, bName)
	# get the parent bone's default position in worldspace
	parentBoneLocWS = getBoneRestPosWS(arm, parentName)
	# subtract out the parent bone's position, this gives us the offset of the child in worldspace
	offsetWS = boneLocWS - parentBoneLocWS
	# scale the offset by armature's scale - this is stupid, but it works
	armSize = bMath.Vector(arm.getSize())	
	offsetWS = bMath.Vector(offsetWS[0] * armSize[0], offsetWS[1] * armSize[1], offsetWS[2]  * armSize[2])
	# rotate the offset into the parent bone's default local space
	offsetPS = offsetWS * getBoneRestRotWS(arm, parentName).invert()
	return offsetPS
	

# determine a bone's default rotation in parent space
# This is what the bone's rotation should be, relative to the parent bone,
# if it has not been directly rotated or affected by a constraint.
# TESTED
def getBoneDefRotPS(arm, bName, parentName):
	# get the bone's default rotation in worldspace
	boneRotWS = getBoneRestRotWS(arm, bName)
	# get the parent bone's default rotation in worldspace
	parentBoneRotWS = getBoneRestRotWS(arm, parentName)
	bDefRotPS = bMath.DifferenceQuats(boneRotWS.toQuat(), parentBoneRotWS.toQuat())
	return bDefRotPS
	
# --------- Local Space getters ----------------


# Should return zero if the bone is in default position with respect to the parent bone's
# rotation and location.
# TESTED
def getUnconnectedBoneLocLS(arm, bName, parentName, pose):
	# get the bone's location in parent space
	whereIsBonePS = getBonePosPS(arm, bName, parentName, pose)
	# get the bone's default location in parent space
	# ( This is where the bone should be if it has not been explicitly moved or
	# effected by a constraint.)
	whereShouldBoneBePS = getBoneDefPosPS(arm, bName, parentName)
	# subtract out the position that the bone will end up in due to FK transforms
	# from the parent bone, as these are already taken care of due to the nodes being
	# in the parent's local space.
	whereIsBonePS = whereIsBonePS - whereShouldBoneBePS
	return whereIsBonePS


# NOTE: same as getUnconnectedBoneLocLS
# TESTED
def getConnectedBoneLocLS(arm, bName, parentName, pose):
	# get the bone's location in parent space
	whereIsBonePS = getBonePosPS(arm, bName, parentName, pose)
	# get the bone's default location in parent space
	# ( This is where the bone should be if it has not been explicitly moved or
	# effected by a constraint.)
	whereShouldBoneBePS = getBoneDefPosPS(arm, bName, parentName)
	# subtract out the position that the bone will end up in due to FK transforms
	# from the parent bone, as these are already taken care of due to the nodes being
	# in the parent's local space.
	whereIsBonePS = whereIsBonePS - whereShouldBoneBePS
	return whereIsBonePS


# orphan bone translations are defined in worldspace
# relative to the default postion of the bone.
# TESTED
def getOrphanBoneLocLS(arm, bName, pose):
	# get the rest position of the bone
	bRestPos = getBoneRestPosWS(arm, bName)
	# get the bone's current position
	bCurPos = getBoneLocWS(arm, bName, pose)
	# subtract the rest postion from the current position to get
	# the bone's local movement
	bMovement = bCurPos - bRestPos
	return bMovement


# get the difference between an orphan bone's rest rotation
# and it's current rotation; this is the bone's localspace
# rotation.
# TESTED
def getOrphanBoneRotLS(arm, bName, pose):
	# get the bone's rest rotation in worldspace
	bRestRot = getBoneRestRotWS(arm, bName)
	# get the bone's worldspace rotation
	bCurRot = getBoneRotWS(arm, bName, pose)
	# get the differnce between the two, worldspace factors out
	bRotDelta = bMath.DifferenceQuats(bRestRot.toQuat(), bCurRot.toQuat())
	return bRotDelta

# get the delta rotation from rest of an unconnected bone in the parent's
# space.  Rotations of the parent are removed, leaving only the bone's
# local space rotation.
# TESTED
# NOTE - SAME AS getConnectedBoneRotLS
def getUnconnectedBoneRotLS(arm, bName, parentName, pose):
	# get the default rotation of the bone in parent space, this
	# is what the bone's rotation should be if it has not been
	# explicitly rotated or affected by a constraint.
	bDefRotPS = getBoneDefRotPS(arm, bName, parentName)
	# get the current rotation of the bone in parent space.
	bCurRotPS = getBoneRotPS(arm, bName, parentName, pose)
	bRotLS = ( bCurRotPS.toMatrix().invert() * bDefRotPS.toMatrix()).toQuat()
	return bRotLS


# get the rotation from rest of a connected bone in the bone's local space.
# TESTED
def getConnectedBoneRotLS(arm, bName, parentName, pose):
	# get the default rotation of the bone in parent space, this
	# is what the bone's rotation should be if it has not been
	# explicitly rotated or affected by a constraint.
	bDefRotPS = getBoneDefRotPS(arm, bName, parentName)
	# get the current rotation of the bone in parent space.
	bCurRotPS = getBoneRotPS(arm, bName, parentName, pose)
	bRotLS = ( bCurRotPS.toMatrix().invert() * bDefRotPS.toMatrix()).toQuat()
	return bRotLS

	

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
	arm = Blender.Object.Get('WalkMachine')
	scene = Blender.Scene.GetCurrent()
	scene.getRenderingContext().currentFrame(1)
	scene.update(1)
	# get the pose
	pose = arm.getPose()
	armDb = arm.getData()
	# get the armature's rotation
	armRot = arm.matrix.rotationPart()
	# and its inverse
	armRotInv = bMath.Matrix(armRot).invert()


	# get the child's translation
	boneName = 'MGBTip'
	parentName = 'FP'
	
	setEmptyRot(getBoneRestRotWS(arm, boneName))
	putEmptyAt(getBoneRestPosWS(arm, boneName))
	#getUnconnectedBoneRotLS(arm, boneName, parentName, pose)
	#getConnectedBoneRotLS(arm, boneName, parentName, pose)
	#getConnectedBoneLocLS(arm, boneName, parentName, pose)
	#getBoneRotPS(arm, boneName, parentName, pose)
	#getBoneDefRotPS(arm, boneName, parentName)
	#getOrphanBoneRotLS(arm, boneName, pose)
	#getOrphanBoneLocLS(arm, boneName, pose)
	#getConnectedBoneLocLS(arm, boneName, parentName, pose)
	#getUnconnectedBoneLocLS(arm, boneName, parentName, pose)
	#getBoneDefPosPS(arm, boneName, parentName)
	print "Done!"