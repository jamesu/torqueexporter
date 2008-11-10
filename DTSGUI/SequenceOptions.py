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
		self.guiTwoPassButton = Common_Gui.ToggleButton("guiTwoPassButton", "Two pass animation export (CAUTION!, see note)", "Perform a two pass export of all sequences (NOT recommended, may cause data loss!)", 7, self.handleGuiTwoPassButtonEvent, self.guiTwoPassButtonResize)
		self.guiTwoPassText = Common_Gui.MultilineText("guiTwoPassText", "!!! WARNING !!! - USE WITH CAUTION, MAY CAUSE DATA LOSS!\n"\
		                                                                +"Use this animation export mode ONLY if your animations\n"\
		                                                                +"contain non-uniform (anisotropic) scaling.  Anisotropic\n"\
		                                                                +"scale is best avoided, since it causes all kinds of\n"\
		                                                                +"problems within Blender and with the exporter.  This mode\n"\
		                                                                +"has the potential to cause data loss in Blender's IPO\n"\
		                                                                +"curve data and should only be used as a last resort.\n"\
		                                                                +"If you decide to enable this option, it is recommened\n"\
		                                                                +"that you make frequent backups of your work!!!", None, self.guiTwoPassTextResize)


		
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
		Prefs = DtsGlobals.Prefs
		pass

	def handleGuiTwoPassButtonEvent(self, control):
		Prefs = DtsGlobals.Prefs
		pass
	
	

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
