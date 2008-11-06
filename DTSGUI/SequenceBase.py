'''
SequenceBase.py

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

# ***************************************************************************************************
## @brief Base Class For sequence control sub-panel classes.
#
# This class implements functionality that is common to all sequence sub panels.
#
class SeqControlsClassBase:
	## @brief Initialize the controls and values that are common to all sequence control panels.
	#  @note Child classes should call this method explicitly at the beginning of their own __init__ methods.
	#  @param tabContainer The GUI tab container control into which everything should be placed.
	def __init__(self, tabContainer):
		self.startEvent = 5
		# initialize GUI controls
		self.guiSeqList = Common_Gui.ListContainer("guiSeqList", "sequence.list", self.handleListEvent, self.guiSeqListResize)
		self.guiSeqListTitle = Common_Gui.SimpleText("guiSeqListTitle", "All Sequences:", None, self.guiSeqListTitleResize)
		self.guiSeqOptsContainerTitle = Common_Gui.MultilineText("guiSeqOptsContainerTitle", "Selected Sequence:\n None Selected", None, self.guiSeqOptsContainerTitleResize)
		self.guiSeqOptsContainerTitleBox = Common_Gui.BasicFrame(resize_callback = self.guiSeqOptsContainerTitleBoxResize)
		self.guiSeqOptsContainer = Common_Gui.BasicContainer("guiSeqOptsContainer", "guiSeqOptsContainer", None, self.guiSeqOptsContainerResize)
		
		# set initial states
		self.guiSeqOptsContainer.enabled = False
		self.guiSeqOptsContainer.fade_mode = 5
		self.guiSeqOptsContainer.borderColor = None
		self.guiSeqList.fade_mode = 0
		

		# add controls to containers
		self.guiSeqOptsContainer.addControl(self.guiSeqOptsContainerTitle)
		self.guiSeqOptsContainer.addControl(self.guiSeqOptsContainerTitleBox)
		tabContainer.addControl(self.guiSeqOptsContainer)
		tabContainer.addControl(self.guiSeqList)
		tabContainer.addControl(self.guiSeqListTitle)
	
		## Need to set this explicitly in child classes
		#  @note valid values are: "All", "Action", "IFL", "Vis" and eventually "TexUV" and "Morph"
		self.seqFilter = "All"


	## @brief Gets an event ID # for native Blender controls that need one.  We don't actually
	#     use these, but most native controls must have one.
	#  @note Most child classes should be able to inherit this method and use it as-is
	def getNextEvent(self):
		retVal = self.startEvent
		self.startEvent += 1
		return retVal

	## @brief Gets the name of the sequence currently selected in the sequence list
	#  @note Most child classes should be able to inherit this method and use it as-is
	def getSelectedSeqNameAndPrefs(self):
		Prefs = DtsGlobals.Prefs
		if self.guiSeqList.itemIndex == -1: return None, None
		try:
			seqName = self.guiSeqList.controls[self.guiSeqList.itemIndex].controls[0].label
			seqPrefs = Prefs['Sequences'][seqName]
		except:
			return None, None
		return seqName, seqPrefs

	## @brief Selects the desired sequence in the list
	#  @note If the sequence is not found, nothing happens.
	#  @note Most child classes should be able to inherit this method and use it as-is
	#  @param selectThis string name of sequence to select.
	def selectSequence(self, selectThis):
		for i in range(0,len(self.guiSeqList.controls)):
			seqName = self.guiSeqList.controls[i].controls[0].label
			if seqName == selectThis:
				self.guiSeqList.selectItem(i)
				self.guiSeqList.scrollToSelectedItem()
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
				return

	## @brief Cleans up Blender GUI objects before the interpreter exits;
	#     we must destroy any GUI objects that are referenced in a non-global scope
	#     explicitly before interpreter shutdown to avoid the dreaded
	#     "error totblock" message when exiting Blender.
	#  @note The builtin __del__ method is not guaranteed to be called for objects
	#     that still exist when the interpreter exits.
	#  @note Child classes should explicitly call this method at the end of their own cleanup method.
	def cleanup(self):
		del self.guiSeqList
		del self.guiSeqListTitle
		del self.guiSeqOptsContainerTitle
		del self.guiSeqOptsContainer


	## @brief Refreshes all controls on the panel w/ fresh data from blender and the prefs.
	#  @note Most child classes should be able to inherit this method and use it as-is
	def refreshAll(self):
		# refresh action data and repopulate the sequence list		
		self.refreshSequenceList()

	
	## @brief Refreshes the items in the sequence list, preserving list selection if possible.
	#  @note Most child classes should be able to inherit this method and use it as-is
	def refreshSequenceList(self):
		Prefs = DtsGlobals.Prefs
		Prefs.refreshSequencePrefs()
		# store last sequence selection
		seqName = None
		seqPrefs = None
		if self.guiSeqList.itemIndex != -1:
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		else:
			# no valid selection, so select the first item in the list
			self.guiSeqList.selectItem(0)
			self.guiSeqList.scrollToSelectedItem()
			if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()

		# populateSequenceList automatically clears the sequence list first.
		self.populateSequenceList()

		# restore last sequence selection
		for itemIndex in range(0, len(self.guiSeqList.controls)):
			if self.guiSeqList.controls[itemIndex].controls[0].label == seqName:
				self.guiSeqList.selectItem(itemIndex)
				self.guiSeqList.scrollToSelectedItem()
				self.refreshSequenceOptions(seqName, seqPrefs)
				if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
				return
		self.guiSeqList.selectItem(0)
		self.guiSeqList.scrollToSelectedItem()
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList)
	
	## @brief Refreshes sequence specific option controls on the right side of the sequences panel.
	#  @note This method should be called whenever the sequence list is refreshed, or when sequence
	#     list selection changes.
	#  @note Must be overridden by child classes.
	#  @param seqName The name of the currently selected sequence.
	#  @param seqPrefs The preferences key of the currently selected sequence.
	def refreshSequenceOptions(self, seqName, seqPrefs):
		print "Parent refreshSequenceOptions called.  You probably forgot to implement it in your new child class :-)"
		pass

	## @brief Clears sequence specific option controls on the right side of the sequences panel.
	#  @note This method should be called when no sequence list item is currently selected.
	#  @note Must be overridden by child classes.
	def clearSequenceOptions(self):
		print "Parent clearSequenceOptions called.  You probably forgot to implement it in your new child class :-)"
		pass

	## @brief Updates GUI states when the sequence list item selection is changed.
	#  @note This method should only be called by the sequence list GUI control
	#     event handler callback mechanism.
	#  @note Most child classes should be able to inherit this method and use it as-is
	#  @param control The invoking GUI Control object (should be the sequence list control)
	def handleListEvent(self, control):
		if control.itemIndex != -1:
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
			self.refreshSequenceOptions(seqName, seqPrefs)
			self.guiSeqOptsContainerTitle.label = "Selected Sequence:\n '%s'" % seqName
			self.guiSeqOptsContainer.enabled = True
		else:
			self.clearSequenceOptions()
			self.guiSeqOptsContainer.enabled = False


	
	## @brief Updates relevant preferences when a sequence list item button state is changed.
	#  @note This method should only be called by the list item container's event handing mechanism
	#  @note Most child classes should be able to inherit this method and use it as-is
	#  @param control The invoking GUI Control object (should be a sequence list item container control)
	def handleListItemEvent(self, control):
		Prefs = DtsGlobals.Prefs
		ShowDSQButton = len(self.guiSeqList.controls[0].controls) == 4
		if ShowDSQButton: evtOffset = 3
		else: evtOffset = 2
		# Determine sequence name
		if control.evt == 40:
			calcIdx = 0
		else:
			calcIdx = (control.evt - 40) / evtOffset

		# Must use calcIdx here instead of self.getSelectedSeqNameAndPrefs()
		# because the user can click on a list button even when the list item
		# isn't selected.
		seqName = self.guiSeqList.controls[calcIdx].controls[0].label
		seqPrefs = Prefs['Sequences'][seqName]
		#seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		realItem = control.evt - 40 - (calcIdx*evtOffset)

		# no validation needed on these, so it's OK to set the prefs directly.
		if ShowDSQButton:
			if realItem == 0:
				seqPrefs['NoExport'] = not control.state
			elif realItem == 1:
				seqPrefs['Cyclic'] = control.state
			elif realItem == 2:
				seqPrefs['Dsq'] = control.state
				
		else:
			if realItem == 0:
				seqPrefs['NoExport'] = not control.state
			elif realItem == 1:
				seqPrefs['Cyclic'] = control.state



	def guiSeqButtonItemResize(self, control, newwidth, newheight):
		Prefs = DtsGlobals.Prefs
		listWidth = self.guiSeqList.width - self.guiSeqList.barWidth
		buttonWidth = 50
		numButtons = len(self.guiSeqList.controls[0].controls)-1
		buttonPos = []
		for i in range(1,numButtons+1): buttonPos.append(((listWidth - 5) - (buttonWidth*i + 1)))
		if control.name == "guiExport":
			pos = buttonPos[2]			
		elif control.name == "guiCyclic":
			pos = buttonPos[1]
		elif control.name == "guiDSQ":
			pos = buttonPos[0]
		
		control.x, control.y = pos, 5
		control.width, control.height = 50, 15





	## @brief Place holder resize callback
	#  @note Child classes should call override this method explicitly
	#  @param control The invoking GUI control object
	#  @param newwidth The new width of the GUI control in pixels.
	#  @param newheight The new height of the GUI control in pixels.
	def guiSeqListResize(self, control, newwidth, newheight):
		pass
		#control.x, control.y, control.height, control.width = 10,28, newheight - 68,230

	## @brief Place holder resize callback
	#  @note Child classes should call override this method explicitly
	#  @param control The invoking GUI control object
	#  @param newwidth The new width of the GUI control in pixels.
	#  @param newheight The new height of the GUI control in pixels.
	def guiSeqListTitleResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,310, 20,82
	## @brief Place holder resize callback
	#  @note Child classes should call override this method explicitly
	#  @param control The invoking GUI control object
	#  @param newwidth The new width of the GUI control in pixels.
	#  @param newheight The new height of the GUI control in pixels.
	def guiSeqOptsContainerResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 241,0, 334,249

	def guiSeqOptsContainerTitleResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-30, 20,82

	def guiSeqOptsContainerTitleBoxResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 3,newheight-35, 33,117

	## @brief Creates a sequence list item and it's associated GUI controls.
	#  @note If a child class needs to display a "DSQ" button, it should call 
	#     the parent version explicitly with the third parameter set to True from
	#     it's own createSequenceListItem method.
	#  @note Called by populateSequenceList, and methods of derived classes, as needed.
	#  @note Most child classes can inherit this method and just use it as-is.
	#  @param seqName The name of the sequence for which we're creating the list item.
	#  @param ShowDSQButton If true, a DSQ button is displayed in the list item.  If
	# false, no DSQ button is displayed.
	def createSequenceListItem(self, seqName, ShowButtons=False):
		Prefs = DtsGlobals.Prefs
		startEvent = self.curSeqListEvent
		listWidth = self.guiSeqList.width - self.guiSeqList.barWidth
		buttonWidth = 50
		numButtons = 0
		if ShowButtons: numButtons = 3
		# Note on positions:
		# It quicker to assign these here, as there is no realistic chance of scaling being required.
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiName = Common_Gui.SimpleText("", seqName, None, None)
		if ShowButtons:
			guiExport = Common_Gui.ToggleButton("guiExport", "Export", "Export Sequence", startEvent, self.handleListItemEvent, self.guiSeqButtonItemResize)
			guiCyclic = Common_Gui.ToggleButton("guiCyclic", "Cyclic", "Export Sequence as Cyclic", startEvent+1, self.handleListItemEvent, self.guiSeqButtonItemResize)
			guiDSQ = Common_Gui.ToggleButton("guiDSQ", "Dsq", "Export Sequence as DSQ", startEvent+2, self.handleListItemEvent, self.guiSeqButtonItemResize)

		guiContainer.fade_mode = 0  # flat color

		guiContainer.addControl(guiName)
		guiName.x, guiName.y = 5, 5
		
		if numButtons == 3:
			# Add everything
			guiContainer.addControl(guiExport)
			guiContainer.addControl(guiCyclic)
			guiContainer.addControl(guiDSQ)
		
			guiExport.state = not Prefs['Sequences'][seqName]['NoExport']
			guiCyclic.state = Prefs['Sequences'][seqName]['Cyclic']
			guiDSQ.state = Prefs['Sequences'][seqName]['Dsq']
		
			# increment the current event counter
			self.curSeqListEvent += 3
		else:
			self.curSeqListEvent += 1
		
		return guiContainer

	## @brief Populates the sequence list using current pref values.
	def populateSequenceList(self):
		self.clearSequenceList()
		Prefs = DtsGlobals.Prefs
		#if self.guiSeqList.width == 0: return
		# loop through all actions in the preferences
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seqPrefs = Prefs['Sequences'][seqName]
			if self.seqFilter == "All":				
				self.guiSeqList.addControl(self.createSequenceListItem(seqName))
			elif seqPrefs[self.seqFilter]['Enabled']:
				self.guiSeqList.addControl(self.createSequenceListItem(seqName))

	
	## @brief Clears the sequence list.
	def clearSequenceList(self):
		for i in range(0, len(self.guiSeqList.controls)):
			del self.guiSeqList.controls[i].controls[:]
		del self.guiSeqList.controls[:]
		self.curSeqListEvent = 40
		self.guiSeqList.itemIndex = -1
		self.guiSeqList.scrollPosition = 0
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList) # Bit of a hack, but works

