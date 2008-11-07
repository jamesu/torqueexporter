'''
UserAnimBase.py

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

from SequenceBase import *
import Blender

# ***************************************************************************************************
## @brief Base Class For sequence control sub-panel classes.
#
# This class implements functionality that is common to all sequence sub panels that allow for
#  user defined sequences (currently IFL and Visibility panels).  These sequences are not read
#  from blender's actions, and can be renamed, deleted, or added through the exporter GUI.
class UserCreatedSeqControlsClassBase(SeqControlsClassBase):


	#######################################
	#  init and cleanup methods
	#######################################


	## @brief Initialize the controls and values that are common to all sequence control panels.
	#  @note Child classes should call this method explicitly at the beginning of their own __init__ methods.
	#  @param tabContainer The GUI tab container control into which everything should be placed.
	def __init__(self, tabContainer):
		# initialize the base class
		SeqControlsClassBase.__init__(self, tabContainer)
		
		try: x = self.animationTypeString
		except: self.animationTypeString = "Unknown"
		try: x = self.shortAnimationTypeString
		except: self.shortAnimationTypeString = "Unk" # :-)

		# initialize GUI controls
		#self.guiSeqAddToExistingTxt = Common_Gui.SimpleText("guiSeqAddToExistingTxt", "Add " + self.shortAnimationTypeString + " anim to existing sequence:", None, self.guiSeqAddToExistingTxtResize)
		#self.guiSeqDelFromExistingTxt = Common_Gui.SimpleText("guiSeqDelFromExistingTxt", "Del " + self.shortAnimationTypeString + " Animation from selected seq:", None, self.guiSeqDelFromExistingTxtResize)
		self.guiSeqExistingSequences = Common_Gui.ComboBox("guiSeqExistingSequences", "Sequence", "Select a Sequence from this list to add a " + self.animationTypeString + " Animation", self.getNextEvent(), self.handleGuiSeqExistingSequencesEvent, self.guiSeqExistingSequencesResize)
		#self.guiSeqAddToExisting = Common_Gui.BasicButton("guiSeqAddToExisting", "Add " + self.animationTypeString, "Add an " + self.animationTypeString + " animation to an existing sequence.", self.getNextEvent(), self.handleGuiSeqAddToExistingEvent, self.guiSeqAddToExistingResize)
		self.guiSeqAddToExisting = Common_Gui.BasicButton("guiSeqAddToExisting", "Add " + self.shortAnimationTypeString + " anim to existing sequence:", "Add an " + self.animationTypeString + " animation to an existing sequence.", self.getNextEvent(), self.handleGuiSeqAddToExistingEvent, self.guiSeqAddToExistingResize)
		self.guiSeqDelFromExisting = Common_Gui.BasicButton("guiSeqDelFromExisting", "Remove " + self.animationTypeString + " anim from selected sequence", "Delete " + self.animationTypeString + " animation from selected sequence.", self.getNextEvent(), self.handleGuiSeqDelFromExistingEvent, self.guiSeqDelFromExistingResize)
		
		# add controls to containers
		#tabContainer.addControl(self.guiSeqAddToExistingTxt)
		#tabContainer.addControl(self.guiSeqDelFromExistingTxt)
		tabContainer.addControl(self.guiSeqExistingSequences)
		tabContainer.addControl(self.guiSeqAddToExisting)
		tabContainer.addControl(self.guiSeqDelFromExisting)
		
		self.guiSeqListTitle.label = self.animationTypeString +" Sequences:"
		
		## @brief a list of possible animation types to be used as keys for sequence prefs
		#  @note: need to update this when new sequence types are added in the future
		self.sequenceTypes = ["IFL", "Vis"]

	## @brief Cleans up Blender GUI objects before the interpreter exits;
	#     we must destroy any GUI objects that are referenced in a non-global scope
	#     explicitly before interpreter shutdown to avoid the dreaded
	#     "error totblock" message when exiting Blender.
	#  @note The builtin __del__ method is not guaranteed to be called for objects
	#     that still exist when the interpreter exits.
	#  @note Child classes should explicitly call this method at the end of their own cleanup method.
	def cleanup(self):
		SeqControlsClassBase.cleanup(self)
		#del self.guiSeqAddToExistingTxt
		#del self.guiSeqDelFromExistingTxt
		del self.guiSeqExistingSequences
		del self.guiSeqAddToExisting
		del self.guiSeqDelFromExisting



	#######################################
	#  Event handler methods
	#######################################


	## @brief Updates GUI states when the sequence list item selection is changed.
	#  @note This method should only be called by the sequence list GUI control
	#     event handler callback mechanism.
	#  @note Most child classes should be able to inherit this method and use it as-is
	#  @param control The invoking GUI Control object (should be the sequence list control)
	def handleListEvent(self, control):
		seqName, seqPrefs = self.getSelectedSeqNameAndPrefs()
		SeqControlsClassBase.handleListEvent(self, control)


	## @brief Handle events generated by the "Existing Sequences" menu (guiSeqExistingSequences).
	#  @note Does nothing :-)
	#  @param control The invoking GUI control (guiSeqExistingSequences)
	def handleGuiSeqExistingSequencesEvent(self, control):
		pass
		
	## @brief Handle events generated by the "Add [seq type]" (to existing) sequence button (guiSeqAddToExisting).
	#  @param control The invoking GUI control (guiSeqAddToExisting)
	def handleGuiSeqAddToExistingEvent(self, control):
		if self.guiSeqExistingSequences.itemIndex == -1:
			message = "No existing sequence was selected.%t|Cancel"
			Blender.Draw.PupMenu(message)
			return
		seqName = self.guiSeqExistingSequences.getSelectedItemString()
		self.addNewAnim(seqName)
		self.guiSeqExistingSequences.selectStringItem("")
		self.refreshAll()
		self.selectSequence(seqName)

	def handleGuiSeqDelFromExistingEvent(self, control):
		pass

	#######################################
	#  Refresh and Clear methods
	#######################################


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

	## @brief Refreshes all controls on the panel w/ fresh data from blender and the prefs.
	#  @note Calls parent class refresh all method and additionall populates the existing
	#     sequences pulldown.
	def refreshAll(self):
		SeqControlsClassBase.refreshAll(self)
		self.refreshExistingSeqPulldown()

	## @brief Refreshes the "Existing Sequences" pulldown.
	def refreshExistingSeqPulldown(self):
		self.clearExistingSeqPulldown()
		# loop through all actions in the preferences and check for sequences without (self.seqFilter) animations
		Prefs = DtsGlobals.Prefs
		keys = Prefs['Sequences'].keys()
		keys.sort(lambda x, y: cmp(x.lower(),y.lower()))
		for seqName in keys:
			seqPrefs = Prefs['Sequences'][seqName]
			if not seqPrefs[self.seqFilter]['Enabled']:
				self.guiSeqExistingSequences.items.append(seqName)

	## @brief Clears the "Existing Sequences" pulldown.
	def clearExistingSeqPulldown(self):
		self.guiSeqExistingSequences.itemsIndex = -1
		self.guiSeqExistingSequences.items = []	



	#########################
	#  Resize callback methods
	#########################


	## @brief Resize callback for guiSeqList
	#  @param control The invoking GUI control object
	def guiSeqListResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 10,52, newheight - 92,145
		control.x = 10
		control.y = 32
		control.height = newheight - 94
		control.width = 145

	## @brief Resize callback for guiSeqListTitle
	#  @param control The invoking GUI control object
	def guiSeqListTitleResize(self, control, newwidth, newheight):			
		control.x, control.y, control.height, control.width = 10,newheight-57, 20,82


	## @brief Resize callback for guiSeqAddToExistingTxt
	#  @param control The invoking GUI control object
	#def guiSeqAddToExistingTxtResize(self, control, newwidth, newheight):
	#	#control.x, control.y, control.height, control.width = 10,38, 20,230
	#	control.width = 145
	#	control.height = 20
	#	control.x = 10
	#	control.y = newheight - control.height - 12
		

	## @brief Resize callback for guiSeqExistingSequences
	#  @param control The invoking GUI control object
	def guiSeqExistingSequencesResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 10,11, 20,145
		control.width = 145
		control.height = 20
		control.x = 222
		control.y = newheight - control.height - 17
		
	## @brief Resize callback for guiSeqAddToExisting
	#  @param control The invoking GUI control object
	def guiSeqAddToExistingResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 157,11, 20,82
		control.width = 210
		control.height = 20
		#control.x = 358
		control.x = 10
		control.y = newheight - control.height - 17


	#def guiSeqDelFromExistingTxtResize(self, control, newwidth, newheight):
	#	control.x, control.y, control.height, control.width = 261,38, 20,230


		
	def guiSeqDelFromExistingResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 261,11, 20,200
		control.x = 10
		control.y = 7
		control.height = 19
		control.width = 285
		


	## @brief Resize callback for guiSeqOptsContainer
	#  @param control The invoking GUI control object
	def guiSeqOptsContainerResize(self, control, newwidth, newheight):
		#control.x, control.y, control.height, control.width = 155,32, newheight-92,newwidth-145
		control.x, control.y, control.height, control.width = 155,32, newheight-94,newwidth-165
