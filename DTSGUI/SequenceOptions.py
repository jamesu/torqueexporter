'''
SequenceOptions.py

Copyright (c) 2008 - 2009 Joseph Greenawalt(jsgreenawalt@gmail.com)

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
* Class that creates and owns the GUI controls on the Shape Options sub-panel.
*
***************************************************************************************************
'''
class SequenceOptionsControlsClass:
	def __init__(self, guiShapeOptionsSubtab):
		global globalEvents
		Prefs = DtsGlobals.Prefs
		
		# initialize GUI controls
		self.guiAnimExportModeText = Common_Gui.SimpleText("guiAnimExportModeText", "Animation export mode:", None, self.guiAnimExportModeTextResize)
		self.guiSinglePassButton = Common_Gui.ToggleButton("guiSinglePassButton", "Single pass animation export (default)", "Perform a standard single pass export of all sequences (recommended)", 6, self.handleGuiSinglePassButtonEvent, self.guiSinglePassButtonResize)
		self.guiSinglePassText = Common_Gui.SimpleText("guiSinglePassText", "Fast and safe, this is the recommended animation export mode.", None, self.guiSinglePassTextResize)
		self.guiTwoPassButton = Common_Gui.ToggleButton("guiTwoPassButton", "Two pass animation export (CAUTION!, see note)", "Perform a two pass export of all sequences (NOT recommended, may cause data loss!)", 6, self.handleGuiTwoPassButtonEvent, self.guiTwoPassButtonResize)
		self.guiTwoPassText = Common_Gui.MultilineText("guiTwoPassText", "!!! WARNING !!! - USE WITH CAUTION, MAY CAUSE DATA LOSS!\n"\
		                                                                +"Use this animation export mode ONLY if your animations\n"\
		                                                                +"contain non-uniform (anisotropic) scaling.  Anisotropic\n"\
		                                                                +"scale is best avoided, since it causes all kinds of\n"\
		                                                                +"problems within Blender and with the exporter.  This mode\n"\
		                                                                +"has the potential to cause data loss in Blender's IPO\n"\
		                                                                +"curve data and should only be used as a last resort.\n"\
		                                                                +"If you decide to enable this option, it is recommened\n"\
		                                                                +"that you make frequent backups of your work!!!", None, self.guiTwoPassTextResize)

		'''
		self.guiTriMeshesButton = Common_Gui.ToggleButton("guiTriMeshesButton", "Triangles", "Generate individual triangles for meshes", 6, self.handleGuiTriMeshesButtonEvent, self.guiTriMeshesButtonResize)
		self.guiTriListsButton = Common_Gui.ToggleButton("guiTriListsButton", "Triangle Lists", "Generate triangle lists for meshes", 7, self.handleGuiTriListsButtonEvent, self.guiTriListsButtonResize)
		self.guiStripMeshesButton = Common_Gui.ToggleButton("guiStripMeshesButton", "Triangle Strips", "Generate triangle strips for meshes", 8, self.handleGuiStripMeshesButtonEvent, self.guiStripMeshesButtonResize)
		self.guiMaxStripSizeSlider = Common_Gui.NumberSlider("guiMaxStripSizeSlider", "Strip Size ", "Maximum size of generated triangle strips", 9, self.handleGuiMaxStripSizeSliderEvent, self.guiMaxStripSizeSliderResize)


		self.guiBillboardText = Common_Gui.SimpleText("guiBillboardText", "Auto-Billboard LOD:", None, self.guiBillboardTextResize)
		self.guiBillboardButton = Common_Gui.ToggleButton("guiBillboardButton", "Enable", "Add a billboard detail level to the shape", 12, self.handleGuiBillboardButtonEvent, self.guiBillboardButtonResize)
		self.guiBillboardEquator = Common_Gui.NumberPicker("guiBillboardEquator", "Equator", "Number of images around the equator", 13, self.handleGuiBillboardEquatorEvent, self.guiBillboardEquatorResize)
		self.guiBillboardPolar = Common_Gui.NumberPicker("guiBillboardPolar", "Polar", "Number of images around the polar", 14, self.handleGuiBillboardPolarEvent, self.guiBillboardPolarResize)
		self.guiBillboardPolarAngle = Common_Gui.NumberSlider("guiBillboardPolarAngle", "Polar Angle", "Angle to take polar images at", 15, self.handleGuiBillboardPolarAngleEvent, self.guiBillboardPolarAngleResize)
		self.guiBillboardDim = Common_Gui.NumberPicker("guiBillboardDim", "Dim", "Dimensions of billboard images", 16, self.handleGuiBillboardDimEvent, self.guiBillboardDimResize)
		self.guiBillboardPoles = Common_Gui.ToggleButton("guiBillboardPoles", "Poles", "Take images at the poles", 17, self.handleGuiBillboardPolesEvent, self.guiBillboardPolesResize)
		self.guiBillboardSize = Common_Gui.NumberSlider("guiBillboardSize", "Size", "Size of billboard's detail level", 18, self.handleGuiBillboardSizeEvent, self.guiBillboardSizeResize)
		# --
		self.guiMiscText = Common_Gui.SimpleText("guiMiscText", "Miscellaneous:", None, self.guiMiscTextResize)
		self.guiScale = Common_Gui.NumberPicker("guiScale", "Export Scale", "Multiply output scale by this number", 26, self.handleGuiScaleEvent, self.guiScaleResize)
		
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

		self.guiScale.value = Prefs['ExportScale']
		self.guiScale.min = 0.001
		self.guiScale.max = 1000000.0
		
		# Hiding these for now, since cluster mesh sorting is still broken.
		#self.guiClusterText.visible = False
		#self.guiClusterWriteDepth.visible = False
		#self.guiClusterDepth.visible = False
		'''
		
		# add controls to containers
		guiShapeOptionsSubtab.addControl(self.guiAnimExportModeText)
		guiShapeOptionsSubtab.addControl(self.guiSinglePassButton)
		guiShapeOptionsSubtab.addControl(self.guiTwoPassButton)
		guiShapeOptionsSubtab.addControl(self.guiSinglePassText)
		guiShapeOptionsSubtab.addControl(self.guiTwoPassText)
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiAnimExportModeText
		del self.guiSinglePassButton
		del self.guiTwoPassButton
		del self.guiSinglePassText
		del self.guiTwoPassText

	def refreshAll(self):
		pass
		
	
	def handleGuiSinglePassButtonEvent(self, control):
		pass

	def handleGuiTwoPassButtonEvent(self, control):
		pass
	
	
	'''	
	def handleGuiTriMeshesButtonEvent(self, control):
		Prefs = DtsGlobals.Prefs
		Prefs['PrimType'] = "Tris"
		self.guiTriListsButton.state = False
		self.guiStripMeshesButton.state = False
		self.guiTriMeshesButton.state = True
	'''

	def guiAnimExportModeTextResize(self, control, newwidth, newheight):
		control.x, control.y = 10,newheight-50

	def guiSinglePassButtonResize(self, control, newwidth, newheight):
		control.x, control.y = 15,newheight-90
		control.width, control.height = 340, 20
	
	def guiSinglePassTextResize(self, control, newwidth, newheight):
		control.x, control.y = 25,newheight-105
		control.width, control.height = 340, 20
	
	def guiTwoPassButtonResize(self, control, newwidth, newheight):
		control.x, control.y = 15,newheight-160
		control.width, control.height = 340, 20

	def guiTwoPassTextResize(self, control, newwidth, newheight):
		control.x, control.y = 25,40
		control.width, control.height = 340, 20
