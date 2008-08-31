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
		
		# set rest frame before initializing poseUtil
		Blender.Set('curframe', prefs['RestFrame'])
		# this object is the interface through which we interact with the
		# pose module and the blender armature system.		
		self.poseUtil = DtsPoseUtil.DtsPoseUtilClass(prefs)
		
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
		# Check for armature modifier
		for mod in o.modifiers:
			if mod.type == Blender.Modifier.Types.ARMATURE:					
				hasArmatureDeform = True
		# Check for an armature parent
		try:
			if o.parentType == Blender.Object.ParentTypes['ARMATURE']:
				hasArmatureDeform = True
		except: pass
		# does the object have geometry?

		# do we even have any modifiers?  If not, we can skip copying the display data.
		#print "Checking object", o.name

		try: hasMultiRes = o.getData(False,True).multires
		except AttributeError: hasMultiRes = False

		if len(o.modifiers) != 0 or hasMultiRes:
			hasModifiers = True
		else:
			hasModifiers = False

		# Otherwise, get the final display data, as affected by modifers.
		if ((not hasArmatureDeform) and hasModifiers) or (o.getType() in ['Surf', 'Text', 'MBall']):
			#print "Getting raw data for", o.getName()
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

		# if we have armature deformation, or don't have any modifiers, get the mesh data the old fashon way
		else:
			#print "Getting mesh data for", o.getName()
			mesh_data = o.getData(False,True);
			temp_obj = None


		# Get Object's Matrix
		mat = self.collapseBlenderTransform(o)

		# Import Mesh, process flags
		try: x = self.preferences['PrimType']
		except KeyError: self.preferences['PrimType'] = "Tris"
		tmsh = BlenderMesh( self, o.name, mesh_data, -1, 1.0, mat, hasArmatureDeform, False, (self.preferences['PrimType'] == "TriLists" or self.preferences['PrimType'] == "TriStrips") )

		# todo - fix mesh flags
		#if len(names) > 1: tmsh.setBlenderMeshFlags(names[1:])

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
		hasArmatureDeform = False
		if False:
			# Check for armature modifier
			for mod in o.modifiers:
				if mod.type == Blender.Modifier.Types.ARMATURE:					
					hasArmatureDeform = True
			# Check for an armature parent
			try:
				if o.parentType == Blender.Object.ParentTypes['ARMATURE']:
					hasArmatureDeform = True
			except: pass
		

		# do we even have any modifiers?  If not, we can skip copying the display data.
		print "Checking object", o.name

		try: hasMultiRes = o.getData(False,True).multires
		except AttributeError: hasMultiRes = False

		if len(o.modifiers) != 0 or hasMultiRes:
			hasModifiers = True
		else:
			hasModifiers = False

		# Otherwise, get the final display data, as affected by modifers.
		if ((not hasArmatureDeform) and hasModifiers) or (o.getType() in ['Surf', 'Text', 'MBall']):
			#print "Getting raw data for", o.getName()
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

		# if we have armature deformation, or don't have any modifiers, get the mesh data the old fashon way
		else:
			#print "Getting mesh data for", o.getName()
			mesh_data = o.getData(False,True);
			temp_obj = None


		# Get Object's Matrix
		mat = self.collapseBlenderTransform(o)

		# Import Mesh, process flags
		try: x = self.preferences['PrimType']
		except KeyError: self.preferences['PrimType'] = "Tris"
		tmsh = BlenderMesh(self, o.name, mesh_data, 0, 1.0, mat, False, True)
		#tmsh = BlenderMesh( self, o.name, mesh_data, -1, 1.0, mat, hasArmatureDeform, False, (self.preferences['PrimType'] == "TriLists" or self.preferences['PrimType'] == "TriStrips") )


		# Increment polycount metric
		polyCount = tmsh.getPolyCount()
		masterObject.tempMeshes.append(tmsh)
		

		# clean up temporary objects
		try:Blender.Scene.GetCurrent().objects.unlink(Blender.Object.Get("DTSExpObj_Tmp"))
		except: pass

		del mesh_data
		del temp_obj
		
		return polyCount

		

	
	# Adds all meshes, detail levels, and dts objects to the shape.
	# this should be called after nodes are added.
	def addAllDetailLevels(self, dtsObjects, sortedDetailLevels):
		dtsObjList = dtsObjects.keys()
		# add each detail level
		for dlName in sortedDetailLevels:
			# --------------------------------------------
			numAddedMeshes = 0
			polyCount = 0
			size = DtsGlobals.Prefs.getTrailingNumber(dlName)
			# loop through each dts object, add dts objects and meshes to the shape.
			for dtsObjName in dtsObjList:

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
						if self.sTable.get(node.name).upper() == pNodeNI.dtsObjName.upper():
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
				
				#print "self.tempMeshes =", masterObject.tempMeshes
								
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
			#self.detaillevels.append(DetailLevel(self.addName(detailName), 0, self.numBaseDetails-1, calcSize, -1, -1, polyCount))
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
			Torque_Util.dump_writeWarning("      Warning : Shape contains no detail levels!")
			
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
		#print "exportScale = ", exportScale
		# add on export scale factor
		csize[0], csize[1], csize[2] = csize[0]*exportScale, csize[1]*exportScale, csize[2]*exportScale
		return csize


	# A utility method that gets the min and max positions of the bones in an armature
	# within a passed-in ordered list.
	def getMinMax(self, rootBone, nodeOrder, nodeOrderDict):
		# find the current node in our ordered list
		try: pos = nodeOrderDict[rootBone.name]
		except:
			return None, None
		minPos, maxPos = pos, pos
		cMin = []
		cMax = []
		nnames = []
		for child in rootBone.children:
			nnames.append(child.name)
			start, end = self.getMinMax(child, nodeOrder, nodeOrderDict)
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
		return minPos, maxPos
	
	
	# adds all object and bone nodes to the shape using the poseUtil tree
	def addAllNodes(self):
		# strike a pose
		#poses = {}
		for arm in filter(lambda x: x.getType()=='Armature', Blender.Object.Get()):
			self.addedArmatures.append(arm)
		print "self.addedArmatures:",self.addedArmatures
		# get a list of ordered nodes by walking the poseUtil node tree.
		nodeList = []
		for nodeInfo in filter(lambda x: x.parentNI == None, self.poseUtil.nodes.values()):
			self.addNodeTree(nodeInfo)
	
	# adds a node tree recursively.
	# called by addAllNodes, not to be called externally.
	def addNodeTree(self, nodeInfo, parentNodeIndex =-1):
		if not nodeInfo.isExcluded():
			n = Node(self.sTable.addString(nodeInfo.dtsObjName), parentNodeIndex)
			pos = nodeInfo.defPosPS
			rot = nodeInfo.defRotPS
			self.defaultTranslations.append(pos)
			self.defaultRotations.append(rot)
			try: n.armName = nodeInfo.armParentNI.nodeName
			except: n.armName = None
			n.obj = nodeInfo.getBlenderObj()
			self.nodes.append(n)		
			nodeIndex = len(self.nodes)-1
			self.subshapes[0].numNodes += 1
		else:
			nodeIndex = parentNodeIndex
		for nodeInfo in filter(lambda x: x.parentNI == nodeInfo, self.poseUtil.nodes.values()):
			self.addNodeTree(nodeInfo, nodeIndex)
		
		
	# These three helper methods are used by getPoseTransform. They should probably be moved elsewhere.
	def isRotated(self, quat):
		delta = 0.0001
		return not ((quat[0] < delta) and (quat[0] > -delta) and (quat[1] < delta) and (quat[1] > -delta) and (quat[2] < delta) and (quat[2] > -delta))
	
	def isTranslated(self, vec):
		delta = 0.00001
		return not ((vec[0] < delta) and (vec[0] > -delta) and (vec[1] < delta) and (vec[1] > -delta) and (vec[2] < delta) and (vec[2] > -delta))
	
	def isScaled(self, vec):
		delta = 0.00001
		return not ((vec[0] < 1.0 + delta) and (vec[0] > 1.0 - delta) and (vec[1] < 1.0 + delta) and (vec[1] > 1.0 - delta) and (vec[2] < 1.0 + delta) and (vec[2] > 1.0 - delta))

	
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
						bound_parent = bound_obj.getParent()
						if bound_parent != None and bound_parent.getType() == 'Armature':
							pose = bound_parent.getPose()
							pos = self.poseUtil.getBoneLocWS(bound_parent.getName(), bound_obj.parentbonename, pose)
							pos = pos - self.poseUtil.getBoneRestPosWS(bound_parent.name, bound_obj.parentbonename)
							rot = self.poseUtil.getBoneRotWS(bound_parent.getName(), bound_obj.parentbonename, pose)
							rot = self.poseUtil.getBoneRestRotWS(bound_parent.name, bound_obj.parentbonename).inverse() * rot
							self.groundTranslations.append(pos)
							self.groundRotations.append(rot)
						else:
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
						Torque_Util.dump_writeErr("Error: Could not get ground frames %d" % sequence.numGroundFrames)
						Torque_Util.dump_writeln("  You must have an object named Bounds in your scene to export ground frames.")


	
	# grab the pose transform of whatever frame we're currently at.  Frame must be set before calling this method.
	def getPoseTransform(self, sequence, nodeIndex, frame_idx, pose, baseTransform=None, getRawValues=False):

		loc, rot, scale = None, None, None
		#try: armName = self.addedArmatures[self.nodes[nodeIndex].armIdx][0].name
		#except: armName = None

		# duration should already be calculated at this point.
		# Convert time units from Blender's frame (starting at 1) to second
		# (using sequence FPS)
		#time = float(frame_idx - 1) / sequence.fps
		#if sequence.duration < time:
		#	sequence.duration = time

		# some temp variables to make life easier
		node = self.nodes[nodeIndex]
		parentNode = self.nodes[node.parent]
		bonename = self.sTable.get(node.name)
		parentname = self.sTable.get(parentNode.name)
		

		
		# Get our values from the poseUtil interface		
		transVec, quatRot = self.poseUtil.getNodeLocRotLS(bonename, pose)
		# - determine the scale of the bone.
		#scaleVec = pose.bones[bonename].size
		scaleVec = self.poseUtil.toTorqueVec([1,1,1])


		# We dump out every transform regardless of whether it matters or not.  This avoids having to
		# make multiple passes through the frames to determine what's animated.  Unused tracks and channels
		# are cleaned up later.
		if baseTransform != None:
			# Blended animation, so find the difference between
			# frames and store this

			# process translation
			transVec = transVec - baseTransform[0]
			# rotate the translation into the bone's local space.
			transVec = self.defaultRotations[nodeIndex].inverse().apply(transVec)
			if self.isTranslated(transVec):
				sequence.matters_translation[nodeIndex] = True
				sequence.has_loc = True				
			loc = transVec


			# process rotation
			# Get the difference between the current rotation and the base
			# rotation.
			btqt = baseTransform[1]
			quatRot = (btqt.inverse() * quatRot).inverse()
			if self.isRotated(quatRot):
				sequence.matters_rotation[nodeIndex] = True
				sequence.has_rot = True
			rot = quatRot

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
				loc = transVec				
			else:
				if self.isTranslated(transVec):
					sequence.matters_translation[nodeIndex] = True
					sequence.has_loc = True				
				loc = transVec
				loc += self.defaultTranslations[nodeIndex]

			# process rotation
			if getRawValues:
				rot = quatRot
			else:
				if self.isRotated(quatRot):
					sequence.matters_rotation[nodeIndex] = True
					sequence.has_rot = True
				rot = quatRot.inverse() * self.defaultRotations[nodeIndex]
				
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
	def buildBaseTransforms(self, blendSequence, blendAction, useActionName, useFrame, scene):
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
			#for bonename in armOb.getData().bones.keys():
			for bonename in self.poseUtil.armBones[armOb.name].keys():
				# reset the bone's transform
				tempPose.bones[bonename].quat = bMath.Quaternion().identity()
				tempPose.bones[bonename].size = bMath.Vector(1.0, 1.0, 1.0)
				tempPose.bones[bonename].loc = bMath.Vector(0.0, 0.0, 0.0)
			# update the pose.
			tempPose.update()

		# now set the active action and move to the desired frame
		for i in range(0, len(self.addedArmatures)):
			arm = self.addedArmatures[i]
			useAction.setActive(arm)

		# Set the current frame in blender
		Blender.Set('curframe', useFrame)
		
		for armIdx in range(0, len(self.addedArmatures)):
			arm = self.addedArmatures[armIdx]
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
			#print "   Adding action data for", seqName
			sequence, lastFrameRemoved = self.addNodeSeq(sequence, action, numFrameSamples, scene, seqPrefs)
			# if we had to remove the last frame from a cyclic action, and the original action
			# frame samples was the same as the overall number of frames for the sequence, adjust
			# the overall sequence length.
			if lastFrameRemoved:
				numFrameSamples -= 1
		if visIsValid:
			#print "   Adding visibility data for", seqName
			sequence = self.addSequenceVisibility( sequence, numFrameSamples, seqPrefs, int(seqPrefs['StartFrame']), int(seqPrefs['EndFrame']))
			#if sequence.numKeyFrames <  numVisFrames: sequence.numKeyFrames = numVisFrames
		if IFLIsValid:
			#print "   Adding IFL data for", seqName
			sequence = self.addSequenceIFL(sequence, getNumIFLFrames(seqName, seqPrefs), seqPrefs)
			
		self.sequences.append(sequence)
		
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
		

		# Lets start off with the basic sequence
		'''
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
		'''
		
		'''
		# Figure out which nodes have IPO curves.  Need this to determine the number of keyframes; and
		# possibly to force export of some channels where nothing actually moves but the user requires
		# the transforms to be keyed in place for some reason.
		nodeFound = False
		nodeIndex = None
		channels = action.getAllChannelIpos()
		for channel_name in channels:
			if channels[channel_name] == None or channels[channel_name].getNcurves() == 0: continue
			nodeIndex = self.getNodeIndex(channel_name)
			# Determine if this node is in the shape
			if nodeIndex == None: continue
			# Print informative sequence name if we found a node in the shape (first time only)
			if not nodeFound:
				Torque_Util.dump_writeln("   Action %s used, dumping..." % action.getName())
			nodeFound = True
			# Print informative track message
			Torque_Util.dump_writeln("      Track: %s (node %d)" % (channel_name,nodeIndex))
		del channels
		'''
			

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
		
		'''
		# Calculate the raw number of action frames, from start frame to end frame, inclusive.
		rawActFrames = (seqPrefs['Action']['EndFrame'] - seqPrefs['Action']['StartFrame']) + 1

		# calc the interpolation increment
		try: interpolateInc = float(rawActFrames-1.0) / float(seqPrefs['Action']['FrameSamples']-1.0)
		except: interpolateInc = 1.0
		
		# make sure it's not less than 1
		if interpolateInc < 1.0: interpolateInc = 1.0
		'''
		interpolateInc = 1

		Torque_Util.dump_writeln("      Frames: %d " % numOverallFrames)
		
		# Depending on what we have, set the bases accordingly
		if sequence.has_ground: sequence.firstGroundFrame = len(self.groundTranslations)
		else: sequence.firstGroundFrame = -1
		
		# this is the number of real action frames we are exporting.
		#numFrameSamples = seqPrefs['Action']['FrameSamples']+1
		#numFrameSamples = seqPrefs['FrameSamples']
		numFrameSamples = numOverallFrames
		
		removeLast = False
		baseTransforms = []
		useAction = None
		useFrame = None
		if isBlend:
			# Need to build a list of node transforms to use as the
			# base transforms for nodes in our blend animation.
 			#useAction = seqPrefs['Action']['BlendRefPoseAction']
			useFrame = seqPrefs['BlendRefPoseFrame']
			baseTransforms = self.buildBaseTransforms(sequence, action, useAction, useFrame, scene)
			if baseTransforms == None:
				Torque_Util.dump_writeln("Error getting base Transforms!!!!!")



		# *** special processing for the first frame:
		# store off the default position of the bounds box
		try:
			Blender.Set('curframe', 1)
			bound_obj = Blender.Object.Get("Bounds")
			boundsStartMat = self.collapseBlenderTransform(bound_obj)
		except ValueError:
			boundsStartMat = MatrixF()

		# For blend animations, we need to reset the pose to the reference pose instead of the default
		# transforms.  Otherwise, we won't be able to tell reliably which bones have actually moved
		# during the blend sequence.
		if isBlend:
			# get our blend ref pose action
			#refPoseAct = Blender.Armature.NLA.GetActions()[useAction]
			# now set the active action and move to the desired frame
			#for i in range(0, len(self.addedArmatures)):
			#	arm = self.addedArmatures[i]
			#	refPoseAct.setActive(arm)
			# Set the current frame in blender
			Blender.Set('curframe', useFrame)

		# For normal animations, loop through each node and reset it's transforms.
		# This avoids transforms carrying over from other action animations.
		else:			
			# need to cycle through ALL bones and reset the transforms.
			for armOb in Blender.Object.Get():
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
		
		# loop through all of the armatures and set the current action as active for all
		# of them.  Sadly, there is no way to tell which action belongs with which armature
		# using the Python API in Blender, so this is a bit messy.
		#act = Blender.Armature.NLA.GetActions()[sequence.name]
		#for i in range(0, len(self.addedArmatures)):
		#	arm = self.addedArmatures[i][0]			
		#	act.setActive(arm)
		# loop through all of the exisitng action frames
		for frame in range(0, numOverallFrames):
			# Set the current frame in blender
			curFrame = int(round(float(frame)*interpolateInc,0)) + seqPrefs['StartFrame']
			Blender.Set('curframe', curFrame)
			# add ground frames
			self.addGroundFrame(sequence, curFrame, boundsStartMat)
			
			# get poses for all armatures in the scene
			armPoses = {}
			for armIdx in range(0, len(self.addedArmatures)):
				arm = self.addedArmatures[armIdx]
				armPoses[arm.name] = arm.getPose()
			
			pose = None
			lastGoodPose = None
			# add object node frames
			for nodeIndex in range(1, len(self.nodes)):
				# see if we're dealing with an object node
				#if self.nodes[nodeIndex].armIdx != -1: continue
				
				try:
					pose = armPoses[ self.nodes[nodeIndex].armName ]
					lastGoodPose = pose
				except:
					pose = lastGoodPose

				if isBlend:
					baseTransform = baseTransforms[nodeIndex]
				else:
					baseTransform = None
				# make sure we're not past the end of our action
				if frame < numFrameSamples:
					# let's pretend that everything matters, we'll remove the cruft later
					# this prevents us from having to do a second pass through the frames.
					loc, rot, scale = self.getPoseTransform(sequence, nodeIndex, curFrame, pose, baseTransform)
					sequence.frames[nodeIndex].append([loc,rot,scale])
				# if we're past the end, just duplicate the last good frame.
				else:
					loc, rot, scale = sequence.frames[nodeIndex][-1][0], sequence.frames[nodeIndex][-1][1], sequence.frames[nodeIndex][-1][2]
					sequence.frames[nodeIndex].append([loc,rot,scale])
			
			'''
			# add bone node frames
			# loop through each armature, we only want to call getPose once for each armature in the scene.			
			for armIdx in range(0, len(self.addedArmatures)):
				arm = self.addedArmatures[armIdx][0]
				pose = arm.getPose()
				print self.nodes
				# loop through each node for the current frame.
				for nodeIndex in range(1, len(self.nodes)):
					# since Armature.getPose() leaks memory in Blender 2.41, skip nodes not
					# belonging to the current armature to avoid having to call it unnecessarily.


					# see if we're dealing with an object node
					if self.nodes[nodeIndex].armIdx == -1: continue

					if self.nodes[nodeIndex].armIdx != armIdx and self.nodes[nodeIndex].armIdx != -1: continue


					if isBlend:
						baseTransform = baseTransforms[nodeIndex]
					else:
						baseTransform = None
					# make sure we're not past the end of our action
					print "frame=",frame
					print "numFrameSamples=",numFrameSamples
					if frame < numFrameSamples:
						# let's pretend that everything matters, we'll remove the cruft later
						# this prevents us from having to do a second pass through the frames.
						print "Sequence=",sequence
						print "nodeIndex=",nodeIndex
						print "curFrame=",curFrame
						print "pose=",pose
						print "baseTransform=",baseTransform
						print "parent node idx=",self.nodes[nodeIndex].parent
						loc, rot, scale = self.getPoseTransform(sequence, nodeIndex, curFrame, pose, baseTransform)
						print "loc=",loc
						print "rot=",rot
						print "scale=",scale
						sequence.frames[nodeIndex].append([loc,rot,scale])
					# if we're past the end, just duplicate the last good frame.
					else:
						loc, rot, scale = sequence.frames[nodeIndex][-1][0], sequence.frames[nodeIndex][-1][1], sequence.frames[nodeIndex][-1][2]
						sequence.frames[nodeIndex].append([loc,rot,scale])
						
			'''
		
		
		# if nothing was actually animated abandon exporting the action.
		if not (sequence.has_loc or sequence.has_rot or sequence.has_scale):
			Torque_Util.dump_writeWarning("Warning: Action has no keyframes, aborting export for this animation.")
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
		# but don't remove the last frame if the action is shorter than the overall sequence length :-)
		removeLast = removeLast and numFrameSamples == numOverallFrames
		if removeLast:
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

		return sequence, removeLast



	
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

		print "addSequenceVisibility called..."
		scene = Blender.Scene.GetCurrent()
		sequence.matters_vis = [False]*len(self.objects)

		# includes last frame
		numVisFrames = int((startFrame - endFrame) + 1)

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
				#print "#####  Writing IPO for frame:%2i (%f)" % (int(fr), IPOCurve[fr])
				#print "#####  Writing IPO Value:", IPOCurve[fr]				
				val = IPOCurve[int(fr)]
				if val > 1.0: val = 1.0
				elif val < 0.0: val = 0.0
				# Make sure we're still in the user define frame range.
				if fr <= endFrame:
					self.objectstates.append(ObjectState(val,0,0))
				# If we're past the user defined frame range, pad out object states
				# with copies of the good last frame state.
				else:
					val = IPOCurve[int(endFrame)]
					if val > 1.0: val = 1.0
					elif val < 0.0: val = 0.0
					self.objectstates.append(ObjectState(val,0,0))
							
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
	
