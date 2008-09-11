'''
General.py

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
from DTSPython import Torque_Util
from DtsSceneInfo import *

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the General sub-panel.
*
***************************************************************************************************
'''
class GeneralControlsClass:
	def __init__(self, guiGeneralSubtab):
		global globalEvents
		Prefs = DtsGlobals.Prefs
		
		# initialize GUI controls
		
		# --
		self.guiOutputText = Common_Gui.SimpleText("guiOutputText", "Output path and file name:", None, self.resize)
		self.guiCustomFilename = Common_Gui.TextBox("guiCustomFilename", "Filename: ", "Filename to write to", 20, self.handleEvent, self.resize)
		self.guiCustomFilenameSelect = Common_Gui.BasicButton("guiCustomFilenameSelect", "Select...", "Select a filename and destination for export", 21, self.handleEvent, self.resize)
		self.guiCustomFilenameDefaults = Common_Gui.BasicButton("guiCustomFilenameDefaults", "Default", "Reset filename and destination to defaults", 22, self.handleEvent, self.resize)
		self.guiScriptOutputText = Common_Gui.SimpleText("guiScriptOutputText", "Script output:", None, self.resize)
		self.guiShapeScriptButton =  Common_Gui.ToggleButton("guiShapeScriptButton", "Write Shape Script", "Write .cs script that details the .dts and all .dsq sequences", 19, self.handleEvent, self.resize)
		self.guiTGEAMaterial = Common_Gui.ToggleButton("guiTGEAMaterial", "Write TGEA Material Script", "Write materials and scripts geared for TSE", 24, self.handleEvent, self.resize)
		self.guiLogOutputText = Common_Gui.SimpleText("guiLogOutputText", "Log file output:", None, self.resize)
		self.guiLogToOutputFolder = Common_Gui.ToggleButton("guiLogToOutputFolder", "Write log file to output folder", "Write Log file to .DTS output folder", 25, self.handleEvent, self.resize)
		self.guiWarnErrText = Common_Gui.SimpleText("guiWarnErrText", "Errors and Warnings:", None, self.resize)
		self.guiShowWarnErrPopup = Common_Gui.ToggleButton("guiShowWarnErrPopup", "Show Error/Warning popup", "Shows a popup when errors or warnings occur during export.", 27, self.handleEvent, self.resize)
		
		# set initial states
		self.guiShowWarnErrPopup.state = Prefs["ShowWarningErrorPopup"]
		self.guiCustomFilename.length = 255
		pathSep = DtsGlobals.SceneInfo.getPathSeparator()
		self.guiCustomFilename.value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename'] + ".dts"
		self.guiTGEAMaterial.state = Prefs['TSEMaterial']		
		try: self.guiLogToOutputFolder.state = Prefs['LogToOutputFolder']
		except:
			Prefs['LogToOutputFolder'] = True
			self.guiLogToOutputFolder.state = True
		
		
		
		# add controls to containers		
		guiGeneralSubtab.addControl(self.guiOutputText)
		guiGeneralSubtab.addControl(self.guiCustomFilename)
		guiGeneralSubtab.addControl(self.guiCustomFilenameSelect)
		guiGeneralSubtab.addControl(self.guiCustomFilenameDefaults)
		guiGeneralSubtab.addControl(self.guiScriptOutputText)
		guiGeneralSubtab.addControl(self.guiShapeScriptButton)
		guiGeneralSubtab.addControl(self.guiTGEAMaterial)
		guiGeneralSubtab.addControl(self.guiLogOutputText)
		guiGeneralSubtab.addControl(self.guiLogToOutputFolder)
		guiGeneralSubtab.addControl(self.guiWarnErrText)
		guiGeneralSubtab.addControl(self.guiShowWarnErrPopup)

		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiOutputText
		del self.guiCustomFilename
		del self.guiCustomFilenameSelect
		del self.guiCustomFilenameDefaults
		del self.guiScriptOutputText
		del self.guiShapeScriptButton
		del self.guiTGEAMaterial
		del self.guiLogOutputText
		del self.guiLogToOutputFolder
		del self.guiShowWarnErrPopup
		del self.guiWarnErrText


	def refreshAll(self):
		Prefs = DtsGlobals.Prefs
		self.guiShowWarnErrPopup.state = Prefs["ShowWarningErrorPopup"]

	def handleEvent(self, control):
		Prefs = DtsGlobals.Prefs
		if control.name == "guiShapeScriptButton":
			Prefs['WriteShapeScript'] = control.state
		elif control.name == "guiShowWarnErrPopup":
			Prefs["ShowWarningErrorPopup"] = control.state
		elif control.name == "guiCustomFilename":
			Prefs['exportBasename'] = SceneInfoClass.fileNameFromPath(control.value)
			Prefs['exportBasepath'] = SceneInfoClass.pathPortion(control.value)
			if self.guiCustomFilename.value[len(self.guiCustomFilename.value)-4:] != ".dts":
				self.guiCustomFilename.value += ".dts"

			if Prefs['LogToOutputFolder']:
				pathSep = DtsGlobals.SceneInfo.getPathSeparator()
				Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSep, Prefs['exportBasename']) )
		elif control.name == "guiCustomFilenameSelect":
			pathSep = DtsGlobals.SceneInfo.getPathSeparator()
			Blender.Window.FileSelector (self.guiGeneralSelectorCallback, 'Select destination and filename', Prefs['exportBasepath'] + pathSep + Prefs['exportBasename'])
		elif control.name == "guiCustomFilenameDefaults":
			Prefs['exportBasename'] = SceneInfoClass.getDefaultBaseName()
			Prefs['exportBasepath'] = SceneInfoClass.getDefaultBasePath()
			pathSep = DtsGlobals.SceneInfo.getPathSeparator()
			self.guiCustomFilename.value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']
			if self.guiCustomFilename.value[len(self.guiCustomFilename.value)-4:] != ".dts":
				self.guiCustomFilename.value += ".dts"
		elif control.name == "guiTGEAMaterial":
			Prefs['TSEMaterial'] = control.state

		elif control.name == "guiLogToOutputFolder":
			Prefs['LogToOutputFolder'] = control.state
			if control.state:
				pathSep = DtsGlobals.SceneInfo.getPathSeparator()
				Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSep, Prefs['exportBasename']) )
			else:
				Torque_Util.dump_setout("%s.log" % Prefs['exportBasename'])
			Prefs['exportBasename']

		
	def resize(self, control, newwidth, newheight):
		if control.name == "guiOutputText":
			control.x, control.y, control.width = 10,newheight-45-control.height, 220
		elif control.name == "guiCustomFilename":
			#control.x, control.y, control.width = 10,newheight-60-control.height, 220
			control.x, control.y, control.width = 10,newheight-60-control.height, 370
		elif control.name == "guiCustomFilenameSelect":
			control.x, control.y, control.width = 382,newheight-60-control.height, 55
		elif control.name == "guiCustomFilenameDefaults":
			control.x, control.y, control.width = 439,newheight-60-control.height, 55
		elif control.name == "guiScriptOutputText":
			control.x, control.y, control.width = 10,newheight-125-control.height, 220
		elif control.name == "guiShapeScriptButton":
			control.x, control.y, control.width = 10,newheight-140-control.height, 132
		elif control.name == "guiTGEAMaterial":
			control.x, control.y, control.width = 157,newheight-140-control.height, 182
		elif control.name == "guiLogOutputText":
			control.x, control.y, control.width = 10,newheight-205-control.height, 220
		elif control.name == "guiLogToOutputFolder":
			control.x, control.y, control.width = 10,newheight-220-control.height, 182
		elif control.name == "guiWarnErrText":
			control.x, control.y, control.width = 10,newheight-285-control.height, 220
		elif control.name == "guiShowWarnErrPopup":
			control.x, control.y, control.width = 10,newheight-300-control.height, 220

	
	def guiGeneralSelectorCallback(self, filename):
		global guiGeneralSubtab
		Prefs = DtsGlobals.Prefs
		if filename != "":
			Prefs['exportBasename'] = SceneInfoClass.fileNameFromPath(filename)
			Prefs['exportBasepath'] = SceneInfoClass.pathPortion(filename)
			pathSep = DtsGlobals.SceneInfo.getPathSeparator()
			self.guiCustomFilename.value = Prefs['exportBasepath'] + pathSep + Prefs['exportBasename']
			if self.guiCustomFilename.value[len(self.guiCustomFilename.value)-4:] != ".dts":
				self.guiCustomFilename.value += ".dts"
