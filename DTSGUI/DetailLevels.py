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

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Detail Levels control page
*
***************************************************************************************************
'''
class DetailLevelControlsClass:
	def __init__(self, guiDetailLevelsSubtab):
		global globalEvents

		# panel state
		self.curListEvent = 40
		
		# initialize GUI controls
		self.guiDetailLevelsListTitle = Common_Gui.SimpleText("guiDetailLevelsListTitle", "Detail Levels:", None, self.guiDetailLevelsListTitleResize)
		self.guiDetailLevelsList = Common_Gui.ListContainer("guiDetailLevelsList", "dl.list", self.handleEvent, self.guiDetailLevelsListResize)		
		self.guiDetailLevelsAddButton = Common_Gui.BasicButton("guiDetailLevelsAddButton", "Add:", "Add a new detail level of the indicated type", 1, self.handleEvent, self.guiDetailLevelsAddButtonResize)
		self.guiDetailLevelsTypeMenu = Common_Gui.ComboBox("guiDetailLevelsTypeMenu", "Type", "Select the type of detail level to add", 2, self.handleEvent, self.guiDetailLevelsTypeMenuResize)
		self.guiDetailLevelsDelButton = Common_Gui.BasicButton("guiDetailLevelsDelButton", "Delete Selected Detail Lvl", "Import Blender materials and settings", 3, self.handleEvent, self.guiDetailLevelsDelButtonResize)
		self.guiDetailLevelsSortButton = Common_Gui.BasicButton("guiDetailLevelsSortButton", "Sort List", "Sort the detail levels list", 4, self.handleEvent, self.guiDetailLevelsSortButtonResize)
		
		# set default values for controls
		self.guiDetailLevelsList.childHeight = 30
		
		# add controls to containers
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsListTitle)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsList)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsAddButton)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsTypeMenu)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsDelButton)
		guiDetailLevelsSubtab.addControl(self.guiDetailLevelsSortButton)
		
		self.populateDLList()
		

	def cleanup(self):

		# Must destroy any GUI objects that are referenced in a non-global scope
		# explicitly before interpreter shutdown to avoid the dreaded
		# "error totblock" message when exiting Blender.
		# Note: __del__ is not guaranteed to be called for objects that still
		# exist when the interpreter exits.
		
		# todo - clean up objects
		pass

	def refreshAll(self):
		pass
		
	def handleEvent(self, control):
		pass
	
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
				Prefs.renameDetailLevel(dlName, newName)
				self.guiDetailLevelsList.controls[calcIdx].controls[0].label = newName
				

		
	# resize events
	def guiDetailLevelsListTitleResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,310, 20,150
	def guiDetailLevelsListResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,50, newheight - 90, newwidth - 20
	def guiDetailLevelsAddButtonResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,15, 20,50
	def guiDetailLevelsTypeMenuResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 62,15, 20,150
	def guiDetailLevelsDelButtonResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 228,15, 20,160
	def guiDetailLevelsSortButtonResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = newwidth - 85,15, 20,75



	## @brief Creates a detail level list item and its associated GUI controls.
	#  @note Called by populateDLList
	#  @param dlName The name of the sequence for which we're creating the list item.
	def createDLListItem(self, dlName):
		Prefs = DtsGlobals.Prefs
		DLPrefs = Prefs['DetailLevels'][dlName]
		startEvent = self.curListEvent
		listWidth = self.guiDetailLevelsList.width - self.guiDetailLevelsList.barWidth
		
		guiContainer = Common_Gui.BasicContainer("", None, None)		
		guiName = Common_Gui.SimpleText("", dlName, None, None)
		guiLayersLabel = Common_Gui.SimpleText("", "Use Layers:", None, None)
		guiSize = Common_Gui.NumberPicker("guiSize", "Min Pixel Size:", "Height in pixels at which detail level begins to display", startEvent, self.handleListItemEvent, None)
		guiSize.value = Prefs.getTrailingNumber(dlName)
		guiSize.min = 1
		guiSize.max = 999
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
		#self.clearSequenceList()
		# Force a  list resize event, to make sure our button offsets
		# are correct.
		#if self.guiDetailLevelsList.width == 0: return
		# loop through all detail levels in the preferences
		Prefs = DtsGlobals.Prefs
		keys = Prefs['DetailLevels'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for dlName in keys:			
			self.guiDetailLevelsList.addControl(self.createDLListItem(dlName))

	
	# other event callbacks and helper methods go here.

