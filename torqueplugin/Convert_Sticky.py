'''
Convert_Sticky.py

Copyright (c) 2003 - 2006 James Urquhart(j_urquhart@btinternet.com)

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
# Converts Sticky UV Coordinates to Mesh Face coordinates
'''
In essence, blender's sticky coordinates are Per Vertex UV coordinates - just like what torque uses.
In order to simplify importing of dts aswell as 3ds, this script handles converting these coordinates
to Per Face UV coordinates.
'''


def convertObject(object):
	msh = object.getData()
	
	if not msh.hasVertexUV(): return
	if not msh.hasFaceUV():
		msh.hasFaceUV(1)
		msh.update()

	# Loop through faces
	for f in msh.faces:
		for v in range(0, len(f.v)):
			# Get face vert
			vert = f.v[v]
			# Find mesh verts that are identical
			# and get corresponding uvco's
			#for vt in msh.verts:
			#	if vt.index == vert.index:
			
			# Sticky coords seem to have
			# odd texture coords. Lets convert them
			# to fit in blenders 0-1.0 bounds
			v1 = (vert.uvco[0])
			v2 = (-((vert.uvco[1]))) +1
			f.uv[v] = (v1 , v2)
	msh.hasVertexUV(0)
	msh.update()

if __name__ == "__main__":
	for o in Blender.Object.Get():
		if o.getType() == "Mesh": convertObject(o)
