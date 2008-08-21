'''
VisAnim.py

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
import Blender


# helper functions for VisControlsClass

## @brief Returns a list of IPO channel types that are selectable for use in visibility animations
def getIPOChannelTypes(IPOType):
	typesDict = {	"Object": ["LocX", "LocY", "LocZ", "dLocX", "dLocY", "dLocZ", "RotX", "RotY", "RotZ", "dRotX", "dRotY", "dRotZ", "ScaleX", "ScaleY", "ScaleZ", "dScaleX", "dScaleY", "dScaleZ", "Layer", "Time", "ColR", "ColG", "ColB", "ColA", "FSteng", "FFall", "RDamp", "Damping", "Perm"],\
			"Material":["R", "G", "B", "SpecR", "SpecG", "SpecB", "MirR", "MirG", "MirB", "Ref", "Alpha", "Emit", "Amb", "Spec", "Hard"],\
		    }
	try: retVal = typesDict[IPOType]
	except: retVal = []
	return retVal
	
## @brief Returns a list of all objects or materials in the scene.
#  @param IPOType What we want.  Valid values are "Object" or "Material"
def getAllSceneObjectNames(IPOType):
	scene = Blender.Scene.GetCurrent()
	retVal = []
	if IPOType == "Object":
		allObjs = Blender.Object.Get()
		for obj in allObjs:
			retVal.append(obj.name)
	elif IPOType == "Material":
		allObjs = Blender.Material.Get()
		for obj in allObjs:
			retVal.append(obj.name)

	return retVal
	
## @Brief Returns a list of all the bones in an armature
#  @param armature The name of the armature.
def getArmBoneNames(armature):
	try: arm = Blender.Armature.Get(armature)
	except: return []
	retVal = []
	for bone in arm.bones.keys():
		retVal.append(bone)
	return retVal


# ***************************************************************************************************
## @brief Class that creates and owns the GUI controls on the Visibility sub-panel of the Sequences panel.
#
#  This class contains event handler and resize callbacks for it's associated GUI controls, along
#  with implementations of refreshSequenceOptions, clearSequenceOptions, and addNewAnim specific to its
#  controls.
#
class VisControlsClass(UserCreatedSeqControlsClassBase):


	#######################################
	#  init and cleanup methods
	#######################################


	## @brief Initialize the controls and values that are specific to this panel
	#  @note Calls parent init method
	#  @param tabContainer The GUI tab container control into which everything should be placed.
	def __init__(self, tabContainer):
		self.animationTypeString = "Visibility"
		self.shortAnimationTypeString = "Vis"
		UserCreatedSeqControlsClassBase.__init__(self, tabContainer)
		
		self.seqFilter = "Vis"
		
		# panel state
		self.curSeqListEvent = 40
		self.curVisTrackEvent = 80

		# initialize GUI controls
		self.guiVisTrackListTxt = Common_Gui.SimpleText("guiVisTrackListTxt", "Object Visibility Tracks:", None, self.guiVisTrackListTxtResize)
		self.guiVisTrackList = Common_Gui.ListContainer("guiVisTrackList", "", self.handleGuiVisTrackListEvent, self.guiVisTrackListResize)
		self.guiVisTrackListContainer = Common_Gui.BasicContainer("guiVisTrackListContainer", "", None, self.guiVisTrackListContainerResize)
		self.guiIpoTypeTxt = Common_Gui.SimpleText("guiIpoTypeTxt", "IPO Type:", None, self.guiIpoTypeTxtResize)
		self.guiIpoType = Common_Gui.ComboBox("guiIpoType", "IPO Type", "Select the type of IPO curve to use for Visibility Animation", self.getNextEvent(), self.handleGuiIpoTypeEvent, self.guiIpoTypeResize)
		self.guiIpoChannelTxt = Common_Gui.SimpleText("guiIpoChannelTxt", "IPO Channel:", None, self.guiIpoChannelTxtResize)
		self.guiIpoChannel = Common_Gui.ComboBox("guiIpoChannel", "IPO Channel", "Select the IPO curve to use for Visibility Animation", self.getNextEvent(), self.handleGuiIpoChannelEvent, self.guiIpoChannelResize)
		self.guiIpoObjectTxt = Common_Gui.SimpleText("guiIpoObjectTxt", "IPO Object:", None, self.guiIpoObjectTxtResize)
		self.guiIpoObject = Common_Gui.ComboBox("guiIpoObject", "IPO Object", "Select the object whose IPO curve will be used for Visibility Animation", self.getNextEvent(), self.handleGuiIpoObjectEvent, self.guiIpoObjectResize)

		self.guiTrackListContainerTitle = Common_Gui.MultilineText("guiTrackListContainerTitle", "Selected object:\n None Selected", None, self.guiTrackListContainerTitleResize)
		self.guiTrackListContainerTitleBox = Common_Gui.BasicFrame(resize_callback = self.guiTrackListContainerTitleBoxResize)


		# set initial states
		self.guiVisTrackList.enabled = True


		# add controls to containers
		self.guiSeqOptsContainer.addControl(self.guiVisTrackListTxt)
		self.guiSeqOptsContainer.addControl(self.guiVisTrackList)
		self.guiSeqOptsContainer.addControl(self.guiVisTrackList)
		self.guiSeqOptsContainer.addControl(self.guiVisTrackListContainer)
		self.guiVisTrackListContainer.addControl(self.guiTrackListContainerTitle)
		self.guiVisTrackListContainer.addControl(self.guiTrackListContainerTitleBox)
		self.guiVisTrackListContainer.addControl(self.guiIpoTypeTxt)
		self.guiVisTrackListContainer.addControl(self.guiIpoChannelTxt)
		self.guiVisTrackListContainer.addControl(self.guiIpoObjectTxt)
		self.guiVisTrackListContainer.addControl(self.guiIpoType)
		self.guiVisTrackListContainer.addControl(self.guiIpoChannel)
		self.guiVisTrackListContainer.addControl(self.guiIpoObject)

		## @brief Stores a string corresponding to the last object visibility track selection
		#  @note Used to restore the selection on panel switches.
		self.lastVisTrackListSelection = ""
		
	## @brief Cleans up Blender GUI objects before the interpreter exits;
	#     we must destroy any GUI objects that are referenced in a non-global scope
	#     explicitly before interpreter shutdown to avoid the dreaded
	#     "error totblock" message when exiting Blender.
	#  @note The builtin __del__ method is not guaranteed to be called for objects
	#     that still exist when the interpreter exits.
	#  @note Calls base class cleanup method explicitly.
	def cleanup(self):
		UserCreatedSeqControlsClassBase.cleanup(self)
		del self.guiVisTrackListTxt
		del self.guiVisTrackList
		del self.guiVisTrackListContainer
		del self.guiIpoTypeTxt
		del self.guiIpoType
		del self.guiIpoChannelTxt
		del self.guiIpoChannel
		del self.guiIpoObjectTxt
		del self.guiIpoObject
		del self.guiTrackListContainerTitle
		del self.guiTrackListContainerTitleBox


	#######################################
	#  Event handler methods
	#######################################



	## @brief Handle events generated by the "Ipo Type" menu (guiIpoType).
	#  @param control The invoking GUI control (guiIpoType)
	def handleGuiIpoTypeEvent(self, control):
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		IpoType = self.guiIpoType.getSelectedItemString()
		if IpoType == "":
			self.clearIpoCurvePulldown()
			self.clearIpoObjectPulldown()
			return
		objName = self.getVisTrackListSelectedItem()
		seqPrefs['Vis']['Tracks'][objName]['IPOType'] = IpoType
		seqPrefs['Vis']['Tracks'][objName]['IPOChannel'] = None
		seqPrefs['Vis']['Tracks'][objName]['IPOObject'] = None
		self.refreshIpoControls(seqPrefs)

	## @brief Handle events generated by the "Ipo Channel" menu (guiIpoChannel).
	#  @param control The invoking GUI control (guiIpoChannel)
	def handleGuiIpoChannelEvent(self, control):
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		objName = self.getVisTrackListSelectedItem()
		channel = self.guiIpoChannel.getSelectedItemString()
		seqPrefs['Vis']['Tracks'][objName]['IPOChannel'] = channel

	## @brief Handle events generated by the "Ipo Object/Material" menu (guiIpoObject).
	#  @param control The invoking GUI control (guiIpoObject)
	def handleGuiIpoObjectEvent(self, control):
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		objName = self.getVisTrackListSelectedItem()
		type = self.guiIpoType.getSelectedItemString()
		if control.itemIndex > -1:
			seqPrefs['Vis']['Tracks'][objName]['IPOObject'] = self.guiIpoObject.getSelectedItemString()
		

	## @brief Handle list selection events generated by the "Object Visibility Tracks" list (guiVisTrackList).
	#  @param control The invoking GUI control (guiVisTrackList)
	def handleGuiVisTrackListEvent(self, control):
		curSelection = self.getVisTrackListSelectedItem()
		if curSelection != "":
			self.lastVisTrackListSelection = curSelection
		if self.guiVisTrackList.itemIndex != -1:
			seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
			self.guiIpoType.enabled = True
			self.guiIpoChannel.enabled = True
			self.guiIpoObject.enabled = True
			self.refreshIpoControls(seqPrefs)
		else:
			self.guiIpoType.enabled = False
			self.guiIpoChannel.enabled = False
			self.guiIpoObject.enabled = False
			self.clearIpoControls()

	## @brief Handle list events generated by the "Object Visibility Tracks" items list enable buttons (guiVisTrackListItem).
	#  @param control The invoking GUI control (guiVisTrackListItem)
	def handleGuiVisTrackListItemEvent(self, control):
		Prefs = DtsGlobals.Prefs
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		#objName = self.getVisTrackListSelectedItem()
		objName = self.guiVisTrackList.controls[control.evt - 80].controls[0].label
		if control.state:
			# create the track if we need to
			try: x = seqPrefs['Vis']['Tracks'][objName]
			except:
				Prefs.createVisTrackKey(objName, seqName)
				Prefs['Sequences'][seqName]['Vis']['Tracks'][objName]['hasVisTrack'] = True
		else:
			# delete the vis track key.
			Prefs.deleteVisTrackKey(objName, seqName)


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
		self.refreshVisTrackList(seqName)
		self.guiSeqOptsContainerTitle.label = ("Selected Sequence:\n %s" % seqName)
		# restore last vis track list selection
		found = False
		for i in range(0,len(self.guiVisTrackList.controls)):
			listItem = self.guiVisTrackList.controls[i]
			if listItem.controls[0].label == self.lastVisTrackListSelection:
				self.guiVisTrackList.selectItem(i)				
				found = True
				break
		if not found: self.guiVisTrackList.selectItem(0)
		self.guiVisTrackList.scrollToSelectedItem()
		self.refreshIpoControls(seqPrefs)


	## @brief Clears sequence specific option controls on the right side of the sequences panel.
	#  @note Overrides parent class "virtual" method.
	def clearSequenceOptions(self):
		self.guiSeqOptsContainer.enabled = False
		self.clearVisTrackList()
		self.guiSeqOptsContainerTitle.label = "Selected Sequence:\n None Selected"
		self.clearIpoControls()

	## @brief Refreshes the 3 Ipo selection pulldown menus
	#  @note Called when object visibility track list selection is changed.
	#  @note A valid list Vis track list item must be selected prior to
	#     calling this method.
	#  @param seqPrefs The prefs key of the currently selected sequence
	def refreshIpoControls(self, seqPrefs):
		# do we have a valid track key?
		foundKey = True
		objName = self.getVisTrackListSelectedItem()
		try: x = seqPrefs['Vis']['Tracks'][objName]
		except: foundKey = False
		if not foundKey:
			self.clearIpoControls()
			self.guiIpoType.enabled = False
			self.guiIpoChannel.enabled = False
			self.guiIpoObject.enabled = False
			return
		# refresh our pulldowns		
		IpoType = seqPrefs['Vis']['Tracks'][objName]['IPOType']
		self.refreshIpoTypePulldown()		
		self.refreshIpoObjectPulldown(IpoType)
		self.refreshIpoCurvePulldown(IpoType)
		# select stuff
		self.guiIpoType.setTextValue(seqPrefs['Vis']['Tracks'][objName]['IPOType'])
		self.guiIpoChannel.setTextValue(seqPrefs['Vis']['Tracks'][objName]['IPOChannel'])
		self.guiIpoObject.setTextValue(seqPrefs['Vis']['Tracks'][objName]['IPOObject'])
		# enable stuff
		self.guiIpoType.enabled = True
		self.guiIpoChannel.enabled = True
		self.guiIpoObject.enabled = True
		# update label
		if type == "Object":
			self.guiIpoObjectTxt.label = "IPO Object:"
		elif type == "Material":
			self.guiIpoObjectTxt.label = "IPO Material:"

	## @brief Clears all 3 Ipo selection menus
	def clearIpoControls(self):
		self.clearIpoTypePulldown()
		self.clearIpoObjectPulldown()
		self.clearIpoCurvePulldown()
		
	## @brief Refreshes the Ipo type pulldown menu
	def refreshIpoTypePulldown(self):		
		self.clearIpoTypePulldown()
		typeList = ["Object", "Material"]
		for type in typeList:
			self.guiIpoType.items.append(type)

	## @brief Clears the Ipo type pulldown menu
	def clearIpoTypePulldown(self):
		self.guiIpoType.itemIndex = -1
		self.guiIpoType.items = []
	
	## @brief Refreshes the Ipo object pulldown menu
	#  @param IpoType The type of IPO curve we're looking for, either "Object" or "Material"
	def refreshIpoObjectPulldown(self, IpoType):
		self.clearIpoObjectPulldown()
		objs = getAllSceneObjectNames(IpoType)
		objs.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for obj in objs:
			self.guiIpoObject.items.append(obj)

	## @brief Clears the Ipo object pulldown menu
	def clearIpoObjectPulldown(self):
		self.guiIpoObject.itemIndex = -1
		self.guiIpoObject.items = []

	## @brief Refreshes the Ipo curve pulldown menu
	#  @param IpoType The type of IPO curve we're looking for, either "Object" or "Material"
	def refreshIpoCurvePulldown(self, IpoType):
		self.clearIpoCurvePulldown()
		for chann in getIPOChannelTypes(IpoType):
			self.guiIpoChannel.items.append(chann)

	## @brief Clears the Ipo curve pulldown menu
	def clearIpoCurvePulldown(self):
		self.guiIpoChannel.itemIndex = -1
		self.guiIpoChannel.items = []

	## @brief Refreshes the visibility track list
	#  @param seqName The name of the currently selected sequence
	def refreshVisTrackList(self, seqName):
		Prefs = DtsGlobals.Prefs
		SceneInfo = DtsGlobals.SceneInfo
		self.clearVisTrackList()		
		# loop through all objects, and sort into two lists
		enabledList = []
		disabledList = []
		for objName in SceneInfo.getDtsObjectNames():
			if objName == "Bounds": continue
			# process mesh objects
			# add an entry in the track list for the mesh object.
			#self.guiVisTrackList.addControl(self.createVisTrackListItem(obj.name))
			# set the state of the enabled button
			try: enabled = Prefs['Sequences'][seqName]['Vis']['Tracks'][objName]['hasVisTrack']
			except: enabled = False
			if enabled: enabledList.append(objName)
			else: disabledList.append(objName)

		# sort, then combine lists
		enabledList.sort(lambda x, y: cmp(x.lower(),y.lower()))
		disabledList.sort(lambda x, y: cmp(x.lower(),y.lower()))
		combinedList = enabledList + disabledList

		# add everything in the combined list
		for item in combinedList:
			self.guiVisTrackList.addControl(self.createVisTrackListItem(item))
			try: self.guiVisTrackList.controls[-1].controls[1].state = Prefs['Sequences'][seqName]['Vis']['Tracks'][item]['hasVisTrack']
			except: self.guiVisTrackList.controls[-1].controls[1].state = False

	## @brief Clears the object visibility track list
	def clearVisTrackList(self):
		for i in range(0, len(self.guiVisTrackList.controls)):
			del self.guiVisTrackList.controls[i].controls[:]
		del self.guiVisTrackList.controls[:]

		self.guiVisTrackList.itemIndex = -1
		self.guiVisTrackList.scrollPosition = 0
		self.curVisTrackEvent = 80
		if self.guiVisTrackList.callback: self.guiVisTrackList.callback(self.guiVisTrackList) # Bit of a hack, but works


	#########################
	#  Misc / utility methods
	#########################


	## @brief Adds a new Visibility sequence in the GUI and the prefs
	#  @note Overrides parent class "virtual" method.
	#  @param newSeqName The name of the sequence
	def addNewAnim(self, newSeqName):
		Prefs = DtsGlobals.Prefs
		# add vis pref key w/ default values
		seq = Prefs['Sequences'][newSeqName]
		seq['Vis'] = {}
		seq['Vis']['Enabled'] = True
		seq['Vis']['Tracks'] = {}
		# add sequence to GUI sequence list		
		#self.guiSeqList.addControl(self.createSequenceListItem(seqName))
		# refresh the Image frames list
		#self.populateVisTrackList(seqName)
		# re-populate the sequence list
		self.refreshSequenceList()
		# Select the new sequence.
		self.selectSequence(newSeqName)

	## @brief Creates an object visibility track list item
	#  @param objName The name of the object.
	def createVisTrackListItem(self, objName):
		startEvent = self.curVisTrackEvent
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SimpleText("", objName, None, None)
		guiName.x, guiName.y = 5, 5
		guiEnable = Common_Gui.ToggleButton("guiEnable", "Enable", "Enable Visibility track for object", startEvent, self.handleGuiVisTrackListItemEvent, None)
		guiEnable.x, guiEnable.y = 105, 5
		guiEnable.width, guiEnable.height = 50, 15


		# Add everything
		guiContainer.addControl(guiName)
		guiContainer.addControl(guiEnable)
		
		self.curVisTrackEvent += 1
		return guiContainer

	## @brief Returns a string corresponding to the currently selected vis track list item.
	def getVisTrackListSelectedItem(self):
		if self.guiVisTrackList.itemIndex != -1:
			return self.guiVisTrackList.controls[self.guiVisTrackList.itemIndex].controls[0].label
		else: return ""


	#########################
	#  Resize callback methods
	#########################

	

	## @brief Resize callback for guiVisTrackListTxt
	#  @param control The invoking GUI control object
	def guiVisTrackListTxtResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,190, 20,120

	## @brief Resize callback for guiVisTrackList
	#  @param control The invoking GUI control object
	def guiVisTrackListResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 20,10, 173,175

	def guiVisTrackListContainerResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 196,10, 173,newwidth - 196
	
	def guiTrackListContainerTitleBoxResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 3,newheight-35, 33,107

	def guiTrackListContainerTitleResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-30, 20,82

	## @brief Resize callback for guiIpoTypeTxt
	#  @param control The invoking GUI control object
	def guiIpoTypeTxtResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,newheight-50, 20,newwidth-20

	## @brief Resize callback for guiIpoType
	#  @param control The invoking GUI control object
	def guiIpoTypeResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-75, 20,newwidth-10

	## @brief Resize callback for ChannelTxt
	#  @param control The invoking GUI control object
	def guiIpoChannelTxtResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,newheight-95, 20,newwidth-20

	## @brief Resize callback for guiIpoChannel
	#  @param control The invoking GUI control object
	def guiIpoChannelResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-120, 20,newwidth-10

	## @brief Resize callback for guiIpoObjectTxt
	#  @param control The invoking GUI control object
	def guiIpoObjectTxtResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 10,newheight-140, 20,newwidth-20

	## @brief Resize callback for guiIpoObject
	#  @param control The invoking GUI control object
	def guiIpoObjectResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-165, 20,newwidth-10
