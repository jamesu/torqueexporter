'''
DetailLevels.py

Copyright (c) 2008 Joseph Greenawalt(jsgreenawalt@gmail.com)

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
from DtsPrefs import *

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Detail Levels control page
*
***************************************************************************************************
'''
class DetailLevelControlsClass:
	

	#######################################
	#  init and cleanup methods
	#######################################


	def __init__(self, guiDetailLevelsSubtab):
		global globalEvents

		# panel state
		self.curListEvent = 40
		
		# initialize GUI controls
		self.guiDetailLevelsListTitle = Common_Gui.SimpleText("guiDetailLevelsListTitle", "Detail Levels:", None, self.guiDetailLevelsListTitleResize)
		self.guiDetailLevelsList = Common_Gui.ListContainer("guiDetailLevelsList", "dl.list", self.handleEvent, self.guiDetailLevelsListResize)		
		self.guiDetailLevelsAddButton = Common_Gui.BasicButton("guiDetailLevelsAddButton", "Add:", "Add a new detail level of the indicated type", 5, self.handleAddEvent, self.guiDetailLevelsAddButtonResize)
		self.guiDetailLevelsTypeMenu = Common_Gui.ComboBox("guiDetailLevelsTypeMenu", "Type", "Select the type of detail level to add", 6, self.handleEvent, self.guiDetailLevelsTypeMenuResize)
		self.guiDetailLevelsDelButton = Common_Gui.BasicButton("guiDetailLevelsDelButton", "Delete Selected Detail Level", "Import Blender materials and settings", 7, self.handleDelEvent, self.guiDetailLevelsDelButtonResize)
		
		# set default values for controls
		self.guiDetailLevelsList.childHeight = 30
		
		# add controls to containers
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsListTitle)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsList)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsAddButton)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsTypeMenu)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsDelButton)
		
		self.populateDLList()
		self.populateTypePulldown()
		

	def cleanup(self):

		# Must destroy any GUI objects that are referenced in a non-global scope
		# explicitly before interpreter shutdown to avoid the dreaded
		# "error totblock" message when exiting Blender.
		# Note: __del__ is not guaranteed to be called for objects that still
		# exist when the interpreter exits.
		
		# todo - clean up objects
		pass

		

	#######################################
	#  Event handler methods
	#######################################


	def handleEvent(self, control):
		pass
		
	def handleAddEvent(self, control):
		Prefs = DtsGlobals.Prefs
		DLType = self.guiDetailLevelsTypeMenu.getSelectedItemString()
		dlName = None
		size = None
		if DLType == "Visible Detail Level":
			dlName = "Detail"
		elif DLType == "Collision Detail Level":
			dlName = "Collision"
			size = -1
		elif DLType == "LOS Col Detail Level":
			dlName = "LOSCollision"
			size = -1
			
		Prefs.addDetailLevel(dlName, size)
		self.populateDLList()

	def handleDelEvent(self, control):
		Prefs = DtsGlobals.Prefs
		dlName = self.getDLListSelectedItem()
		
		# todo - are you sure dialog?
		Prefs.delDetailLevel(dlName)
		self.populateDLList()

	
	def handleListItemEvent(self, control):
		Prefs = DtsGlobals.Prefs
		evtOffset = 21
		# Determine DL name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / evtOffset
		pass
		dlName = self.guiDetailLevelsList.controls[calcIdx].controls[0].label
		realItem = control.evt - 40 - (calcIdx*evtOffset)
		# get the shift state
		shiftState = Common_Gui.shiftState
		
		# a layer button was clicked		
		if realItem > 0 and realItem < 21:
			# if shifted, click does not affect other layer buttons in the DL
			if shiftState:
				# button pressed
				if control.state:
					# assign the layer to the detail level
					Prefs.setLayerAssignment(dlName, realItem)
				# button un-pressed
				else:
					#Remove layer from this dl
					Prefs.removeLayerAssignment(realItem)

			# if not shifted, click turns all other layer buttons off
			else:
				# clear other layers assigned to this dl
				Prefs['DetailLevels'][dlName] = []
				Prefs.setLayerAssignment(dlName, realItem)
				# clear button states
				for i in range(1,21):
					if i == realItem:						
						control.state = True
					else:
						self.guiDetailLevelsList.controls[calcIdx].controls[i].state = False
				control.state = True

		# size was changed
		elif realItem == 0:
			# rename detail level
			newName = Prefs.getTextPortion(dlName)
			newName += str(control.value)
			if newName != dlName:
				if Prefs.renameDetailLevel(dlName, newName):
					self.guiDetailLevelsList.controls[calcIdx].controls[0].label = newName
				else:
					control.value = int(Prefs.getTrailingNumber(dlName))
				
	#######################################
	#  Refresh and Clear methods
	#######################################

	def refreshAll(self):
		self.populateDLList()


	#########################
	#  Resize callback methods
	#########################

		
	# resize events
	def guiDetailLevelsListTitleResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,270, 20,150
	def guiDetailLevelsListResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,45, newheight - 120, newwidth - 20
	def guiDetailLevelsAddButtonResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,295, 20,50
	def guiDetailLevelsTypeMenuResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 62,295, 20,150
	def guiDetailLevelsDelButtonResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,15, 20,180




	
	#########################
	#  Misc / utility methods
	#########################

	## @brief Creates a detail level list item and its associated GUI controls.
	#  @note Called by populateDLList
	#  @param dlName The name of the sequence for which we're creating the list item.
	def createDLListItem(self, dlName):
		Prefs = DtsGlobals.Prefs
		DLPrefs = Prefs['DetailLevels'][dlName]
		DLType = prefsClass.getTextPortion(dlName)
		startEvent = self.curListEvent
		listWidth = self.guiDetailLevelsList.width - self.guiDetailLevelsList.barWidth
		
		guiContainer = Common_Gui.BasicContainer("", None, None)		
		guiName = Common_Gui.SimpleText("", dlName, None, None)
		guiLayersLabel = Common_Gui.SimpleText("", "Use Layers:", None, None)
		guiSize = Common_Gui.NumberPicker("guiSize", "Min Pixel Size:", "Height in pixels at which detail level begins to display", startEvent, self.handleListItemEvent, None)
		guiSize.value = Prefs.getTrailingNumber(dlName)
		if DLType == 'Detail':
			guiSize.min = 0
			guiSize.max = 1024
		elif DLType == 'Collision' or DLType == 'LOSCollision':
			guiSize.min = -1
			guiSize.max = -1
			guiSize.enabled = False

		#getTextPortion(dlName)
		startEvent += 1

		# create layer buttons
		guiLayerButton = []
		for i in range(1,21):
			# create the button
			guiLayerButton.append(Common_Gui.ToggleButton("guiLayer"+str(i), "", "Use Layer "+str(i) + " in Detail Level", startEvent + i - 1, self.handleListItemEvent, None))
			if i in DLPrefs:
				# turn on the button
				guiLayerButton[len(guiLayerButton)-1].state = True
			else:
				# turn the button off
				guiLayerButton[len(guiLayerButton)-1].state = False
		

		guiContainer.fade_mode = 0  # flat color

		guiName.x, guiName.y = 5, 8
		guiSize.x, guiSize.y = 100, 5
		guiLayersLabel.x, guiLayersLabel.y = 270, 8

		# todo - clean this up :-)
		
		buttonWidth = 10
		# position buttons in groups of 5
		buttonsStartX = 340
		buttonsStartY = 15
		buttonPos = buttonsStartX
		for i in range(0,5):
			guiLayerButton[i].x, guiLayerButton[i].y = buttonPos, buttonsStartY
			guiLayerButton[i].width = buttonWidth
			guiLayerButton[i].height = buttonWidth
			buttonPos += buttonWidth

		buttonsStartX = 340
		buttonsStartY = 5
		buttonPos = buttonsStartX
		for i in range(5,10):
			guiLayerButton[i].x, guiLayerButton[i].y = buttonPos, buttonsStartY
			guiLayerButton[i].width = buttonWidth
			guiLayerButton[i].height = buttonWidth
			buttonPos += buttonWidth

		buttonsStartX = 395
		buttonsStartY = 15
		buttonPos = buttonsStartX
		for i in range(10,15):
			guiLayerButton[i].x, guiLayerButton[i].y = buttonPos, buttonsStartY
			guiLayerButton[i].width = buttonWidth
			guiLayerButton[i].height = buttonWidth
			buttonPos += buttonWidth

		buttonsStartX = 395
		buttonsStartY = 5
		buttonPos = buttonsStartX
		for i in range(15,20):
			guiLayerButton[i].x, guiLayerButton[i].y = buttonPos, buttonsStartY
			guiLayerButton[i].width = buttonWidth
			guiLayerButton[i].height = buttonWidth
			buttonPos += buttonWidth
		
		# Add everything
		guiContainer.addControl(guiName)
		
		for i in range(0,20):
			guiContainer.addControl(guiLayerButton[i])

		guiContainer.addControl(guiSize)
		guiContainer.addControl(guiLayersLabel)

		
		# increment the current event counter
		self.curListEvent += 21
		
		return guiContainer

	## @brief Populates the sequence list using current pref values.
	def populateDLList(self):
		Prefs = DtsGlobals.Prefs
		self.clearDLList()
		# Force a  list resize event, to make sure our button offsets
		# are correct.
		#if self.guiDetailLevelsList.width == 0: return
		# loop through all detail levels in the preferences
		Prefs = DtsGlobals.Prefs
		keys = Prefs['DetailLevels'].keys()
		keys.sort(lambda x, y: cmp(prefsClass.getTrailingNumber(x),prefsClass.getTrailingNumber(y)))
		keys.reverse()
		for dlName in keys:			
			self.guiDetailLevelsList.addControl(self.createDLListItem(dlName))

	def clearDLList(self):
		for i in range(0, len(self.guiDetailLevelsList.controls)):
			del self.guiDetailLevelsList.controls[i].controls[:]
		del self.guiDetailLevelsList.controls[:]
		self.curListEvent = 40
		self.guiDetailLevelsList.itemIndex = -1
		self.guiDetailLevelsList.scrollPosition = 0
		if self.guiDetailLevelsList.callback: self.guiDetailLevelsList.callback(self.guiDetailLevelsList) # Bit of a hack, but works

	def populateTypePulldown(self):
		self.guiDetailLevelsTypeMenu.items.append("Visible Detail Level")
		self.guiDetailLevelsTypeMenu.items.append("Collision Detail Level")
		self.guiDetailLevelsTypeMenu.items.append("LOS Col Detail Level")
		self.guiDetailLevelsTypeMenu.selectStringItem("Visible Detail Level")

	## @brief Returns a string corresponding to the currently selected vis track list item.
	def getDLListSelectedItem(self):
		if self.guiDetailLevelsList.itemIndex != -1:
			return self.guiDetailLevelsList.controls[self.guiDetailLevelsList.itemIndex].controls[0].label
		else: return ""
