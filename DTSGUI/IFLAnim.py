'''
IFLAnim.py

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

from UserAnimBase import *

# ***************************************************************************************************
## @brief Class that creates and owns the GUI controls on the IFL sub-panel of the Sequences panel.
#
#  This class contains event handler and resize callbacks for it's associated GUI controls, along
#  with implementations of refreshSequenceOptions, clearSequenceOptions, and addNewAnim specific to its
#  controls.
#
class IFLControlsClass(UserCreatedSeqControlsClassBase):


	#######################################
	#  init and cleanup methods
	#######################################


	## @brief Initialize the controls and values that are specific to this panel
	#  @note Calls parent init method
	#  @param tabContainer The GUI tab container control into which everything should be placed.
	def __init__(self, tabContainer):
		self.animationTypeString = "IFL"
		self.shortAnimationTypeString = "IFL"
		UserCreatedSeqControlsClassBase.__init__(self, tabContainer)

		## Need to set this in all classes derived from SeqControlsClassBase
		#  @note valid values are: "All", "Action", "IFL", "Vis" and eventually "TexUV" and "Morph"
		self.seqFilter = "IFL"

		

		#self.guiMatTxt = Common_Gui.SimpleText("guiMatTxt", "IFL Material:", None, self.guiMatTxtResize)
		self.guiMat = Common_Gui.ComboBox("guiMat", "IFL Material", "Select a Material from this list to use in the IFL Animation", self.getNextEvent(), self.handleGuiMatEvent, self.guiMatResize)
		self.guiNumImages = Common_Gui.NumberPicker("guiNumImages", "Images", "Number of Images in the IFL animation", self.getNextEvent(), self.handleGuiNumImagesEvent, self.guiNumImagesResize)
		self.guiFramesListTxt = Common_Gui.SimpleText("guiFramesListTxt", "Images:", None, self.guiFramesListTxtResize)
		self.guiFramesList = Common_Gui.ListContainer("guiFramesList", "", self.handleGuiFrameListEvent, self.guiFramesListResize)
		self.guiFramesListContainer = Common_Gui.BasicContainer("guiFramesListContainer", "", None, self.guiFramesListContainerResize)
		self.guiFramesListSelectedTxt = Common_Gui.SimpleText("guiFramesListSelectedTxt", "Hold image for:", None, self.guiFramesListSelectedTxtResize)
		self.guiNumFrames = Common_Gui.NumberPicker("guiNumFrames", "Frames", "Hold Selected image for n frames", self.getNextEvent(), self.handleGuiNumFramesEvent, self.guiNumFramesResize)
		self.guiApplyToAll = Common_Gui.BasicButton("guiApplyToAll", "Apply to all", "Apply current frame display value to all IFL images", self.getNextEvent(), self.handleGuiApplyToAllEvent, self.guiApplyToAllResize)
		self.guiWriteIFLFile = Common_Gui.ToggleButton("guiWriteIFLFile", "Write .ifl file", "Write .ifl file for this sequence to disk upon export.", self.getNextEvent(), self.handleGuiWriteIFLFileEvent, self.guiWriteIFLFileResize)

		#self.guiFramesListContainerTitle = Common_Gui.MultilineText("guiFramesListContainerTitle", "Selected image:\n None Selected", None, self.guiSeqOptsContainerTitleResize)
		#self.guiFramesListContainerTitleBox = Common_Gui.BasicFrame(resize_callback = self.guiFramesListContainerTitleBoxResize)
		self.guiFrameSelectedBoxLabel = Common_Gui.BoxSelectionLabel("guiFrameSelectedBoxLabel", "Selected image:\n None Selected", None, self.guiFrameSelectedBoxLabelResize)

		# set initial states
		self.guiFramesList.enabled = True
		self.guiNumImages.min = 1
		self.guiNumFrames.min = 1
		self.guiNumImages.value = 1
		self.guiNumFrames.value = 1
		self.guiNumFrames.max = 65535 # <- reasonable?  I wonder if anyone wants to do day/night cycles with IFL? - Joe G.
		self.guiWriteIFLFile.state = False

		# add controls to containers
		#self.guiSeqOptsContainer.addControl(self.guiMatTxt)
		self.guiSeqOptsContainer.addControl(self.guiMat)
		self.guiSeqOptsContainer.addControl(self.guiNumImages)
		self.guiSeqOptsContainer.addControl(self.guiFramesListTxt)
		self.guiSeqOptsContainer.addControl(self.guiFramesList)
		self.guiSeqOptsContainer.addControl(self.guiFramesListContainer)
		self.guiSeqOptsContainer.addControl(self.guiWriteIFLFile)
		#self.guiFramesListContainer.addControl(self.guiFramesListContainerTitle)
		#self.guiFramesListContainer.addControl(self.guiFramesListContainerTitleBox)
		self.guiFramesListContainer.addControl(self.guiFrameSelectedBoxLabel)
		self.guiFramesListContainer.addControl(self.guiFramesListSelectedTxt)
		self.guiFramesListContainer.addControl(self.guiNumFrames)
		self.guiFramesListContainer.addControl(self.guiApplyToAll)
		
		
	
	## @brief Cleans up Blender GUI objects before the interpreter exits;
	#     we must destroy any GUI objects that are referenced in a non-global scope
	#     explicitly before interpreter shutdown to avoid the dreaded
	#     "error totblock" message when exiting Blender.
	#  @note The builtin __del__ method is not guaranteed to be called for objects
	#     that still exist when the interpreter exits.
	#  @note Calls base class cleanup method explicitly.
	def cleanup(self):
		UserCreatedSeqControlsClassBase.cleanup(self)
		#del self.guiMatTxt
		del self.guiMat
		del self.guiNumImages
		del self.guiFramesListTxt
		del self.guiFramesList
		del self.guiFramesListSelectedTxt
		del self.guiNumFrames
		del self.guiApplyToAll
		del self.guiWriteIFLFile
		#del self.guiFramesListContainerTitle
		#del self.guiFramesListContainerTitleBox
		del self.guiFrameSelectedBoxLabel


	#######################################
	#  Event handler methods
	#######################################


	## @brief Handle events generated by the "Images" number picker (guiNumImages).
	#  @param control The invoking GUI control (guiNumImages)
	def handleGuiNumImagesEvent(self, control):
		Prefs = DtsGlobals.Prefs
		if self.guiMat.itemIndex < 0:
			control.value = 1
			return

		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		newCount = control.value
		holdCount = self.guiNumFrames.value
		Prefs.changeSeqIFLImageCount(seqName, newCount, holdCount)
		self.refreshImageFramesList(seqName)



	## @brief Handle events generated by the "Select IFL Material" menu (guiMat).
	#  @param control The invoking GUI control (guiMat)
	def handleGuiMatEvent(self, control):
		Prefs = DtsGlobals.Prefs
		guiSeqList = self.guiSeqList
		guiMat = self.guiMat
		itemIndex = guiMat.itemIndex
		# set the pref for the selected sequence
		if guiSeqList.itemIndex > -1 and itemIndex >=0 and itemIndex < len(guiMat.items):
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
			matName = control.getSelectedItemString()
			# ifl material name changed
			if Prefs['Sequences'][seqName]['IFL']['Material'] != matName:
				# rename images
				Prefs.changeSeqIFLMaterial(seqName, matName)
				# make frames if we don't have any yet.
				Prefs.changeSeqIFLImageCount(seqName, self.guiNumImages.value, self.guiNumFrames.value)
				#Prefs['Sequences'][seqName]['IFL']['Material'] = control.getSelectedItemString()				
				self.refreshImageFramesList(seqName)

	## @brief Handle events generated by the "Frames" number picker (guiNumFrames).
	#  @param control The invoking GUI control (guiNumFrames)
	def handleGuiNumFramesEvent(self, control):
		guiSeqList = self.guiSeqList
		guiFramesList = self.guiFramesList
		if guiFramesList.itemIndex > -1:
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
			itemIndex = guiFramesList.itemIndex
			seqPrefs['IFL']['IFLFrames'][itemIndex][1] = control.value
			guiFramesList.controls[guiFramesList.itemIndex].controls[1].label = "fr:" + str(control.value)
			if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works

	## @brief Handle events generated by the "Apply to all" button (guiApplyToAll).
	#  @param control The invoking GUI control (guiApplyToAll)
	def handleGuiApplyToAllEvent(self, control):
		guiSeqList = self.guiSeqList
		guiFramesList = self.guiFramesList
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		itemIndex = guiFramesList.itemIndex
		for i in range(0, len(seqPrefs['IFL']['IFLFrames'])):				
			seqPrefs['IFL']['IFLFrames'][i][1] = self.guiNumFrames.value
			guiFramesList.controls[i].controls[1].label = "fr:" + str(self.guiNumFrames.value)
		if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works

	## @brief Handle events generated by the "Write .ifl file" button (guiWriteIFLFile).
	#  @param control The invoking GUI control (guiWriteIFLFile)
	def handleGuiWriteIFLFileEvent(self, control):
		if self.guiSeqList.itemIndex > -1:
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
			seqPrefs['IFL']['WriteIFLFile'] = control.state

	## @brief Handle events generated by the "IFL Image Frames" list (guiFramesList).
	#  @param control The invoking GUI control (guiFramesList)
	def handleGuiFrameListEvent(self, control):
		guiFramesList = self.guiFramesList
		guiNumFrames = self.guiNumFrames
		if control.itemIndex > -1:
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
			guiNumFrames.value = seqPrefs['IFL']['IFLFrames'][control.itemIndex][1]
			curImageName = seqPrefs['IFL']['IFLFrames'][control.itemIndex][0]
			if curImageName != "" and curImageName != None:
				self.guiFrameSelectedBoxLabel.text = ("Selected image:\n \'%s\'" % curImageName)
			#else:
			#	self.guiFrameSelectedBoxLabel.text = "Selected image:\n None Selected"
		else:
			guiNumFrames.value = 1
			self.guiFrameSelectedBoxLabel.text = "Selected image:\n None Selected"
		
	## @brief Handle events generated by the "Remove Visibility from selected" button
	#  @param control The invoking GUI control (guiSeqDelFromExisting)
	def handleGuiSeqDelFromExistingEvent(self, control):
		Prefs = DtsGlobals.Prefs
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		Prefs.delIFLAnim(seqName)
		self.refreshAll()
	#######################################
	#  Refresh and Clear methods
	#######################################


	## @brief Refreshes sequence specific option controls on the right side of the sequences panel.
	#  @note This method should be called whenever the sequence list is refreshed, or when sequence
	#     list selection changes.
	#  @note Overrides parent class "virtual" method.
	#  @param seqName The name of the currently selected sequence.
	#  @param seqPrefs The preferences key of the currently selected sequence.
	def refreshSequenceOptions(self, seqName, seqPrefs):
		self.guiSeqOptsContainer.enabled = True
		self.guiSeqOptsContainer.visible = True
		self.refreshIFLMatPulldown()
		self.guiMat.selectStringItem(seqPrefs['IFL']['Material'])
		self.guiNumImages.value = seqPrefs['IFL']['NumImages']
		try: self.guiNumFrames.value = seqPrefs['IFL']['IFLFrames'][1]
		except: self.guiNumFrames.value = 1
		self.refreshImageFramesList(seqName)
		#self.guiSeqOptsContainerTitle.label = ("Selected Sequence:\n %s" % seqName)
		self.guiSeqSelectedBoxLabel.text = ("Selected Sequence:\n %s" % seqName)
		self.guiWriteIFLFile.state = seqPrefs['IFL']['WriteIFLFile']


	## @brief Clears sequence specific option controls on the right side of the sequences panel.
	#  @note Overrides parent class "virtual" method.
	#  @note This method should be called when no sequence list item is currently selected.
	def clearSequenceOptions(self):
		self.guiSeqOptsContainer.enabled = False		
		self.guiMat.selectStringItem("")
		self.guiNumImages.value = 1
		self.guiNumFrames.value = 1
		self.clearImageFramesList()
		self.guiNumFrames.value = 1
		self.guiSeqOptsContainer.enabled = False
		#self.guiSeqOptsContainerTitle.label = "Selected Sequence:\n None Selected"
		self.guiSeqSelectedBoxLabel.text = "Selected Sequence:\n None Selected"
		self.guiWriteIFLFile.state = False			

	## @brief Clears the list of IFL image frames
	def clearIFLList(self):
		for i in range(0, len(self.guiSeqList.controls)):
			del self.guiSeqList.controls[i].controls[:]
		del self.guiSeqList.controls[:]
		self.curSeqListEvent = 40
		self.guiSeqList.itemIndex = -1
		self.guiSeqList.scrollPosition = 0
		if self.guiSeqList.callback: self.guiSeqList.callback(self.guiSeqList) # Bit of a hack, but works

	
	## @brief Refreshes the items in the IFL material menu.
	def refreshIFLMatPulldown(self):
		self.clearIFLMatPulldown()
		# loop through all materials in the preferences and check for IFL materials
		Prefs = DtsGlobals.Prefs
		try: x = Prefs['Materials'].keys()
		except: Prefs['Materials'] = {}
		keys = Prefs['Materials'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for matName in Prefs['Materials'].keys():
			mat = Prefs['Materials'][matName]
			try: x = mat['IFLMaterial']
			except KeyError: mat['IFLMaterial'] = False
			if mat['IFLMaterial'] == True:
				self.guiMat.items.append(matName)

	## @brief Clears the items in the IFL material menu.
	def clearIFLMatPulldown(self):
		self.guiMat.itemIndex = -1
		self.guiMat.items = []

	
	## @brief Refreshes the items in the IFL Image Frames list based on current pref settings
	def refreshImageFramesList(self, seqName):
		Prefs = DtsGlobals.Prefs
		self.clearImageFramesList()
		guiFramesList = self.guiFramesList
		
		IFLMat = Prefs['Sequences'][seqName]['IFL']['IFLFrames']
		for fr in IFLMat:
			guiFramesList.addControl(self.createFramesListItem(fr[0], fr[1]))


	## @brief Clears the items in the IFL Image Frames list
	def clearImageFramesList(self):
		for i in range(0, len(self.guiFramesList.controls)):
			del self.guiFramesList.controls[i].controls[:]
		del self.guiFramesList.controls[:]
		self.guiFramesList.itemIndex = -1
		self.guiFramesList.scrollPosition = 0
		if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works


	#########################
	#  Misc / utility methods
	#########################


	## @brief Adds a new IFL sequence in the GUI and the prefs
	#  @note Overrides parent class "virtual" method.
	def addNewAnim(self, seqName):
		Prefs = DtsGlobals.Prefs		
		# add ifl pref key w/ default values
		Prefs.addIFLAnim(seqName)
		# re-populate the sequence list
		self.populateSequenceList()
		# Select the new sequence.
		self.selectSequence(seqName)


	## @brief Creates a list item for the IFL Image Frames List
	#  @param matName The name of the current IFL material
	#  @param holdFrames The number of frames for which the image is to be displayed.
	def createFramesListItem(self, matName, holdFrames = 1):
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", matName, None, None)
		guiName.x, guiName.y = 5, 5
		guiHoldFrames = Common_Gui.SimpleText("", "fr:"+ str(holdFrames), None, None)
		guiHoldFrames.x, guiHoldFrames.y = 140, 5

		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiHoldFrames)
		return guiContainer
	
		

	## @brief Removes the last item from the frames list box
	def removeLastItemFromFrameList(self):
		i = len(self.guiFramesList.controls)-1
		try:
			del self.guiFramesList.controls[i].controls[:]
			del self.guiFramesList.controls[i]
		except IndexError: pass
		self.guiFramesList.itemIndex = -1
		self.guiFramesList.scrollPosition = 0
		if self.guiFramesList.callback: self.guiFramesList.callback(self.guiFramesList) # Bit of a hack, but works


	#########################
	#  Resize callback methods
	#########################

	
	'''
	## @brief Resize callback for guiMatTxt
	#  @param control The invoking GUI control object
	def guiMatTxtResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,278, 20,120
	'''
	## @brief Resize callback for guiMat
	#  @param control The invoking GUI control object
	def guiMatResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 125,newheight-50, 20,115
		control.x, control.y, control.height, control.width = 10,newheight-60, 20,120


	## @brief Resize callback for guiNumImages
	#  @param control The invoking GUI control object
	def guiNumImagesResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 245,newheight-50, 20,85
		control.x, control.y, control.height, control.width = 132,newheight-60, 20,90

	## @brief Resize callback for guiSeqIFLFrame
	#  @param control The invoking GUI control object
	def guiSeqIFLFrameResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 64,211, 20,120

	## @brief Resize callback for guiSeqIFLImageBox
	#  @param control The invoking GUI control object
	def guiSeqIFLImageBoxResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 4,5, 220,241

	## @brief Resize callback for guiSeqImageName
	#  @param control The invoking GUI control object
	def guiSeqImageNameResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 15,183, 20,219

	## @brief Resize callback for guiFramesListTxt
	#  @param control The invoking GUI control object
	def guiFramesListTxtResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 10,190, 20,120
		control.x, control.y, control.height, control.width = 10,168, 20,120

	## @brief Resize callback for guiFramesList
	#  @param control The invoking GUI control object
	def guiFramesListResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 20,10, 173,200
		#control.x, control.y, control.height, control.width = 10,10, 173,185
		control.x, control.y, control.height, control.width = 10,10, 153,185

	def guiFramesListContainerResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 221,10, 173,newwidth-221
		#control.x, control.y, control.height, control.width = 196,10, 173,newwidth - 206
		control.x, control.y, control.height, control.width = 196,10, 153,newwidth - 206
	
	def guiFrameSelectedBoxLabelResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-35, 33,107

	#def guiFramesListContainerTitleResize(self, control, newwidth, newheight):
	#	control.x, control.y, control.height, control.width = 5,newheight-30, 20,82

	## @brief Resize callback for guiFramesListSelectedTxt
	#  @param control The invoking GUI control object
	def guiFramesListSelectedTxtResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-60, 20,120

	## @brief Resize callback for guiNumFrames
	#  @param control The invoking GUI control object
	def guiNumFramesResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-88, 20,newwidth-10

	## @brief Resize callback for guiApplyToAll
	#  @param control The invoking GUI control object
	def guiApplyToAllResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-114, 20,newwidth-10

	## @brief Resize callback for guiWriteIFLFile
	#  @param control The invoking GUI control object
	def guiWriteIFLFileResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 125,newheight-25, 20,75
		control.x, control.y, control.height, control.width = 232,newheight-60, 20,80
