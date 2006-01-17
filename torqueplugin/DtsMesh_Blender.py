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
	def __init__(self, shape, msh,  rootBone, scaleFactor, matrix, triStrips=False):
		DtsMesh.__init__(self)
		self.vertsIndexMap = []		# Map of TexCoord index <> Vertex index map
		self.mainMaterial = None	# For determining material ipo track to use for ObjectState visibility animation
		self.weightDictionary = self.createWeightDictionary(msh);
		# Joe : this appears to be causing all faces to be added twice!
		#materialGroups = [[]]*(len(msh.materials)+1)
		materialGroups = [[]]
		for i in range (0, len(msh.materials)):
			materialGroups.append([])
		
		
		# First, sort faces by material
		for face in msh.faces:
			if len(face.v) < 3:
				continue # skip to next face
			#print "DBG: face idx=%d" % face.materialIndex
			materialGroups[face.mat].append(face)
		
		# Then, we can add in batches
		for group in materialGroups: 
			# Insert Polygons
			for face in group:
				if len(face.v) < 3:
					continue # skip to next face

				# Insert primitive
				pr = Primitive(len(self.indices), 3, 0)
				pr.matindex = pr.Strip | pr.Indexed
				
				useSticky = False
				# Find the image associated with the face on the mesh, if any
				if len(msh.materials) > 0:
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
				
				# Add an extra element if using triangle strips, else add a new primitive
				if (len(face.v) > 3) and (triStrips == False):
					pr.numElements = 4
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,3, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))
				else:
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,1, useSticky))
					self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))
					
					if len(face.v) > 3:
						self.primitives.append(pr)
						
						# Duplicate primitive in reverse order if doublesided
						if (msh.mode & NMesh.Modes.TWOSIDED) or (face.mode & NMesh.FaceModes.TWOSIDE):
							for i in range(1, pr.numElements+1):
								self.indices.append(self.indices[-i])
							self.primitives.append(Primitive(pr.firstElement+pr.numElements,pr.numElements,pr.matindex))
					
						pr = Primitive(len(self.indices), 3, pr.matindex)
						self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,3, useSticky))
						self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,2, useSticky))
						self.indices.append(self.appendVertex(shape,msh,rootBone,matrix,scaleFactor,face,0, useSticky))
				
				# Finally add primitive
				self.primitives.append(pr)
						
				# Duplicate primitive in reverse order if doublesided
				if (msh.mode & NMesh.Modes.TWOSIDED) or (face.mode & NMesh.FaceModes.TWOSIDE):
					for i in range(1, pr.numElements+1):
						self.indices.append(self.indices[-i])
					self.primitives.append(Primitive(pr.firstElement+pr.numElements,pr.numElements,pr.matindex))

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
		self.numFrames = len(self.verts) / self.vertsPerFrame

		# Mesh parent
		self.parent = -1

		# Calculate Limits
		self.calculateBounds()
		self.calculateCenter()
		self.calculateRadius()

		del self.vertsIndexMap
		
	def __del__(self):
		DtsMesh.__del__(self)

	
	def createWeightDictionary(self, mesh):
		weightDictionary = {}
		for i in range(len(mesh.verts)):
			weightDictionary[i] = []
		for group in mesh.getVertGroupNames():
			for vert in mesh.getVertsFromGroup(group, 1):
			    	index, weight = vert[0], vert[1]
			    	weightDictionary[index].append((group, weight))
		return weightDictionary
		
	def appendVertex(self, shape, msh, rootBone, matrix, scaleFactor, face, faceIndex, useSticky):
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

		# See if the vertex/texture combo already exists..
		bvIndex = face.v[faceIndex].index
		for vi in range(0,len(self.vertsIndexMap)):
			if bvIndex == self.vertsIndexMap[vi]:
				# See if the texture coordinates match up.
				tx = self.tverts[vi]
				if tx[0] == texture[0] and tx[1] == texture[1]:
					return vi

		'''
			Add new mesh vert and texture
			Get Vert in world coordinates using object matrix
			Texture needs to be flipped to work in torque
		'''
		vert = msh.verts[face.v[faceIndex].index]
		nvert = matrix.passPoint(Vector(vert.co[0], vert.co[1], vert.co[2])) * scaleFactor
		vindex = len(self.verts)
		self.verts.append(nvert)
		self.tverts.append(texture)
		self.vertsIndexMap.append(bvIndex)

		# Add vert Normals
		normal = Vector(vert.no[0], vert.no[1], vert.no[2])
		#normal = matrix.passPoint(Vector(vert.no[0], vert.no[1], vert.no[2]))
		#normal.normalize()
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

