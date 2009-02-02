'''
Dts.Shape_Blender.py

Copyright (c) 2005 - 2006 James Urquhart(j_urquhart@btinternet.com)

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
import DTSPython
from DTSPython import *

import DtsMesh_Blender
from DtsMesh_Blender import *

import Blender
from Blender import NMesh, Armature, Scene, Object, Material, Texture
from Blender import Mathutils as bMath

import DtsPoseUtil

import gc

'''
   Util functions used by class as well as exporter gui
'''
#-------------------------------------------------------------------------------------------------
# Helpful function to make a map of curve names
def BuildCurveMap(ipo):
	curvemap = {}
	ipocurves = ipo.getCurves()
	for i in range(ipo.getNcurves()):
		curvemap[ipocurves[i].getName()] = i
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
	
# gets the highest frame in an action
def getHighestActFrame(act):
	actFrames = act.getFrameNumbers()
	highest = 0
	for fr in actFrames:
		if fr > highest:
			highest = int(fr)
	return highest

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
		
		# temp container that holds the raw rest transforms, including default scale
		self.restTransforms = None
		
		# set rest frame before initializing transformUtil
		Blender.Set('curframe', prefs['RestFrame'])

		# this object is the interface through which we get blender tranform data
		# for object and bone nodes
		self.transformUtil = DtsPoseUtil.NodeTransformUtil(self.preferences['ExportScale'])
		
		# extra book keeping for armature modifier warning (see long note/explanation in Dts_Blender.py)
		self.badArmatures = []
		
		gc.enable()
		
	def __del__(self):
		DtsShape.__del__(self)
		del self.addedArmatures
		del self.externalSequences
		del self.scriptMaterials




	# Find an existing dts object in the shape	
	def findDtsObject(self, dtsObjName):
		# get/add dts object to shape
		masterObject = None
		for dObj in self.objects:
			if self.sTable.get(dObj.name).upper() == dtsObjName.upper():
				masterObject = dObj
		return masterObject

	# Adds a dts object to the shape
	def addDtsObject(self, dtsObjName, pNodeIdx):
		masterObject = dObject(self.addName(dtsObjName), -1, -1, pNodeIdx)
		masterObject.tempMeshes = []
		self.objects.append(masterObject)
		return masterObject

	# Adds a mesh to a dts object
	def addMesh(self, o, masterObject):
		hasArmatureDeform = False
		armParentDeform = False
		# Check for armature modifier
		for mod in o.modifiers:
			if mod.type == Blender.Modifier.Types.ARMATURE:
				hasArmatureDeform = True
		# Check for an armature parent
		try:
			if o.parentType == Blender.Object.ParentTypes['ARMATURE']:
				hasArmatureDeform = True
				armParentDeform = True
		except: pass
		# does the object have geometry?

		# do we even have any modifiers?  If not, we can skip copying the display data.
		try: hasMultiRes = o.getData(False,True).multires
		except AttributeError: hasMultiRes = False

		hasModifiers = False
		for mod in o.modifiers:
			# skip armature modifiers
			if mod.type == Blender.Modifier.Types.ARMATURE: continue

			# skip modifiers that are "OK" if we know they can't affect the number
			# of verts in the mesh.
			
			# undocumented implicit "Collision" modifier
			if mod.type == 23: continue
			# if we've got a skinned mesh, we can safely bake some modifiers
			# into the mesh's root pose.
			if hasArmatureDeform:
				if mod.type == Blender.Modifier.Types.CURVE\
				or mod.type == Blender.Modifier.Types.LATTICE\
				or mod.type == Blender.Modifier.Types.WAVE\
				or mod.type == Blender.Modifier.Types.DISPLACE\
				or mod.type == Blender.Modifier.Types.SMOOTH\
				or mod.type == Blender.Modifier.Types.CAST : continue

			# if we made it here we've got at least one valid (non-armature) modifier on the mesh
			hasModifiers = True
			break
		# if a mesh has multires, treat it as if it has modifiers			
		if hasMultiRes: hasModifiers = True

		# Get display data for non-skinned mesh with modifiers
		if (not hasArmatureDeform) and (hasModifiers or (o.getType() in DtsGlobals.needDisplayDataTypes)):
			#print "mesh:", o.name, "has modifers but not armature deform or is not a true mesh."
			try:
				temp_obj = Blender.Object.Get("DTSExpObj_Tmp")
			except:
				temp_obj = Blender.Object.New("Mesh", "DTSExpObj_Tmp")
			try:
				mesh_data = Blender.Mesh.Get("DTSExpMshObj_Tmp")
			except:
				mesh_data = Blender.Mesh.New("DTSExpMshObj_Tmp")
			# try to get the raw display data
			try:
				mesh_data.getFromObject(o)
				temp_obj.link(mesh_data)
			except: 
				#todo - warn when we couldn't get mesh data?
				pass

		# Get display data for skinned mesh without (additional) modifiers
		elif hasArmatureDeform and not (hasModifiers or (o.getType() in DtsGlobals.needDisplayDataTypes)):
			#print "mesh:", o.name, "has armature deform but no modifiers."
			originalMesh = o.getData(False,True)
			
			# get vertex weight info
			influences = {}
			for v in originalMesh.verts:
				influences[v.index] = originalMesh.getVertexInfluences(v.index)

			groups = originalMesh.getVertGroupNames()

			
			# -----------------------------
			# apply armature modifier
			try:
				temp_obj = Blender.Object.Get("DTSExpObj_Tmp")
			except:
				temp_obj = Blender.Object.New("Mesh", "DTSExpObj_Tmp")
			try:
				mesh_data = Blender.Mesh.Get("DTSExpMshObj_Tmp")
			except:
				mesh_data = Blender.Mesh.New("DTSExpMshObj_Tmp")
			# try to get the raw display data
			try:
				mesh_data.getFromObject(o)
				temp_obj.link(mesh_data)
			except: 
				#todo - warn when we couldn't get mesh data?
				pass
				
			# -----------------------------
			
			# remove any existing groups if we are recycling a datablock
			
			if len(mesh_data.getVertGroupNames()) != 0:
				for group in mesh_data.getVertGroupNames():
					mesh_data.removeVertsFromGroup(group)
			mesh_data.update()
			

			# add vertex weights back in			
			existingNames = mesh_data.getVertGroupNames()
			for group in groups:
				if not group in existingNames:
					mesh_data.addVertGroup(group)
			
			# recreate vertex groups
			for vIdx in influences.keys():
				for inf in influences[vIdx]:
					group, weight = inf
					mesh_data.assignVertsToGroup(group, [vIdx], weight, Blender.Mesh.AssignModes.ADD)
			
			
		# Get (non-display) mesh data for ordinary mesh with no armature deform or modifiers		
		elif (not hasArmatureDeform) and not (hasModifiers or (o.getType() in DtsGlobals.needDisplayDataTypes)):
			#print "mesh:", o.name, "has no modifiers and no armature deform"
			mesh_data = o.getData(False,True)
			temp_obj = None

		# Give error message if we've got a skinned mesh with additional modifiers
		elif hasArmatureDeform and (hasModifiers or (o.getType() in DtsGlobals.needDisplayDataTypes)):
			# we can't support this, since the number of verts in the mesh may have been changed
			# by one if the modifiers, it is impossible to reconstruct vertex groups.
			print "Can't reconstruct vertex group for skinned mesh with additional modifiers!"
			mesh_data = o.getData(False,True)
			temp_obj = None

		else:
			# unknown mesh configuration?!
			print "Unknown mesh configuration!!!"

		# Get Object's Matrix
		mat = self.collapseBlenderTransform(o)
		#print "mat = \n", str(mat)

		# Get armatures targets if mesh is skinned
		armTargets = DtsGlobals.SceneInfo.getSkinArmTargets(o)

		# Import Mesh, process flags
		try: x = self.preferences['PrimType']
		except KeyError: self.preferences['PrimType'] = "Tris"
		tmsh = BlenderMesh( self, o.name, mesh_data, -1, 1.0, mat, o.size, hasArmatureDeform, armTargets, False, (self.preferences['PrimType'] == "TriLists" or self.preferences['PrimType'] == "TriStrips") )

		# Add mesh flags based on blender object game properties.
		if len(o.game_properties) > 0:
			propNames = []
			for prop in o.game_properties:
				if (prop.getType().lower() == "bool" and prop.getData() == True)\
				or (prop.getType().lower() == "int" and prop.getData() != 0)\
				or (prop.getType().lower() == "float" and prop.getData() != 0.0)\
				or (prop.getType().lower() == "string" and prop.getData().lower() =="true"):
					propNames.append(prop.getName())
			tmsh.setBlenderMeshFlags(propNames)

		# If we ended up being a Sorted Mesh, sort the faces
		if tmsh.mtype == tmsh.T_Sorted:
			tmsh.sortMesh(self.preferences['AlwaysWriteDepth'], self.preferences['ClusterDepth'])

		# Increment polycount metric
		polyCount = tmsh.getPolyCount()
		masterObject.tempMeshes.append(tmsh)
		

		# clean up temporary objects
		try:Blender.Scene.GetCurrent().objects.unlink(Blender.Object.Get("DTSExpObj_Tmp"))
		except: pass

		del mesh_data
		del temp_obj
		
		return polyCount


	# todo - combine with addMesh and paramatize
	def addCollisionMesh(self, o, masterObject):
		mesh_data = o.getData();

		# Get Object's Matrix
		mat = self.collapseBlenderTransform(o)

		# Import Mesh, process flags
		tmsh = BlenderMesh(self, o.name, mesh_data, -1, 1.0, mat, o.size, False, None, True)

		# Increment polycount metric
		polyCount = tmsh.getPolyCount()
		masterObject.tempMeshes.append(tmsh)

		return polyCount

		

	
	# Adds all meshes, detail levels, and dts objects to the shape.
	# this should be called after nodes are added.
	def addAllDetailLevels(self, dtsObjects, sortedDetailLevels, sortedObjects):
		# set current frame to rest frame
		restFrame = self.preferences['RestFrame']
		if Blender.Get('curframe') == restFrame: Blender.Set('curframe',restFrame+1)
		Blender.Set('curframe', restFrame)		
		#dtsObjList = dtsObjects.keys()
		dtsObjList = dtsObjects
		# add each detail level
		for dlName in sortedDetailLevels:
			# --------------------------------------------
			numAddedMeshes = 0
			polyCount = 0
			size = DtsGlobals.Prefs.getTrailingNumber(dlName)
			# loop through each dts object, add dts objects and meshes to the shape.
			for dtsObjName in sortedObjects:

				# get nodeinfo struct for the current DL and dts object
				ni = dtsObjects[dtsObjName][dlName]

				# get parent node index for dts object
				pNodeNI = None
				# find the actual parent node
				for dln in sortedDetailLevels:
					if dtsObjects[dtsObjName][dln] != None:
						pNodeNI = dtsObjects[dtsObjName][dln].getGoodMeshParentNI()
						break

				if pNodeNI == None:
					pNodeIdx = -1
				else:
					pNodeIdx = -1
					for node in self.nodes:
						if self.sTable.get(node.name).upper() == pNodeNI.dtsNodeName.upper():
							pNodeIdx = node.name
							break

				
				# get/add dts object to shape
				masterObject = self.findDtsObject(dtsObjName)
				if masterObject == None:
					masterObject = self.addDtsObject(dtsObjName, pNodeIdx)

				
				if ni == None:
					# add a null mesh if there's no mesh for this dl
					masterObject.tempMeshes.append(DtsMesh(DtsMesh.T_Null))
				else:
					# otherwise add a regular mesh
					o = ni.getBlenderObj()
					if dlName[0:3].upper() == "DET":
						polyCount += self.addMesh(o, masterObject)
					elif dlName[0:3].upper() == "COL" or dlName[0:3].upper() == "LOS":
						polyCount += self.addCollisionMesh(o, masterObject)
				
				numAddedMeshes += 1
				
								
			# Modify base subshape if required
			if self.numBaseDetails == 0:
				self.subshapes[0].firstObject = len(self.objects)-numAddedMeshes
				self.subshapes[0].numObjects = numAddedMeshes

			# Get name, do housekeeping			
			strippedDLName = DtsGlobals.Prefs.getTextPortion(dlName)
			self.numBaseDetails += 1
			if strippedDLName.upper() == "DETAIL":
				detailName = "Detail-%d" % (self.numBaseDetails)				
			elif strippedDLName.upper() == "COLLISION":
				self.numCollisionDetails += 1
				detailName = "Collision-%d" % (self.numCollisionDetails)
			elif strippedDLName.upper() == "LOSCOLLISION":
				self.numLOSCollisionDetails += 1
				detailName = "LOS-%d" % (self.numLOSCollisionDetails + 9)
			

			# Store constructed detail level info into shape
			self.detaillevels.append(DetailLevel(self.addName(detailName), 0, self.numBaseDetails-1, size, -1, -1, polyCount))
			# --------------------------------------------
	

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

	# create triangle strips
	def stripMeshes(self, maxsize):
		subshape = self.subshapes[0]
		for obj in self.objects[subshape.firstObject:subshape.firstObject+(subshape.numObjects-(self.numCollisionDetails+self.numLOSCollisionDetails))]:
			for i in range(obj.firstMesh,(obj.firstMesh+obj.numMeshes)):
				tmsh = self.meshes[i]
				if len(tmsh.primitives) == 0: continue
				tmsh.windStrip(maxsize)
		return True
	
	# this should probably be called before the other finalize functions
	def finalizeMaterials(self):
		# Go through materials, strip ".ignore", add IFL image frames.
		for i in range(0, len(self.materials.materials)):
			mat = self.materials.materials[i]		
			if mat.flags & mat.IFLMaterial != 0:
				# remove the trailing numbers from the IFL material
				mntp = self.preferences.getTextPortion(mat.name)
				# add a name for our IflMaterial into the string table
				si = self.sTable.addString(mntp + ".ifl")
				# create an IflMaterial object and append it to the shape
				iflMat = IflMaterial(si, i, 0, 0, 0)
				self.iflmaterials.append(iflMat)
			mat.name = finalizeImageName(mat.name, False)		
		
	def finalizeObjects(self):
		# Go through objects, add meshes, set transforms
		for o in self.objects:
			o.numMeshes = len(o.tempMeshes)
			o.firstMesh = len(self.meshes)
			
			# Initial animation frame
			# (We could add other frames here for visibility / material / vertex animation)
			self.objectstates.append(ObjectState(1.0, 0, 0))
			
			# Get node from first mesh
			if len(o.tempMeshes) == 0:
				Torque_Util.dump_writeWarning("Warning: Object '%s' has no meshes!" % self.sTable.get(o.name));
				continue
			
			isSkinned = False
			#if o.tempMeshes[0].mtype != o.tempMeshes[0].T_Null: o.mainMaterial = o.tempMeshes[0].mainMaterial
			#else: o.mainMaterial = None
			
			# Determine mesh type for these objects (assumed by first entry)
			if o.tempMeshes[0].mtype != o.tempMeshes[0].T_Skin:
				if o.tempMeshes[0].getNodeIndex(0) != None:
					o.node = o.tempMeshes[0].getNodeIndex(0)
				elif o.node < 1:
					o.node = 0
			else:
				#o.node = -1
				o.node = 0
				isSkinned = True
				Torque_Util.dump_writeln("Object %s, Skinned" % (self.sTable.get(o.name)))
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
						Torque_Util.dump_writeWarning("Warning: Invalid skinned mesh in rigid object '%s'!" % (self.sTable.get(o.name)))
					
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
			Torque_Util.dump_writeErr("      Error : Shape contains no meshes (no valid detail levels)!")
			
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
		cmat = self.toTorqueUtilMatrix(object.getMatrix("worldspace"))

		# add on scaling factor
		exportScale = self.preferences['ExportScale']
		scaleMat = MatrixF([exportScale, 0.0, 0.0, 0.0,
				    0.0, exportScale, 0.0, 0.0,
				    0.0, 0.0, exportScale, 0.0,
				    0.0, 0.0, 0.0, exportScale])
		return scaleMat * cmat
		
	# Creates a cumilative scaling ratio for an object
	def collapseBlenderScale(self, object):
		csize = object.getSize()
		csize = [csize[0], csize[1], csize[2]]
		parent = object.getParent()
		while parent != None:
			nsize = parent.getSize()
			csize[0],csize[1],csize[2] = csize[0]*nsize[0],csize[1]*nsize[1],csize[2]*nsize[2]
			parent = parent.getParent()
		exportScale = self.preferences['ExportScale']
		# add on export scale factor
		csize[0], csize[1], csize[2] = csize[0]*exportScale, csize[1]*exportScale, csize[2]*exportScale
		return csize


	# A utility method that gets the min and max positions of the nodes in an armature
	# within a passed-in ordered list.
	def getMinMax(self, rootNode, nodeOrder, nodeOrderDict, warning=False):
		# find the current node in our ordered list
		try:
			pos = nodeOrderDict[rootNode.dtsNodeName]
			minPos, maxPos = pos, pos
		except:
			minPos, maxPos = 99999, -99999

		cMin = []
		cMax = []
		nnames = []
		for child in filter(lambda x: x.getGoodNodeParentNI() == rootNode, self.transformUtil.nodes.values()):
			nnames.append(child.dtsNodeName)
			start, end, warning = self.getMinMax(child, nodeOrder, nodeOrderDict, warning)
			if start == None and end == None: continue
			if end > maxPos: maxPos = end
			if start < minPos: minPos = start
			cMin.append(start)
			cMax.append(end)
		
		# check all children of the current root bone to make sure their min/max values don't
		# overlap.
		for i in range(0, len(cMin)):
			for j in range(i+1, len(cMin)):
				if (cMin[i] <= cMax[j] and cMin[i] >= cMin[j])\
				or (cMax[i] <= cMax[j] and cMax[i] >= cMin[j])\
				or (cMin[j] <= cMax[i] and cMin[j] >= cMin[i])\
				or (cMax[j] <= cMax[i] and cMax[j] >= cMin[i]):
					Torque_Util.dump_writeWarning("-\nWarning: Invalid Traversal - Node hierarchy cannot be matched with the")
					Torque_Util.dump_writeln(     "  node ordering specified in the NodeOrder text buffer.")
					Torque_Util.dump_writeln(     "  Details:")
					Torque_Util.dump_writeln(     "    node tree with root node \'%s\'" % nnames[i])
					Torque_Util.dump_writeln(     "    overlaps sibling tree with root node \'%s\'" % nnames[j])
					Torque_Util.dump_writeln(     "    in the NodeOrder text buffer.")
					Torque_Util.dump_writeln(     "    cMin[i], cMax[i] = %i, %i" % (cMin[i], cMax[i]) )
					Torque_Util.dump_writeln(     "    cMin[j], cMax[j] = %i, %i\n-" % (cMin[j], cMax[j]) )
					warning = True
		return minPos, maxPos, warning
	

	def createOrderedNodeList(self):
		orderedNodeList = []

		# read in desired node ordering from a text buffer, if it exists.
		no = None
		try:
			noTxt = Blender.Text.Get("NodeOrder")
			no = noTxt.asLines()
			Torque_Util.dump_writeln("NodeOrder text buffer found, attempting to export nodes in the order specified.")
		except: no = None
		nodeOrderDict = {}

		if no != None:
			# build a dictionary for fast order compares
			i = 0
			for n in no:
				nodeOrderDict[n] = i
				i += 1			

			boneTree = []

			# Validate the node ordering against the bone hierarchy in our armatures.
			#
			# Validation rules:
			#
			# 	1. Child nodes must come after their parents in the node order
			#	list.
			#
			#	2. The min and max positions of all child nodes in a given bone
			#	tree should not overlap the min/max positions of other bone
			#	trees on the same level of the overall tree.

			# Test Rule #1
			for nodeInfo in self.transformUtil.nodes.values():
				if nodeInfo.getGoodNodeParentNI() != None:
					if nodeInfo.dtsNodeName in nodeOrderDict.keys()\
					and nodeInfo.getGoodNodeParentNI() != None\
					and nodeInfo.getGoodNodeParentNI().dtsNodeName in nodeOrderDict.keys():
						if nodeOrderDict[nodeInfo.dtsNodeName] < nodeOrderDict[nodeInfo.getGoodNodeParentNI().dtsNodeName]:
							Torque_Util.dump_writeWarning("-\nWarning: Invalid node order, child bone \'%s\' comes before" % nodeInfo.dtsNodeName)
							Torque_Util.dump_writeln("  parent bone \'%s\' in the NodeOrder text buffer\n-" % nodeInfo.getGoodNodeParentNI().dtsNodeName)
			# Test Rule #2
			start, end, warning = self.getMinMax(None, no, nodeOrderDict)

			
			if not warning:
				# export in the specified order
				orderedNodeList = self.walkNodeTreeInOrder(None, nodeOrderDict, [])
			else:
				# otherwise export in natural order
				orderedNodeList = self.walkNodeTree(None, [])
		else:
			# get list of nodes in natural order
			orderedNodeList = self.walkNodeTree(None, [])

		return orderedNodeList

	# Walks the node tree recursively and returns a list of nodes in natural order
	def walkNodeTree(self, nodeInfo, nodeOrderList):
		thisLevel = filter(lambda x: x.getGoodNodeParentNI() == nodeInfo, self.transformUtil.nodes.values())
		thisLevel.sort(lambda x,y: cmp(x.dtsNodeName, y.dtsNodeName))
		for child in thisLevel:
			if not child.isBanned(): nodeOrderList.append(child.dtsNodeName)
			nodeOrderList = self.walkNodeTree(child, nodeOrderList)
		
		return nodeOrderList

	# Walks the node tree recursively and returns a list of nodes in the specified order, if possible
	def walkNodeTreeInOrder(self, nodeInfo, nodeOrderDict, nodeOrderList):
		childList = filter(lambda x: x.getGoodNodeParentNI() == nodeInfo, self.transformUtil.nodes.values())
		orderedChildList = filter(lambda x: x.dtsNodeName in nodeOrderDict.keys(), childList)
		extraChildList = filter(lambda x: not (x.dtsNodeName in nodeOrderDict.keys()), childList)
		
		orderedChildList.sort(lambda x, y: cmp(nodeOrderDict[x.dtsNodeName], nodeOrderDict[y.dtsNodeName]))
		
		for child in orderedChildList:
			if not child.isBanned(): nodeOrderList.append(child.dtsNodeName)
			nodeOrderList = self.walkNodeTreeInOrder(child, nodeOrderDict, nodeOrderList)
		for child in extraChildList:
			if not child.isBanned(): nodeOrderList.append(child.dtsNodeName)
			nodeOrderList = self.walkNodeTreeInOrder(child, nodeOrderDict, nodeOrderList)
		
		return nodeOrderList
	
	# adds all object and bone nodes to the shape using the poseUtil tree
	def addAllNodes(self):
		
		orderedNodeList = self.createOrderedNodeList()
		
		# add armatures to our list
		for arm in filter(lambda x: x.getType()=='Armature', Blender.Scene.GetCurrent().objects):
			self.addedArmatures.append(arm)
		
		
		# build a dict of node indices for lookup
		nodeIndices = {}
		i = 1
		for nodeName in orderedNodeList:
			nodeInfo = self.transformUtil.nodes[nodeName]
			if not nodeInfo.isBanned():
				nodeIndices[nodeName] = i
				i += 1
		
		# add nodes in order
		for nodeName in orderedNodeList:
			nodeInfo = self.transformUtil.nodes[nodeName]
			if not nodeInfo.isBanned():
				if nodeInfo.getGoodNodeParentNI() != None:
					parentNodeIndex = nodeIndices[nodeInfo.getGoodNodeParentNI().dtsNodeName]
				else:
					parentNodeIndex = -1
				n = Node(self.sTable.addString(nodeInfo.dtsNodeName), parentNodeIndex)
				try: n.armName = nodeInfo.armParentNI.dtsNodeName
				except: n.armName = None
				n.obj = nodeInfo.getBlenderObj()
				self.nodes.append(n)		
				nodeIndex = len(self.nodes)-1
				self.subshapes[0].numNodes += 1
		
		# dump node transforms for the rest frame
		Blender.Set('curframe', self.preferences['RestFrame'])
		self.restTransforms = self.transformUtil.dumpReferenceFrameTransforms(orderedNodeList, self.preferences['RestFrame'], self.preferences['SequenceExportTwoPassMode'])

		# Set up default translations and rotations for nodes.
		i = 0
		for nname in orderedNodeList:
			pos = self.restTransforms[i][0]
			rot = self.restTransforms[i][2]
			self.defaultTranslations.append(pos)
			self.defaultRotations.append(rot)
			i += 1

		
	# adds a ground frame to a sequence
	def addGroundFrame(self, sequence, frame_idx, boundsStartMat):
		# quit trying to export ground frames if we have had an error.
		try: x = self.GroundFrameError
		except: self.GroundFrameError = False
		if self.GroundFrameError: return
		
		# Add ground frames if enabled
		if sequence.has_ground:
			# Check if we have any more ground frames to add
			if sequence.ground_target != sequence.numGroundFrames:
				# Ok, we can add a ground frame, but do we add it now?
				duration = sequence.numKeyFrames / sequence.ground_target
				if frame_idx >= (duration * (sequence.numGroundFrames+1))-1:
					# We are ready, lets stomp!
					try:						
						bound_obj = Blender.Object.Get("Bounds")
						matf = self.collapseBlenderTransform(bound_obj)
						pos = Vector(matf.get(3,0),matf.get(3,1),matf.get(3,2))
						pos = pos - Vector(boundsStartMat.get(3,0),boundsStartMat.get(3,1),boundsStartMat.get(3,2))
						matf = boundsStartMat.inverse() * matf
						rot = Quaternion().fromMatrix(matf).inverse()
						self.groundTranslations.append(pos)
						self.groundRotations.append(rot)							
							
						sequence.numGroundFrames += 1
					except ValueError:
						# record the error state so we don't repeat ourselves.
						self.GroundFrameError = True
						sequence.has_ground = False # <- nope, no ground frames.
						Torque_Util.dump_writeErr("Error: Could not get ground frames for sequence %s." % sequence.name)
						Torque_Util.dump_writeln("  You must have an object named Bounds in your scene to export ground frames.")

	# Adds a generic sequence
	def addSequence(self, seqName, seqPrefs, scene = None, action=None):



		numFrameSamples = self.preferences.getSeqNumFrames(seqName)

		visIsValid = validateVisibility(seqName, seqPrefs)
		IFLIsValid = validateIFL(seqName, seqPrefs)
		#ActionIsValid = validateAction(seqName, seqPrefs)
		ActionIsValid = True

		if numFrameSamples < 1:
			ActionIsValid = False
			visIsValid = False
			IFLIsValid = False
		# Did we have any valid animations at all for the sequence?
		if not (visIsValid or IFLIsValid or ActionIsValid):
			Torque_Util.dump_writeln("   Skipping sequence %s, no animation types were valid for the sequence. " % seqName)
			return None
			

		# We've got something to export, so lets start off with the basic sequence
		sequence = Sequence(self.sTable.addString(seqName))
		sequence.name = seqName
		sequence.numTriggers = 0
		sequence.firstTrigger = -1
		sequence.numKeyFrames = 0

		sequence.has_vis = False
		sequence.has_ifl = False
		sequence.has_loc = False
		sequence.has_rot = False
		sequence.has_scale = False
		sequence.has_ground = False
		
		sequence.frames = []
		for n in self.nodes:
			sequence.matters_translation.append(False)
			sequence.matters_rotation.append(False)
			sequence.matters_scale.append(False)
			sequence.frames.append(0)
		
		# apply common sequence settings
		sequence.fps = seqPrefs['FPS']
		if seqPrefs['Cyclic']: 
			sequence.flags |= sequence.Cyclic


		sequence.duration = seqPrefs['Duration']
		
		sequence.priority = seqPrefs['Priority']


	
		lastFrameRemoved = False
		if ActionIsValid:
			#startTime = Blender.sys.time()
			sequence, lastFrameRemoved = self.addNodeSeq(sequence, action, numFrameSamples, scene, seqPrefs)
			#endTime = Blender.sys.time()
			#print "Sequence export finished in:", str(endTime-startTime)		

			# if we had to remove the last frame from a cyclic action, and the original action
			# frame samples was the same as the overall number of frames for the sequence, adjust
			# the overall sequence length.
			if lastFrameRemoved:
				numFrameSamples -= 1
		if visIsValid:
			sequence = self.addSequenceVisibility( sequence, numFrameSamples, seqPrefs, int(seqPrefs['StartFrame']), int(seqPrefs['EndFrame']))
		if IFLIsValid:
			sequence = self.addSequenceIFL(sequence, getNumIFLFrames(seqName, seqPrefs), seqPrefs)

			
		self.sequences.append(sequence)

		# add triggers
		if len(seqPrefs['Triggers']) != 0:
			self.addSequenceTriggers(sequence, seqPrefs['Triggers'], numFrameSamples)
		
		return sequence
	
	
	
	# Import an action
	def addNodeSeq(self, sequence, action, numOverallFrames, scene, seqPrefs):
		'''
		This adds an action to a shape as a sequence.
		
		Sequences are added on a one-by-one basis.
		The first part of the function determines if the action is worth exporting - if not, the function fails,
		otherwise it is setup.
		
		The second part of the function determines what the action animates.
		
		The third part of the function adds the keyframes, making heavy use of the getPoseTransform function. You can control the
		amount of frames exported via the 'FrameSamples' option.
		
		Finally, the sequence data is dumped to the shape. Additionally, if the sequence has been marked as a dsq,
		the dsq writer function is invoked - the data for that particular sequence is then removed from the shape.
		
		NOTE: this function needs to be called AFTER all calls to addArmature/addNode, for obvious reasons.
		'''
		
		# build ordered node list.
		orderedNodeList = []
		for nodeIndex in range(1, len(self.nodes)):
                	orderedNodeList.append(self.sTable.get(self.nodes[nodeIndex].name))


		# Get a list of armatures that need to be checked in order to issue
		# warnings regarding armature modifiers (see long note in Dts_Blender.py)
		checkArmatureNIs = DtsGlobals.SceneInfo.getArmaturesOfConcern()

		# Add sequence flags
		if seqPrefs['Blend']:
			isBlend = True
			sequence.flags |= sequence.Blend
		else: isBlend = False
		if seqPrefs['NumGroundFrames'] != 0:
			sequence.has_ground = True
			sequence.ground_target = seqPrefs['NumGroundFrames']
			sequence.flags |= sequence.MakePath
		else: sequence.has_ground = False

		# Determine the number of key frames. Takes into account channels for bones that are
		# not being exported, as they may still effect the animation through IK or other constraints.
		#sequence.numKeyFrames = getNumFrames(action.getAllChannelIpos().values(), False)
		sequence.numKeyFrames = numOverallFrames
		
		interpolateInc = 1

		Torque_Util.dump_writeln("      Frames: %d " % numOverallFrames)
		
		# Depending on what we have, set the bases accordingly
		if sequence.has_ground: sequence.firstGroundFrame = len(self.groundTranslations)
		else: sequence.firstGroundFrame = -1
		
		# this is the number of real action frames we are exporting.
		numFrameSamples = numOverallFrames
		
		removeLast = False
		baseTransforms = []
		useAction = None
		useFrame = None
		
		
		if isBlend:
			# Need to build a list of node transforms to use as the
			# base transforms for nodes in our blend animation.
 			#useAction = seqPrefs['Action']['BlendRefPoseAction']
			refFrame = seqPrefs['BlendRefPoseFrame']
			baseTransforms = self.transformUtil.dumpBlendRefFrameTransforms(orderedNodeList, refFrame, self.preferences['SequenceExportTwoPassMode'])			
			if baseTransforms == None:
				Torque_Util.dump_writeln("Error getting base Transforms!!!!!")



		# *** special processing for the first frame:
		# store off the default position of the bounds box
		try:
			Blender.Set('curframe', self.preferences['RestFrame'])
			bound_obj = Blender.Object.Get("Bounds")
			boundsStartMat = self.collapseBlenderTransform(bound_obj)
		except ValueError:
			boundsStartMat = MatrixF()

		# For blend animations, we need to reset the pose to the reference pose instead of the default
		# transforms.  Otherwise, we won't be able to tell reliably which bones have actually moved
		# during the blend sequence.
		if isBlend:
			# Set the current frame in blender
			
			pass


		# For normal animations, loop through each node and reset it's transforms.
		# This avoids transforms carrying over from other action animations.
		else:			
			# need to cycle through ALL bones and reset the transforms.			
			for armOb in Blender.Scene.GetCurrent().objects:
				if (armOb.getType() != 'Armature'): continue
				tempPose = armOb.getPose()
				armDb = armOb.getData()
				for bonename in armDb.bones.keys():
				#for bonename in self.poseUtil.armBones[armOb.name].keys():
				
					# reset the bone's transform
					tempPose.bones[bonename].quat = bMath.Quaternion().identity()
					tempPose.bones[bonename].size = bMath.Vector(1.0, 1.0, 1.0)
					tempPose.bones[bonename].loc = bMath.Vector(0.0, 0.0, 0.0)
				# update the pose.
				tempPose.update()

			
		
		# create blank frames for each node
		for nodeIndex in range(1, len(self.nodes)):
			sequence.frames[nodeIndex] = []
		
		# get transforms for every frame in a big nested list.	
		if isBlend:
			transforms = self.transformUtil.dumpBlendFrameTransforms(orderedNodeList, seqPrefs['StartFrame'], seqPrefs['EndFrame'], self.preferences['SequenceExportTwoPassMode'])
		else:
			transforms = self.transformUtil.dumpFrameTransforms(orderedNodeList, seqPrefs['StartFrame'], seqPrefs['EndFrame'], self.preferences['SequenceExportTwoPassMode'])

		# if this is a blend animation, calculate deltas
		if isBlend and baseTransforms != None:
			transforms = self.transformUtil.getDeltasFromRef(baseTransforms, transforms, orderedNodeList)
		
		# loop through each frame and transcribe transforms
		for frameTransforms in transforms:
			for nodeIndex in range(1, len(self.nodes)):
				if isBlend:
					#print "nodeIndex=", nodeIndex
					baseTransform = baseTransforms[nodeIndex-1]
				else:
					baseTransform = None

				loc, scale, rot = frameTransforms[nodeIndex-1]
				sequence.frames[nodeIndex].append([loc,rot,scale])

		# add ground frames
		for frame in range(0, numOverallFrames):
			self.addGroundFrame(sequence, frame, boundsStartMat)
			
		# calculate matters
		for nodeIndex in range(1, len(self.nodes)):
			# get root transforms
			if not isBlend:
				rootLoc = self.defaultTranslations[nodeIndex]
				rootRot = self.defaultRotations[nodeIndex]
			else:
				rootLoc = Vector(0.0, 0.0, 0.0)
				rootRot = Quaternion(0.0, 0.0, 0.0, 1.0)
			
			for fr in range(0, len(transforms)):
				# check deltas from base transforms
				if sequence.matters_translation[nodeIndex] == False:
					if not rootLoc.eqDelta(transforms[fr][nodeIndex-1][0], 0.02):
						#print "LOC detected:"
						#print " rootLoc=", rootLoc
						#print " loc    =", transforms[fr][nodeIndex-1][0]
						sequence.matters_translation[nodeIndex] = True
						sequence.has_loc = True
				if sequence.matters_rotation[nodeIndex] == False:
					#print "angle between quats is:", rootRot.angleBetween(transforms[fr][nodeIndex-1][2])
					#if not rootRot.eqDelta(transforms[fr][nodeIndex-1][2], 0.02):
					if rootRot.angleBetween(transforms[fr][nodeIndex-1][2]) > 0.008:
						#print "ROT detected:"
						#print " rootRot=", rootRot
						#print " rot    =", transforms[fr][nodeIndex-1][2]
						sequence.matters_rotation[nodeIndex] = True
						sequence.has_rot = True
				if sequence.matters_scale[nodeIndex] == False:
					if not Vector(1.0, 1.0, 1.0).eqDelta(transforms[fr][nodeIndex-1][1], 0.02):
						#print "Scale detected:"
						#print " deltaScale=", transforms[fr][nodeIndex-1][1]
						sequence.matters_scale[nodeIndex] = True
						sequence.has_scale = True

					
		
		# if nothing was actually animated abandon exporting the action.
		if not (sequence.has_loc or sequence.has_rot or sequence.has_scale):
			# don't write this warning anymore, not needed.
			#Torque_Util.dump_writeWarning("Warning: Action has no keyframes, aborting export for this animation.")
			return sequence, False

		# set the aligned scale flag if we have scale.
		if sequence.has_scale: sequence.flags |= Sequence.AlignedScale
		
		# It should be safe to add this sequence to the list now.
		#self.sequences.append(sequence)

		# Now that we have all the transforms for each node at 
		# every frame, remove the ones that we don't need. This is much faster than doing
		# two passes through the blender frames to determine what's animated and what's not.
		for nodeIndex in range(1, len(self.nodes)):
			if not sequence.matters_translation[nodeIndex]:
				for frame in range(0, numOverallFrames):					
					sequence.frames[nodeIndex][frame][0] = None
			if not sequence.matters_rotation[nodeIndex]:
				for frame in range(0, numOverallFrames):
					sequence.frames[nodeIndex][frame][1] = None				
			if not sequence.matters_scale[nodeIndex]:
				for frame in range(0, numOverallFrames):
					sequence.frames[nodeIndex][frame][2] = None

		remove_translation, remove_rotation, remove_scale = True, True, True
		if seqPrefs['Cyclic']:
			for nodeIndex in range(1, len(self.nodes)):
				# If we added any new translations, and the first frame is equal to the last,
				# allow the next pass of nodes to happen, to remove the last frame.
				# (This fixes the "dead-space" issue)
				if len(sequence.frames[nodeIndex]) != 0:
					if (sequence.frames[nodeIndex][0][0] != None) and (sequence.frames[nodeIndex][-1][0] != None) and not sequence.frames[nodeIndex][0][0].eqDelta(sequence.frames[nodeIndex][-1][0], 0.01):
						remove_translation = False
					if (sequence.frames[nodeIndex][0][1] != None) and (sequence.frames[nodeIndex][-1][1] != None) and not sequence.frames[nodeIndex][0][1].eqDelta(sequence.frames[nodeIndex][-1][1], 0.01):
						remove_rotation = False
					if (sequence.frames[nodeIndex][0][2] != None) and (sequence.frames[nodeIndex][-1][2] != None) and not sequence.frames[nodeIndex][0][2].eqDelta(sequence.frames[nodeIndex][-1][2], 0.01):
						remove_scale = False

			# Determine if the change has affected all that we animate
			if (remove_translation) and (remove_rotation) and (remove_scale):
				removeLast = True
			

		Torque_Util.dump_write("      Animates:")
		if sequence.has_loc: Torque_Util.dump_write("loc")
		if sequence.has_rot: Torque_Util.dump_write("rot")
		if sequence.has_scale: Torque_Util.dump_write("scale")
		if sequence.has_ground: Torque_Util.dump_write("ground")
		Torque_Util.dump_writeln("")

		# We can now reveal the true number of keyframes
		#sequence.numKeyFrames = numFrameSamples-1

		# Do a second pass on the nodes to remove the last frame for cyclic anims
		if removeLast:
			# Go through list of frames for nodes animated in sequence and delete the last frame from all of them
			for nodeIndex in range(len(self.nodes)):
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

		return sequence, removeLast



	
	def addSequenceTriggers(self, sequence, unsortedTriggers, nFrames):
		print "addSequenceTriggers called!!!"
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
			print "realPos=", realPos
			self.triggers.append(Trigger(triggers[i][0], triggers[i][2], realPos, triggerState[i]))
		del triggerState
		sequence.numTriggers += len(triggers)
		sequence.flags |= sequence.MakePath


	# Add sequence matters for IFL animation.
	def addSequenceIFL(self, sequence, numFrameSamples, sequenceKey):
		sequence.matters_ifl = [False]*len(self.materials.materials)
		if sequence.baseObjectState == -1:
			sequence.baseObjectState = len(self.objectstates)
		# Now we can dump each frame for the objects
		# Sequence matters_ifl indexes iflmaterials.
		for i in range(0, len(self.iflmaterials)):
					mat = self.iflmaterials[i]
					IFLMatName = self.sTable.get(mat.name)
					# must strip last four chars from IFLMatName (".ifl")
					if self.preferences.getTextPortion(sequenceKey['IFL']['Material']) == IFLMatName[0:len(IFLMatName)-4]:
						sequence.matters_ifl[i] = True
					else:
						pass
		sequence.has_ifl = True
		return sequence

	# Processes a material ipo and incorporates it into the Action
	def addSequenceVisibility(self, sequence, numOverallFrames, sequenceKey, startFrame, endFrame):
		'''
		This adds ObjectState tracks to the sequence.
		
		Since blender's Actions don't support object or material ipo's, we need to use the ipos directly.
		In addition, a starting point and end point must be defined, which is useful in using a the ipo in more than 1 animation track.
		If the visibility subsequence is shorter than the other subsequences belonging to the same sequence,
		sampling of the IPOs will continue past the end of the subsequence until the full sequence is finished.
		If the visibility sequence is longer than the other subsequences, other subsequences will be sampled past the end of their
		runs until the full sequence is finished.

		NOTE: this function needs to be called AFTER finalizeObjects, for obvious reasons.
		'''

		scene = Blender.Scene.GetCurrent()
		sequence.matters_vis = [False]*len(self.objects)

		# includes last frame
		#numVisFrames = int((startFrame - endFrame) + 1)

		# Just do it.
		for i in range(0, len(self.objects)):
			dObj = self.objects[i]
			dObjName = self.sTable.get(dObj.name)
			try: keyedObj = sequenceKey['Vis']['Tracks'][dObjName]
			except:
				sequence.matters_vis[i] = False
				continue
			# skip this object if the vis track is not enabled
			if not keyedObj['hasVisTrack']: continue
			
			try:
				if keyedObj['IPOType'] == "Object":
					bObj = Blender.Object.Get(keyedObj['IPOObject'])
				elif keyedObj['IPOType'] == "Material":
					bObj = Blender.Material.Get(keyedObj['IPOObject'])

				bIpo = bObj.getIpo()
				IPOCurveName = getBlenderIPOChannelConst(keyedObj['IPOType'], keyedObj['IPOChannel'])
				IPOCurve = None
				IPOCurveConst = bIpo.curveConsts[IPOCurveName]
				IPOCurve = bIpo[IPOCurveConst]
				if IPOCurve == None: raise TypeError
			except: 
				Torque_Util.dump_writeErr("Error: Could not get animation curve for visibility animation: %s " % sequence.name)
				continue

			sequence.matters_vis[i] = True
			if sequence.baseObjectState == -1:
				sequence.baseObjectState = len(self.objectstates)
			# add the object states, include the last frame
			for fr in range(startFrame, numOverallFrames + startFrame):
				val = IPOCurve[int(fr)]
				if val > 1.0: val = 1.0
				elif val < 0.0: val = 0.0
				# Make sure we're still in the user defined frame range.
				if fr <= endFrame:
					self.objectstates.append(ObjectState(val,0,0))
					print "appending vis frame with val of:", val
				# If we're past the user defined frame range, pad out object states
				# with copies of the good last frame state.
				else:
					val = IPOCurve[int(endFrame)]
					if val > 1.0: val = 1.0
					elif val < 0.0: val = 0.0
					self.objectstates.append(ObjectState(val,0,0))
					print "appending vis frame with val of:", val
							
		sequence.has_vis = True
		return sequence



		
	def convertAndDumpSequenceToDSQ(self, sequence, filename, version):
		
		# Write entry for this in shape script, if neccesary
		self.externalSequences.append(self.sTable.get(sequence.nameIndex))
		
		# Simple task of opening the file and dumping sequence data
		dsq_file = open(filename, "wb")
		self.writeDSQSequence(dsq_file, sequence, version) # Write only current sequence data
		dsq_file.close()


		# Remove anything we added (using addNodeSeq or addSequenceTrigger only) to the main list
		
		if sequence.baseTranslation != -1: del self.nodeTranslations[sequence.baseTranslation-1:sequence.baseTranslation+sequence.numKeyFrames]
		if sequence.baseRotation != -1:    del self.nodeRotations[sequence.baseRotation-1:sequence.baseRotation+sequence.numKeyFrames]
		if sequence.baseScale != -1:       del self.nodeAlignedScales[sequence.baseScale-1:sequence.baseScale+sequence.numKeyFrames]
		if sequence.firstTrigger != -1:    del self.triggers[sequence.firstTrigger-1:sequence.firstTrigger+sequence.numTriggers]
		if sequence.firstGroundFrame != -1:
			del self.groundTranslations[sequence.firstGroundFrame-1:sequence.firstGroundFrame+sequence.numGroundFrames]
			del self.groundRotations[sequence.firstGroundFrame-1:sequence.firstGroundFrame+sequence.numGroundFrames]
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
	def addMaterial(self, imageName):
		if imageName == None: return None
		
		# find the material associated with the texture image file name
		material = None
		try:
			mat = self.preferences['Materials'][imageName]
			flags = 0x00000000
			if mat['SWrap'] == True: flags |= dMaterial.SWrap
			if mat['TWrap'] == True: flags |= dMaterial.TWrap
			if mat['Translucent'] == True: flags |= dMaterial.Translucent
			if mat['Additive'] == True: flags |= dMaterial.Additive
			if mat['Subtractive'] == True: flags |= dMaterial.Subtractive
			if mat['SelfIlluminating'] == True: flags |= dMaterial.SelfIlluminating
			if mat['NeverEnvMap'] == True: flags |= dMaterial.NeverEnvMap
			if mat['NoMipMap'] == True: flags |= dMaterial.NoMipMap
			if mat['MipMapZeroBorder'] == True: flags |= dMaterial.MipMapZeroBorder
			if mat['IFLMaterial'] == True: flags |= dMaterial.IFLMaterial

			material = dMaterial(mat['BaseTex'], flags,-1,-1,-1,(1.0/mat['detailScale']),mat['reflectance'])
			# Must have something in the reflectance slot to prevent TGE from
			# crashing when env mapping without a reflectance map.
			material.reflectance = len(self.materials.materials)

			if mat['DetailMapFlag'] == True and mat['DetailTex'] != None:
				dmFlags = 0x00000000
				if mat['SWrap'] == True: dmFlags |= dMaterial.SWrap
				if mat['TWrap'] == True: dmFlags |= dMaterial.TWrap
				dmFlags |= dMaterial.DetailMap
				#detail_map = dMaterial(mat['DetailTex'], dmFlags,-1,-1,-1,1.0,mat['reflectance'])
				detail_map = dMaterial(mat['DetailTex'], dmFlags,-1,-1,-1,1.0,0.0)
				material.detail = self.materials.add(detail_map)
				if mat['NeverEnvMap'] == False:
					Torque_Util.dump_writeWarning("    Warning: Material (%s) is using environment mapping with a detail map, strange things may happen!" % imageName)

			if mat['BumpMapFlag'] == True and mat['BumpMapTex'] != None:
				bmFlags = 0x00000000
				if mat['SWrap'] == True: bmFlags |= dMaterial.SWrap
				if mat['TWrap'] == True: bmFlags |= dMaterial.TWrap
				bmFlags |= dMaterial.BumpMap
				bump_map = dMaterial(mat['BumpMapTex'], bmFlags,-1,-1,-1,1.0,mat['reflectance'])
				material.bump = self.materials.add(bump_map)

			if mat['ReflectanceMapFlag'] == True and mat['RefMapTex'] != None:
				rmFlags = 0x00000000
				if mat['SWrap'] == True: rmFlags |= dMaterial.SWrap
				if mat['TWrap'] == True: rmFlags |= dMaterial.TWrap
				rmFlags |= dMaterial.ReflectanceMap
				refl_map = dMaterial(mat['RefMapTex'], rmFlags,-1,-1,-1,1.0,mat['reflectance'])
				material.reflectance = self.materials.add(refl_map)
			
		except KeyError:
			Torque_Util.dump_writeWarning("    Warning: Texture Image (%s) is used on a mesh but could not be found in the material list!" % imageName)
			return None

		material.name = imageName
		retVal = self.materials.add(material)
		if self.preferences['TSEMaterial']:
			self.addTGEAMaterial(imageName)

		return retVal
		
	
	
	
	# Material addition (TGEA mode)
	def addTGEAMaterial(self, imageName):
	
		mat = self.preferences['Materials'][imageName]

		# Build the material string.
		materialString = "new Material(%s)\n{\n" % ( finalizeImageName(SceneInfoClass.stripImageExtension(imageName), True))
		
		materialString += "// Rendering Stage 0\n"
		
		materialString += "baseTex[0] = \"./%s\";\n" % (finalizeImageName(SceneInfoClass.stripImageExtension(imageName)))
		
		if mat['DetailMapFlag'] == True and mat['DetailTex'] != None:
			materialString += "detailTex[0] = \"./%s\";\n" % (mat['DetailTex'])
		if mat['BumpMapFlag'] == True and mat['BumpMapTex'] != None:
			materialString += "bumpTex[0] = \"./%s\";\n" % (mat['BumpMapTex'])		
		if mat['SelfIlluminating'] == True:
			materialString += "emissive[0] = true;\n"
		if mat['Translucent'] == True:
			materialString += "translucent[0] = true;\n"
		if mat['Additive'] == True:
			materialString += "TranslucentBlendOp[0] = Add;\n" # <- not sure if it's Add or $Add, docs incomplete...
		elif mat['Subtractive'] == True:
			materialString += "TranslucentBlendOp[0] = Sub;\n" # <- ditto
		# need to set a default blend op?  Which one?		
		
		materialString += "};\n\n"
		
		self.scriptMaterials.append(materialString)
	
	# Finalizes shape
	def finalize(self, writeShapeScript=False):
		pathSep = "/"
		if "\\" in self.preferences['exportBasepath']: pathSep = "\\"
		
		# Write out shape script
		if writeShapeScript:
			Torque_Util.dump_writeln("   Writing script%s%s%s.cs" % (self.preferences['exportBasepath'], pathSep, self.preferences['exportBasename']))
			shapeScript = open("%s%s%s.cs" % (self.preferences['exportBasepath'], pathSep, self.preferences['exportBasename']), "w")
			shapeScript.write("datablock TSShapeConstructor(%sDts)\n" % self.preferences['exportBasename'])
			shapeScript.write("{\n")
			# don't need to write out the full path, in fact, it causes problems to do so.  We'll just assume
			# that the player is putting their shape script in the same folder as the .dts.
			shapeScript.write("   baseShape = \"./%s\";\n" % (self.preferences['exportBasename'] + ".dts"))
			count = 0
			for sequence in self.externalSequences:
				#shapeScript.write("   sequence%d = \"./%s_%s.dsq %s\";\n" % (count,self.preferences['exportBasepath'],sequence,sequence))
				shapeScript.write("   sequence%d = \"./%s.dsq %s\";\n" % (count,sequence,sequence))
				count += 1
			shapeScript.write("};")
			shapeScript.close()

		# Write out TGEA Material Script
		if self.preferences['TSEMaterial']:
			Torque_Util.dump_writeln("   Writing material script %s%smaterials.cs" % (self.preferences['exportBasepath'], pathSep))
			materialScript = open("%s%smaterials.cs" % (self.preferences['exportBasepath'], pathSep), "w")
			materialScript.write("// Script automatically generated by Blender DTS Exporter\n\n")
			for materialDef in self.scriptMaterials:			
				materialScript.write(materialDef)
			materialScript.write("// End of generated script\n")
			materialScript.close()
		
		# Write out IFL File
		# Now we can dump each frame
		for seqName in self.preferences['Sequences'].keys():
			seqPrefs = self.preferences['Sequences'][seqName]
			if seqPrefs['IFL']['Enabled'] and validateIFL(seqName, seqPrefs) and seqPrefs['IFL']['WriteIFLFile']:				
				iflName = self.preferences.getTextPortion(seqPrefs['IFL']['Material'])
				Torque_Util.dump_writeln("   Writing IFL script %s%s%s.ifl" % (self.preferences['exportBasepath'], pathSep, iflName))
				IFLScript = open("%s%s%s.ifl" % (self.preferences['exportBasepath'], pathSep, iflName), "w")
				for frame in seqPrefs['IFL']['IFLFrames']:
					IFLScript.write("%s %i\n" % (frame[0], frame[1]))
				IFLScript.close()

		
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
			if sequence.has_ifl: Torque_Util.dump_write("ifl")
			if sequence.has_vis: Torque_Util.dump_write("vis")
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
	
