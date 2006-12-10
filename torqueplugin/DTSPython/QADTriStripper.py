'''
QADTriStripper.py
Copyright (c) 2006 - 2007 Joseph Greenawalt(jsgreenawalt@gmail.com)

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

'''
Quick and Dirty Triangle Stripper, uses a simple greedy heuristic.
'''

import copy
import re
import Torque_Util
try:
	from bisect import *
except:
	from pyBisect import *


def indent(string, spaces):
	p = re.compile('\n')
	block = "\n"
	for i in range(0, spaces):
		block += " "
	retVal = p.sub('\n    ',str(string))
	return retVal


class Edge:
	def __init__(self, A, B, triIndex):
		self.A = A
		self.B = B
		self.triIndex = triIndex
		self.trisSharing = []
	
	def __cmp__(self, other):
		if (self.A == other.A and self.B == other.B):
			return 0
		if (self.A < other.A):
			return -1
		if (self.A > other.A):
			return 1
		if (self.A == other.A) and (self.B < other.B):
			return -1
		else:
			return 1

	def reversed(self):
		rev = copy.copy(self)
		rev.A, rev.B = rev.B, rev.A
		return rev
	
	def __str__(self):
		retVal = "\nEdge:"
		retVal += "\n Vertex A:" + `self.A`
		retVal += "\n Vertex B:" + `self.B`
		retVal += "\n triIndex:" + `self.triIndex`
		return retVal

class Triangle:
	def __init__(self, a, b, c, triIndex):
		self.triIndex = triIndex
		self.vertIndex = []
		self.vertIndex.append(a)
		self.vertIndex.append(b)
		self.vertIndex.append(c)
		
		self.edge = []
		self.edge.append( Edge(self.vertIndex[0], self.vertIndex[1], triIndex) )
		self.edge.append( Edge(self.vertIndex[1], self.vertIndex[2], triIndex) )
		self.edge.append( Edge(self.vertIndex[2], self.vertIndex[0], triIndex) )
	
	def rotateVertOrder(self):		
		self.vertIndex[0], self.vertIndex[1], self.vertIndex[2] = self.vertIndex[1], self.vertIndex[2], self.vertIndex[0]
		self.edge[0], self.edge[1], self.edge[2] = self.edge[1], self.edge[2], self.edge[0]

	# rotates a triangle until the given edge is the last edge	
	def rotateEdgeToLast(self, otherEdge):		
		while(self.edge[2] != otherEdge):
			self.rotateVertOrder()
	
	def __str__(self):
		retVal = "\nTriangle:"
		retVal += "\n Edge 0:"
		retVal += indent(self.edge[0], 2)
		retVal += "\n Edge 1:"
		retVal += indent(self.edge[1], 2)
		retVal += "\n Edge 2:"
		retVal += indent(self.edge[2], 2)
		retVal += "\n triIndex:" + `self.triIndex`
		return retVal
		
class TriNode:
	
	def __init__(self, triID):
		self.Neighbours = []
		self.Degree = 0
		self.triID = triID
		self.usedInStrip = False
	
	def isNeighbour(self, tri):
		if tri.triID in self.Neighbours:
			return True
		else:
			return False

	def addNeighbour(self, node):
		# if the neighbor is not already added
		if not self.isNeighbour(node):
			# add each other to neighbors lists
			self.Neighbours.append(node.triID)
			node.Neighbours.append(self.triID)
			self.Degree += 1
			node.Degree += 1
			return True
		else:
			return False
	
	# node comparison is used for sorting nodes by degree (number of neighbours)
	def __cmp__(self, other):
		if len(self.Neighbours) == len(other.Neighbours):
			return 0
		if len(self.Neighbours) < len(other.Neighbours):
			return -1
		if len(self.Neighbours) > len(other.Neighbours):
			return 1
	

class TriGraph:
	def __init__(self, triList):
		self.edgeMap = []
		# first create a sorted list of edges to
		# assist in quickly creating a graph
		self.tris = triList
		self.createEdgeMap()
		# now that we have a sorted list of edges to 
		# play with, lets create our graph
		# create some nodes
		self.nodes = []
		for t in triList:
			self.nodes.append(TriNode(t.triIndex))			
		# hook up the nodes based on triangle connectivity
		self.mapAdjoingTris()
		# now we create another list of nodes sorted by degree (number of neighbours)
		self.sortedNodes = copy.copy(self.nodes)
		self.sortedNodes.sort()
	
	def createEdgeMap(self):
		for i in range (0, len(self.tris)):
			t = self.tris[i]
			self.edgeMap.append(t.edge[0])
			self.edgeMap.append(t.edge[1])
			self.edgeMap.append(t.edge[2])
		self.edgeMap.sort()
	
	def mapAdjoingTris(self):
		i = 0
		for edge in self.edgeMap:
			# see if any edges match this one
			idx = bisect_left(self.edgeMap, edge.reversed())
			if idx == len(self.edgeMap):
				i+=1
				continue
			otherEdge = self.edgeMap[idx]
			if otherEdge == edge.reversed():
				if  self.tris[otherEdge.triIndex].vertIndex[0] in self.tris[edge.triIndex].vertIndex\
				and self.tris[otherEdge.triIndex].vertIndex[1] in self.tris[edge.triIndex].vertIndex\
				and self.tris[otherEdge.triIndex].vertIndex[2] in self.tris[edge.triIndex].vertIndex:
					# if the two triangles share the same verts but are facing opposite directions,
					# treat them like they exist in separate universes.
					i+=1
					continue
				if self.nodes[edge.triIndex].addNeighbour(self.nodes[otherEdge.triIndex]):
					edge.trisSharing.append(otherEdge.triIndex)
					otherEdge.trisSharing.append(edge.triIndex)
			i += 1

	# gets the simulated current degree of a triangle strip during stripping.
	def getSimDegree(self, nodeID):
		node = self.nodes[nodeID]
		degree = node.Degree
		for idx in node.Neighbours:
			x = self.nodes[idx]
			if x.usedInStrip: degree -= 1
		return degree
	

class QADTriStripper:
	def __init__(self, maxStripSize = 6):
		#self.verts = verts
		self.verts = []
		self.faces = []
		self.triList = []
		self.completedStrips = []
		self.triangleStack = []
		self.graph = None
		self.strips = []
		self.maxStripSize = maxStripSize


	# create triangle strips
	def strip(self):	
		
		# convert the faces into a vertlist
		self.verts = []
		for f in self.faces:
			#print "Adding face: ", f
			#print "Adding face: ", f[0]
			if len(f[0]) > 3:
				raise "Too many verticies in primitive, not a triangle !!!"
			for v in f[0]:
				self.verts.append(v)
		# construct triangles
		for i in range(0, len(self.verts), 3):
			self.triList.append( Triangle(self.verts[i], self.verts[i+1], self.verts[i+2], len(self.triList)) )
		# create the graph
		self.graph = TriGraph(self.triList)

		
		# loop through the sorted node list and start building strips
		orphans = []
		i = 0
		for node in self.graph.sortedNodes:
			# continue on if this node is already part of a strip
			if node.usedInStrip: continue
			# continue on if the node has zero neighbours
			if self.graph.getSimDegree(node.triID) == 0:
				# add it to the list of orphan triangles, we'll later add
				# them as triangle primitives to the end of the mesh
				orphans.append(node.triID)
				continue
			# start a new strip
			self.MakeStrip(node)
			i += 1
		#add any left over triangles
		for orphan in orphans:
			self.strips.append([[],self.faces[orphan][1]])
			self.strips[-1][0].append(self.triList[orphan].vertIndex[0])
			self.strips[-1][0].append(self.triList[orphan].vertIndex[1])
			self.strips[-1][0].append(self.triList[orphan].vertIndex[2])
			
		Torque_Util.dump_writeln("    Created " + `len(self.strips)-len(orphans)` + " strips.")
		Torque_Util.dump_writeln("     with " + `len(orphans)` + " trianges left over.")

	
	def MakeStrip(self, node):
		# create a new strip, strips hold vertex indices
		self.strips.append([[],self.faces[node.triID][1]])
		# find the neighbour with the lowest degree that is not zero
		secondID = self.getLowestDegreeNeighbour(node)
		if secondID == -1:
			raise "Error Wil Robinson!"
			return
		secondNode = self.graph.nodes[secondID]
		# find the edge that the first and second triangle have in common
		commonEdge = self.getCommonEdge(node, secondNode)		
		# rotate the first triangle so that the correct edge is last
		self.triList[commonEdge.triIndex].rotateEdgeToLast(commonEdge)
		self.triList[commonEdge.triIndex].rotateVertOrder()		
		# add the current node to the strip
		self.strips[-1][0].append(self.triList[node.triID].vertIndex[0])
		self.strips[-1][0].append(self.triList[node.triID].vertIndex[1])
		self.strips[-1][0].append(self.triList[node.triID].vertIndex[2])
		# add the second node to the strip
		tri = self.triList[secondNode.triID]
		for v in tri.vertIndex:
			if not (v in  self.triList[node.triID].vertIndex):
				self.strips[-1][0].append(v)
		# setup for the main loop
		stripLen = 2
		node = secondNode
		clockwise = True
		# continue adding triangles to the strip until we have to stop
		while True:
			nextID = self.NextMove(node, clockwise)
			if clockwise == True: clockwise = False
			else: clockwise = True
			if nextID == -1:
				break
			oldNode = node
			oldTri = self.triList[node.triID]
			node = self.graph.nodes[nextID]	
			tri = self.triList[node.triID]
			for v in tri.vertIndex:
				if not (v in  self.triList[oldNode.triID].vertIndex):
					self.strips[-1][0].append(v)
					stripLen += 1
			if stripLen >= self.maxStripSize:
				return
		return
	
	def getLowestDegreeNeighbour(self, node):
		node.usedInStrip = True
		bestRank = 1024
		bestID = -1
		for id in node.Neighbours:
			neighbour = self.graph.nodes[id]
			# continue on if this node is already part of a strip
			if neighbour.usedInStrip: continue			
			degree = self.graph.getSimDegree(id)
			# did we find a new best rank among neighbours?
			# (lower is better)
			if degree <= bestRank:
				# store the best one
				bestRank = degree
				bestID = neighbour.triID
		if bestRank == 1024:
			return -1
		else:
			return bestID

	# returns the common edge of the first and second node,
	# the first node's edge is the actual one returned.
	def getCommonEdge(self, node1, node2):
		found = False
		for i in range(0,3):
			for j in range(0,3):
				if self.triList[node1.triID].edge[i].reversed() == self.triList[node2.triID].edge[j]:
					found = True
					break
			if found == True: break
		if found == False: raise "getCommonEdge COULD NOT FIND A COMMON EDGE!!!!"
		return self.triList[node1.triID].edge[i]

	def NextMove(self, node, clockwise):
		node.usedInStrip = True
		if clockwise == True:
			fakeEdge = Edge(self.strips[-1][0][len(self.strips[-1][0])-2], self.strips[-1][0][len(self.strips[-1][0])-1], -1)
		else:
			fakeEdge = Edge(self.strips[-1][0][len(self.strips[-1][0])-1], self.strips[-1][0][len(self.strips[-1][0])-2], -1)
		for id in node.Neighbours:
			#print "Looping through neighbours..."
			neighbour = self.graph.nodes[id]
			# continue on if this node is already part of a strip
			if neighbour.usedInStrip: continue
			
			for edge in self.triList[neighbour.triID].edge:
				if fakeEdge == edge:
					return neighbour.triID
		return -1
	
	def __str__(self):
		retVal = "Triangle Strips:"
		for s in self.strips:
			retVal += "\n  Strip:"
			for v in self.strips:
				retVal += indent(v, 2)
		return retVal


