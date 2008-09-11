'''
ShapeOptions.py

Copyright (c) 2003 - 2008 James Urquhart(j_urquhart@btinternet.com)

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

import Common_Gui
import DtsGlobals
from DtsSceneInfo import *

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the General sub-panel.
*
***************************************************************************************************
'''
class ShapeOptionsControlsClass:
	def __init__(self, guiGeneralSubtab):
		global globalEvents
		Prefs = DtsGlobals.Prefs
		
		# initialize GUI controls
		self.guiStripText = Common_Gui.SimpleText("guiStripText", "Geometry type:", None, self.resize)
		self.guiTriMeshesButton = Common_Gui.ToggleButton("guiTriMeshesButton", "Triangles", "Generate individual triangles for meshes", 6, self.handleEvent, self.resize)
		self.guiTriListsButton = Common_Gui.ToggleButton("guiTriListsButton", "Triangle Lists", "Generate triangle lists for meshes", 7, self.handleEvent, self.resize)
		self.guiStripMeshesButton = Common_Gui.ToggleButton("guiStripMeshesButton", "Triangle Strips", "Generate triangle strips for meshes", 8, self.handleEvent, self.resize)
		self.guiMaxStripSizeSlider = Common_Gui.NumberSlider("guiMaxStripSizeSlider", "Strip Size ", "Maximum size of generated triangle strips", 9, self.handleEvent, self.resize)
		# --
		self.guiScale = Common_Gui.NumberPicker("guiScale", "Export Scale", "Multiply output scale by this number", 26, self.handleEvent, self.resize)
		
		#self.guiClusterText = Common_Gui.SimpleText("guiClusterText", "Cluster Mesh", None, self.resize)
		#self.guiClusterWriteDepth = Common_Gui.ToggleButton("guiClusterWriteDepth", "Write Depth ", "Always Write the Depth on Cluster meshes", 10, self.handleEvent, self.resize)
		#self.guiClusterDepth = Common_Gui.NumberSlider("guiClusterDepth", "Depth", "Maximum depth Clusters meshes should be calculated to", 11, self.handleEvent, self.resize)
		# --
		self.guiBillboardText = Common_Gui.SimpleText("guiBillboardText", "Auto-Billboard LOD:", None, self.resize)
		self.guiBillboardButton = Common_Gui.ToggleButton("guiBillboardButton", "Enable", "Add a billboard detail level to the shape", 12, self.handleEvent, self.resize)
		self.guiBillboardEquator = Common_Gui.NumberPicker("guiBillboardEquator", "Equator", "Number of images around the equator", 13, self.handleEvent, self.resize)
		self.guiBillboardPolar = Common_Gui.NumberPicker("guiBillboardPolar", "Polar", "Number of images around the polar", 14, self.handleEvent, self.resize)
		self.guiBillboardPolarAngle = Common_Gui.NumberSlider("guiBillboardPolarAngle", "Polar Angle", "Angle to take polar images at", 15, self.handleEvent, self.resize)
		self.guiBillboardDim = Common_Gui.NumberPicker("guiBillboardDim", "Dim", "Dimensions of billboard images", 16, self.handleEvent, self.resize)
		self.guiBillboardPoles = Common_Gui.ToggleButton("guiBillboardPoles", "Poles", "Take images at the poles", 17, self.handleEvent, self.resize)
		self.guiBillboardSize = Common_Gui.NumberSlider("guiBillboardSize", "Size", "Size of billboard's detail level", 18, self.handleEvent, self.resize)
		
		# set initial states
		try: x = Prefs['PrimType']
		except KeyError: Prefs['PrimType'] = "Tris"
		if Prefs['PrimType'] == "Tris": self.guiTriMeshesButton.state = True
		else: self.guiTriMeshesButton.state = False
		if Prefs['PrimType'] == "TriLists": self.guiTriListsButton.state = True
		else: self.guiTriListsButton.state = False
		if Prefs['PrimType'] == "TriStrips": self.guiStripMeshesButton.state = True
		else: self.guiStripMeshesButton.state = False
		self.guiMaxStripSizeSlider.min, self.guiMaxStripSizeSlider.max = 3, 30
		self.guiMaxStripSizeSlider.value = Prefs['MaxStripSize']
		self.guiScale.value = Prefs['ExportScale']
		self.guiScale.min = 0.001
		self.guiScale.max = 1000000.0
		#self.guiClusterDepth.min, self.guiClusterDepth.max = 3, 30
		#self.guiClusterDepth.value = Prefs['ClusterDepth']
		#self.guiClusterWriteDepth.state = Prefs['AlwaysWriteDepth']
		self.guiBillboardButton.state = Prefs['Billboard']['Enabled']
		self.guiBillboardEquator.min, self.guiBillboardEquator.max = 2, 64
		self.guiBillboardEquator.value = Prefs['Billboard']['Equator']
		self.guiBillboardPolar.min, self.guiBillboardPolar.max = 3, 64
		self.guiBillboardPolar.value = Prefs['Billboard']['Polar']
		self.guiBillboardPolarAngle.min, self.guiBillboardPolarAngle.max = 0.0, 45.0
		self.guiBillboardPolarAngle.value = Prefs['Billboard']['PolarAngle']
		self.guiBillboardDim.min, self.guiBillboardDim.max = 16, 128
		self.guiBillboardDim.value = Prefs['Billboard']['Dim']
		self.guiBillboardPoles.state = Prefs['Billboard']['IncludePoles']		
		self.guiBillboardSize.min, self.guiBillboardSize.max = 0.0, 128.0
		self.guiBillboardSize.value = Prefs['Billboard']['Size']
		
		# Hiding these for now, since cluster mesh sorting is still broken.
		#self.guiClusterText.visible = False
		#self.guiClusterWriteDepth.visible = False
		#self.guiClusterDepth.visible = False
		
		
		# add controls to containers
		guiGeneralSubtab.addControl(self.guiStripText)
		guiGeneralSubtab.addControl(self.guiTriMeshesButton)
		guiGeneralSubtab.addControl(self.guiTriListsButton)
		guiGeneralSubtab.addControl(self.guiStripMeshesButton)	
		guiGeneralSubtab.addControl(self.guiMaxStripSizeSlider)
		guiGeneralSubtab.addControl(self.guiScale)
		#guiGeneralSubtab.addControl(self.guiClusterText)
		#guiGeneralSubtab.addControl(self.guiClusterDepth)
		#guiGeneralSubtab.addControl(self.guiClusterWriteDepth)
		guiGeneralSubtab.addControl(self.guiBillboardText)
		guiGeneralSubtab.addControl(self.guiBillboardButton)
		guiGeneralSubtab.addControl(self.guiBillboardEquator)
		guiGeneralSubtab.addControl(self.guiBillboardPolar)
		guiGeneralSubtab.addControl(self.guiBillboardPolarAngle)
		guiGeneralSubtab.addControl(self.guiBillboardDim)
		guiGeneralSubtab.addControl(self.guiBillboardPoles)
		guiGeneralSubtab.addControl(self.guiBillboardSize)

		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		# initialize GUI controls
		del self.guiStripText
		del self.guiTriMeshesButton
		del self.guiTriListsButton
		del self.guiStripMeshesButton
		del self.guiMaxStripSizeSlider
		del self.guiScale
		# --
		#del self.guiClusterText
		#del self.guiClusterWriteDepth
		#del self.guiClusterDepth
		# --
		del self.guiBillboardText
		del self.guiBillboardButton
		del self.guiBillboardEquator
		del self.guiBillboardPolar
		del self.guiBillboardPolarAngle
		del self.guiBillboardDim
		del self.guiBillboardPoles
		del self.guiBillboardSize


	def refreshAll(self):
		pass
		
	def handleEvent(self, control):
		Prefs = DtsGlobals.Prefs
		global guiGeneralSubtab
		if control.name == "guiTriMeshesButton":
			Prefs['PrimType'] = "Tris"
			self.guiTriListsButton.state = False
			self.guiStripMeshesButton.state = False
			self.guiTriMeshesButton.state = True
		elif control.name == "guiTriListsButton":
			Prefs['PrimType'] = "TriLists"
			self.guiTriListsButton.state = True
			self.guiStripMeshesButton.state = False
			self.guiTriMeshesButton.state = False
		elif control.name == "guiStripMeshesButton":
			Prefs['PrimType'] = "TriStrips"
			self.guiTriListsButton.state = False
			self.guiStripMeshesButton.state = True
			self.guiTriMeshesButton.state = False
		elif control.name == "guiMaxStripSizeSlider":
			Prefs['MaxStripSize'] = control.value
		elif control.name == "guiScale":
			Prefs['ExportScale'] = control.value
		#elif control.name == "guiClusterWriteDepth":
		#	Prefs['AlwaysWriteDepth'] = control.state
		#elif control.name == "guiClusterDepth":
		#	Prefs['ClusterDepth'] = control.value
		elif control.name == "guiBillboardButton":
			Prefs['Billboard']['Enabled'] = control.state
		elif control.name == "guiBillboardEquator":
			Prefs['Billboard']['Equator'] = control.value
		elif control.name == "guiBillboardPolar":
			Prefs['Billboard']['Polar'] = control.value
		elif control.name == "guiBillboardPolarAngle":
			Prefs['Billboard']['PolarAngle'] = control.value
		elif control.name == "guiBillboardDim":
			val = int(control.value)
			# need to constrain this to be a power of 2
			# it would be easier just to use a combo box, but this is more fun.
			# did the value go up or down?
			if control.value > Prefs['Billboard']['Dim']:
				# we go up
				val = int(2**math.ceil(math.log(control.value,2)))
			elif control.value < Prefs['Billboard']['Dim']:
				# we go down
				val = int(2**math.floor(math.log(control.value,2)))
			control.value = val
			Prefs['Billboard']['Dim'] = control.value
		elif control.name == "guiBillboardPoles":
			Prefs['Billboard']['IncludePoles'] = control.state
		elif control.name == "guiBillboardSize":
			Prefs['Billboard']['Size'] = control.value

		
	def resize(self, control, newwidth, newheight):
		if control.name == "guiStripText":
			control.x, control.y = 10,newheight-20
		elif control.name == "guiClusterText":
			control.x, control.y = 10,newheight-70
		elif control.name == "guiBillboardText":
			control.x, control.y = 10,newheight-120
		elif control.name == "guiOutputText":
			control.x, control.y = 10,newheight-250
		elif control.name == "guiTriMeshesButton":
			control.x, control.y, control.width = 102,newheight-30-control.height, 90			
		elif control.name == "guiTriListsButton":
			control.x, control.y, control.width = 10,newheight-30-control.height, 90
		elif control.name == "guiStripMeshesButton":
			control.x, control.y, control.width = 194,newheight-30-control.height, 90
		elif control.name == "guiMaxStripSizeSlider":
			control.x, control.y, control.width = 286,newheight-30-control.height, 180
		elif control.name == "guiScale":
			control.x, control.y, control.width = 10, newheight-70-control.height, 180
		#elif control.name == "guiClusterWriteDepth":
		#	control.x, control.y, control.width = 10,newheight-80-control.height, 80
		#elif control.name == "guiClusterDepth":
		#	control.x, control.y, control.width = 92,newheight-80-control.height, 180
		elif control.name == "guiBillboardButton":
			control.x, control.y, control.width = 10,newheight-130-control.height, 50
		elif control.name == "guiBillboardEquator":
			control.x, control.y, control.width = 62,newheight-130-control.height, 100
		elif control.name == "guiBillboardPolar":
			control.x, control.y, control.width = 62,newheight-152-control.height, 100
		elif control.name == "guiBillboardPolarAngle":
			control.x, control.y, control.width =  164,newheight-152-control.height, 200
		elif control.name == "guiBillboardDim":
			control.x, control.y, control.width = 366,newheight-130-control.height, 100
		elif control.name == "guiBillboardPoles":
			control.x, control.y, control.width = 366,newheight-152-control.height, 100
		elif control.name == "guiBillboardSize":
			control.x, control.y, control.width = 164,newheight-130-control.height, 200

	
