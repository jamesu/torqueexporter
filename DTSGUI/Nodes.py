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

		# number of items per line in the node list
		self.itemsPerLine = 4
		
		# initialize GUI controls
		self.guiNodeListLabel = Common_Gui.SimpleText("guiNodeListLabel", "Nodes that should be exported :", None, self.resize)
		self.guiNodeList = Common_Gui.BoneListContainer("guiNodeList", None, None, self.resize)
		self.guiMatchLabel =  Common_Gui.SimpleText("guiMatchLabel", "Match pattern", None, self.resize)
		self.guiPatternText = Common_Gui.TextBox("guiPatternText", "", "pattern to match bone names, asterix is wildcard", 6, self.handleEvent, self.resize)
		self.guiPatternOn = Common_Gui.BasicButton("guiPatternOn", "On", "Turn on export of bones matching pattern", 7, self.handleEvent, self.resize)
		self.guiPatternOff = Common_Gui.BasicButton("guiPatternOff", "Off", "Turn off export of bones matching pattern", 8, self.handleEvent, self.resize)
		self.guiNumItemsLabel = Common_Gui.SimpleText("guiNumItemsLabel", "List Display", None, self.resize)
		self.guiNumItemsSlider = Common_Gui.NumberPicker("guiNumItemsSlider", "Items per line:", "Number of items per line to display in the node list", 9, self.handleEvent, self.resize)
		self.guiMatchTypeLabel = Common_Gui.SimpleText("guiMatchTypeLabel", "Match by type", None, self.resize)
		self.guiMatchTypePulldown = Common_Gui.ComboBox("guiMatchTypePulldown", "Node Type", "Type of node to toggle", 10, self.handleEvent, self.resize)
		self.guiTypeOn = Common_Gui.BasicButton("guiTypeOn", "On", "Turn on export of nodes matching type", 11, self.handleEvent, self.resize)
		self.guiTypeOff = Common_Gui.BasicButton("guiTypeOff", "Off", "Turn off export of nodes matching pattern", 12, self.handleEvent, self.resize)

		self.guiRefresh = Common_Gui.BasicButton("guiRefresh", "Refresh", "Refresh bones list", 15, self.handleEvent, self.resize)
				
		# set initial states
		self.guiPatternText.value = "*"
		self.guiNumItemsSlider.value = 4
		self.guiNumItemsSlider.min = 1
		self.guiNumItemsSlider.max = 40
		self.guiMatchTypePulldown.items.append("Object Nodes")
		self.guiMatchTypePulldown.items.append("Bone Nodes")
		self.guiMatchTypePulldown.selectStringItem("Object Nodes")
		
		# add controls to containers
		guiNodeListSubtab.addControl(self.guiNodeListLabel)
		guiNodeListSubtab.addControl(self.guiNodeList)
		guiNodeListSubtab.addControl(self.guiMatchLabel)
		guiNodeListSubtab.addControl(self.guiPatternText)
		guiNodeListSubtab.addControl(self.guiPatternOn)
		guiNodeListSubtab.addControl(self.guiPatternOff)
		guiNodeListSubtab.addControl(self.guiNumItemsLabel)
		guiNodeListSubtab.addControl(self.guiNumItemsSlider)
		guiNodeListSubtab.addControl(self.guiMatchTypeLabel)
		guiNodeListSubtab.addControl(self.guiMatchTypePulldown)
		guiNodeListSubtab.addControl(self.guiTypeOn)
		guiNodeListSubtab.addControl(self.guiTypeOff)
		guiNodeListSubtab.addControl(self.guiRefresh)
		
		# populate node grid
		self.populateNodeGrid()
		
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiNodeListLabel
		del self.guiNodeList
		del self.guiMatchLabel
		del self.guiPatternText
		del self.guiPatternOn
		del self.guiPatternOff
		del self.guiNumItemsLabel
		del self.guiNumItemsSlider
		del self.guiMatchTypeLabel
		del self.guiMatchTypePulldown
		del self.guiTypeOn
		del self.guiTypeOff
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
			self.populateNodeGrid()
		elif control.name == "guiRefresh":
			self.populateNodeGrid()
		elif control.name == "guiNumItemsSlider":
			self.itemsPerLine = control.value
			self.populateNodeGrid()
		elif control.name == "guiTypeOn":
			typeStr = self.guiMatchTypePulldown.getSelectedItemString()
			if typeStr == "Object Nodes":
				nodeList = SceneInfo.getObjectNodeNames()
			else: nodeList = SceneInfo.getBoneNodeNames()			
			for name in nodeList:
				for i in range(len(Prefs['BannedNodes'])-1, -1, -1):
					boneName = Prefs['BannedNodes'][i].upper()
					if name.upper() == boneName:
						del Prefs['BannedNodes'][i]
			self.populateNodeGrid()
		elif control.name == "guiTypeOff":
			typeStr = self.guiMatchTypePulldown.getSelectedItemString()
			if typeStr == "Object Nodes":
				nodeList = SceneInfo.getObjectNodeNames()
			else: nodeList = SceneInfo.getBoneNodeNames()			
			for name in nodeList:
				Prefs['BannedNodes'].append(name.upper())
			self.populateNodeGrid()
		
	def resize(self, control, newwidth, newheight):
		if control.name == "guiNodeListLabel":
			control.x, control.y, control.height, control.width = 10,310, 20,82
		elif control.name == "guiNodeList":
			control.x = 10
			control.y = 92
			control.width, control.height = newwidth - 20, newheight-134
		elif control.name == "guiMatchLabel":
			control.x, control.y = 10,newheight-285
		elif control.name == "guiPatternText":
			control.x, control.y, control.width = 95,newheight-290, 100
		elif control.name == "guiPatternOn":
			control.x, control.y, control.width = 199,newheight-290, 35
		elif control.name == "guiPatternOff":
			control.x, control.y, control.width = 236,newheight-290, 35
		elif control.name == "guiMatchTypeLabel":
			control.x, control.y, control.width = 10,newheight-315, 150
		elif control.name == "guiMatchTypePulldown":
			control.x, control.y, control.width = 95,newheight-320, 100
		elif control.name == "guiTypeOn":
			control.x, control.y, control.width = 199,newheight-320, 35
		elif control.name == "guiTypeOff":
			control.x, control.y, control.width = 236,newheight-320, 35
		elif control.name == "guiNumItemsLabel":
			control.x, control.y, control.width = 355,newheight-285, 150
		elif control.name == "guiNumItemsSlider":
			control.x, control.y, control.width = 355,newheight-315, 125

		elif control.name == "guiRefresh":
			control.width = 75
			control.x = newwidth - (control.width + 10)
			control.y = newheight - (control.height + 10)
		
	def resizeListButton(self, control, newwidth, newheight):
		listWidth = self.guiNodeList.width
		buttonWidth = (listWidth-self.guiNodeList.barWidth)/self.itemsPerLine
		buttonHeight = self.guiNodeList.childHeight
		control.x, control.y = 1 + (control.columnNum*(buttonWidth)), 0
		control.width, control.height = buttonWidth, buttonHeight

	def guiNodeListItemCallback(self, control):
		Prefs = DtsGlobals.Prefs
		real_name = control.text.upper()
		if control.state:
			# Remove entry from BannedNodes
			for i in range(0, len(Prefs['BannedNodes'])):
				if Prefs['BannedNodes'][i] == real_name:
					del Prefs['BannedNodes'][i]
					break
		else:
			Prefs['BannedNodes'].append(real_name)

	# create a row of node buttons
	def createBoneListitem(self, boneNames, startEvent):
		if len(boneNames) == 0: return # don't even bother
		Prefs = DtsGlobals.Prefs
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0
		guiContainer.borderColor = None
		guiBones = []
		for i in range(0, len(boneNames)):
			boneName = boneNames[i]
			if boneName != None:
				guiBones.append(Common_Gui.ToggleButton("guiBone_" + boneName, boneName, "Toggle Status of " + boneName, startEvent+i, self.guiNodeListItemCallback, self.resizeListButton))
				guiBones[i].state = not (boneName.upper() in Prefs['BannedNodes'])
				guiBones[i].columnNum = i
				guiContainer.addControl(guiBones[i])

		
		return guiContainer
		

	def populateNodeGrid(self):
		self.clearBoneGrid()
		SceneInfo = DtsGlobals.SceneInfo
		evtNo = 40
		names = []
		# add one row at a time
		for name in SceneInfo.getAllNodeNames():
			names.append(name)
			if len(names) == self.itemsPerLine:
				self.guiNodeList.addControl(self.createBoneListitem(names, evtNo))
				evtNo += self.itemsPerLine
				names = []
		# add leftovers in last row
		if len(names) > 0:
			for i in range(len(names)-1, self.itemsPerLine):
				names.append(None)
			self.guiNodeList.addControl(self.createBoneListitem(names, evtNo))


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
