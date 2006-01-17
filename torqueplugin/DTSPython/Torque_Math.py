'''
Torque_Math.py

Copyright (c) 2005 - 2006 James Urquhart(j_urquhart@btinternet.com)

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and toMathutils
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

import struct, math
from struct import *

#############################
# Torque Game Engine
# ---------------------------------
# Torque Utility Classes for Python
#############################

#Notes:
'''
- Code taken from various sources; See Credits.
- Acclerator interfaces available
	* Blender
	* None
- Accelerated classes
	* Vector2
	* Vector
	* Vector4
	* Quaternion
	* MatrixF
'''

try:
	# TODO: fix. Blender interface does not currently work correctly
	import BlFender
	accelerator = "BLENDER"
except:
	accelerator = None

if accelerator == "BLENDER":
	# Vector class (3 members)
	class Vector:
		def __init__(self, x=0, y=0, z=0):
			self.object = Blender.Mathutils.Vector([x,y,z])
		def __del__(self):
			del self.object
		def __getitem__(self, key):
			if key == 0: return self.object.x
			elif key == 1: return self.object.y
			elif key == 2: return self.object.z
			else: return 0
		def __setitem__(self, key, value):
			if key == 0: self.object.x = value
			elif key == 1: self.object.y = value
			elif key == 2: self.object.z = value
		def __neg__(self):
			res = Vector(self.object.x, self.object.y, self.object.z)
			res.object.negate()
			return res
		def __add__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z)
			res.object += other.object
			return res
		def __sub__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z)
			res.object -= other.object
			return res
		def __mul__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z)
			res.object *= other
			return res
		def __div__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z)
			res.object /= other
			return res
		def __eq__(self, other):
			return (self.object == other.object)
		def x(self):
			return self.object.x
		def y(self):
			return self.object.y
		def z(self):
			return self.object.z
		def mag(self):
			return self.length()
		def dot(self, other):
			return self.object.x * other[0] + self.object.y * other[1] + self.object.z * other[2]
		def midpoint(self, other):
			return Vector(
			((other[0] - self.object.x)/2 + self.object.x),
			((other[1] - self.object.y)/2 + self.object.y),
			((other[2] - self.object.z)/2 + self.object.z))
		def length(self):
			return self.object.length
		def cross(self, other):
			res = Vector()
			res[0] = (self.object.y * other[2]) - (self.object.z * other[1])
			res[1] = (self.object.z * other[0]) - (self.object.x * other[2])
			res[2] = (self.object.x * other[1]) - (self.object.y * other[0])
			return res
		def normalize(self):
			# Make Vector Length 1
			#      V
			# U = ---
			#     |V|
			return self / self.length()
		# I/O
		def read(self, fs):
			self.object.x, self.object.y, self.object.z = struct.unpack('<fff', fs.read(calcsize('<fff')))
		def write(self, fs):
			fs.write(struct.pack('<fff', [self.object.x,self.object.y,self.object.z]))

	# Vector Class (4 members)
	class Vector4(Vector):
		def __init__(self, x=0, y=0, z=0, w=0):
			self.object = Blender.Mathutils.Vector([x,y,z,w])
		def __del__(self):
			del self.object
		def __getitem__(self, key):
			if key == 0: return self.object.x
			elif key == 1: return self.object.y
			elif key == 2: return self.object.z
			elif key == 3: return self.object.w
			else: return 0
		def __setitem__(self, key, value):
			if key == 0: self.object.x = value
			elif key == 1: self.object.y = value
			elif key == 2: self.object.z = value
			elif key == 3: self.object.w = value
		def __neg__(self):
			res = Vector(self.object.x, self.object.y, self.object.z, self.object.w)
			res.object.negate()
			return res
		def __add__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z, self.object.w)
			res.object += other.object
			return res
		def __sub__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z, self.object.w)
			res.object -= other.object
			return res
		def __mul__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z, self.object.w)
			res.object *= other
			return res
		def __div__(self, other):
			res = Vector(self.object.x, self.object.y, self.object.z, self.object.w)
			res.object /= other
			return res
		def __eq__(self, other):
			return (self.object == other.object)
		def x(self):
			return self.object.x
		def y(self):
			return self.object.y
		def z(self):
			return self.object.z
		def w(self):
			return self.object.w
		def midpoint(self, other):
			r = Vector(
			((other[0] - self.object.x)/2 + self.object.x)
			((other[1] - self.object.y)/2 + self.object.y)
			((other[2] - self.object.z)/2 + self.object.z)
			((other[3] - self.object.w)/2 + self.object.w)
			)
			return r
		def length(self):
			return self.object.length
		# I/O
		def read(self, fs):
			self.object.x, self.object.y, self.object.z, self.object.w = struct.unpack('<fff', fs.read(calcsize('<ffff')))
		def write(self, fs):
			fs.write(struct.pack('<ffff', [self.object.x,self.object.y,self.object.z, self.object.w]))

	# Vector Class (2 members)
	class Vector2(Vector):
		def __init__(self, x=0, y=0):
			self.object = Blender.Mathutils.Vector([x,y])
		def __del__(self):
			del self.object
		def __getitem__(self, key):
			if key == 0: return self.object.x
			elif key == 1: return self.object.y
			else: return 0
		def __setitem__(self, key, value):
			if key == 0: self.object.x = value
			elif key == 1: self.object.y = value
		def __neg__(self):
			res = Vector2(self.object.x, self.object.y)
			res.object.negate()
			return res
		def __add__(self, other):
			res = Vector2(self.object.x, self.object.y)
			res.object += other.object
			return res
		def __sub__(self, other):
			res = Vector2(self.object.x, self.object.y)
			res.object -= other.object
			return res
		def __mul__(self, other):
			res = Vector2(self.object.x, self.object.y)
			res.object *= other
			return res
		def __div__(self, other):
			res = Vector2(self.object.x, self.object.y)
			res.object /= other
			return res
		def x(self):
			return self.object.z
		def y(self):
			return self.object.z
		def mag(self):
			return self.length()
		def midpoint(self, other):
			r = Vector(
			((other[0] - self.object.x)/2 + self.object.x)
			((other[1] - self.object.y)/2 + self.object.y)
			)
			return r
		def length(self):
			return self.object.length

	# Quaternion Class (4 members)
	class Quaternion(Vector4):
		def __init__(self, x=0, y=0, z=0, w=0):
			self.object = Blender.Mathutils.Quaternion([x,y,z,w])
		def __del__(self):
			del self.object
		def __mul__(self, other): # against another quat
			res = Quaternion()
			res.object =  Blender.Mathutils.CrossQuats(self.object, other.object)
			return res
		def conjugate(self):
			ret = Quaternion(self.object.x, self.object.y, self.object.z, self.object.w)
			ret.object.conjugate()
			return ret
		def inverse(self):
			res = Quaternion(self.object.x, self.object.y, self.object.z, self.object.w)
			res.object.inverse()
			return res
		def vecmul(self, other): # Vector Version
			result = Quaternion()
			# iterate through the members
			for i in range(len(self.members)):
				# multiply by the val stored in other
				result[i] = self[i] * float(other)
			return result
		def __neg__(self):
			res = Quaternion()
			for m in range(0, len(self.members)):
				res[m] = -self[m]
			return res
		def __div__(self, other):
			res = Quaternion()
			res.object = self.object / other
			return res
		def toMatrix(self):
			mat = MatrixF()
			mat.object = self.object.toMatrix()
			mat.object.resize4x4()
			return mat
		def fromMatrix(self, m):
			res = Quaternion()
			res.object = m.object.toQuat()
			return res			
		def fromAxis(self, ax, an):
			# Create from an axis and angle
			res = Quaternion()
			res.object = Mathutils.Quaternion(ax, an)
			return res
		def angleBetween(self, quat):
			# Get angle between quat's. Returns float
			return acos(self.x()*quat.x() + self.y()*quat.y() + self.z()*quat.z() + self.w()*quat.w())
		def toQuat16(self):
			return Quat16([self.object.x, self.object.y, self.object.z, self.object.w])
		def apply(self, v):
			# Apply. Returns a point(or rather Vector).
			# Torque uses column vectors, which means quaternions
			# rotate backwards from what you might normally expect.
			q = Quaternion(v.x(), v.y(), v.z(), 0)
			r = self.conjugate() * q * self
			return Vector(r.x(), r.y(), r.z())

	# The Matrix Class
	class MatrixF:
		'''
			Blender version of MatrixF
			
			This is a bit tricky since torque's matrices are arranged by rows where blenders is the opposite.
		'''
		
		def __init__(self, dat=None):
			if dat == None:
				self.object = Blender.Mathutils.Matrix(
				[0.0, 0.0, 0.0, 0.0],
				[0.0, 0.0, 0.0, 0.0],
				[0.0, 0.0, 0.0, 0.0],
				[0.0, 0.0, 0.0, 0.0])
			else:
				self.object = Blender.Mathutils.Matrix(
				[dat[0],  dat[1],  dat[2],  dat[3]],
				[dat[4],  dat[5],  dat[6],  dat[7]],
				[dat[8],  dat[9],  dat[10], dat[11]],
				[dat[12], dat[13], dat[14], dat[15]])
		def __del__(self):
			del self.object
		def setData(self, dat):
			self.members = dat
		def __getitem__(self, key):
			bin = int(key) / 4
			return self.object[bin][bin*4]
		def __setitem__(self, key, value):
			bin = int(key) / 4
			self.object[bin][bin*4] = value
		def get(self, x, y):
			# x = row, y = col
			return self.object[x][y]
		def set(self, x, y, val):
			# x = row, y = col
			self.object[x][y] = val
		def identity(self):
			return MatrixF(
			[1.0, 0.0, 0.0, 0.0,
			0.0, 1.0, 0.0, 0.0,
			0.0, 0.0, 1.0, 0.0,
			0.0, 0.0, 0.0, 1.0])
		def transpose(self):
			result = self.copy()
			result.object.transpose()
			return result
		def getCol(self, no):
			result = []
			for r in range(0, 4):
				result.append(self.get(r, no))
			return result
		def setCol(self, no, col):
			for r in range(0, 4):
				self.set(r, no, col[r]) # self.members[(x*4)+y] = val
		def setRow(self, no, row):
			for r in range(0, 4):
				self.set(no, r, row[r])
		def getRow(self, no):
			result = []
			for r in range(0, 4):
				result.append(self.get(no, r))
			return result
		def mul(self, vect):
			res = Vector4()
			for r in range(0, 4):
				cell = self.get(r, 0) * vect[0]
				for e in range(0, 4):
					cell += self.get(r, e) * vect[e]
				res[r] = cell
			return res
		def xVector4(self, vect):
			result = Vector4(
			(self.object[0][0]*vect[0] + self.object[0][1]*vect[1] + self.object[0][2]*vect[2] + self.object[0][3]*vect[3]) # r1 
			(self.object[1][0]*vect[0] + self.object[1][1]*vect[1] + self.object[1][2]*vect[2] + self.object[1][3]*vect[3]) # r2
			(self.object[2][0]*vect[0] + self.object[2][1]*vect[1] + self.object[2][2]*vect[2] + self.object[2][3]*vect[3]) # r3
			(self.object[3][0]*vect[0] + self.object[3][1]*vect[1] + self.object[4][2]*vect[2] + self.object[3][3]*vect[3])) # r4
			return result
		def passPoint(self, point):
			return Vector(point[0] * self.get(0, 0) + point[1] * self.get(1, 0) + point[2] * self.get(2, 0) + self.get(3, 0),
				point[0] * self.get(0, 1) + point[1] * self.get(1, 1) + point[2] * self.get(2, 1) + self.get(3, 1),
				point[0] * self.get(0, 2) + point[1] * self.get(1, 2) + point[2] * self.get(2, 2) + self.get(3, 2))
		def passVector(self, vec):
			return Vector(vec[0] * self.get(0, 0) + vec[1] * self.get(1, 0) + vec[2] * self.get(2, 0),
				vec[0] * self.get(0, 1) + vec[1] * self.get(1, 1) + vec[2] * self.get(2, 1),
				vec[0] * self.get(0, 2) + vec[1] * self.get(1, 2) + vec[2] * self.get(2, 2))
		def determinant(self):
			return self.object.determinant()
		def inverse(self):
			return self.invert()
		def __mul__(self, a):
			result = self.copy()
			result.object = self.object * a.object
			return result
		def rotate(self, axis, angle):
			result = MatrixF()
			result.object = Blender.Mathutils.RotationMatrix(float(angle), 4, "r", axis.object)
			return result
		def translate_matrix(self, vec):
			result = self.copy()
			result.object = Blender.Mathutils.CopyMat(self.object)
			result[3][0] += vec[0]
			result[3][0] += vec[1]
			result[3][0] += vec[2]
			return result
		def scale_matrix(self, vec):
			result = self.copy()
			result.object = Blender.Mathutils.CopyMat(self.object)
			result[0][0] *= vec[0]
			result[0][1] *= vec[1]
			result[0][2] *= vec[2]
			result[1][0] *= vec[0]
			result[1][1] *= vec[1]
			result[1][2] *= vec[2]
			result[2][0] *= vec[0]
			result[2][1] *= vec[1]
			result[2][2] *= vec[2]
			result[3][0] *= vec[0]
			result[3][1] *= vec[1]
			result[3][2] *= vec[2]
			return result
		def copy(self):
			result = MatrixF()
			result.object = Blender.Mathutils.CopyMat(self.object)
			return result
		def invert(self):
			result = self.copy()
			result.object.invert()
			return result
		def mprint(self):
			for x in range(0, 4):
				print "| %f %f %f %f |" % (self.get(x, 0), self.get(x,1), self.get(x,2), self.get(x,3))
else:
	# Vector class (3 members)
	class Vector:
		def __init__(self, x=0, y=0, z=0):
			self.members = [float(x), float(y), float(z)]
		def __del__(self):
			del self.members
		def __getitem__(self, key):
			if key > (len(self.members)-1):
				return 0
			return(self.members[key])
		def __setitem__(self, key, value):
			self.members[key] = value
		def __neg__(self):
			return Vector(
				-float(self[0]),
				-float(self[1]),
				-float(self[2]))
		def __add__(self, other):
			return Vector(
				float(self[0]) + float(other[0]),
				float(self[1]) + float(other[1]),
				float(self[2]) + float(other[2]))
		def __sub__(self, other):
			return Vector(
				float(self[0]) - float(other[0]),
				float(self[1]) - float(other[1]),
				float(self[2]) - float(other[2]))
		def __mul__(self, other):
			return Vector(
				self[0] * float(other),
				self[1] * float(other),
				self[2] * float(other))
		def __div__(self, other):
			result = Vector()
			# iterate through the members
			for i in range(len(self.members)):
				# divide by the val stored in other
				if self[i] != 0:
					result[i] = self[i] / float(other)
				else:
					result[i] = .0
			return result
		def __eq__(self, other):
			if len(other.members) != len(self.members):
				return False
			for i in range(0, len(self.members)):
				if other.members[i] != self.members[i]:
					return False
			return True
		def x(self):
			return self.members[0]
		def y(self):
			return self.members[1]
		def z(self):
			return self.members[2]
		def mag(self):
			return self.length()
		def dot(self, other):
			return float(
			(self[0] * other[0]) +
			(self[1] * other[1]) +
			(self[2] * other[2]))
		def midpoint(self, other):
			return Vector(
			(other[0] - self[0])/2.0 + self[0],
			(other[1] - self[1])/2.0 + self[1],
			(other[2] - self[2])/2.0 + self[2])
		def length(self):
			#|V| = (V12 + V22 + V32)1/2
			return math.sqrt(
			(self[0] * self[0]) +
			(self[1] * self[1]) +
			(self[2] * self[2]))
		def cross(self, other):
			return Vector(
			(self[1] * other[2]) - (self[2] * other[1]),
			(self[2] * other[0]) - (self[0] * other[2]),
			(self[0] * other[1]) - (self[1] * other[0]))
		def normalize(self):
			# Make Vector Length 1
			#      V
			# U = ---
			#     |V|
			return self / self.length()
		# I/O
		def read(self, fs):
			p1, p2, p3 = struct.unpack('<fff', fs.read(calcsize('<fff')))
			self.members = [p1, p2, p3]
		def write(self, fs):
			fs.write(struct.pack('<fff', self.members[0:-1]))

	# Vector Class (4 members)
	class Vector4(Vector):
		def __init__(self, x=0, y=0, z=0, w=0):
			self.members = [float(x), float(y), float(z), float(w)]
		def __add__(self, other):
			return Vector4(
			float(self[0]) + float(other[0]),
			float(self[1]) + float(other[1]),
			float(self[2]) + float(other[2]),
			float(self[3]) + float(other[3]))
		def __sub__(self, other):
			return Vector4(
				float(self[0]) - float(other[0]),
				float(self[1]) - float(other[1]),
				float(self[2]) - float(other[2]),
				float(self[3]) - float(other[3]))
		def __neg__(self):
			return Vector4(
			-float(self[0]),
			-float(self[1]),
			-float(self[2]),
			-float(self[3]))
		def __mul__(self, other):
			return Vector4(
				self[0] * other[0],
				self[1] * other[1],
				self[2] * other[2],
				self[3] * other[3])
		def __div__(self, other):
			result = Vector4()
			# iterate through the members
			for i in range(len(self.members)):
				# divide by the val stored in other
				if self[i] != 0:
					result[i] = self[i] / float(other)
				else:
					result[i] = .0
				result[i] = self[i] / float(other)
			return result
		def w(self):
			return self.members[3]
		def length(self):
			return math.sqrt(
			(self[0] * self[0]) +
			(self[1] * self[1]) +
			(self[2] * self[2]) +
			(self[3] * self[3]))
		def dot(self, other):	
			return float(
			(self[0] * other[0]) +
			(self[1] * other[1]) +
			(self[2] * other[2]) +
			(self[3] * other[3]))
		def midpoint(self, other):
			return Vector4(
			(other[0] - self[0])/2.0 + self[0],
			(other[1] - self[1])/2.0 + self[1],
			(other[2] - self[2])/2.0 + self[2],
			(other[3] - self[3])/2.0 + self[3])
		# I/O
		def read(self, fs):
			p1, p2, p3, p4 = struct.unpack('<ffff', fs.read(calcsize('<ffff')))
			self.members = [p1, p2, p3, p4]
		def write(self, fs):
			fs.write(struct.pack('<ffff', self.members[0:-1]))

	# Vector Class (2 members)
	class Vector2(Vector):
		def __init__(self, x=0, y=0):
			self.members = [float(x), float(y)]
		def __add__(self, other):
			result = Vector2()
			# iterate through the members
			for i in range(len(self.members)):
				# add them together
				result[i] = float(self[i]) + float(other[i])
			return result
		def __neg__(self):
			res = Vector2()
			for m in range(0, len(self.members)):
				res[m] = -self[m]
			return res
		def __sub__(self, other):
			result = Vector2()
			# iterate through the members
			for i in range(len(self.members)):
				# subtract them
				result[i] = float(self[i]) - float(other[i])
			return result
		def __mul__(self, other):
			result = Vector2()
			# iterate through the members
			for i in range(len(self.members)):
				# multiply by the val stored in other
				result[i] = self[i] * float(other)
			return result
		def __div__(self, other):
			result = Vector2()
			# iterate through the members
			for i in range(len(self.members)):
				# divide by the val stored in other
				if self[i] != 0:
					result[i] = self[i] / float(other)
				else:
					result[i] = .0
			return result
		def length(self):
			return math.sqrt(
			(self[0] * self[0]) +
			(self[1] * self[1]))
		def midpoint(self, other):
			r = Vector2()
			for i in range(len(self.members)):
				r[i] = ((other[i] - self[i])/2 + self[i])
			return r

	# Quaternion Class (4 members)
	class Quaternion(Vector4):
		def __mul__(self, other): # against another quat
			return (Quaternion(+self[0]*other[3] +self[1]*other[2] -self[2]*other[1] +self[3]*other[0], -self[0]*other[2] +self[1]*other[3] +self[2]*other[0] +self[3]*other[1], +self[0]*other[1] -self[1]*other[0] +self[2]*other[3] +self[3]*other[2], -self[0]*other[0] -self[1]*other[1] -self[2]*other[2] +self[3]*other[3]))
		def conjugate(self):
			return Quaternion(-self.x(), -self.y(), -self.z(), self.w())
		def inverse(self):
			#norm = self.x()*self.x() + self.y()*self.y() + self.z()*self.z() + self.w()*self.w()
			#return (self.conjugate().vecmul(norm / 1.0))
			# Hmm... which way? =/
			
			res = Quaternion()
			mag = float(self.x()*self.x() + self.y()*self.y() + self.z()*self.z() + self.w()*self.w())
			invMag = 0.0
			if mag == 1.0: # Special Case 
				res[0] = -self[0]
				res[1] = -self[1]
				res[2] = -self[2]
				res[3] = self[3]
			else:  # Scale
				if mag == 0.0:
					invMag = 1.0
				else:
					invMag = 1.0 / mag
					
				res[0] = self[0] * -invMag
				res[1] = self[1] * -invMag
				res[2] = self[2] * -invMag
				res[3] = self[3] * invMag
			return res
		def vecmul(self, other): # Vector Version
			result = Quaternion()
			# iterate through the members
			for i in range(len(self.members)):
				# multiply by the val stored in other
				result[i] = self[i] * float(other)
			return result
		def __neg__(self):
			res = Quaternion()
			for m in range(0, len(self.members)):
				res[m] = -self[m]
			return res
		def __div__(self, other):
			result = Quaternion()
			# iterate through the members
			for i in range(len(self.members)):
				# divide by the val stored in other
				if self[i] != 0:
					result[i] = self[i] / float(other)
				else:
					result[i] = .0
				result[i] = self[i] / float(other)
			return result
		def toMatrix(self):
			# Note : NOT TESTED!!
			mat = MatrixF()
			xx = float(self[0] * self[0])
			xy = float(self[0] * self[1])
			yy = float(self[1] * self[1])
			xz = float(self[0] * self[2])
			yz = float(self[1] * self[2])
			zz = float(self[2] * self[2])
			xw = float(self[0] * self[3])
			yw = float(self[1] * self[3])
			zw = float(self[2] * self[3])
			ww = float(self[3] * self[3])
			
			dat = [1-2*(yy+zz), 2*(xy-zw), 2*(xz+yw), 0,  2*(xy + zw), 1-2*(xx+zz), 2*(yz-xw), 0, 2*(xz-yw), 2*(yz+xw), 1-2*(xx+yy), 0, 0, 0, 0, 1]
			mat.setData(dat)
			return mat
		def fromMatrix(self, m):
			# Create from a Matrix
			s = math.sqrt(abs(m.get(0,0) + m.get(1,1) + m.get(2,2) + m.get(3,3)))
			if s == 0.0:
				x = abs(m.get(2,1) - m.get(1,2))
				y = abs(m.get(0,2) - m.get(2,0))
				z = abs(m.get(1,0) - m.get(0,1))
				if   (x >= y) and (x >= z):
					return Quaternion(1.0, 0.0, 0.0, 0.0)
				elif (y >= x) and (y >= z):
					return Quaternion(0.0, 1.0, 0.0, 0.0)
				else:
					return Quaternion(0.0, 0.0, 1.0, 0.0)
			res = Quaternion(-(m.get(2,1) - m.get(1,2)) / (2.0 * s), -(m.get(0,2) - m.get(2,0)) / (2.0 * s), -(m.get(1,0) - m.get(0,1)) / (2.0 * s), 0.5 * s)
			return res.normalize()
		def fromAxis(self, ax, an):
			# Create from an axis and angle
			res = Quaternion()
			ax.normalize()
			s = math.sin(an / 2.0)
			res[0] = ax.x() * s
			res[1] = ax.y() * s
			res[2] = ax.z() * s
			res[3] = math.cos(an / 2.0)
			return res.normalize()
		def angleBetween(self, quat):
			# Get angle between quat's. Returns float
			return acos(self.x()*quat.x() + self.y()*quat.y() + self.z()*quat.z() + self.w()*quat.w())
		def toQuat16(self):
			return Quat16(self.members)
		def apply(self, v):
			# Apply. Returns a point(or rather Vector).
			# Torque uses column vectors, which means quaternions
			# rotate backwards from what you might normally expect.
			q = Quaternion(v.x(), v.y(), v.z(), 0)
			r = self.conjugate() * q * self
			return Vector(r.x(), r.y(), r.z())
			
			

	# The Matrix Class
	class MatrixF:
		def __init__(self, dat=None):
			if dat == None:
				self.members = [
				0.0, 0.0, 0.0, 0.0,
				0.0, 0.0, 0.0, 0.0,
				0.0, 0.0, 0.0, 0.0,
				0.0, 0.0, 0.0, 0.0]
			else:
				self.members = [
				dat[0],  dat[1],  dat[2],  dat[3],
				dat[4],  dat[5],  dat[6],  dat[7],
				dat[8],  dat[9],  dat[10], dat[11],
				dat[12], dat[13], dat[14], dat[15]]
		def __del__(self):
			del self.members
		def setData(self, dat):
			self.members = dat
		def __getitem__(self, key):
			if key > (len(self.members)-1):
				return 0
			return(self.members[key])
		def __setitem__(self, key, value):
			self.members[key] = value
		def get(self, x, y):
			# x = row, y = col
			return self.members[(x*4)+y]
		def set(self, x, y, val):
			# x = row, y = col
			self.members[(x*4)+y] = val
		def col(self, no):
			result = Vector()
			for r in range(0, 4):
				result[r] = self.get(r, no)
			return result
		def identity(self):
			return MatrixF(
			[1.0, 0.0, 0.0, 0.0,
			0.0, 1.0, 0.0, 0.0,
			0.0, 0.0, 1.0, 0.0,
			0.0, 0.0, 0.0, 1.0])
		def transpose(self):
			result = MatrixF()
			for r in range(0, 4):
				for r in range(0, 4):
					result.set(c, r, self.get(r, c))
			return result
		def setCol(self, no, col):
			for c in range(0, 4):
				self.set(c, no, col[c]) # self.members[(x*4)+y] = val
		def setRow(self, no, row):
			for r in range(0, 4):
				self.set(no, r, row[r])
		def getRow(self, no):
			for r in range(0, 4):
				result.append(self.get(no, r))
			return result
		def mul(self, vect):
			res = Vector4()
			for r in range(0, 4):
				cell = self.get(r, 0) * vect[0]
				for e in range(0, 4):
					cell += self.get(r, e) * vect[e]
				res[r] = cell
			return res
		def xVector4(self, vect):
			result = Vector4()
			result[0] = (self[0]*vect[0] + self[1]*vect[1] + self[2]*vect[2]  + self[3]*vect[3])
			result[1] = (self[4]*vect[0] + self[5]*vect[1] + self[6]*vect[2]  + self[7]*vect[3])
			result[2] = (self[8]*vect[0] + self[9]*vect[1] + self[10]*vect[2] + self[11]*vect[3])
			result[3] = (self[12]*vect[0]+ self[13]*vect[1]+ self[14]*vect[2] + self[15]*vect[3])
			return result
		def passPoint(self, point):
			return Vector(point[0] * self.get(0, 0) + point[1] * self.get(1, 0) + point[2] * self.get(2, 0) + self.get(3, 0),
				point[0] * self.get(0, 1) + point[1] * self.get(1, 1) + point[2] * self.get(2, 1) + self.get(3, 1),
				point[0] * self.get(0, 2) + point[1] * self.get(1, 2) + point[2] * self.get(2, 2) + self.get(3, 2))
		def passVector(self, vec):
			return Vector(vec[0] * self.get(0, 0) + vec[1] * self.get(1, 0) + vec[2] * self.get(2, 0),
				vec[0] * self.get(0, 1) + vec[1] * self.get(1, 1) + vec[2] * self.get(2, 1),
				vec[0] * self.get(0, 2) + vec[1] * self.get(1, 2) + vec[2] * self.get(2, 2))
		def determinant(self):
			return (self[0] * (self[5] * self[10] - self[6] * self[9])  + self[4] * (self[2] * self[9]  - self[1] * self[10]) +  self[8] * (self[1] * self[6]  - self[2] * self[5]))
		def inverse(self):
			return self.invert()
		def __mul__(self, a): # self, a
			return MatrixF([
			a.get(0,0) * self.get(0,0) + a.get(0,1) * self.get(1,0) + a.get(0,2) * self.get(2,0),
			a.get(0,0) * self.get(0,1) + a.get(0,1) * self.get(1,1) + a.get(0,2) * self.get(2,1),
			a.get(0,0) * self.get(0,2) + a.get(0,1) * self.get(1,2) + a.get(0,2) * self.get(2,2),
			0.0,
			a.get(1,0) * self.get(0,0) + a.get(1,1) * self.get(1,0) + a.get(1,2) * self.get(2,0),
			a.get(1,0) * self.get(0,1) + a.get(1,1) * self.get(1,1) + a.get(1,2) * self.get(2,1),
			a.get(1,0) * self.get(0,2) + a.get(1,1) * self.get(1,2) + a.get(1,2) * self.get(2,2),
			0.0,
			a.get(2,0) * self.get(0,0) + a.get(2,1) * self.get(1,0) + a.get(2,2) * self.get(2,0),
			a.get(2,0) * self.get(0,1) + a.get(2,1) * self.get(1,1) + a.get(2,2) * self.get(2,1),
			a.get(2,0) * self.get(0,2) + a.get(2,1) * self.get(1,2) + a.get(2,2) * self.get(2,2),
			0.0,
			a.get(3,0) * self.get(0,0) + a.get(3,1) * self.get(1,0) + a.get(3,2) * self.get(2,0) + self.get(3,0),
			a.get(3,0) * self.get(0,1) + a.get(3,1) * self.get(1,1) + a.get(3,2) * self.get(2,1) + self.get(3,1),
			a.get(3,0) * self.get(0,2) + a.get(3,1) * self.get(1,2) + a.get(3,2) * self.get(2,2) + self.get(3,2),
			1.0])
		def rotate(self, axis, angle):
			# Returns a rotated matrix
			vx, vy, vz  = axis[0], axis[1], axis[2]
			vx2, vy2, vz2 = vx**2, vy**2, vz**2
			cos, sin = math.cos(angle), math.sin(angle)
			co1 = 1.0 - cos
			return MatrixF([
			vx2 * co1 + cos, vx * vy * co1 + vz * sin, vz * vx * co1 - vy * sin, 0.0,
			vx * vy * co1 - vz * sin, vy2 * co1 + cos, vy * vz * co1 + vx * sin, 0.0,
			vz * vx * co1 + vy * sin, vy * vz * co1 - vx * sin, vz2 * co1 + cos, 0.0,
			0.0, 0.0, 0.0, 1.0])
		def translate_matrix(self, vec):
			narr = self.members
			return MatrixF([narr[0],narr[1],narr[2],narr[3],
								narr[4],narr[5],narr[6],narr[7],
								narr[8],narr[9],narr[10],narr[11],
								narr[12]+vec[y],narr[13]+vec[y],narr[14]+vec[y],narr[15]])
		def scale_matrix(self, vec):
			narr = self.members
			return MatrixF([narr[0]*vec[0],narr[1]*vec[1],narr[2]*vec[2],narr[3],
								narr[4]*vec[0],narr[5]*vec[1],narr[6]*vec[2],narr[7],
								narr[8]*vec[0],narr[9]*vec[1],narr[10]*vec[2],narr[11],
								narr[12]*vec[0],narr[13]*vec[1],narr[14]*vec[2],narr[15]])
		
		def copy(self):
			return MatrixF(copy.deepcopy(n.members))
		def invert(self):
			det = self.determinant()
			if det == 0.0:
				return None
			det = 1.0 / det
			r = [
			det * (self.get(1, 1) * self.get(2, 2) - self.get(2, 1) * self.get(1, 2)),
			- det * (self.get(0, 1) * self.get(2, 2) - self.get(2, 1) * self.get(0, 2)),
			det * (self.get(0, 1) * self.get(1, 2) - self.get(1, 1) * self.get(0, 2)),
			0.0,
			- det * (self.get(1, 0) * self.get(2, 2) - self.get(2, 0) * self.get(1, 2)),
			det * (self.get(0, 0) * self.get(2, 2) - self.get(2, 0) * self.get(0, 2)),
			- det * (self.get(0, 0) * self.get(1, 2) - self.get(1, 0) * self.get(0, 2)),
			0.0,
			det * (self.get(1, 0) * self.get(2, 1) - self.get(2, 0) * self.get(1, 1)),
			- det * (self.get(0, 0) * self.get(2, 1) - self.get(2, 0) * self.get(0, 1)),
			det * (self.get(0, 0) * self.get(1, 1) - self.get(1, 0) * self.get(0, 1)),
			0.0]
			r.append(-(self.get(3, 0) * r[0] + self.get(3, 1) * r[1*4] + self.get(3, 2) * r[2*4]))
			r.append(-(self.get(3, 0) * r[1] + self.get(3, 1) * r[(1*4)+1] + self.get(3, 2) * r[(2*4)+1]))
			r.append(-(self.get(3, 0) * r[2] + self.get(3, 1) * r[(1*4)+2] + self.get(3, 2) * r[(2*4)+2]))
			r.append(1.0)
			mat = MatrixF(r)
			return mat
		def mprint(self):
			for x in range(0, 4):
				print "| %f %f %f %f |" % (self.get(x, 0), self.get(x,1), self.get(x,2), self.get(x,3))

# Quat16 - Compressed Quaternion
class Quat16:
	MAX_VAL = 0x7fff
	def __init__(self, members=None):
		if members != None:
			self.x = int(members[0] * float(self.MAX_VAL))
			self.y = int(members[1] * float(self.MAX_VAL))
			self.z = int(members[2] * float(self.MAX_VAL))
			self.w = int(members[3] * float(self.MAX_VAL))
	def toQuat(self):
		q = Quaternion()
		q[0] = float(self.x) / float(self.MAX_VAL)
		q[1] = float(self.y) / float(self.MAX_VAL)
		q[2] = float(self.z) / float(self.MAX_VAL)
		q[3] = float(self.w) / float(self.MAX_VAL)
		return q
	def __getitem__(self, key):
		if key > 3:
			return 0
		if key == 0:
			return self.x
		elif key == 1:
			return self.y
		elif key == 2:
			return self.z
		elif key == 3:
			return self.w
		return(self.members[key])
	def __setitem__(self, key, value):
		if key > 3:
			return 0
		if key == 0:
			self.x = value
		elif key == 1:
			self.y = value
		elif key == 2:
			self.z = value
		elif key == 3:
			self.w = value

class PlaneF:
	PLANE_FRONT = 0
	PLANE_BACK = 1
	PLANE_ON = 2
	PLANE_CROSS = 3
	EPSILON = 0.0001
	def __init__(self, vert1=Vector(), vert2=Vector(), vert3=Vector()):
		# Create a plane from 3 points
		vec1 = vert3 - vert1
		vec2 = vert2 - vert1

		self.normal = vec1.cross(vec2).normalize()
		self.k = self.normal.dot(vert1)

	def distToPlane(self, p1):
		# This appears to work
		return self.k - self.normal.dot(p1) # deltaD

	def intersect(self, p1, p2):
		# Returns distance along ray that the hit occured
		cosAlpha = self.normal.dot((p2 - p1).normalize())
		if (cosAlpha < self.EPSILON) and (cosAlpha > -self.EPSILON):
			return None # parralel
		return (self.distToPlane(p1) / cosAlpha)

	def intersectRay(self, p1, p2):
		# Returns point of intersection
		# First lets check if p1 and p2 are in suitable positions
		# If not, then this ray (p1 -> p2) does not pass through plane
		p1c = self.classifyVert(p1)
		p2c = self.classifyVert(p2)
		if ((p1c == self.PLANE_BACK) and (p2c == self.PLANE_FRONT)) or ((p2c == self.PLANE_BACK) and (p1c == self.PLANE_FRONT)):
			# Ray passing through plane
			rayDist = self.intersect(p1, p2) # Get length of ray hit
		else:
			# Ray nowhere near plane
			return None

		if rayDist == None:
			return None
		intersection = p1 + ((p2 - p1).normalize() * (rayDist))

		#print "Ray %f %f %f [%f %f %f] intersection is [%f %f %f]" % (p1[0], p1[1], p1[2], p2[0], p2[1], p2[2], intersection[0], intersection[1], intersection[2])
		return intersection

	def classifyPrimitive(self, verts):
		# front, back, crossing, on (verts)
		# front, back, on (vert)

		# Classify the different vertexes
		cVerts = [self.classifyVert(verts[0]),self.classifyVert(verts[1]), self.classifyVert(verts[2])]
		vFront, vBack, vPlane = False, False, False

		for v in cVerts:
			if v == self.PLANE_FRONT: vFront = True
			elif v == self.PLANE_BACK: vBack = True
			elif v == self.PLANE_ON: vPlane = True

		if vFront and vBack: return self.PLANE_CROSS	# Crossing Over
		elif vFront: return self.PLANE_FRONT	# At front
		elif vBack: return self.PLANE_BACK	# At Back
		elif vPlane: return self.PLANE_ON	# On

	def classifyVert(self, vert):
		check = self.normal.dot(vert)

		# If vert in front, behind, or on plane?
		if check > (self.k + self.EPSILON):
			return self.PLANE_FRONT
		elif check < (self.k - self.EPSILON):
			return self.PLANE_BACK
		else:
			return self.PLANE_ON

# The Box Class
class Box:
	def __init__(self, v1=Vector(0,0,0), v2=Vector(0,0,0)):
		self.min = v1
		self.max = v2

	def isContained(self, obj):
		if type(obj) == Box:
			# Check boxes
			cCount = 0
			for i in range(0, 3):
				if self.min[i] > obj.min[i]:
					return 0
			for i in range(0, 3):
				if self.max[i] < obj.max[i]:
					return 0
			return 1
		elif type(obj) == Vector:
			# Check a vert
			cCount = 0
			for i in range(0, 3):
				if (obj[i] < self.min[i]) and (obj[i] >= self.max[i]):
					return 0
			return 1
		else:
			print "ERROR; Could not check object",type(obj)
			return None

	def isOverlapped(self, obj):
		for i in range(0, 3):
			if obj.min[i] > self.min[i]:
				return 0
		for i in range(0, 3):
			if obj.max[i] < self.max[i]:
				return 0
		return 1

	def getCenter(self):
		return Vector((self.min[0] + self.max[0]) * 0.5,
		              (self.min[1] + self.max[1]) * 0.5,
			      (self.min[2] + self.max[2]) * 0.5)

	def split(self, axis):
		middle = self.getCenter()
		if axis == 1:
			# Split along X axis
			ret = Box(Vector(middle[0], self.min[1], self.min[2]), Vector(self.max[0], self.max[1], self.max[2]))
			self.max[0] = middle[0]
		elif axis == 2:
			# Split along Y axis
			ret = Box(Vector(self.min[0], middle[1], self.min[2]), Vector(self.max[0], self.max[1], self.max[2]))
			self.max[1] = middle[1]
		elif axis == 3:
			# Split along Z axis
			ret = Box(Vector(self.min[0], self.min[1], middle[2]), Vector(self.max[0], self.max[1], self.max[2]))
			self.max[2] = middle[2]
		else:
			print "ERROR: Cannot open inter-dimensional portal!"
			return None

		return ret


