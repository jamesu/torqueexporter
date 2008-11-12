'''
DtsPoseUtil.py

Copyright (c) 2006-2009 Joseph Greenawalt(jsgreenawalt@gmail.com)

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
import math as pMath

gc.enable()
#-------------------------------------------------------------------------------------------------
def initRestScaleData(self, initPoses=None):
	self.restScale = self.__getNodeRestScale(initPoses)

def __getNodeRestScale(self, poses):
	if self.blenderType == "object":
		retVal = self.__getObjectScale()
	elif self.blenderType == "bone":
		retVal = self.__getBoneScale(poses)
	return retVal


# ***********************
# determine the position of any bone in worldspace
# TESTED
def __getBoneLocWS(self, poses):
	pose = poses[self.armParentNI.blenderObjName]
	# get the armature's rotation
	armRot = self.armParentNI.getNodeRotWS(poses)
	# get the pose location
	bTrans = armRot.apply(toTorqueVec(pose.bones[self.originalBoneName].poseMatrix.translationPart()))
	# Scale by armature's scale
	bTrans = self.__fixBoneOffset(bTrans, self.armParentNI, poses)
	# add on armature pivot to translate into worldspace
	bTrans = bTrans + self.armParentNI.getNodeLocWS(poses)
	return bTrans
	
def __fixBoneOffset(self, bOffset, armNI, poses):
	offsetAccum = bOffset
	for parentNI in armNI.parentStack:
		scale = parentNI.getNodeScale(poses, False)
		# this early out is a big win!
		if scale.eqDelta(Vector(1.0, 1.0, 1.0), 0.02): continue
		# get parent rotation and inverse rotation
		rot = parentNI.getNodeRotWS(poses)
		rotInv = rot.inverse()
		# rotate the offset into parent bone's space 
		offsetAccum = rotInv.apply(offsetAccum)
		# apply the parent node's scale to the offset.
		offsetAccum = Vector(offsetAccum[0] * scale[0], offsetAccum[1] * scale[1], offsetAccum[2] * scale[2])
		# rotate back into worldspace for next iteration :-)
		offsetAccum = rot.apply(offsetAccum)
	# finally, add the armature's own scale
	armScale = armNI.getNodeScale(poses, False)
	offsetAccum = Vector(offsetAccum.members[0] * armScale.members[0], offsetAccum.members[1] * armScale.members[1], offsetAccum.members[2]  * armScale.members[2])
	return offsetAccum


# determine the rotation of any bone in worldspace
# TESTED
def __getBoneRotWS(self, poses):
	pose = poses[self.armParentNI.blenderObjName]
	# get the armature's rotation
	armRot = self.armParentNI.getNodeRotWS(poses)
	# get the pose rotation and rotate into worldspace
	bRot = ( toTorqueQuat(pose.bones[self.originalBoneName].poseMatrix.rotationPart().toQuat().inverse()) * armRot)
	return bRot



# determine the scale of any bone (relative to local axies)
# TESTED
def __getBoneScale(self, poses):
	pose = poses[self.armParentNI.blenderObjName]
	bScale = toTorqueVec(pose.bones[self.originalBoneName].size)
	return bScale



# determine the location of an object node in worldspace
# TESTED
def __getObjectLocWS(self, poses=None):
	bLoc = toTorqueVec(Blender.Object.Get(self.blenderObjName).getMatrix('worldspace').translationPart())
	return bLoc

# determine the rotation of an object node in worldspace
# TESTED
def __getObjectRotWS(self, poses=None):
	bRot = toTorqueQuat(Blender.Object.Get(self.blenderObjName).getMatrix('worldspace').rotationPart().toQuat()).inverse()
	return bRot

# determine the scale of any object (relative to local axies)
# TESTED
def __getObjectScale(self):
	bLoc = toTorqueVec([Blender.Object.Get(self.blenderObjName).SizeX,\
	                    Blender.Object.Get(self.blenderObjName).SizeY,\
	                    Blender.Object.Get(self.blenderObjName).SizeZ])
	return bLoc


def getNodeScale(self, poses, delta=True):
	if self.blenderType == "object":
		retVal = self.__getObjectScale()
	elif self.blenderType == "bone":
		retVal = self.__getBoneScale(poses)
	if delta:
		#print self.restScale
		retVal = Vector(retVal[0]/self.restScale[0], retVal[1]/self.restScale[1], retVal[2]/self.restScale[2])
	return retVal

# bind loc/rot methods dynamically based on node type
def bindLocRotMethods(self):
	if self.blenderType == "object":
		self.getNodeLocWS = self.__getObjectLocWS
		self.getNodeRotWS = self.__getObjectRotWS
	elif self.blenderType == "bone":
		self.getNodeLocWS = self.__getBoneLocWS
		self.getNodeRotWS = self.__getBoneRotWS


# binds the above methods to the nodeInfo class imported from DtsSceneInfo.py.
def bindDynamicMethods():
	new.instancemethod(__getNodeRestScale, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getNodeRestScale'] = __getNodeRestScale
	new.instancemethod(__getBoneLocWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getBoneLocWS'] = __getBoneLocWS
	new.instancemethod(__getBoneRotWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getBoneRotWS'] = __getBoneRotWS
	new.instancemethod(__getBoneScale, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getBoneScale'] = __getBoneScale
	new.instancemethod(__getObjectLocWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getObjectLocWS'] = __getObjectLocWS
	new.instancemethod(__getObjectRotWS, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getObjectRotWS'] = __getObjectRotWS
	new.instancemethod(__getObjectScale, None, nodeInfoClass)
	nodeInfoClass.__dict__['__getObjectScale'] = __getObjectScale
	new.instancemethod(getNodeScale, None, nodeInfoClass)
	nodeInfoClass.__dict__['getNodeScale'] = getNodeScale
	new.instancemethod(bindLocRotMethods, None, nodeInfoClass)
	nodeInfoClass.__dict__['bindLocRotMethods'] = bindLocRotMethods
	new.instancemethod(initRestScaleData, None, nodeInfoClass)
	nodeInfoClass.__dict__['initRestScaleData'] = initRestScaleData
	
	new.instancemethod(__fixBoneOffset, None, nodeInfoClass)
	nodeInfoClass.__dict__['__fixBoneOffset'] = __fixBoneOffset
	#__fixBoneOffset



# -------------------------------------------------------------------------------------
# stand-alone functions (for now)
# These functions represent an extreme workaround to the problem of blender matrices
# that are pre-gimbal-locked when non-uniform scaling of objects or bones is present.
# This is obviously not the prefered solution, as it could potentially lead to data
# loss, but, the problem is so pervasive that no other solution currently seems possible.
# 

# find Ipo objects with non-defualt (1,1,1) scales.


def getScaledIpoNames():
	retVal = []
	ipos = Blender.Ipo.Get()
	for ipo in ipos:		
		ipoName = ipo.name
		
		# determine IPO type
		if Blender.Ipo.PO_SCALEX in ipo.curveConsts.values():
			curveConsts = [Blender.Ipo.PO_SCALEX, Blender.Ipo.PO_SCALEY, Blender.Ipo.PO_SCALEZ]
		elif Blender.Ipo.OB_SCALEX in ipo.curveConsts.values():
			curveConsts = [Blender.Ipo.OB_SCALEX, Blender.Ipo.OB_SCALEY, Blender.Ipo.OB_SCALEZ]
		else:
			# ipo is not of interest
			continue

		# we've got an object or pose IPO
		
		# calc range that we need to check
		lowest = 1000000 # one million frames should be enough for anyone :-)
		highest = -1000000
		for i in range(0, len(curveConsts)):
			if ipo[curveConsts[i]] == None: continue
			startPoint = ipo[curveConsts[i]].bezierPoints[0].pt[0]
			endPoint = ipo[curveConsts[i]].bezierPoints[len(ipo[curveConsts[i]].bezierPoints)-1].pt[0]
			if startPoint < lowest: lowest = startPoint
			if endPoint > highest: highest = endPoint
			
		# check every frame in range		
		for fr in range(int(round(lowest)), int(round(highest)+2)):

			try: curveValX = ipo[curveConsts[0]][fr]
			except: curveValX = None
			try: curveValY = ipo[curveConsts[1]][fr]
			except: curveValY = None
			try: curveValZ = ipo[curveConsts[2]][fr]
			except: curveValZ = None
			
			if curveValX == None: curveValX = 1.0
			if curveValY == None: curveValY = 1.0
			if curveValZ == None: curveValZ = 1.0
			scaleVec = Vector(curveValX, curveValY, curveValZ)

			if scaleVec.eqDelta(Vector(1.0,1.0,1.0), 0.001):
				continue
			else:
				# we've got a non-default scale so
				# store off the name of the IPO
				if not ipoName in retVal: retVal.append(ipoName)
				break

	return retVal

		

# save scales from every pose and object ipo in the scene
# returns a nested dict containing all values needed to recreate the
# original curves.
def saveIpoScales(scaledIpoNames):
	savedScales = {}
	for ipoName in scaledIpoNames:		
		savedScales[ipoName] = {}
		savedScales[ipoName]['X'] = {}
		savedScales[ipoName]['X']['vec'] = []
		savedScales[ipoName]['X']['ht'] = []
		savedScales[ipoName]['Y'] = {}
		savedScales[ipoName]['Y']['vec'] = []
		savedScales[ipoName]['Y']['ht'] = []
		savedScales[ipoName]['Z'] = {}
		savedScales[ipoName]['Z']['vec'] = []
		savedScales[ipoName]['Z']['ht'] = []
		
		ipo = Blender.Ipo.Get(ipoName)
		
		# determine ipo type
		if Blender.Ipo.PO_SCALEX in ipo.curveConsts.values():
			savedScales[ipoName]['type'] = 'object'
			curveConsts = [Blender.Ipo.PO_SCALEX, Blender.Ipo.PO_SCALEY, Blender.Ipo.PO_SCALEZ]
		elif Blender.Ipo.OB_SCALEX in ipo.curveConsts.values():
			savedScales[ipoName]['type'] = 'pose'
			curveConsts = [Blender.Ipo.OB_SCALEX, Blender.Ipo.OB_SCALEY, Blender.Ipo.OB_SCALEZ]
		else:
			# panic and bail
			print "This should never happen! Possible data loss!"
			# todo - bail

		# save off knot points and handle types
		if ipo[curveConsts[0]] != None:
			savedScales[ipoName]['extendType'] = ipo[curveConsts[0]].extend
			savedScales[ipoName]['interpolationMode'] = ipo[curveConsts[0]].interpolation
			for point in ipo[curveConsts[0]].bezierPoints:
				savedScales[ipoName]['X']['vec'].append(point.vec)
				savedScales[ipoName]['X']['ht'].append(point.handleTypes)

		if ipo[curveConsts[1]] != None:
			savedScales[ipoName]['extendType'] = ipo[curveConsts[1]].extend
			savedScales[ipoName]['interpolationMode'] = ipo[curveConsts[1]].interpolation
			for point in ipo[curveConsts[1]].bezierPoints:
				savedScales[ipoName]['Y']['vec'].append(point.vec)
				savedScales[ipoName]['Y']['ht'].append(point.handleTypes)


		if ipo[curveConsts[2]] != None:
			savedScales[ipoName]['extendType'] = ipo[curveConsts[2]].extend
			savedScales[ipoName]['interpolationMode'] = ipo[curveConsts[2]].interpolation
			for point in ipo[curveConsts[2]].bezierPoints:
				savedScales[ipoName]['Z']['vec'].append(point.vec)
				savedScales[ipoName]['Z']['ht'].append(point.handleTypes)		
	return savedScales



# removes all scale keys/channels from all IPOs in the scene.
def removeIpoScales(scaledIpoNames):

	for ipoName in scaledIpoNames:
		ipo = Blender.Ipo.Get(ipoName)
		# determine ipo type
		if Blender.Ipo.PO_SCALEX in ipo.curveConsts.values():
			curveConsts = [Blender.Ipo.PO_SCALEX, Blender.Ipo.PO_SCALEY, Blender.Ipo.PO_SCALEZ]
		elif Blender.Ipo.OB_SCALEX in ipo.curveConsts.values():
			curveConsts = [Blender.Ipo.OB_SCALEX, Blender.Ipo.OB_SCALEY, Blender.Ipo.OB_SCALEZ]	
		# remove scale ipos
		try:ipo[curveConsts[0]] = None
		except: pass
		try:ipo[curveConsts[1]] = None
		except: pass
		try:ipo[curveConsts[2]] = None
		except: pass
	
	# loop through each object in the scene and clear its scale if it uses an IPO in our list
	for ob in Blender.Scene.GetCurrent().objects:
		if ob.ipo != None:
			if ob.ipo.name in scaledIpoNames:
				ob.SizeX = 1.0
				ob.SizeY = 1.0
				ob.SizeZ = 1.0
	
	# clear bone scales as well
	for armOb in filter(lambda x: x.type == 'Armature', Blender.Scene.GetCurrent().objects):
		tempPose = armOb.getPose()
		for poseBone in tempPose.bones.values():
			# reset the bone's transform
			poseBone.quat = bMath.Quaternion().identity()
			poseBone.size = bMath.Vector(1.0, 1.0, 1.0)
			poseBone.loc = bMath.Vector(0.0, 0.0, 0.0)
		# update the pose.
		tempPose.update()




# restores all scale keys/channels that were previously saved and removed
def restoreIpoScales(ipoScales):

	for ipoName in ipoScales.keys():
		
		ipo = Blender.Ipo.Get(ipoName)
		# determine type
		ipoType = ipoScales[ipoName]['type']
		if ipoType == 'object':
			curveConsts = [Blender.Ipo.OB_SCALEX, Blender.Ipo.OB_SCALEY, Blender.Ipo.OB_SCALEZ]
			curveNames = ['ScaleX', 'ScaleY', 'ScaleZ']
		elif ipoType == 'pose':
			curveConsts = [Blender.Ipo.PO_SCALEX, Blender.Ipo.PO_SCALEY, Blender.Ipo.PO_SCALEZ]
			curveNames = ['SizeX', 'SizeY', 'SizeZ']
			
		# re-create curves
		if len(ipoScales[ipoName]['X']['vec']) > 0:
			ipo.addCurve(curveNames[0])
			ipo[curveConsts[0]].extend = ipoScales[ipoName]['extendType']
			ipo[curveConsts[0]].interpolation = ipoScales[ipoName]['interpolationMode']
		if len(ipoScales[ipoName]['Y']['vec']) > 0:
			ipo.addCurve(curveNames[1])
			ipo[curveConsts[1]].extend = ipoScales[ipoName]['extendType']
			ipo[curveConsts[1]].interpolation = ipoScales[ipoName]['interpolationMode']
		if len(ipoScales[ipoName]['Z']['vec']) > 0:
			ipo.addCurve(curveNames[2])
			ipo[curveConsts[2]].extend = ipoScales[ipoName]['extendType']
			ipo[curveConsts[2]].interpolation = ipoScales[ipoName]['interpolationMode']

		# add points
		i = 0
		for point in ipoScales[ipoName]['X']['vec']:
			knot = point[1]
			ipo[curveConsts[0]].append((knot[0], knot[1]))
			point = ipo[curveConsts[0]].bezierPoints[len(ipo[curveConsts[0]].bezierPoints)-1]
			point.handleTypes = ipoScales[ipoName]['X']['ht'][i]
			point.vec = ipoScales[ipoName]['X']['vec'][i]
			i += 1
		i = 0
		for point in ipoScales[ipoName]['Y']['vec']:
			knot = point[1]
			ipo[curveConsts[1]].append((knot[0], knot[1]))
			point = ipo[curveConsts[1]].bezierPoints[len(ipo[curveConsts[1]].bezierPoints)-1]
			point.handleTypes = ipoScales[ipoName]['Y']['ht'][i]
			point.vec = ipoScales[ipoName]['Y']['vec'][i]
			i += 1
		i = 0
		for point in ipoScales[ipoName]['Z']['vec']:
			knot = point[1]
			ipo[curveConsts[2]].append((knot[0], knot[1]))
			point = ipo[curveConsts[2]].bezierPoints[len(ipo[curveConsts[2]].bezierPoints)-1]
			point.handleTypes = ipoScales[ipoName]['Z']['ht'][i]
			point.vec = ipoScales[ipoName]['Z']['vec'][i]
			i += 1
		
		# recalc scale curves		
		try: ipo[curveConsts[0]].recalc()
		except: pass
		try: ipo[curveConsts[1]].recalc()
		except: pass
		try: ipo[curveConsts[2]].recalc()
		except: pass



# -------------------------------------------------------------------------------------

# --------- Class that dumps node transform data for any/all frames ----------
class NodeTransformUtil:
	def __init__(self, exportScale = 1.0):
		print "initializing NodeTransformUtil..."
		# get dictionaries
		self.nodes = DtsGlobals.SceneInfo.nodes
		self.armatures = DtsGlobals.SceneInfo.armatures

		# bind dynamic methods to nodeInfoClass
		bindDynamicMethods()

		# bind test methods - todo - rename these
		for ni in self.nodes.values():
			ni.bindLocRotMethods()

		# get poses for all armatures in the scene
		armPoses = {}
		for armNI in self.armatures.values():
			arm = armNI.getBlenderObj()
			armPoses[arm.name] = arm.getPose()

		# init default scales - need these first, chicken and egg.
		for ni in self.nodes.values():
			ni.initRestScaleData(armPoses)
		
		self.exportScale = exportScale
		if pMath.fabs(exportScale - 1.0) < 0.001:
			self.useExportScale = False
		else:
			self.useExportScale = True



	# ******************
	def dumpReferenceFrameTransforms(self, orderedNodeList, refFrame, twoPass=True):
		# dump world space transforms, use raw scale values
		transformsWS = self.dumpNodeTransformsWS(orderedNodeList, refFrame, refFrame, twoPass, False)
		# get parent space tranforms without correcting scaled offsets (bake scale into offsets)
		transformsPS = self.worldSpaceToParentSpace(orderedNodeList, transformsWS, refFrame, refFrame, False)

		return transformsPS[0]


	def dumpBlendRefFrameTransforms(self, orderedNodeList, refFrame, twoPass=True):
		# dump world space transforms, use raw scale values
		transformsWS = self.dumpNodeTransformsWS(orderedNodeList, refFrame, refFrame, twoPass, False)
		# get parent space tranforms without correcting scaled offsets (bake scale into offsets)
		transformsPS = self.worldSpaceToParentSpace(orderedNodeList, transformsWS, refFrame, refFrame, True)

		return transformsPS[0]


	# used for regular animations (non-blend)
	def dumpFrameTransforms(self, orderedNodeList, startFrame, endFrame, twoPass=True):
		# dump world space transforms, use delta scale values
		transformsWS = self.dumpNodeTransformsWS(orderedNodeList, startFrame, endFrame, twoPass, True)
		# get parent space tranforms, correcting scaled offsets
		transformsPS = self.worldSpaceToParentSpace(orderedNodeList, transformsWS, startFrame, endFrame, True)

		return transformsPS

	# used for blend animations
	def dumpBlendFrameTransforms(self, orderedNodeList, startFrame, endFrame, twoPass=True):
		# dump world space transforms, use raw scale values
		transformsWS = self.dumpNodeTransformsWS(orderedNodeList, startFrame, endFrame, twoPass, False)
		# get parent space tranforms, correcting scaled offsets
		transformsPS = self.worldSpaceToParentSpace(orderedNodeList, transformsWS, startFrame, endFrame, True)

		return transformsPS
		

	# used to get deltas for Torque blend animations
	def getDeltasFromRef(self, refTransforms, transformsPS):
		# loop through node transforms for each frame
		for frameTransforms in transformsPS:
			# loop through each node tranform and convert to deltas from reference frame
			for i in range(0, len(frameTransforms)):
				nodeTransforms = frameTransforms[i]
				nodeRefTransforms = refTransforms[i]
				# loc, rot, and scale for the frame
				loc = nodeTransforms[0]
				scale = nodeTransforms[1]
				rot = nodeTransforms[2]
				
				# reference loc, rot, and scale for the frame
				refLoc = nodeRefTransforms[0]
				refScale = nodeRefTransforms[1]
				refRot = nodeRefTransforms[2]

				# loc
				nodeTransforms[0][0] = loc[0] - refLoc[0]
				nodeTransforms[0][1] = loc[1] - refLoc[1]
				nodeTransforms[0][2] = loc[2] - refLoc[2]				
				# loc for blend animations is relative to the default transform of the node
				frameTransforms[i][0] = refRot.inverse().apply(nodeTransforms[0])

				# scale
				try:    frameTransforms[i][1][0] = scale[0] / refScale[0]
				except: frameTransforms[i][1][0] = 0.0
				try:    frameTransforms[i][1][1] = scale[1] / refScale[1]
				except: frameTransforms[i][1][1] = 0.0
				try:    frameTransforms[i][1][2] = scale[2] / refScale[2]
				except: frameTransforms[i][1][2] = 0.0

				# rot
				frameTransforms[i][2] = rot * refTransforms[i][2].inverse()
		
		return transformsPS
	# ******************

	# Dump raw blender worldspace matrices for all nodes in the orderedNodeList.
	# Returns a nested list containing a list node matrices for each frame in
	# the specified order
	# DESIGNED FOR SPEED
	def dumpNodeTransformsWS(self, orderedNodeList, startFrame, endFrame, twoPass=True, wantDeltaScale=True):
		#print "wantDeltaScale=",wantDeltaScale
		transforms = []
		
		# build lists so we don't have to keep doing it.
		orderedNIList = []
		for nname in orderedNodeList:
			orderedNIList.append(self.nodes[nname])
		
		if twoPass:
			# 1st pass - get loc and scale for the given nodes on every frame in the specified range
			for fr in range(startFrame, endFrame+1):
				
				# new frame
				transforms.append([])
				frameTransforms = transforms[-1]

				# set the current frame
				Blender.Set('curframe',fr)

				# get poses for all armatures in the scene
				armPoses = {}
				for armNI in self.armatures.values():
					arm = armNI.getBlenderObj()
					armPoses[arm.name] = arm.getPose()

				# get loc and scale for each node
				for ni in orderedNIList:
					frameTransforms.append([ni.getNodeLocWS(armPoses), ni.getNodeScale(armPoses, wantDeltaScale)])
					

			# save and clear scale IPOs
			# get the names of IPOs with scale keys
			scaledIpoNames = getScaledIpoNames()
			# store scale IPOs
			savedScales = saveIpoScales(scaledIpoNames)
			# remove the scale IPOs
			removeIpoScales(scaledIpoNames)
			

			# 2nd pass - get rot for the given nodes on every frame in the specified range
			# 1st pass - get loc and scale for the given nodes on every frame in the specified range
			for fr in range(startFrame, endFrame+1):
				
				# get existing frame
				frameTransforms = transforms[fr - startFrame]

				# set the current frame
				if Blender.Get('curframe') == fr: Blender.Set('curframe',fr+1)
				Blender.Set('curframe',fr)

				# get poses for all armatures in the scene
				armPoses = {}
				for armNI in self.armatures.values():
					arm = armNI.getBlenderObj()
					armPoses[arm.name] = arm.getPose()

				# get rot for each node
				i = 0
				for ni in orderedNIList:
					frameTransforms[i].append(ni.getNodeRotWS(armPoses))
					i += 1

			# restore scale IPOs
			restoreIpoScales(savedScales)
			
		else:
			# one pass - get loc, scale, and rot for the given nodes on every frame in the specified range
			for fr in range(startFrame, endFrame+1):
				
				# new frame
				transforms.append([])
				frameTransforms = transforms[-1]

				# set the current frame
				Blender.Set('curframe',fr)

				# get poses for all armatures in the scene
				armPoses = {}
				for armNI in self.armatures.values():
					arm = armNI.getBlenderObj()
					armPoses[arm.name] = arm.getPose()

				# get loc and scale for each node
				for ni in orderedNIList:
					frameTransforms.append([ni.getNodeLocWS(armPoses), ni.getNodeScale(armPoses, wantDeltaScale), ni.getNodeRotWS(armPoses)])

		if self.useExportScale:
			transforms = self.applyExportScale(transforms)
			
		return transforms
	
	# Convert worldspace loc and rot transforms to parent space
	def worldSpaceToParentSpace(self, orderedNodeList, transformsWS, startFrame, endFrame, correctScaledTransforms=True):
		
		transformsPS = []

		# build lists so we don't have to keep doing it.
		orderedNIList = []
		i = 0
		for nname in orderedNodeList:
			orderedNIList.append(self.nodes[nname])
			self.nodes[nname].tempIdx = i
			i += 1
			
		# breadcrumb parent stack, saves on hierarchy lookups
		parentStacks = []
		for ni in orderedNIList:
			parentStacks.append([])			
			pNI = ni.getGoodNodeParentNI()
			while pNI != None:
				parentStacks[-1].append(pNI.tempIdx)
				pNI = pNI.getGoodNodeParentNI()
			parentStacks[-1].reverse()
		
		# go through all frames and convert to parent space.
		for fr in range(startFrame, endFrame+1):
			# get WS frame transforms
			frameTransformsWS = transformsWS[fr - startFrame]
			
			# new frame
			transformsPS.append([])
			frameTransformsPS = transformsPS[-1]
			
			# convert transforms one node at a time
			i = 0 
			for ni in orderedNIList:
				locWS = frameTransformsWS[i][0]
				scale = frameTransformsWS[i][1]
				rotWS = frameTransformsWS[i][2]				
				pNI = ni.getGoodNodeParentNI()
				if pNI == None:
					# use worldspace loc and rot as-is
					frameTransformsPS.append([locWS, scale, rotWS])
				else:
					pLocWS = frameTransformsWS[pNI.tempIdx][0]
					pRotWS = frameTransformsWS[pNI.tempIdx][2]
					if correctScaledTransforms: locPS = pRotWS.inverse().apply(self.correctScaledOffset(locWS - pLocWS, parentStacks[i], frameTransformsWS))
					else: locPS = pRotWS.inverse().apply(locWS - pLocWS)					
					rotPS = rotWS * pRotWS.inverse()
					frameTransformsPS.append([locPS, scale, rotPS])
				i += 1

		return transformsPS
	
	

	# -------------------------------------------------------------------
	# functions below this point are private, for internal use only
	def correctScaledOffset(self, offsetIn, parentStack, frameTransformsWS):
		offsetAccum = offsetIn
		for pIdx in parentStack:
			scale = frameTransformsWS[pIdx][1]			
			# this early out is a big win!
			if scale.eqDelta(Vector(1.0, 1.0, 1.0), 0.02): continue
			# get parent rotation and inverse rotation
			rot = frameTransformsWS[pIdx][2]
			rotInv = rot.inverse()
			# rotate the offset into parent bone's space 
			offsetAccum = rotInv.apply(offsetAccum)
			# remove the parent bone's scale from the offset.
			offsetAccum = Vector(offsetAccum[0] * (1.0/scale[0]), offsetAccum[1] * (1.0/scale[1]), offsetAccum[2] * (1.0/scale[2]))
			# rotate back into worldspace for next iteration :-)
			offsetAccum = rot.apply(offsetAccum)
		
		return offsetAccum
		

	# apply export scale factor to offsets
	def applyExportScale(self, transforms):
		exportScale = self.exportScale
		for frameTransforms in transforms:
			for nodeTransforms in frameTransforms:
				nodeTransforms[0][0] = nodeTransforms[0][0] * exportScale
				nodeTransforms[0][1] = nodeTransforms[0][1] * exportScale
				nodeTransforms[0][2] = nodeTransforms[0][2] * exportScale
		return transforms
		

# --------- Utility functions -------------
def toTorqueVec(v):
	return Vector(v[0], v[1], v[2])
	
def toBlenderVec(v):
	return bMath.Vector(v[0], v[1], v[2])
	
def toTorqueQuat(q):
	return Quaternion(q[1],q[2],q[3],q[0])
	
def toBlenderQuat(q):
	#print "\nq = ", q
	return bMath.Quaternion(q[3],q[0],q[1],q[2])


# --------- test functions ----------------
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