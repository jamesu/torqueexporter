'''
Dts.Mesh_Blender.py

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

import Blender
from Blender import NMesh

'''
   Mesh Class (Blender Export)
'''
#-------------------------------------------------------------------------------------------------

class BlenderMesh(DtsMesh):
	def __init__(self, shape, msh,  rootBone, scaleFactor, matrix, isCollision=False, useLists = False):
		DtsMesh.__init__(self)
		#self.vertsIndexMap = []		# Map of TexCoord index <> Vertex index map
		self.bVertList = [] # list of blender mesh vertex indices ordered by value, for fast searching
		self.dVertList = [] # list containing lists of dts vertex indices, the outer list elements correspond to the bVertList element in the same position.
		self.mainMaterial = None	# For determining material ipo track to use for ObjectState visibility animation
		ignoreDblSided = False # set to true if you want to ignore double sided meshes
		
		self.weightDictionary = self.createWeightDictionary(msh);
		materialGroups = []
		for i in range (0, len(msh.materials)):
			materialGroups.append([])
		if len(materialGroups) == 0: materialGroups = [[]]

		# if we're dealing with a collision mesh, init differently
		if isCollision:
			self.initColMesh(shape, msh,  rootBone, scaleFactor, matrix)
			return
		

		# First, sort faces by material
		for face in msh.faces:
			if len(face.v) < 3:
				continue # skip to next face
			#print "DBG: face idx=%d" % face.materialIndex
			materialGroups[face.mat].append(face)
		
		# Then, we can add in batches
		for group in materialGroups: 
			self.bVertList = []
			self.dVertList = []
			# Insert Polygons

			# if we're using triangle lists, insert one primitive first since that's all we'll need.
			if useLists:
				# Insert primitive
				pr = Primitive(len(self.indices), 3, 0)
				pr.matindex = pr.Triangles | pr.Indexed
				# clear our duplicate vertex search structures
				#if not isCollision:
				#	self.bVertList = []
				#	self.dVertList = []
			
			# Create primitive
			#pr = Primitive(len(self.indices), 3, 0)
			#pr.matindex = pr.Triangles | pr.Indexed

			for face in group:
				if len(face.v) < 3:
					continue # skip to next face

				# if we're not using triangle lists, insert one primitive per face
				if not useLists:
					# Insert primitive
					pr = Primitive(len(self.indices), 3, 0)
					pr.matindex = pr.Triangles | pr.Indexed
				
				useSticky = False
				# Find the image associated with the face on the mesh, if any
				if msh.hasFaceUV:
					imageName = face.image.getName().split(".")[0]
					matIndex = shape.materials.findMaterial(imageName)
					if matIndex == None: matIndex = shape.addMaterial(imageName)
					if matIndex == None: matIndex = pr.NoMaterial
					if matIndex != pr.NoMaterial: 
						self.mainMaterial = matIndex
						#useSticky = shape.materials.get(matIndex).sticky
				else:
					matIndex = pr.NoMaterial # Nope, no material
				pr.matindex |= matIndex

				'''
				if len(msh.materials) > 0 and face.mat < len(msh.materials):
					# Also, use sticky coords if we were asked to
					matIndex = shape.materials.findMaterial(msh.materials[face.mat].getName())
					if matIndex == None: matIndex = shape.addMaterial(msh.materials[face.mat])
					if matIndex == None: matIndex = pr.NoMaterial
					if matIndex != pr.NoMaterial: 
						self.mainMaterial = matIndex
						useSticky = shape.materials.get(matIndex).sticky
				else:
					matIndex = pr.NoMaterial # Nope, no material
				pr.matindex |= matIndex
				'''
				
				# we've got a quad
				if (len(face.v) > 3):
					# convert the quad into two triangles
					# first triangle
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))

					# if we're not using triangle lists, first insert the primitive for the first triangle
					if not useLists: self.primitives.append(pr)

					# Duplicate first triangle in reverse order if doublesided
					if ((msh.mode & NMesh.Modes.TWOSIDED) or (face.mode & NMesh.FaceModes.TWOSIDE)) and not ignoreDblSided:
						#for i in range((len(self.indices)-1),(len(self.indices)-4),-1):
						#	self.indices.append(self.indices[i])
						if not useLists:
							#for i in range((pr.firstElement+pr.numElements)-1,pr.firstElement-1,-1):
							for i in range((pr.firstElement+pr.numElements)-1,pr.firstElement-1,-1):
								self.indices.append(self.indices[i])
							# insert a new primitive for the back facing triangle
							self.primitives.append(Primitive((pr.firstElement+pr.numElements),pr.numElements,pr.matindex))
						else:
							for i in range((len(self.indices)-1),(len(self.indices)-4),-1):
								self.indices.append(self.indices[i])
					
					if not useLists: pr = Primitive(len(self.indices), 3, pr.matindex)							

					# second triangle
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,3, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))						
				else:
					# add the triangle normally.
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))
					
				if not useLists:
					self.primitives.append(pr)					
						
				# Duplicate triangle in reverse order if doublesided
				if ((msh.mode & NMesh.Modes.TWOSIDED) or (face.mode & NMesh.FaceModes.TWOSIDE)) and not ignoreDblSided: 
					#for i in range((len(self.indices)-1),(len(self.indices)-4),-1):
					#	self.indices.append(self.indices[i])
					if not useLists:
						#for i in range((pr.firstElement+pr.numElements)-1,pr.firstElement,-1):
						for i in range((pr.firstElement+pr.numElements)-1,pr.firstElement-1,-1):
							self.indices.append(self.indices[i])
						self.primitives.append(Primitive(pr.firstElement+pr.numElements,pr.numElements,pr.matindex))
					else:
						for i in range((len(self.indices)-1),(len(self.indices)-4),-1):
							self.indices.append(self.indices[i])

			if useLists:
				# Finally add the primitive
				pr.numElements = (len(self.indices) - pr.firstElement) #-1
				self.primitives.append(pr)


			# Finally add primitive
			#pr.numElements = (len(self.indices) - pr.firstElement) #-1			
			#if pr.numElements != 0: self.primitives.append(pr)

		
		# Determine shape type based on vertex weights
		if len(self.bindex) <= 1:
			self.mtype = self.T_Standard
		else:
			if not self.mtype == self.T_Standard:
				self.mtype = self.T_Standard # default
				for v in self.bindex:
					if v != self.bindex[0]:
						self.mtype = self.T_Skin
						break

		# vertsPerFrame is related to the vertex animation code
		self.vertsPerFrame = len(self.verts) # set verts in a frame

		# Final stuff...
		# Total number of frames. For a non animated mesh, this will always be 1
		if self.vertsPerFrame != 0: self.numFrames = len(self.verts) / self.vertsPerFrame
		else: self.numFrames = 0

		# Mesh parent
		self.parent = -1

		# Calculate Limits
		self.calculateBounds()
		self.calculateCenter()
		self.calculateRadius()

		del self.bVertList
		del self.dVertList

		
	def initColMesh(self, shape, msh,  rootBone, scaleFactor, matrix):
		# Insert Polygons
		for face in msh.faces:
			if len(face.v) < 3:
				continue # skip to next face

			# Insert primitive
			pr = Primitive(len(self.indices), 3, 0)
			pr.matindex = pr.Triangles | pr.Indexed
			useSticky = False
			# no material for collision meshes
			pr.matindex |= pr.NoMaterial 
			if (len(face.v) > 3):
				# convert the quad into two triangles
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky, True))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky, True))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky, True))

				# add the first triangle to the primitives and duplicate if doublesided.
				self.primitives.append(pr)

				# second triangle
				pr = Primitive(len(self.indices), 3, pr.matindex)
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,3, useSticky, True))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky, True))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky, True))						
			else:
				# add the triangle normally.
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky, True))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky, True))
				self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky, True))

			# Finally add primitive
			self.primitives.append(pr)

		self.mtype = self.T_Standard

		# vertsPerFrame is related to the vertex animation code
		self.vertsPerFrame = len(self.verts) # set verts in a frame

		# Final stuff...
		# Total number of frames. For a non animated mesh, this will always be 1
		if self.vertsPerFrame != 0: self.numFrames = len(self.verts) / self.vertsPerFrame
		else: self.numFrames = 0
		#self.numFrames = len(self.verts) / self.vertsPerFrame

		# Mesh parent
		self.parent = -1

		# Calculate Limits
		self.calculateBounds()
		self.calculateCenter()
		self.calculateRadius()

		del self.bVertList
		del self.dVertList
		
	def __del__(self):
		DtsMesh.__del__(self)

	
	def createWeightDictionary(self, mesh):
		weightDictionary = {}
		boneList = []
		for arm in Blender.Armature.Get().values():
			for b in arm.bones.values():
				boneList.append(b.name)

		for i in range(len(mesh.verts)):
			weightDictionary[i] = []

		for group in mesh.getVertGroupNames():
			# ignore groups that have no corresponding bone.
			if not (group in boneList): continue
			for vert in mesh.getVertsFromGroup(group, 1):
			    	index, weight = vert[0], vert[1]
			    	weightDictionary[index].append((group, weight))
				
		return weightDictionary
		
	def appendVertex(self, shape, msh, rootBone, matrix, scaleFactor, face, faceIndex, useSticky, isCollision = False):
		# Use Face coords if requested
		if not useSticky:
			# The face may not have texture coordinate, in which case we assign 0,0
			if len(face.uv) < faceIndex + 1:
				texture = Vector2(float(0.0),float(0.0))
			else:
				texture = Vector2(face.uv[faceIndex][0], 1.0 - face.uv[faceIndex][1])
				
		# Add sticky coords *if* they are available
		elif msh.hasVertexUV():
			texture = Vector2(msh.verts[face.v[faceIndex].index].uvco[0],msh.verts[face.v[faceIndex].index].uvco[1])
		# We were supposed to use sticky coords, but none were found
		else:
			texture = Vector2(float(0.0),float(0.0))
		
		# Compute vert normals
		vert = msh.verts[face.v[faceIndex].index]
		if face.smooth:
			#normal = matrix.passVector(Vector(vert.no[0], vert.no[1], vert.no[2]))
			normal = Torque_Math.Matrix3x3(matrix).transpose().inverse().passVector(Vector(vert.no[0], vert.no[1], vert.no[2]))
		else:
			#normal = matrix.passVector(Vector(face.no[0], face.no[1], face.no[2]))
			normal = Torque_Math.Matrix3x3(matrix).transpose().inverse().passVector(Vector(face.no[0], face.no[1], face.no[2]))
		normal.normalize()
		
		# See if the vertex/texture/normal combo already exists..
		bvIndex = face.v[faceIndex].index
		# if the bVertList already contains this blender vert,
		sharedVertsIdx = bisect_left(self.bVertList, bvIndex)
		if sharedVertsIdx < len(self.bVertList) and self.bVertList[sharedVertsIdx] == bvIndex:
			# check the already added dts verts to if this one even needs to be added				
			for dVert in self.dVertList[sharedVertsIdx]:
				# See if the texture coordinates and normals match up.
				tx = self.tverts[dVert]
				no = self.normals[dVert]
				if (tx.eqDelta(texture, 0.0001) and no.eqDelta(normal, 0.001)) or isCollision:
					# use the existing dts vert with the same tex coords and normal
					return dVert
				


		'''
			Add new mesh vert and texture
			Get Vert in world coordinates using object matrix
			Texture needs to be flipped to work in torque
		'''
		
		nvert = matrix.passPoint(Vector(vert.co[0], vert.co[1], vert.co[2])) * scaleFactor
		vindex = len(self.verts)
		self.verts.append(nvert)
		self.tverts.append(texture)		
		
		# see if the blender vertex is already in our bVertList
		pos = bisect_left(self.bVertList, bvIndex)
		if pos < len(self.bVertList) and self.bVertList[pos] == bvIndex:
			# if it is, just add the new dts vert to the end of it's corresponding dVertList entry		
			self.dVertList[pos].append(len(self.verts)-1)
		else:
			# this is the first time we've seen this blender vert
			# insert the bVert into the correct location in our bVertList
			self.bVertList.insert(pos, bvIndex)
			#insort_left(self.bVertList, bvIndex)
			# insert a new list (containing the current dts vert) into the dVertList
			# at the corresponding location.
			self.dVertList.insert(pos, [len(self.verts)-1])
			

		# Add vert Normals
		self.normals.append(normal)
		self.enormals.append(self.encodeNormal(normal))

		# Add bone weights
		bone, weight = -1, 1.0
		influences = []
		weights = self.weightDictionary[vert.index]
		for weight in weights:
			# group name and weight
			influences.append([weight[0], weight[1]])

		if len(influences) > 0:
			# Total weights should add up to one, so we need
			# to normalize the weights assigned in blender.
			total = 0
			for inf in influences:
				total += inf[1]

			for inf in influences:
				# Add the vertex influence. Any number can be added,
				# but they must be ordered by vertex.
				self.vindex.append(vindex)
				bone, weight = shape.getNodeIndex(inf[0]), inf[1]
				if bone >= 0:
					self.bindex.append(self.getVertexBone(bone))
				else:
					self.bindex.append(self.getVertexBone(rootBone))
				# getVertexBone() also adds the nodeTransform(matrixF),
				# and node Index (if not already on list)
				self.vweight.append(weight / total)
		return vindex
		
	def setBlenderMeshFlags(self, names):
		# Look through elements in names
		for n in names:
			if n == "BB":
				self.flags |= DtsMesh.Billboard
			elif n == "BBZ":
				self.flags |= DtsMesh.Billboard | DtsMesh.BillboardZ
			elif n == "SORT":
				self.mtype = self.T_Sorted

