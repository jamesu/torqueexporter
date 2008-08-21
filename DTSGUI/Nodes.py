'''
Nodes.py

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

import re

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Armatures sub-panel.
*
***************************************************************************************************
'''
class NodeControlsClass:
	def __init__(self, guiNodeListSubtab):
		global globalEvents

		# initialize GUI controls
		self.guiNodeText = Common_Gui.SimpleText("guiNodeText", "Nodes that should be exported :", None, self.resize)
		self.guiNodeList = Common_Gui.BoneListContainer("guiNodeList", None, None, self.resize)
		self.guiMatchText =  Common_Gui.SimpleText("guiMatchText", "Match pattern", None, self.resize)
		self.guiPatternText = Common_Gui.TextBox("guiPatternText", "", "pattern to match bone names, asterix is wildcard", 6, self.handleEvent, self.resize)
		self.guiPatternOn = Common_Gui.BasicButton("guiPatternOn", "On", "Turn on export of bones matching pattern", 7, self.handleEvent, self.resize)
		self.guiPatternOff = Common_Gui.BasicButton("guiPatternOff", "Off", "Turn off export of bones matching pattern", 8, self.handleEvent, self.resize)
		self.guiRefresh = Common_Gui.BasicButton("guiRefresh", "Refresh", "Refresh bones list", 9, self.handleEvent, self.resize)
				
		# set initial states
		self.guiPatternText.value = "*"
		
		# add controls to containers
		guiNodeListSubtab.addControl(self.guiNodeText)
		guiNodeListSubtab.addControl(self.guiNodeList)
		guiNodeListSubtab.addControl(self.guiMatchText)
		guiNodeListSubtab.addControl(self.guiPatternText)
		guiNodeListSubtab.addControl(self.guiPatternOn)
		guiNodeListSubtab.addControl(self.guiPatternOff)
		guiNodeListSubtab.addControl(self.guiRefresh)
		
		# populate bone grid
		self.populateNodeGrid()
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiNodeText
		del self.guiNodeList
		del self.guiMatchText
		del self.guiPatternText
		del self.guiPatternOn
		del self.guiPatternOff
		del self.guiRefresh


	
	def refreshAll(self):
		pass

	def handleEvent(self, control):
		guiNodeList = self.guiNodeList
		guiPatternText = self.guiPatternText
		Prefs = DtsGlobals.Prefs
		SceneInfo = DtsGlobals.SceneInfo
		if control.name == "guiPatternOn" or control.name == "guiPatternOff":
			userPattern = self.guiPatternText.value
			# convert to uppercase
			userPattern = userPattern.upper()
			newPat = re.sub("\\*", ".*", userPattern)
			if newPat[-1] != '*':
				newPat += '$'
			for name in SceneInfo.getAllNodeNames():
				name = name.upper()
				if re.match(newPat, name) != None:				
					if control.name == "guiPatternOn":
						for i in range(len(Prefs['BannedNodes'])-1, -1, -1):
							boneName = Prefs['BannedNodes'][i].upper()
							if name == boneName:
								del Prefs['BannedNodes'][i]
					elif control.name == "guiPatternOff":
						Prefs['BannedNodes'].append(name)
			self.clearBoneGrid()
			self.populateNodeGrid()
		elif control.name == "guiRefresh":
			self.clearBoneGrid()
			self.populateNodeGrid()

	def resize(self, control, newwidth, newheight):
		if control.name == "guiNodeText":
			control.x, control.y = 10,newheight-20
		elif control.name == "guiNodeList":
			#control.x, control.y, control.width, control.height = 10,70, 470,242
			control.x, control.y = 10, 90
			control.width, control.height = newwidth - 20, newheight-120
		elif control.name == "guiMatchText":
			control.x, control.y = 10,newheight-285
		elif control.name == "guiPatternText":
			control.x, control.y, control.width = 10,newheight-315, 70
		elif control.name == "guiPatternOn":
			control.x, control.y, control.width = 84,newheight-315, 35
		elif control.name == "guiPatternOff":
			control.x, control.y, control.width = 121,newheight-315, 35
		elif control.name == "guiRefresh":
			control.x, control.y, control.width = 400,newheight-315, 75

	def guiNodeListItemCallback(self, control):
		global guiSeqActList
		Prefs = DtsGlobals.Prefs
		# Determine id of clicked button
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) #/ 4
		real_name = control.text.upper()
		if control.state:
			# Remove entry from BannedNodes
			for i in range(0, len(Prefs['BannedNodes'])):
				if Prefs['BannedNodes'][i] == real_name:
					del Prefs['BannedNodes'][i]
					break
		else:
			Prefs['BannedNodes'].append(real_name)

	def createBoneListitem(self, bone1, bone2, bone3, bone4, bone5, startEvent):
		#seqPrefs = getSequenceKey(seq_name)
		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0
		guiContainer.borderColor = None
		if bone1 != None:
			guiBone1 = Common_Gui.ToggleButton("guiBone_" + bone1, bone1, "Toggle Status of " + bone1, startEvent, self.guiNodeListItemCallback, None)
			guiBone1.x, guiBone1.y = 1, 0
			guiBone1.width, guiBone1.height = 90, 19
			guiBone1.state = True
			guiContainer.addControl(guiBone1)
		if bone2 != None:
			guiBone2 = Common_Gui.ToggleButton("guiBone_" + bone2, bone2, "Toggle Status of " + bone2, startEvent+1, self.guiNodeListItemCallback, None)
			guiBone2.x, guiBone2.y = 92, 0
			guiBone2.width, guiBone2.height = 90, 19
			guiBone2.state = True
			guiContainer.addControl(guiBone2)
		if bone3 != None:
			guiBone3 = Common_Gui.ToggleButton("guiBone_" + bone3, bone3, "Toggle Status of " + bone3, startEvent+3, self.guiNodeListItemCallback, None)
			guiBone3.x, guiBone3.y = 183, 0
			guiBone3.width, guiBone3.height = 90, 19
			guiBone3.state = True
			guiContainer.addControl(guiBone3)
		if bone4 != None:
			guiBone4 = Common_Gui.ToggleButton("guiBone_" + bone4, bone4, "Toggle Status of " + bone4, startEvent+4, self.guiNodeListItemCallback, None)
			guiBone4.x, guiBone4.y = 274, 0
			guiBone4.width, guiBone4.height = 89, 19
			guiBone4.state = True
			guiContainer.addControl(guiBone4)	
		if bone5 != None:
			guiBone5 = Common_Gui.ToggleButton("guiBone_" + bone5, bone5, "Toggle Status of " + bone5, startEvent+5, self.guiNodeListItemCallback, None)
			guiBone5.x, guiBone5.y = 364, 0
			guiBone5.width, guiBone5.height = 89, 19
			guiBone5.state = True
			guiContainer.addControl(guiBone5)
		return guiContainer

	def populateNodeGrid(self):
		global export_tree, guiNodeList
		SceneInfo = DtsGlobals.SceneInfo
		Prefs = DtsGlobals.Prefs
		evtNo = 40
		count = 0
		names = []
		for name in SceneInfo.getAllNodeNames():
			names.append(name)
			if len(names) == 5:
				self.guiNodeList.addControl(self.createBoneListitem(names[0],names[1],names[2],names[3],names[4], evtNo))
				self.guiNodeList.controls[count].controls[0].state = not (self.guiNodeList.controls[count].controls[0].text.upper() in Prefs['BannedNodes'])
				self.guiNodeList.controls[count].controls[1].state = not (self.guiNodeList.controls[count].controls[1].text.upper() in Prefs['BannedNodes'])
				self.guiNodeList.controls[count].controls[2].state = not (self.guiNodeList.controls[count].controls[2].text.upper() in Prefs['BannedNodes'])
				self.guiNodeList.controls[count].controls[3].state = not (self.guiNodeList.controls[count].controls[3].text.upper() in Prefs['BannedNodes'])
				self.guiNodeList.controls[count].controls[4].state = not (self.guiNodeList.controls[count].controls[4].text.upper() in Prefs['BannedNodes'])

				evtNo += 6
				count += 1
				names = []
		# add leftovers in last row
		if len(names) > 0:
			for i in range(len(names)-1, 5):
				names.append(None)
			self.guiNodeList.addControl(self.createBoneListitem(names[0],names[1],names[2],names[3], names[4], evtNo))
			if names[0] != None: self.guiNodeList.controls[count].controls[0].state = not (self.guiNodeList.controls[count].controls[0].text.upper() in Prefs['BannedNodes'])
			if names[1] != None: self.guiNodeList.controls[count].controls[1].state = not (self.guiNodeList.controls[count].controls[1].text.upper() in Prefs['BannedNodes'])
			if names[2] != None: self.guiNodeList.controls[count].controls[2].state = not (self.guiNodeList.controls[count].controls[2].text.upper() in Prefs['BannedNodes'])
			if names[3] != None: self.guiNodeList.controls[count].controls[3].state = not (self.guiNodeList.controls[count].controls[3].text.upper() in Prefs['BannedNodes'])
			if names[4] != None: self.guiNodeList.controls[count].controls[4].state = not (self.guiNodeList.controls[count].controls[4].text.upper() in Prefs['BannedNodes'])


	def clearBoneGrid(self):
		global guiNodeList
		del self.guiNodeList.controls[:]
		#for control in self.guiNodeList.controls:
		#	del control
		

	def guiBoneGridCallback(self, control):
		Prefs = DtsGlobals.Prefs
		real_name = control.name.upper()
		if control.state:
			# Remove entry from BannedNodes
			for i in range(0, len(Prefs['BannedNodes'])):
				if Prefs['BannedNodes'][i] == real_name:
					del Prefs['BannedNodes'][i]
					break
		else:
			Prefs['BannedNodes'].append(real_name)
