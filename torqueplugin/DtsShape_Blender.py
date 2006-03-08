'''
Dts.Shape_Blender.py

Copyright (c) 2005 - 2006 James Urquhart(j_urquhart@btinternet.com)

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
import DTSPython
from DTSPython import *

import DtsMesh_Blender
from DtsMesh_Blender import *

import Blender
from Blender import NMesh, Armature, Scene, Object, Material, Texture
from Blender import Mathutils as bMath

import gc

'''
   Util functions used by class as well as exporter gui
'''
#-------------------------------------------------------------------------------------------------

# Convert Bone pos to a MatrixF
def blender_bone2matrixf(head, tail, roll):
	'''
		Convert bone rest state (defined by bone.head, bone.tail and bone.roll)
		to a matrix (the more standard notation).
		Taken from blenkernel/intern/armature.c in Blender source.
		See also DNA_armature_types.h:47.
	'''
	target = Vector(0.0, 1.0, 0.0)
	delta  = Vector(tail[0] - head[0], tail[1] - head[1], tail[2] - head[2])
	nor    = delta.normalize()

	# Find Axis & Amount for bone matrix
	axis   = target.cross(nor)

	if axis.dot(axis) > 0.0000000000001:
		# if nor is *not* a multiple of target ...
		axis    = axis.normalize()
		theta   = math.acos(target.dot(nor))
		# Make Bone matrix
		bMatrix = MatrixF().rotate(axis, theta)
	else:
		# if nor is a multiple of target ...
		# point same direction, or opposite?
		if target.dot(nor) > 0.0:
			updown =  1.0
		else:
			updown = -1.0

		# I think this should work ...
		dMatrix = [
		updown, 0.0, 0.0, 0.0,
		0.0, updown, 0.0, 0.0,
		0.0, 0.0, 1.0, 0.0,
		0.0, 0.0, 0.0, 1.0,
		]
		bMatrix = MatrixF(dMatrix)

	# Make Roll matrix
	rMatrix = MatrixF().rotate(nor, roll)
	# Combine and output result
	return (rMatrix * bMatrix)


# Makes a ghost copy of an armature in blender, puts it in a
# cannonical state, and uses it for the export, rather than
# the user's armature.  This avoids many problems and will
# allow the exporter code to be simplifed. - Joe
def getGhostArmature(armOb, ghostName):
	'''

	Armature ghosting function
	by J.S. Greenawalt

	'''
	# put the scene in object mode if it's not already there.
	in_editmode = Blender.Window.EditMode()
 	if in_editmode: Blender.Window.EditMode(0)
	
	# get the existing armature data.
	arm = armOb.getData() # assumes 'Armature' exists

	# get the current scene
	scene = Blender.Scene.getCurrent()

	# try to find an existing ghost object to recycle
	# if not found make a new one
	try:
		ghostObject = Blender.Object.Get(ghostName + "-OB")
		# in 2.40 returns none, in 2.41 throws ValueError
		if ghostObject == None:
			raise AttributeError
	except:
		ghostObject = Blender.Object.New('Armature', ghostName + "-OB")

	# try to find an existing ghost data block to recycle
	# if not found, make a new one.
	try:
		ghostData = Blender.Armature.Get(ghostName + "-DB")
		if ghostData == None:
			raise AttributeError
	except:
		ghostData = Blender.Armature.Armature(ghostName + "-DB")

	# link the data with the object
	ghostObject.link(ghostData)

	# link the object with the scene
	if ghostObject not in scene.getChildren():
		scene.link(ghostObject)

	# copy location from the real armature to the ghost.
	ghostObject.setLocation(armOb.getLocation())

	# begin data copy
	ghostData.makeEditable()

	# delete all existing data from the ghost armature
	for bone in ghostData.bones.values():
		del ghostData.bones[bone.name]

	# copy all bones from the real armature to the ghost
	for bone in arm.bones.values():
		eb = Blender.Armature.Editbone()
		# transform the bones to match the armature's rotation
		rotMat = armOb.getMatrix().rotationPart() #.invert()
		eb.head = bone.head['ARMATURESPACE'] * rotMat
		eb.tail = bone.tail['ARMATURESPACE'] * rotMat
		ghostData.bones[bone.name] = eb

	# match bone roll angles to worldspace
	for bone in arm.bones.values():
		rotMat = armOb.getMatrix().rotationPart()
		# which way is the z axis of the bone pointing in worldspace?
		bWorld = bone.matrix['ARMATURESPACE'].rotationPart()  * rotMat
		xVec = bMath.Vector(1.0,0.0,0.0) * bWorld
		yVec = bMath.Vector(0.0,1.0,0.0) * bWorld
		zVec = bMath.Vector(0.0,0.0,1.0) * bWorld
		'''
		# add some new bones to visualize these vectors
		eb = A.Editbone()
		eb.head = bone.tail['ARMATURESPACE'] * rotMat
		eb.tail = (bone.tail['ARMATURESPACE'] * rotMat) + zVec
		ghostData.bones['zVec'] = eb
		eb = A.Editbone()
		eb.head = bone.tail['ARMATURESPACE'] * rotMat
		eb.tail = (bone.tail['ARMATURESPACE'] * rotMat) + xVec
		ghostData.bones['xVec'] = eb
		'''

		# now, figure out what the roll angle should be.
		# get the z vector for the new bone
		zVecNew = bMath.Vector(0.0,0.0,1.0) * ghostData.bones[bone.name].matrix.rotationPart()
		# and the y vector
		yVecNew = bMath.Vector(0.0,1.0,0.0) * ghostData.bones[bone.name].matrix.rotationPart()
		'''
		# visualize the vector
		eb = A.Editbone()
		eb.head = bone.tail['ARMATURESPACE'] * rotMat
		eb.tail = (bone.tail['ARMATURESPACE'] * rotMat) + zVecNew
		ghostData.bones['zVecNEW'] = eb
		'''

		# now find the angle between zVec and zVecNew and set the roll angle 
		# accordingly.
		bRoll = bMath.AngleBetweenVecs(zVecNew, zVec)
		# see if we need to reverse the roll
		# rotate zVecNew around the bone's y axis by bRoll
		zRotTest = zVecNew * bMath.RotationMatrix(bRoll, 3, 'r', yVecNew)
		zRotDif = bMath.AngleBetweenVecs(zRotTest, zVec)
		# if they don't match, reverse the roll angle
		if zRotDif > 0.0001:
			bRoll = 360.0 - bRoll

		ghostData.bones[bone.name].roll = bRoll

	# hook up parent/child relationships
	for bone in arm.bones.values():
		if bone.hasParent():
			ghostData.bones[bone.name].parent = ghostData.bones[bone.parent.name]
		else:
			ghostData.bones[bone.name].clearParent()
		# copy options
		ghostData.bones[bone.name].options = bone.options

	ghostData.update()
	# end data copy

	# must unlink the ghost from the scene when we are done with it!!!
	return ghostObject


# Helpful function to make a map of curve names
def BuildCurveMap(ipo):
	curvemap = {}
	ipocurves = ipo.getCurves()
	for i in range(ipo.getNcurves()):
		curvemap[ipocurves[i].getName()] = i

	if Blender.Get('version') == 234:
		# HACKHACK! 2.34 doesn't give us the correct quat values
		try:
			# X=Y, Y=Z, Z=W, W=X
			curvemap['QuatX'],curvemap['QuatY'],curvemap['QuatZ'],curvemap['QuatW'] = curvemap['QuatY'],curvemap['QuatZ'],curvemap['QuatW'],curvemap['QuatX']
		except:
			pass

	return curvemap

# Function to determine what animation is present in a curveMap
def getCMapSupports(curveMap):
	try:
		foo = curveMap['LocX']
		has_loc = True
	except KeyError: has_loc = False
	try:
		foo = curveMap['QuatX']
		has_rot = True
	except KeyError: has_rot = False
	try:
		foo = curveMap['SizeX']
		has_scale = True
	except KeyError: has_scale = False
	return has_loc,has_rot,has_scale
	
# Tells us the maximum frame count in a set of ipo's
def getNumFrames(ipos, useKey = False):
	numFrames = 0
	if not useKey:
		for i in ipos:
			if i != 0:
				# This basically gets the furthest frame in blender this sequence has a keyframe at
				# *** Blender Bug *** Sometimes Blender crashes under windows when accessing an ipo 
				# ** with an "Inf" (influence) key associated in 2.41.
				# ** Blender is returning a pointer into nowhere land and there's nothing we can do to 
				# ** detect it until it's too late to avoid crashing the whole app >:( - Joe G.
				try:
					if i.getCurveBeztriple(0, i.getNBezPoints(0)-1)[3] > numFrames:
						#numframes = int(i.getRctf()[1])
						numFrames = int(i.getCurveBeztriple(0, i.getNBezPoints(0)-1)[3])
				except TypeError:
					# no IPO curve...
					continue
	else:
		for i in ipos:
			if i != 0:
				# This simply counts the keyframes assigned by users
				if i.getNBezPoints(0) > numFrames:
					numFrames = i.getNBezPoints(0)
	return numFrames

'''
Shape Class (Blender Export)
'''
#-------------------------------------------------------------------------------------------------

class BlenderShape(DtsShape):
	def __init__(self, prefs):
		DtsShape.__init__(self)
		self.preferences = prefs

		# Add Root Node to catch meshes and vertices not assigned to the armature
		n = Node(self.addName("Exp-Catch-Root"), -1)
		# Add default translations and rotations for this bone
		self.defaultTranslations.append(Vector(0,0,0))
		self.defaultRotations.append(Quaternion(0,0,0,1))
		self.nodes.append(n)
		
		# Detail level counts
		self.numBaseDetails = 0
		self.numCollisionDetails = 0
		self.numLOSCollisionDetails = 0
				
		self.subshapes.append(SubShape(0,0,0,1,0,0)) # Regular meshes
		self.subshapes.append(SubShape(0,0,0,1,0,0)) # Collision meshes
		
		self.addedArmatures = []	# Armature object,  Armature matrix
		self.externalSequences = []
		self.scriptMaterials = []
		gc.enable()
		
	def __del__(self):
		DtsShape.__del__(self)
		del self.addedArmatures
		del self.externalSequences
		del self.scriptMaterials
		
	# Adds collision mesh
	def addCollisionMesh(self, mesh, LOS=False):
		'''
		This adds a collision mesh to the shape.
		Each collision mesh has its own detail level, and is packed into objects in the second subshape.
		
		Like normal details, the objectDetail property is used to differentiate between collision meshes,
		which results in dummy T_Null type meshes being inserted into the objects, like so:
		
			FirstObject : FirstMesh NULL NULL
			SecondObject: NULL SecondMesh NULL
			ThirdObject : NULL NULL ThirdMesh
		
		Alternatively, we could have packed the meshes into a single object:
		
		Objects: FirstMesh SecondMesh ThirdMesh
		
		However, this approach only allows 1 node to animate all of the collision meshes, rather than
		multiple nodes with the previous method. But as an advantage, this allows for a much more packed file.
		
		NOTE: this function needs to be called AFTER all of the calls to addDetailLevel()!
		'''
		
		# Add or get the collision object
		
		obj = dObject(0, -1, -1, -1)
		obj.tempMeshes = []
		objectDetail = self.numCollisionDetails+self.numLOSCollisionDetails
		
		# Prefix objects meshes
		for c in range(0, self.numCollisionDetails+self.numLOSCollisionDetails):
			obj.tempMeshes.append(DtsMesh(DtsMesh.T_Null))
		
		if self.subshapes[1].numObjects == 0:
			self.subshapes[1].firstObject = len(self.objects)
		else:
			# Postfix everyone else's objects
			for itr in self.objects[self.subshapes[1].firstObject:self.subshapes[1].firstObject+self.subshapes[1].numObjects]:
				itr.tempMeshes.append(DtsMesh(DtsMesh.T_Null))
				
		self.subshapes[1].numObjects += 1
		
		# Assign name to object and update totals
		if LOS:
			self.numLOSCollisionDetails += 1
			detailName = "LOS-%d" % (8+self.numLOSCollisionDetails)
			obj.name = self.addName("LOS-%d" % (self.numLOSCollisionDetails))
		else:
			self.numCollisionDetails += 1
			detailName = "Collision-%d" % (self.numCollisionDetails)
			obj.name = self.addName("Col-%d" % (self.numCollisionDetails))
		
		# Import the mesh - make sure its static
		mat = self.collapseBlenderTransform(mesh)
		# last parameter tells BlenderMesh to ignore the double sided flag, double sided meshes are harmful to convexity :)
		tmsh = BlenderMesh(self, mesh.getData(), 0 ,  1.0, mat, self.preferences['StripMeshes'], True)
		tmsh.mtype = tmsh.T_Standard
		
		# Store constructed detail level info into shape
		self.detaillevels.append(DetailLevel(self.addName(detailName), 1, objectDetail, -1, -1, -1, tmsh.getPolyCount()))
		
		obj.tempMeshes.append(tmsh)
		self.objects.append(obj)
	
	# Adds non-specific detail levels
	def addDetailLevel(self, meshes, size=-1):
		'''
		This adds a detail level to the shape.
		Meshes are bundled into individual object's, all of which belong in the first subshape.
		The first detail level is used as a template for the rest; All other detail levels
		must contain the same, or a lower amount of mesh objects than the first detail level.
		
		A mesh is matched with its corresponding copy in the first detail level via checking the
		first part of its name, prefixed before the ".", e.g:
		
			Head_<flags>
			Head.1_<flags>
			Head.2
			
		Would all link to the object "Head".
		
		The end result is a set of objects in the first subshape something like this:
		
			Head: HeadMesh(128) HeadMesh(64) HeadMesh(32)
			Body: BodyMesh(128) BodyMesh(64) HeadMesh(32)
			RightLeg: RightLegMesh(128) RightLegMesh(64) RightLegMesh(32)
			RightArm: RightArmMesh(128) RightArmMesh(64) RightArmMesh(32)
			LeftLeg: LeftLegMesh(128) LeftLegMesh(64) LeftLegMesh(32)
			LeftArm: LeftArmMesh(128) LeftArmMesh(64) LeftArmMesh(32)
			Bag: BagMesh(128) NULL NULL
			
		An obvious limitation with this method is that, presuming all your meshes are rigid, you cannot
		have HeadMesh(128) animated by bone1 and HeadMesh(32) animated by bone12 - they all need to be attached to the same bone!
		This limitation can of course be worked around if you use skinned meshes instead.
		'''
		numAddedMeshes = 0
		polyCount = 0
		# First, import meshes
		for o in meshes:
			names = o.getName().split("_")
			detail_name = names[0].split(".")[0]
			obj = None
			sorted = False
			
			# Identify corresponding master object
			if self.subshapes[0].numObjects != 0:
				subshape = self.subshapes[self.detaillevels[self.numBaseDetails-1].subshape]
				for dObj in self.objects[subshape.firstObject:subshape.firstObject+subshape.numObjects]:
					if self.sTable.get(dObj.name).upper() == detail_name.upper():
						obj = dObj
						break
				if obj == None:
					Torque_Util.dump_writeln("Warning: No object found, make sure an object with prefix '%s' exists in the base detail." % detail_name)
					continue
			else:
				# Must be unique
				obj = dObject(self.addName(detail_name), -1, -1, -1)
				obj.tempMeshes = []
				self.objects.append(obj)
				
			# Kill the clones
			if (self.subshapes[0].numObjects != 0) and (len(obj.tempMeshes) > self.numBaseDetails):
				Torque_Util.dump_writeln("Warning: Too many clone's of mesh found in detail level, object '%s' skipped!" % o.getName())
				continue
			
			
			# Now we can import as normal
			mesh_data = o.getData();
			mesh_data.update()
				
			# Get Object's Matrix
			mat = self.collapseBlenderTransform(o)
			
			# Import Mesh, process flags
			tmsh = BlenderMesh(self, mesh_data, 0 , 1.0, mat, self.preferences['StripMeshes'])
			if len(names) > 1: tmsh.setBlenderMeshFlags(names[1:])
			
			# If we ended up being a Sorted Mesh, sort the faces
			if tmsh.mtype == tmsh.T_Sorted:
				#tmsh.sortMesh(Prefs['AlwaysWriteDepth'], Prefs['ClusterDepth'])
				tmsh.sortMesh(self.preferences['AlwaysWriteDepth'], self.preferences['ClusterDepth'])
				
			# Increment polycount metric
			polyCount += tmsh.getPolyCount()
				
			obj.tempMeshes.append(tmsh)
			numAddedMeshes += 1
		
		# Modify base subshape if required
		if self.numBaseDetails == 0:
			self.subshapes[0].firstObject = len(self.objects)-numAddedMeshes
			self.subshapes[0].numObjects = numAddedMeshes
			
		# Get name, do housekeeping
		self.numBaseDetails += 1
		detailName = "Detail-%d" % (self.numBaseDetails)
		if self.subshapes[0].numObjects != numAddedMeshes:
			# The following condition should NEVER happen
			if self.subshapes[0].numObjects < numAddedMeshes:
				print "PANIC!! PANIC!! RUN!!!"
				return False
			# Ok, so we have an object with not enough meshes - find the odd one out
			for obj in self.objects[self.subshapes[0].firstObject:self.subshapes[0].firstObject+self.subshapes[0].numObjects]:
				if len(obj.tempMeshes) != self.numBaseDetails:
					# Add dummy mesh (presumed non-existant)
					obj.tempMeshes.append(DtsMesh(DtsMesh.T_Null))
		
		# Does my bum look big in this?
		if size == -1:
			# Calculate size using meshes
			# TODO
			print "TODO: calcSize"
			calcSize = 0
		else:
			# No, not at all
			calcSize = size
		
		# Store constructed detail level info into shape
		self.detaillevels.append(DetailLevel(self.addName(detailName), 0, self.numBaseDetails-1, calcSize, -1, -1, polyCount))
			
		return True
		
	def addBillboardDetailLevel(self, dispDetail, equator, polar, polarangle, dim, includepoles, size):
		self.numBaseDetails += 1
		bb = DetailLevel(self.addName("BILLBOARD-%d" % (self.numBaseDetails)),-1,
					encodeBillBoard(
						equator,
						polar,
						polarangle,
						dispDetail,
						dim,
						includepoles),
						size,-1,-1,0)
		self.detaillevels.insert(self.numBaseDetails-1, bb)
		
	def stripMeshes(self, maxsize):
		# Take into account triangle strips ONLY on non-collision meshes
		for d in self.detaillevels:
			if (d.size < 0) or (d.subshape < 0): continue
			subshape = self.subshapes[d.subshape]
			for obj in self.objects[subshape.firstObject:subshape.firstObject+subshape.numObjects]:
				for tmsh in self.meshes[obj.firstMesh:obj.firstMesh+obj.numMeshes]:
					tmsh.windStrip(maxsize)
		return True
		
	def finalizeObjects(self):
		# Go through object's, add meshes, set transforms
		for o in self.objects:
			o.numMeshes = len(o.tempMeshes)
			o.firstMesh = len(self.meshes)
			
			# Initial animation frame
			# (We could add other frames here for visibility / material / vertex animation)
			self.objectstates.append(ObjectState(1.0, 0, 0))
			
			# Get node from first mesh
			if len(o.tempMeshes) == 0:
				Torque_Util.dump("Warning: Object '%s' has no meshes!" % self.sTable.get(o.name));
				continue
			
			isSkinned = False
			if o.tempMeshes[0].mtype != o.tempMeshes[0].T_Null: o.mainMaterial = o.tempMeshes[0].mainMaterial
			else: o.mainMaterial = None
			
			# Determine mesh type for these objects (assumed by first entry)
			if o.tempMeshes[0].mtype != o.tempMeshes[0].T_Skin:
				o.node = o.tempMeshes[0].getNodeIndex(0)
				if o.node == None:
						# Collision Meshes have to have nodes assigned to them
						# In addition, all orphaned meshes need to be attatched to a root bone
						o.node = 0 # Root is the first bone
						#Torque_Util.dump_writeln("Object %s node %d, Rigid" % (self.sTable.get(o.name),o.node))				
			else:
				o.node = -1
				isSkinned = True
				#Torque_Util.dump_writeln("Object %s, Skinned" % (self.sTable.get(o.name)))
			
			for tmsh in o.tempMeshes:
				'''
					We need to assign nodes to objects and set transforms.
					Rigid meshes can be attached to a single node, in which
					case we need to transform the vertices into the node's
					local space.
				'''
				
				if not isSkinned:
					
					# Transform the mesh into node space. The Mesh vertices
					# must all be relative to the bone they're attached to
					
					world_trans, world_rot = self.getNodeWorldPosRot(o.node)
					tmsh.translate(-world_trans)
					tmsh.rotate(world_rot.inverse())
					
					if tmsh.mtype == tmsh.T_Skin:
						tmsh.mtype = tmsh.T_Standard
						Torque_Util.dump_writeln("Warning: Invalid skinned mesh in rigid object '%s'!" % (self.sTable.get(o.name)))
					
				else:
					
					for n in range(0, tmsh.getNodeIndexCount()):
						# The node transform must take us from shape space to bone space
						world_trans, world_rot = self.getNodeWorldPosRot(tmsh.getNodeIndex(n))
						tmsh.setNodeTransform(n, world_trans, world_rot)		
				
				self.meshes.append(tmsh)
				
		# To conclude, remove subshape's and details we don't need
		if self.subshapes[1].numObjects == 0: del self.subshapes[1]
		if self.subshapes[0].numObjects == 0: del self.subshapes[0]
		
		count = 0
		while count != len(self.detaillevels):
			if self.detaillevels[count].subshape >= len(self.subshapes):
				del self.detaillevels[count]
			else: count += 1
		# Calculate bounds and sizes
		if len(self.detaillevels) == 0:
			Torque_Util.dump_writeln("      Warning : Shape contains no detail levels!")
			
		self.calcSmallestSize() # Get smallest size where shape is visible
				
		# Calculate the bounds,
		# If we have an object in blender called "Bounds" of type "Mesh", use that.
		try:
			bound_obj = Blender.Object.Get("Bounds")
			matf = self.collapseBlenderTransform(bound_obj)
			if bound_obj.getType() == "Mesh":
				bmesh = bound_obj.getData()
				self.bounds.max = Vector(-10e30, -10e30, -10e30)
				self.bounds.min = Vector(10e30, 10e30, 10e30)
				for v in bmesh.verts:
					real_vert = matf.passPoint(v)
					self.bounds.min[0] = min(self.bounds.min.x(), real_vert[0])
					self.bounds.min[1] = min(self.bounds.min.y(), real_vert[1])
					self.bounds.min[2] = min(self.bounds.min.z(), real_vert[2])
					self.bounds.max[0] = max(self.bounds.max.x(), real_vert[0])
					self.bounds.max[1] = max(self.bounds.max.y(), real_vert[1])
					self.bounds.max[2] = max(self.bounds.max.z(), real_vert[2])
				# The center...
				self.center = self.bounds.max.midpoint(self.bounds.min)
				# Tube Radius.
				dist = self.bounds.max - self.center
				self.tubeRadius = Vector2(dist[0], dist[1]).length()
				# Radius...
				self.radius = (self.bounds.max - self.center).length()
			else:
				self.calculateBounds()
				self.calculateCenter()
				self.calculateRadius()
				self.calculateTubeRadius()
		except ValueError:
				self.calculateBounds()
				self.calculateCenter()
				self.calculateRadius()
				self.calculateTubeRadius()

			
	# Converts a blender matrix to a Torque_Util.MatrixF
	def toTorqueUtilMatrix(self, blendermatrix):
		return MatrixF([blendermatrix[0][0],blendermatrix[0][1],blendermatrix[0][2],blendermatrix[0][3],
				blendermatrix[1][0],blendermatrix[1][1],blendermatrix[1][2],blendermatrix[1][3],
				blendermatrix[2][0],blendermatrix[2][1],blendermatrix[2][2],blendermatrix[2][3],
				blendermatrix[3][0],blendermatrix[3][1],blendermatrix[3][2],blendermatrix[3][3]])

	# Creates a matrix that transforms to shape space
	def collapseBlenderTransform(self, object):
		# In blender 2.33 and before, getMatrix() returned the worldspace matrix.
		# In blender 2.33+, it seems to return the local matrix
		if Blender.Get('version') > 233:
			cmat = self.toTorqueUtilMatrix(object.getMatrix("worldspace"))
		else:
			cmat = self.toTorqueUtilMatrix(object.getMatrix())
		return cmat
		
	# Creates a cumilative scaling ratio for an object
	def collapseBlenderScale(self, object):
		csize = object.getSize()
		csize = [csize[0], csize[1], csize[2]]
		parent = object.getParent()
		while parent != None:
			nsize = parent.getSize()
			csize[0],csize[1],csize[2] = csize[0]*nsize[0],csize[1]*nsize[1],csize[2]*nsize[2]
			parent = parent.getParent()
		return csize
	
	# Import an armature
	def addArmature(self, armature, collapseTransform=True):
		'''
			This adds an armature to the shape.
			
			All armatures in a shape must be added first to the shape (before detail levels or collision meshes),
			and in addition they must all be unique - as in, you can't add "BobsBones" twice. The function takes
			care of this, however.
			An obvious question regarding this would be, "How can i animate my character in multiple detail levels?",
			to which the answer is very simple. Create linked copies of the armature in each detail level - the exporter
			does not take into consideration the name of the object, only what data (the actual armature) contains.
			Of course, take care to keep the linked armature object in the same position in all detail levels, otherwise
			interesting things might start to happen.
			
			The core of this function is really in the call to addBones(), which recursively adds the armature's bones,
			starting fron the root.
			This function simply creates a base node of which to support the rest of the imported nodes.
			The base node transform is collapsed by incorporating the transform of the armature object.
		'''
		# First, process armature
		arm = armature.getData()
		# Don't add existing armatures
		for added in self.addedArmatures:			
			#added = added[0]
			if added[0].getData().name == arm.name:
				#print "Note : ignoring attempt to process armature data '%s' again." % arm.name
				return False
		
		startNode = len(self.nodes)
		
		parentBone = -1

		ghostOb = getGhostArmature(armature, "DTS-EXP-GHOST")
		ghostArm = ghostOb.getData()
		# Get the fake armature's position, rotation, and scale
		matf = self.collapseBlenderTransform(ghostOb)
		pos, rot = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2)), Quaternion().fromMatrix(matf).inverse()
		scale = [1.0, 1.0, 1.0]
			
		# Add each bone tree
		for bone in ghostArm.bones.values():
			if bone.parent == None:
				self.addBones(bone, matf, scale, parentBone, True)
		
		# kill the ghost!
		scene = Blender.Scene.getCurrent()
		scene.unlink(ghostOb)
			
		
		# Set armature index on all added nodes
		for node in self.nodes[startNode:len(self.nodes)]:
			node.armIdx = len(self.addedArmatures)

		# now get the real armature transforms for animations
		matf = self.collapseBlenderTransform(armature)
		rot = Quaternion().fromMatrix(matf)
		self.addedArmatures.append([armature, pos, rot, self.collapseBlenderScale(armature)])		
		
		return True
				
	def addBones(self, bone, transformMat, scale, parentId, isOrphan):
		'''
		This function recursively adds a bone from an armature to the shape as a node.
		
		The exporter exports each bone as a node, using the "head" position as where the
		bone is. For each bone that has a parent in torque, the transform is built up from
		all the previous transfoms - e.g looking at it simply:
		
		Bone1 head[0,0,0]
		Bone2 head[0,0,1]
		Bone3 head[0,0,1]
		
		Bone3 Position = Bone1 head + Bone2 head + Bone3 head = [0,0,2]
		Bone2 Position = Bone1 head + Bone2 head = [0,0,1]
		Bone1 Position = Bone1 head = [0,0,0]
		
		Thankfully, blender has a handy getRestMatrix() function incorporated into all
		recent versions, which will get the location and rotation transforms for us, in
		the coordinate system of the parent bone (or rather, relative to it).
		However, whilst we can easily get the rotation using this function, getting the proper translation
		requires a bit more calculation.
		
		One thing that blender does not take into account however is the scale of the root armature - 
		to solve this, we need to pass down the scaling values for each axis from the addArmature() function.

		
		** Sadly getRestMatrix() is gone in blender 2.40, had to revert back to the old method - Joe G.

		'''
		real_name = bone.name
		# Do not add bones on the "BannedBones" list
		if real_name.upper() in self.preferences['BannedBones']:
			return False

		# Blender bones are defined in their parent's rotational space, but relative to the parent's tail.
		# Convert to vector
                bhead = Vector(bone.head['BONESPACE'][0],bone.head['BONESPACE'][1],bone.head['BONESPACE'][2])
                btail = Vector(bone.tail['BONESPACE'][0],bone.tail['BONESPACE'][1],bone.tail['BONESPACE'][2])
		# Move into parent space & build rotation
		head = transformMat.passPoint(bhead)
		tail = transformMat.passPoint(btail)

		# ... and add on scale
		head[0], head[1], head[2] = scale[0]*head[0], scale[1]*head[1], scale[2]*head[2]
		tail[0], tail[1], tail[2] = scale[0]*tail[0], scale[1]*tail[1], scale[2]*tail[2]
		rot = Quaternion().fromMatrix(transformMat * blender_bone2matrixf(head, tail, bone.roll['BONESPACE']*0.017453293)).inverse()

		# Add a DTS bone to the shape
		b = Node(self.sTable.addString(real_name), parentId, isOrphan)
		self.defaultTranslations.append(head)
		self.defaultRotations.append(rot)
		# need to get the bone's armature space transform and store it to use later with the pose stuff
		b.armSpaceTransform = bone.matrix['ARMATURESPACE']
		self.nodes.append(b)

		# Add any children this bone may have
		# Child nodes are always translated along the Y axis
		nmat = transformMat.identity()
		nmat.setRow(3,Vector(0,(btail - bhead).length(),0)) # Translation matrix
		self.subshapes[0].numNodes += 1
		# Add the rest of the bones
		parentId = len(self.nodes)-1
		if bone.hasChildren():
			for bChild in bone.children:
				# must add only IMMEDIATE children! bone.children gives us the whole branch in 2.40.
				if bChild.parent.name == bone.name:
					self.addBones(bChild, nmat, scale, parentId, False)
			
	def addNode(self, object):
		# Adds generic node with object's name
		Torque_Util.dump_writeln("     Node[%s]: %s" % (object.getType(), obj.getName()))

		# Get the camera's pos and rotation
		matf = collapseBlenderTransform(object)
		rot = Quaternion().fromMatrix(matf).inverse()
		pos = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2))

		parentId = len(self.nodes)
		b = Node(self.sTable.addString(object.getName()), -1)
		self.defaultTranslations.append(pos)
		self.defaultRotations.append(rot)
		self.nodes.append(b)
		
		self.subshapes[0].numNodes += 1

		
	# These three helper methods are used by getPoseTransform. They should probably be moved elsewhere.
	def isRotated(self, quat):
		delta = 0.0001
		return not ((quat[0] < delta) and (quat[0] > 0.0 - delta) and (quat[1] < delta) and (quat[1] > 0.0 - delta) and (quat[2] < delta) and (quat[2] > 0.0 - delta))
	
	def isTranslated(self, vec):
		delta = 0.00001
		return not ((vec[0] < delta) and (vec[0] > -delta) and (vec[1] < delta) and (vec[1] > -delta) and (vec[2] < delta) and (vec[2] > -delta))
	
	def isScaled(self, vec):
		delta = 0.00001
		return not ((vec[0] < 1.0 + delta) and (vec[0] > 1.0 - delta) and (vec[1] < 1.0 + delta) and (vec[1] > 1.0 - delta) and (vec[2] < 1.0 + delta) and (vec[2] > 1.0 - delta))

	
	# grab the pose transform of whatever frame we're currently at.  Frame must be set before calling this method.
	def getPoseTransform(self, sequence, nodeIndex, frame_idx, pose, baseTransform=None, getRawValues=False):

		loc, rot, scale = None, None, None
		arm = self.addedArmatures[self.nodes[nodeIndex].armIdx][0]

		# Add ground frames if enabled
		if sequence.has_ground:
			# Check if we have any more ground frames to add
			if sequence.ground_target != sequence.numGroundFrames:
				# Ok, we can add a ground frame, but do we add it now?
				duration = sequence.numKeyFrames / sequence.ground_target
				if frame_idx >= (duration * (sequence.numGroundFrames+1)):
					# We are ready, lets stomp!
					try:
						bound_obj = Blender.Object.Get("Bounds")
						matf = self.collapseBlenderTransform(bound_obj)
						rot = Quaternion().fromMatrix(matf).inverse()
						pos = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2))
						self.groundTranslations.append(pos)
						self.groundRotations.append(rot)
						sequence.numGroundFrames += 1
					except:
						Torque_Util.dump_writeln("Warning: Error getting ground frame %d" % sequence.numGroundFrames)
						Torque_Util.dump_writeln("  You must have an object named Bounds in your scene to export ground frames.")

		# Convert time units from Blender's frame (starting at 1) to second
		# (using sequence FPS)
		time = float(frame_idx - 1) / sequence.fps
		if sequence.duration < time:
			sequence.duration = time

		# some temp variables to make life easier
		node = self.nodes[nodeIndex]
		parentNode = self.nodes[node.parent]
		bonename = self.sTable.get(node.name)
		parentname = self.sTable.get(parentNode.name)
		


		# our actual pose for this frame.
		#pose = arm.getPose()
		#del pose
		#return loc, rot, scale
		
		# Begin complicated math :)
		
		# - determine the bone's rotation relative to it's default orientation.		
		theMat = bMath.Matrix(pose.bones[bonename].localMatrix.rotationPart())
		defMat = bMath.Matrix(self.nodes[nodeIndex].armSpaceTransform.rotationPart())
		# take the armature's rotation into account.
		defMat = defMat * bMath.Matrix(arm.getMatrix()).rotationPart().invert()
		# get rid of parent rotation.
		if not node.isOrphan:
			theMat = theMat * bMath.Matrix(pose.bones[parentname].localMatrix.rotationPart()).invert()
		# move rotation into bone's local frame of reference.
		theMat = bMath.Matrix(defMat) * bMath.Matrix(theMat)
		# find the difference between the default rotation and the rotation for this frame.
		quat1 = defMat.toQuat()
		quat2 = theMat.toQuat()
		qt = bMath.DifferenceQuats(quat1, quat2)

		
		# - determine the translation of the bone relative to it's parent.
		tp = pose.bones[bonename].loc
		# scale the translation by the armature's scale
		armSize = arm.getSize()
		tp[0],tp[1],tp[2] = tp[0] * armSize[0], tp[1] * armSize[1], tp[2] * armSize[2]
		trans = Vector(tp[0], tp[1], tp[2])


		# - determine the scale of the bone.
		scaleVec = pose.bones[bonename].size


		# We dump out every transform regardless of whether it matters or not.  This avoids having to
		# make multiple passes through the frames to deterime what's animated.  Unused tracks and channels
		# are cleaned up later.
		if baseTransform != None:
			# Blended animation, so find the difference between
			# frames and store this

			# process translation
			trans = trans - baseTransform[0]
			if self.isTranslated(trans):
				sequence.matters_translation[nodeIndex] = True
				sequence.has_loc = True				
			loc = trans

			# process rotation
			btqt = bMath.Quaternion(baseTransform[1][3],baseTransform[1][0], baseTransform[1][1], baseTransform[1][2])
			difqt = bMath.DifferenceQuats(qt, btqt)
			quat = Quaternion(difqt.x, difqt.y, difqt.z, difqt.w)
			rotation = quat
			if self.isRotated(rotation):
				sequence.matters_rotation[nodeIndex] = True
				sequence.has_rot = True
			rot = rotation

			# process scale
			scale = Vector(scaleVec[0], scaleVec[1], scaleVec[2])
			# Get difference between this scale and base scale by division
			scale[0] /= baseTransform[2][0]
			scale[1] /= baseTransform[2][1]
			scale[2] /= baseTransform[2][2]
			if self.isScaled(scale):
				sequence.matters_scale[nodeIndex] = True
				sequence.has_scale = True



		else:
			# Standard animations, so store total translations

			# process translation
			if getRawValues:
				loc = trans
			else:
				if self.isTranslated(trans):
					sequence.matters_translation[nodeIndex] = True
					sequence.has_loc = True				
				loc = trans
				# for orphan bones movement is relative to the bone's own rotation
				if node.isOrphan:
					loc = self.defaultRotations[nodeIndex].apply(loc)
				loc += self.defaultTranslations[nodeIndex]

			
			# process rotation
			quat = Quaternion(qt.x, qt.y, qt.z, qt.w)
			rotation = quat
			if getRawValues:
				rot = rotation
			else:
				if self.isRotated(rotation):
					sequence.matters_rotation[nodeIndex] = True
					sequence.has_rot = True
				rot = rotation.inverse() * self.defaultRotations[nodeIndex]
				
			# process scale.
			if getRawValues:
				scale = Vector(scaleVec[0], scaleVec[1], scaleVec[2])
			else:
				if self.isScaled(scaleVec):
					sequence.matters_scale[nodeIndex] = True
					sequence.has_scale = True			
				scale = Vector(scaleVec[0], scaleVec[1], scaleVec[2])
			
		return loc, rot, scale


	# Builds a base transform for blend animations using the
	# designated action and frame #. 
	def buildBaseTransforms(self, blendSequence, blendAction, useActionName, useFrame, scene, context):
		useAction = Blender.Armature.NLA.GetActions()[useActionName]
		
		# Need to create a temporary sequence and build a list
		# of node transforms to use as the base transforms for nodes
		# in our blend animation.
		tempSequence = Sequence()
		tempSequence.name = useActionName
		tempSequence.numTriggers = 0
		tempSequence.firstTrigger = -1
		tempSequence.has_ground = False
		tempSequence.fps = float(useFrame-1)
		if tempSequence.fps < 1.0: tempSequence.fps = 1.0
		tempSequence.duration = 0

		baseTransforms = []
		# Make set of blank ipos and matters for each node
		tempSequence.ipo = []
		tempSequence.frames = []
		for n in self.nodes:
			tempSequence.matters_translation.append(True)
			tempSequence.matters_rotation.append(True)
			tempSequence.matters_scale.append(True)
			# and a blank transform
			baseTransforms.append(0)
			
		
		tempSequence.numKeyFrames = 10000 # one brazilion

		# loop through each node and reset it's transforms.  This avoids transforms carrying over from
		# other animations. Need to cycle through _ALL_ bones and reset the transforms.
		for armOb in Blender.Object.Get():
			if (armOb.getType() != 'Armature') or (armOb.name == "DTS-EXP-GHOST-OB"): continue
			tempPose = armOb.getPose()
			for bonename in armOb.getData().bones.keys():
				# reset the bone's transform
				tempPose.bones[bonename].quat = bMath.Quaternion().identity()
				tempPose.bones[bonename].size = bMath.Vector(1.0, 1.0, 1.0)
				tempPose.bones[bonename].loc = bMath.Vector(0.0, 0.0, 0.0)
			# update the pose.
			tempPose.update()
		# Update the scene's state.
		scene.update(1)


		# now set the active action and move to the desired frame
		for i in range(0, len(self.addedArmatures)):
			arm = self.addedArmatures[i][0]	
			useAction.setActive(arm)

		# Set the current frame in blender
		context.currentFrame(useFrame)
		# Update the scene's state.
		scene.update(1)
		
		for armIdx in range(0, len(self.addedArmatures)):
			arm = self.addedArmatures[armIdx][0]
			pose = arm.getPose()
			# build our transform for each node		
			for nodeIndex in range(1, len(self.nodes)):
				# since Armature.getPose() leaks memory in Blender 2.41, skip nodes not
				# belonging to the current armature to avoid having to call it unnecessarily.
				if self.nodes[nodeIndex].armIdx != armIdx: continue
				curveMap = None
				tempSequence.matters_translation[nodeIndex] = True
				tempSequence.matters_rotation[nodeIndex] = True
				tempSequence.matters_scale[nodeIndex] = True
				baseTransforms[nodeIndex] = self.getPoseTransform(tempSequence, nodeIndex, useFrame, pose, None, True)
		
		del tempSequence
		return baseTransforms
		

	
	# Import a sequence
	def addAction(self, action, scene, context, sequencePrefs):
		'''
		This adds an action to a shape as a sequence.
		
		Sequences are added on a one-by-one basis.
		The first part of the function determines if the action is worth exporting - if not, the function fails,
		otherwise it is setup.
		
		The second part of the function determines what the action animates.
		
		The third part of the function adds the keyframes, making heavy use of the getPoseTransform function. You can control the
		amount of frames exported via the 'InterpolateFrames' option.
		
		Finally, the sequence data is dumped to the shape. Additionally, if the sequence has been marked as a dsq,
		the dsq writer function is invoked - the data for that particular sequence is then removed from the shape.
		
		NOTE: this function needs to be called AFTER all calls to addArmature/addNode, for obvious reasons.
		'''
		

		# Lets start off with the basic sequence
		sequence = Sequence(self.sTable.addString(action.getName()))
		sequence.name = action.getName()
		sequence.numTriggers = 0
		sequence.firstTrigger = -1

		# Make set of blank ipos and matters for current node
		#sequence.ipo = []
		sequence.frames = []
		for n in self.nodes:
			#sequence.ipo.append(0)
			sequence.matters_translation.append(False)
			sequence.matters_rotation.append(False)
			sequence.matters_scale.append(False)
			sequence.frames.append(0)

		# Assign temp flags
		sequence.has_loc = False
		sequence.has_rot = False
		sequence.has_scale = False
			
		# Figure out which nodes have IPO curves.  Need this to determine the number of keyframes; and
		# possibly to force export of some channels where nothing actually moves but the user requires
		# the transforms to be keyed in place for some reason.
		nodeFound = False
		nodeIndex = None
		channels = action.getAllChannelIpos()
		for channel_name in channels:
			if channels[channel_name].getNcurves() == 0: continue
			nodeIndex = self.getNodeIndex(channel_name)
			# Determine if this node is in the shape
			if nodeIndex == None: continue
			# determine channel type and force matters for all channels that are explicitly keyed.
			# I'm still not sure if I really want to do this :)
			try:
				if (channels[channel_name].getCurve('LocX') != None) or (channels[channel_name].getCurve('LocY') != None) or (channels[channel_name].getCurve('LocZ') != None):
					sequence.matters_translation[nodeIndex] = True
					sequence.has_loc = True
				if (channels[channel_name].getCurve('QuatX') != None) or (channels[channel_name].getCurve('QuatY') != None) or (channels[channel_name].getCurve('QuatZ') != None):
					sequence.matters_rotation[nodeIndex] = True
					sequence.has_rot = True
				if (channels[channel_name].getCurve('SizeX') != None) or (channels[channel_name].getCurve('SizeY') != None) or (channels[channel_name].getCurve('SizeZ') != None):
					sequence.matters_scale[nodeIndex] = True
					sequence.has_scale = True
			except ValueError:
				# not an Action IPO...
				nothing = None # <- buh.
			
			# TODO: how do we determine RVK channels?

			# Print informative sequence name if we found a node in the shape (first time only)
			if not nodeFound:
				Torque_Util.dump_writeln("   Action %s used, dumping..." % action.getName())
			nodeFound = True
			# Print informative track message
			Torque_Util.dump_writeln("      Track: %s (node %d)" % (channel_name,nodeIndex))
		del channels

			

		# Add additional flags, e.g. cyclic
		if sequencePrefs['Cyclic']: 
			isCyclic = True
			sequence.flags |= sequence.Cyclic
		else: isCyclic = False
		if sequencePrefs['Blend']:
			isBlend = True
			sequence.flags |= sequence.Blend
		else: isBlend = False
		if sequencePrefs['NumGroundFrames'] != 0:
			sequence.has_ground = True
			sequence.ground_target = sequencePrefs['NumGroundFrames']
			sequence.flags |= sequence.MakePath
		else: sequence.has_ground = False
		sequence.fps = context.framesPerSec()

		# hack, there must be a more elegant way to handle this.
		try:
			sequence.priority = sequencePrefs['Priority']
		except KeyError:
			sequencePrefs['Priority'] = 0
			sequence.priority = sequencePrefs['Priority']


		# Determine the number of key frames. Takes into account channels for bones that are
		# not being exported, as they may still effect the animation through IK or other constraints.
		sequence.numKeyFrames = getNumFrames(action.getAllChannelIpos().values(), False)

		# calc the interpolation increment
		interpolateInc = float(sequence.numKeyFrames) / float(sequencePrefs['InterpolateFrames'])
		# make sure it's not less than 1
		if interpolateInc < 1.0: interpolateInc = 1.0

		# Print different messages depending if we used interpolate or not
		Torque_Util.dump_writeln("      Frames: %d " % sequencePrefs['InterpolateFrames'])
		
		# Depending on what we have, set the bases accordingly
		if sequence.has_ground: sequence.firstGroundFrame = len(self.groundTranslations)
		else: sequence.firstGroundFrame = -1
		
		# this is the number of frames we are exporting.
		numFrames = sequencePrefs['InterpolateFrames']+1
		
		remove_last = False
		baseTransforms = []
		useAction = None
		useFrame = None
		if isBlend:
			# Need to build a list of node transforms to use as the
			# base transforms for nodes in our blend animation.
 			useAction = sequencePrefs['BlendRefPoseAction']
			useFrame = sequencePrefs['BlendRefPoseFrame']
			baseTransforms = self.buildBaseTransforms(sequence, action, useAction, useFrame, scene, context)
			if baseTransforms == None:
				Torque_Util.dump_writeln("Error getting base Transforms!!!!!")


		# *** special processing for the first frame:
		# For blend animations, we need to reset the pose to the reference pose instead of the default
		# transforms.  Otherwise, we won't be able to tell reliably which bones have actually moved
		# during the blend sequence.
		if isBlend:
			# get our blend ref pose action
			refPoseAct = Blender.Armature.NLA.GetActions()[useAction]
			# now set the active action and move to the desired frame
			for i in range(0, len(self.addedArmatures)):
				arm = self.addedArmatures[i][0]
				refPoseAct.setActive(arm)
			# Set the current frame in blender
			context.currentFrame(useFrame)
			# Update the scene's state.
			scene.update(1)				
		# For normal animations, loop through each node and reset it's transforms.
		# This avoids transforms carrying over from other animations.
		else:
			# need to cycle through ALL bones and reset the transforms.
			for armOb in Blender.Object.Get():
				if (armOb.getType() != 'Armature') or (armOb.name == "DTS-EXP-GHOST-OB"): continue
				tempPose = armOb.getPose()
				for bonename in armOb.getData().bones.keys():
					# reset the bone's transform
					tempPose.bones[bonename].quat = bMath.Quaternion().identity()
					tempPose.bones[bonename].size = bMath.Vector(1.0, 1.0, 1.0)
					tempPose.bones[bonename].loc = bMath.Vector(0.0, 0.0, 0.0)
				# update the pose.
				tempPose.update()
			# Update the scene's state.
			scene.update(1)

		
		# create blank frames for each node
		for nodeIndex in range(1, len(self.nodes)):
			sequence.frames[nodeIndex] = []
		
		# loop through all of the armatures and set the current action as active for all
		# of them.  Sadly, there is no way to tell which action belongs with which armature
		# using the API in Blender 2.41, so this is a bit messy.
		act = Blender.Armature.NLA.GetActions()[sequence.name]
		for i in range(0, len(self.addedArmatures)):
			arm = self.addedArmatures[i][0]			
			act.setActive(arm)
			
		# loop through all of the frames
		for frame in range(1, numFrames):
			# Set the current frame in blender
			context.currentFrame(int(frame*interpolateInc))
			# Update the scene's state.
			scene.update(1)
			# loop through each armature
			for armIdx in range(0, len(self.addedArmatures)):
				arm = self.addedArmatures[armIdx][0]
				pose = arm.getPose()
				# loop through each node for the current frame.
				for nodeIndex in range(1, len(self.nodes)):
					# since Armature.getPose() leaks memory in Blender 2.41, skip nodes not
					# belonging to the current armature to avoid having to call it unnecessarily.
					if self.nodes[nodeIndex].armIdx != armIdx: continue
					if isBlend: 
						baseTransform = baseTransforms[nodeIndex]
					else:
						baseTransform = None
					# let's pretend that everything matters, we'll remove the cruft later
					# this prevents us from having to do a second pass through the frames.
					loc, rot, scale = self.getPoseTransform(sequence, nodeIndex, (frame*interpolateInc), pose, baseTransform)
					sequence.frames[nodeIndex].append([loc,rot,scale])
		
		# if nothing was actually animated abandon exporting the action.
		if not (sequence.has_loc or sequence.has_rot or sequence.has_scale):
			Torque_Util.dump_writeln("Warning: Action has no keyframes, aborting export for this sequence.")
			del sequence.frames
			del sequence
			return None

		# set the aligned scale flag if we have scale.
		if sequence.has_scale: sequence.flags |= Sequence.AlignedScale
		
		# It should be safe to add this sequence to the list now.
		self.sequences.append(sequence)

		# Now that we have all the transforms for each node at 
		# every frame, remove the ones that we don't need. This is much faster than doing
		# two passes through the blender frames to determine what's animated and what's not.
		for nodeIndex in range(1, len(self.nodes)):
			if not sequence.matters_translation[nodeIndex]:
				for frame in range(0, numFrames-1):					
					sequence.frames[nodeIndex][frame][0] = None
			if not sequence.matters_rotation[nodeIndex]:
				for frame in range(0, numFrames-1):
					sequence.frames[nodeIndex][frame][1] = None					
			if not sequence.matters_scale[nodeIndex]:
				for frame in range(0, numFrames-1):
					sequence.frames[nodeIndex][frame][2] = None
		
		remove_translation, remove_rotation, remove_scale = True, True, True
		if isCyclic:
			for nodeIndex in range(1, len(self.nodes)):
				# If we added any new translations, and the first frame is equal to the last,
				# allow the next pass of nodes to happen, to remove the last frame.
				# (This fixes the "dead-space" issue)
				if len(sequence.frames[nodeIndex]) != 0:
					if (sequence.frames[nodeIndex][0][0] != None) and (sequence.frames[nodeIndex][-1][0] != None) and not sequence.frames[nodeIndex][0][0].eqDelta(sequence.frames[nodeIndex][-1][0], 0.000001):
						remove_translation = False
					if (sequence.frames[nodeIndex][0][1] != None) and (sequence.frames[nodeIndex][-1][1] != None) and not sequence.frames[nodeIndex][0][1].eqDelta(sequence.frames[nodeIndex][-1][1], 0.000001):
						remove_rotation = False
					if (sequence.frames[nodeIndex][0][2] != None) and (sequence.frames[nodeIndex][-1][2] != None) and not sequence.frames[nodeIndex][0][2].eqDelta(sequence.frames[nodeIndex][-1][2], 0.000001):
						remove_scale = False

			# Determine if the change has affected all that we animate
			if (remove_translation) and (remove_rotation) and (remove_scale):
				remove_last = True
			

		Torque_Util.dump_write("      Animates:")
		if sequence.has_loc: Torque_Util.dump_write("loc")
		if sequence.has_rot: Torque_Util.dump_write("rot")
		if sequence.has_scale: Torque_Util.dump_write("scale")
		if sequence.has_ground: Torque_Util.dump_write("ground")
		Torque_Util.dump_writeln("")

		# We can now reveal the true number of keyframes
		sequence.numKeyFrames = numFrames-1

		# Do a second pass on the nodes to remove the last frame for cyclic anims
		if remove_last:
			# Go through list of frames for nodes animated in sequence and delete the last frame from all of them
			for nodeIndex in range(len(self.nodes)):
				#ipo = sequence.ipo[nodeIndex]
				#if ipo != 0:
				if sequence.matters_translation[nodeIndex] or sequence.matters_rotation[nodeIndex] or sequence.matters_scale[nodeIndex]:
					del sequence.frames[nodeIndex][-1]
			sequence.numKeyFrames -= 1
			Torque_Util.dump_writeln("      Note: Duplicate frames removed,  (was %d,  now %d)" % (sequence.numKeyFrames+1, sequence.numKeyFrames))

		# Calculate Bases
		if sequence.has_loc: sequence.baseTranslation = len(self.nodeTranslations)
		else: sequence.baseTranslation = -1
		if sequence.has_rot: sequence.baseRotation = len(self.nodeRotations)
		else: sequence.baseRotation = -1
		if sequence.has_scale: sequence.baseScale = len(self.nodeAlignedScales)
		else: sequence.baseScale = -1
		
		# To simplify things, we now assume everything is internal and just dump the sequence
		
		# Dump Frames
		for node in sequence.frames:
			if node == 0: continue
			for frame in node:
				if frame[0]:
					self.nodeTranslations.append(frame[0])
				if frame[1]:
					self.nodeRotations.append(frame[1])
				if frame[2]:
					self.nodeAlignedScales.append(frame[2])
		
		# Clean out temporary junk
		del sequence.frames

		# UGLY WORKAROUND HACK
		# This is a workaround for a bug in blender 2.41 that causes the reference count of the last
		# action that Action.setActive() is called on from a script to be corrupted.  The only way
		# around this nasty bug is to create a fake action and make sure that we always set it active
		# as last action.  When they fix the bug this fake action crap can be removed from the code
		# or surrounded with version checks.  I really hate this, but it seems to be the only possible
		# workaround.
		try:
			# if fake action already exists reuse it.
			act = Blender.Armature.NLA.GetActions()["DTSEXPFAKEACT"]
		except:
			# if it doesn't exist, create it.
			act = Blender.Armature.NLA.NewAction("DTSEXPFAKEACT")
		act.setActive(arm)
		
		gc.collect()
		
		return sequence		



	
	def addSequenceTriggers(self, sequence, unsortedTriggers, nFrames):
		if sequence.firstTrigger == -1:
			sequence.firstTrigger = len(self.triggers)
		
		# Sort triggers by position
		triggers = []
		for u in unsortedTriggers:
			if len(triggers) == 0:
				triggers.append(u)
				continue
			for i in range(0, len(triggers)):
				if (triggers[i][1] <= u[1]):
					triggers.insert(i, u)
					break
				elif (i == (len(triggers)-1)):
					triggers.append(u)
		triggers.reverse()

		# Check for triggers with both on and off states
		triggerState = []
		for t in triggers:
			triggerState.append(False)
			for comp in triggers:
				if (t[0] == comp[0]) and (t[2] != comp[2]):
					# Trigger controls a state that is turned on and off, so must state must reverse
					# if played backwards
					triggerState[-1] = True
					break
		
		for i in range(0, len(triggers)):
			# [ state(1-32), position(0-1.0), on(True/False) ]
			if triggers[i][1] <= 1: realPos = 0.0
			else: realPos = float(triggers[i][1]-1) / (nFrames-1)
			
			self.triggers.append(Trigger(triggers[i][0], triggers[i][2], realPos, triggerState[i]))
		del triggerState
		sequence.numTriggers += len(triggers)


	# Processes a material ipo and incorporates it into the Action
	def addSequenceMaterialIpos(self, sequence, numFrames, startFrame=1):
		'''
		This adds ObjectState tracks to the sequence.
		
		Since blender's Action's don't support material ipo's, we need to use the ipo direct from the Material.
		In addition, a starting point must be defined, which is useful in using a the ipo in more than 1 animation track.
		
		Material ipo's aren't much use to us unless we know which object's they relate to. Luckily,
		the BlenderMesh class can tell us if the material we are adding is associated with a particular object.
		At the moment, only the visibility of the objects are animated, which is controlled by the "Alpha" value of the
		Material ipo.
		
		NOTE: this function needs to be called AFTER finalizeObjects, for obvious reasons.
		'''
		
		scene = Blender.Scene.getCurrent()
		context = Blender.Scene.getCurrent().getRenderingContext()
		sequence.matters_vis = [False]*len(self.objects)
		
		# First, scan for objects that have associated materials
		usedMat = []
		
		# Get a list of used materials
		for i in range(0, len(self.objects)):
			# Only first mesh of object is taken into account, as that represents the object in the highest detail level
			if self.meshes[self.objects[i].firstMesh].mainMaterial == None:
				continue
			else:
				if not (self.meshes[self.objects[i].firstMesh].mainMaterial in usedMat):
					usedMat.append(self.meshes[self.objects[i].firstMesh].mainMaterial)
		
		# Get frames for each used material
		matFrames = [None]*len(usedMat)
		interpolateInc = numFrames / sequence.numKeyFrames
		for i in range(0, len(usedMat)):
			matIdx = usedMat[i]
			
			# Can we get the frames out?
			try: blenderMat = Material.Get(self.materials.get(matIdx).name)
			except: continue
			ipo = blenderMat.getIpo()
			if ipo == None: continue
			
			# Yes? Lets go!
			matFrames[i] = []
			curveMap = BuildCurveMap(ipo)
			for frame in range(startFrame, startFrame+sequence.numKeyFrames):
				frame_idx = int(interpolateInc * frame)
				if frame_idx < 1.0: frame_idx = 1.0
				#print "Grabbing material ipo for frame %d, normally %d" % (frame_idx, frame)
				
				# Set the current frame in blender to the frame the ipo keyframe is at
				context.currentFrame(frame_idx)
				
				# Update the ipo's current value
				scene.update(1)
				
				# Add the frame(s)
				# TODO: ifl frame would be useful here, if blender had a "Frame" value :)
				matFrames[i].append(ipo.getCurveCurval(curveMap['Alpha']))
				
		# Now we can dump each frame for the objects
		for i in range(0, len(self.objects)):
			for m in range(0, len(usedMat)):
				if (self.meshes[self.objects[i].firstMesh].mainMaterial == usedMat[m]) and (matFrames[m] != None):
					sequence.matters_vis[i] = True
					
					if sequence.baseObjectState == -1:
						sequence.baseObjectState = len(self.objectstates)
					
					# Create objectstate's for each frame
					for frame in matFrames[m]:
						self.objectstates.append(ObjectState(frame, 0, 0))
				
		# Cleanup
		for frame in matFrames:
			if frame != None: del frame
		del matFrames
		del usedMat
		
		return True
		
	def convertAndDumpSequenceToDSQ(self, sequence, filename, version):
		# Write entry for this in shape script, if neccesary
		self.externalSequences.append(self.sTable.get(sequence.nameIndex))

		# Simple task of opening the file and dumping sequence data
		dsq_file = open(filename, "wb")
		self.writeDSQSequence(dsq_file, sequence, version) # Write only current sequence data
		dsq_file.close()

		# Remove anything we added (using addAction or addSequenceTrigger only) to the main list
		if sequence.baseTranslation != -1: del self.nodeTranslations[sequence.baseTranslation:sequence.baseTranslation+sequence.numKeyFrames]
		if sequence.baseRotation != -1:    del self.nodeRotations[sequence.baseRotation:sequence.baseRotation+sequence.numKeyFrames]
		if sequence.baseScale != -1:       del self.nodeAlignedScales[sequence.baseScale:sequence.baseScale+sequence.numKeyFrames]
		if sequence.firstTrigger != -1:    del self.triggers[sequence.firstTrigger:sequence.firstTrigger+sequence.numTriggers]
		if sequence.firstGroundFrame != -1:
			del self.groundTranslations[sequence.firstGroundFrame:sequence.firstGroundFrame+sequence.numGroundFrames]
			del self.groundRotations[sequence.firstGroundFrame:sequence.firstGroundFrame+sequence.numGroundFrames]
		# ^^ Add other data here once exporter has support for it.

		# Remove sequence from list
		for i in range(0, len(self.sequences)):
			if self.sequences[i] == sequence:
				del self.sequences[i]
				break
		return True
	
	# Generic object addition
	def addObject(self, object):
		if object.getType() == "Armature":
			return self.addArmature(object)
		elif object.getType() == "Camera":
			return self.addNode(object)
		elif object.getType() == "Mesh":
			return self.addDetailLevel([object], -1)
		else:
			Torque_Util.writeln("addObject() failed for type %s!" % object.getType())
			return False
	
	# Material addition
	def addMaterial(self, bmat):
		if bmat == None: return None
		if self.preferences['TSEMaterial']:
			return self.addTSEMaterial(bmat)
		
		material = dMaterial(bmat.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
		material.sticky = False

		# If we are emitting light, we must be self illuminating
		if bmat.getEmit() > 0.0: material.flags |= dMaterial.SelfIlluminating
		material.flags |= dMaterial.NeverEnvMap

		# Look at the texture channels if they exist
		textures = bmat.getTextures()
		if len(textures) > 0:
			if (textures[0] != None) and (textures[0].tex.type == Texture.Types.IMAGE):
				# Translucency?
				if textures[0].mapto & Texture.MapTo.ALPHA:
					material.flags |= dMaterial.Translucent
					if bmat.getAlpha() < 1.0: material.flags |= dMaterial.Additive

				# Sticky coords?
				if textures[0].texco & Texture.TexCo.STICK:
					material.sticky = True

				# Disable mipmaps?
				if not (textures[0].tex.imageFlags & Texture.ImageFlags.MIPMAP):
					material.flags |= dMaterial.NoMipMap

			for i in range(1, len(textures)):
				texture_obj = textures[i]
				if texture_obj == None: continue
				# Figure out if we have an Image
				if texture_obj.tex.type != Texture.Types.IMAGE:
					Torque_Util.dump_writeln("      Warning: Material(%s,%d) Only Image textures are supported. Skipped." % (bmat.getName(),i))
					continue

				# Determine what this texture is used for
				# A) We have a reflectance map
				if (material.reflectance == -1) and (texture_obj.mapto & Texture.MapTo.REF):
					# Joe : this is still not working in showtool, need to investigate.
					# We have a reflectance map
					reflectance_map = dMaterial(texture_obj.tex.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
					reflectance_map.flags |= dMaterial.ReflectanceMap
					if texture_obj.texco & Texture.TexCo.STICK:
						reflectance_map.sticky = True
					material.flags &= ~dMaterial.NeverEnvMap
					material.reflectance = self.materials.add(reflectance_map)
				# B) We have a normal map (basically a 3d bump map)
				elif (material.bump == -1) and (texture_obj.mapto & Texture.MapTo.NOR):
					bump_map = dMaterial(texture_obj.tex.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
					bump_map.flags |= dMaterial.BumpMap
					if texture_obj.texco & Texture.TexCo.STICK:
						bump_map.sticky = True
					material.bump = self.materials.add(bump_map)
				# C) We have a texture; Lets presume its a detail map (since its laid on top after all)
				elif material.detail == -1:
					detail_map = dMaterial(texture_obj.tex.getName(), dMaterial.SWrap | dMaterial.TWrap,-1,-1,-1,1.0,bmat.getRef())
					detail_map.flags |= dMaterial.DetailMap
					if texture_obj.texco & Texture.TexCo.STICK:
						detail_map.sticky = True
					material.detail = self.materials.add(detail_map)
		else:
			Torque_Util.dump_writeln("      Warning: Material(%s) does not have any textures assigned!" % bmat.getName())
		return self.materials.add(material)
	
	# Material addition (TSE mode)
	def addTSEMaterial(self, bmat):
		if bmat == None: return None
		
		material = dMaterial(bmat.getName(), dMaterial.SWrap | dMaterial.TWrap,self.materials.size(),-1,-1,1.0,bmat.getRef())
		material.sticky = False

		# If we are emitting light, we must be self illuminating
		if bmat.getEmit() > 0.0: material.flags |= dMaterial.SelfIlluminating
		material.flags |= dMaterial.NeverEnvMap

		# Look at the texture channels if they exist
		textures = bmat.getTextures()
		if len(textures) > 0:
			if (textures[0] != None) and (textures[0].tex.type == Texture.Types.IMAGE):
				# Translucency?
				if textures[0].mapto & Texture.MapTo.ALPHA:
					material.flags |= dMaterial.Translucent
					if bmat.getAlpha() < 1.0: material.flags |= dMaterial.Additive

				# Sticky coords?
				if textures[0].texco & Texture.TexCo.STICK:
					material.sticky = True

				# Disable mipmaps?
				if not (textures[0].tex.imageFlags & Texture.ImageFlags.MIPMAP):
					material.flags |= dMaterial.NoMipMap
					
		# Now here's where things get different; we go through the texture channels and add stuff
		materialString = "new Material(%s)\n{\n" % (bmat.getName())
		for idx in range(0, len(textures)):
			texture = textures[idx]
			if texture == None:
				continue
			if texture.tex.type == Texture.Types.IMAGE: imgFilename = texture.tex.getName()
			else: imgFilename = ""
			materialString += "baseTex[%d] = \"./%s\";\n" % (idx, imgFilename)
		materialString += "}\n"
		
		self.scriptMaterials.append(materialString)
		
		return self.materials.add(material)
	
	# Finalizes shape
	def finalize(self, writeShapeScript=False):
		pathSep = "/"
		if "\\" in self.preferences['exportBasepath']: pathSep = "\\"
		
		if writeShapeScript:
			Torque_Util.dump_writeln("   Writing script%s%s%s.cs" % (self.preferences['exportBasepath'], pathSep, self.preferences['exportBasename']))
			shapeScript = open("%s%s%s.cs" % (self.preferences['exportBasepath'], pathSep, self.preferences['exportBasename']), "w")
			shapeScript.write("datablock TSShapeConstructor(%sDts)\n" % self.preferences['exportBasename'])
			shapeScript.write("{\n")
			# don't need to write out the full path, in fact, it causes problems to do so.  We'll just assume
			# that the player is putting their shape script in the same folder as the .dts.
			#shapeScript.write("   baseShape = \"./%s\";\n" % (self.preferences['exportBasepath'] + self.preferences['exportBasename'] + ".dts"))
			shapeScript.write("   baseShape = \"./%s\";\n" % (self.preferences['exportBasename'] + ".dts"))
			count = 0
			for sequence in self.externalSequences:
				#shapeScript.write("   sequence%d = \"./%s_%s.dsq %s\";\n" % (count,self.preferences['exportBasepath'],sequence,sequence))
				shapeScript.write("   sequence%d = \"./%s.dsq %s\";\n" % (count,sequence,sequence))
				count += 1
			shapeScript.write("};")
			shapeScript.close()

		if self.preferences['TSEMaterial']:
			Torque_Util.dump_writeln("   Writing material script %s%smaterials.cs" % (self.preferences['exportBasepath'], pathSep))
			materialScript = open("%s%smaterials.cs" % (self.preferences['exportBasepath'], pathSep), "w")
			for materialDef in self.scriptMaterials:
				materialScript.write("// Script automatically generated by Blender\n\n")
				materialScript.write(materialDef)
				materialScript.write("// End of generated script\n")
			materialScript.close()
				
	def dumpShapeInfo(self):
		Torque_Util.dump_writeln("   > Nodes")
		for n in range(0, len(self.nodes)):
			if self.nodes[n].parent == -1:
				self.dumpShapeNode(n)
				
		Torque_Util.dump_writeln("   > Objects")
		for obj in self.objects:
			Torque_Util.dump_write("    '%s' :" % self.sTable.get(obj.name))
			for mesh in self.meshes[obj.firstMesh:obj.firstMesh+obj.numMeshes]:
				if mesh.mtype == mesh.T_Standard:
					Torque_Util.dump_write("Standard")
				elif mesh.mtype == mesh.T_Skin:
					Torque_Util.dump_write("Skinned")
				elif mesh.mtype == mesh.T_Decal:
					Torque_Util.dump_write("Decal")
				elif mesh.mtype == mesh.T_Sorted:
					Torque_Util.dump_write("Sorted")
				elif mesh.mtype == mesh.T_Null:
					Torque_Util.dump_write("Null")
				else:
					Torque_Util.dump_write("Unknown")
			Torque_Util.dump_writeln("")
			
		Torque_Util.dump_writeln("   > Materials")
		for mat in self.materials.materials:
			Torque_Util.dump_writeln("      %s" % mat.name)
		
		Torque_Util.dump_writeln("   > Detail Levels")
		for detail in self.detaillevels:
			Torque_Util.dump_writeln("      %s (size : %d)" % (self.sTable.get(detail.name), detail.size))
		if len(self.detaillevels) > 0:
			Torque_Util.dump_writeln("      Smallest : %s (size : %d)" % (self.sTable.get(self.detaillevels[self.mSmallestVisibleDL].name), self.mSmallestVisibleSize))
		
		Torque_Util.dump_writeln("   > Internal Sequences")
		for sequence in self.sequences:
			Torque_Util.dump_writeln("    - %s" % self.sTable.get(sequence.nameIndex))
			Torque_Util.dump_write("       Animates:")
			if sequence.has_loc: Torque_Util.dump_write("loc")
			if sequence.has_rot: Torque_Util.dump_write("rot")
			if sequence.has_scale: Torque_Util.dump_write("scale")
			if sequence.has_ground: Torque_Util.dump_write("ground")
			Torque_Util.dump_writeln("")
			Torque_Util.dump_writeln("       Frames: %d" % sequence.numKeyFrames)
			Torque_Util.dump_writeln("       Ground Frames: %d" % sequence.numGroundFrames)
			Torque_Util.dump_writeln("       Triggers: %d" % sequence.numTriggers)

		
	def dumpShapeNode(self, nodeIdx, indent=0):
		Torque_Util.dump_write(" " * (indent+4))
		Torque_Util.dump_writeln("^^ Bone [%s] (parent %d)" % (self.sTable.get(self.nodes[nodeIdx].name),self.nodes[nodeIdx].parent))
		for n in range(0, len(self.nodes)):
			if self.nodes[n].parent == nodeIdx:
				self.dumpShapeNode(n, indent+1)
	