'''
DtsGUI.py

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

# base gui library
import Common_Gui
from Common_Gui import *

# imported for logging
from DTSPython import Torque_Util

# globals
import DtsGlobals

# bring export function into scope
from Dts_Blender import export


# import GUI control pages
from SequenceProperties import *
from VisAnim import *
from IFLAnim import *
from Materials import *
from ShapeOptions import *
from DetailLevels import *
from Nodes import *
from General import *
from About import *

'''
	Gui Handling Code
'''
#-------------------------------------------------------------------------------------------------

'''
	Gui Init Code
'''

Prefs = DtsGlobals.Prefs
SceneInfo = DtsGlobals.SceneInfo


# Controls referenced in functions
guiSequenceTab, guiGeneralTab, guiNodesTab, guiAboutTab, guiTabBar, guiHeaderTab = None, None, None, None, None, None

DetailLevelControls = None
SeqCommonControls = None
IFLControls = None
VisControls = None
MaterialControls = None
ActionControls = None
NodeControls = None
GeneralControls = None
AboutControls = None

mainTabBook = None
shapeTabBook = None
sequencesTabBook = None

# Global control event table.  Containers have their own event tables for child controls
globalEvents = None



# Class that implements a gui tab button and control container
class TabSheetControl:
	def __init__(self, buttonText, tabName, tooltip, eventId, tabBar, container, callback):
		self.tabName = tabName
		self.tabButton = Common_Gui.TabButton(tabName, buttonText, tooltip, None, callback, self.resize)
		self.tabButton.state = False
		self.tabContainer = Common_Gui.TabContainer(tabName, None, self.tabButton, None, self.resize)
		self.tabContainer.fade_mode = 11
		self.tabContainer.borderColor = [0,0,0,1]
		self.tabContainer.color = [.67,.67,.67,1]
		self.tabContainer.enabled = False
		self.tabContainer.visible = False
		self.controlPage = None
		self.childTabBook = None
		
		if container != None:			
			container.addControl(self.tabContainer)
		else:
			Common_Gui.addGuiControl(self.tabContainer)
		tabBar.addControl(self.tabButton)
		
		
	def resize(self, control, newwidth, newheight):
		if control == self.tabButton:
			control.y = 1
		if control == self.tabContainer:
			control.x, control.y = 4, 4
			control.width, control.height = newwidth-8, newheight - 35
	
	def cleanup(self):
		pass
		

# Class that implements a gui tab book control
# owns and initializes tab sheet controls
class TabBookControl:
	def __init__(self, container, parentTabName=None):
		global globalEvents
		self.tabBar = Common_Gui.BasicContainer("tabBar", "tabs", None, self.resize)
		self.tabBar.fade_mode = 0
		self.tabBar.color = None
		self.tabBar.borderColor = None
		self.tabs = []
		self.container = container
		self.parentTabName = parentTabName		
		self.defaultTab = None
		self.lastActiveTab = None
		if container != None:
			container.addControl(self.tabBar)
		else:
			Common_Gui.addGuiControl(self.tabBar)
	

	def setDetaultTab(self, tabName):
		self.defaultTab = tabName

	def addTab(self, buttonText, tabName):
		newTab = TabSheetControl(buttonText, tabName, None, globalEvents.getNewID(), self.tabBar, self.container, self.onTabClick)
		# calculate x location for new tab button
		newPos = 15 # <- initial offset from left edge of container
		for tab in self.tabs:
			newPos += tab.tabButton.width + 2
		newTab.tabButton.x = newPos
		self.tabs.append(newTab)


	def getTab(self, tabName):
		for tab in self.tabs:
			if tab.tabName == tabName:
				return tab
		
	def getTabSheetContainer(self, tabName):
		return self.getTab(tabName).tabContainer

	def getTabButton(self,tabName):
		return self.getTab(tabName).tabButton

	def setControlPage(self, tabName, controlPage):
		self.getTab(tabName).controlPage = controlPage
		
	def setChildTabBook(self, tabName, childBook):
		self.getTab(tabName).childTabBook = childBook

	# private methods and callbacks
	def showTabPage(self, tab):
		tab.tabButton.state = True
		tab.tabContainer.visible = True
		tab.tabContainer.enabled = True
		self.lastActiveTab = tab

	def hideTabPage(self, tab):
		tab.tabButton.state = False
		tab.tabContainer.visible = False
		tab.tabContainer.enabled = False


	def hideAllTabPages(self):
		for tab in self.tabs:
			tab.tabButton.state = False
			tab.tabContainer.visible = False
			tab.tabContainer.enabled = False
		

	def refreshActivePanel(self):
		Prefs = DtsGlobals.Prefs
		for tab in self.tabs:
			if Prefs['LastActivePanel'] == tab.tabName \
			or Prefs['LastActiveSubPanel'] == tab.tabName:
				#print "refershing tab:", tab.tabName
				if tab.controlPage != None:
					tab.controlPage.refreshAll()
			
	def restoreLastActivePanel(self):
		Prefs = DtsGlobals.Prefs
		found = False
		for tab in self.tabs:
			
			# no parent tab
			if self.parentTabName == None:
				#print "no parent tab"
				# if current tab was the last active panel
				if Prefs['LastActivePanel'] == tab.tabName:
					#print "current tab was the last active panel"
					# call the refreshAll method if it exists
					if tab.controlPage != None:
						tab.controlPage.refreshAll()
					self.showTabPage(tab)
				# if current tab was not the last active panel
				else:
					#print "current tab was not the last active panel"
					self.hideTabPage(tab)
			
			#  parent tab was the last active panel
			elif self.parentTabName == Prefs['LastActivePanel']:
				#print "parent tab was last active panel"
				# if this tab was the last active subpanel
				if Prefs['LastActiveSubPanel'] == tab.tabName:
					#print "current tab was the last active supanel"
					# call the refreshAll method if it exists
					if tab.controlPage != None:
						tab.controlPage.refreshAll()
					self.showTabPage(tab)
				# if this tab was not the last active subpanel
				else:
					#print "current tab was not the last active supanel"
					self.hideTabPage(tab)
					
			# parent tab was not the last active panel
			else:
				#print "parent tab was not the last active panel"
				# if an explicit default tab was not set up
				if self.defaultTab == None:
					#print "no explicit default tab exists."
					# call the refreshAll method if it exists
					if self.tabs[0].controlPage != None:
						self.tabs[0].controlPage.refreshAll()
					self.hideAllTabPages()
					self.showTabPage(self.tabs[0])
				# if an explicitly set default tab exists
				else:	
					#print "an explicit default tab exists"
					# if the current tab is the default tab
					if tab.tabName == self.defaultTab:
						#print "the current tab is the default tab"
						# call the refreshAll method if it exists
						if tab.controlPage != None:
							tab.controlPage.refreshAll()
						self.showTabPage(tab)
					# if the current tab is not the default
					else:				
						#print "the current tab is not the default tab"
						self.hideTabPage(tab)

	def resize(self, control, newwidth, newheight):
		if control.name == "tabBar":
			control.x, control.y = 4, newheight - 34
			control.width, control.height = newwidth-8, 35
	
	def onTabClick(self, control):
		Prefs = DtsGlobals.Prefs
		for tab in self.tabs:
			if control == tab.tabButton:
				self.lastActiveTab = tab
				# call the refreshAll method if it exists
				if tab.controlPage != None:
					tab.controlPage.refreshAll()
				# store the last active tabs in prefs
				if self.parentTabName == None:
					Prefs['LastActivePanel'] = tab.tabName
					# Need to find last active sub-panel to refresh it, but how?
					if tab.childTabBook != None:
						childTab = tab.childTabBook.lastActiveTab
						if childTab != None:
							Prefs['LastActiveSubPanel'] = childTab.tabName
							# call the refreshAll method if it exists
							if childTab.controlPage != None:
								childTab.controlPage.refreshAll()

				else:
					Prefs['LastActivePanel'] = self.parentTabName
					Prefs['LastActiveSubPanel'] = tab.tabName
				# turn on the tab button, show and enable the tab container
				self.showTabPage(tab)

			else:
				self.hideTabPage(tab)



	
		
	

# Callback for export button
def guiBaseCallback(control):
	global mainTabBook, shapeTabBook, sequencesTabBook
	if control.name == "guiExportButton":
		export()
	elif control.name == "guiRefreshButton":
		if mainTabBook.lastActiveTab.tabName == "Shape":
			shapeTabBook.refreshActivePanel()
		elif mainTabBook.lastActiveTab.tabName == "Sequences":
			sequencesTabBook.refreshActivePanel()
		else:
			mainTabBook.refreshActivePanel()


		
		

# Resize callback for all global gui controls
def guiBaseResize(control, newwidth, newheight):
	if control.name == "guiMainContainer":
		control.x, control.y = (newwidth/2)-253, (newheight/2) -203
		control.width, control.height = 506, 406
	elif control.name == "guiHeaderBar":
		control.x, control.y = (newwidth/2)-253, (newheight/2) +203
		control.width, control.height = 506, 20
	elif control.name == "guiExportButton":
		control.x, control.y = newwidth-74, newheight - 27
		control.width, control.height = 70, 23
	elif control.name == "guiRefreshButton":
		control.x, control.y = newwidth-73, newheight - 56
		control.width, control.height = 65, 19

# Resize callback for gui header	
def guiHeaderResize(control, newwidth, newheight):
	if control.name == "guiHeaderText":
		control.x = 5
		control.y = 5
	elif control.name == "guiVersionText":
		control.x = newwidth-80
		control.y = 5


def initGui():
	# -------------------------------
	# Globals
	global globalEvents
	globalEvents = Common_Gui.EventTable(1)
	

	global Version
	# object that hands out global event id numbers
	global GlobalEvents
	# these objects create and own all of the actual gui controls on a tab/subtab page
	global ShapeOptionControls, DetailLevelControls, SeqCommonControls, IFLControls, VisControls, ActionControls, MaterialControls, NodeControls, GeneralControls, AboutControls
	# main gui container into which all other gui objects are placed
	global guiMainContainer
	# global tab books
	global mainTabBook, shapeTabBook, sequencesTabBook

	# -------------------------------
	# Initialize GUI system

	Common_Gui.initGui(exit_callback)


	# -------------------------------
	# Create global controls

	# export button
	guiExportButton = Common_Gui.BasicButton("guiExportButton", "Export", "Export .dts shape", globalEvents.getNewID("Export"), guiBaseCallback, guiBaseResize)
	guiRefreshButton = Common_Gui.BasicButton("guiRefreshButton", "Refresh", "Refresh current page", globalEvents.getNewID("Refresh"), guiBaseCallback, guiBaseResize)

	# Header controls
	guiHeaderText = Common_Gui.SimpleText("guiHeaderText", "Torque Exporter Plugin", None, guiHeaderResize)
	headerTextColor = headerColor = Common_Gui.curTheme.get('buts').text_hi
	guiHeaderText.color = [headerTextColor[0]/255.0, headerTextColor[1]/255.0, headerTextColor[2]/255.0, headerTextColor[3]/255.0]
	guiVersionText = Common_Gui.SimpleText("guiVersionText", "Version %s" % Version, None, guiHeaderResize)

	# Container Controls
	guiMainContainer = Common_Gui.BasicContainer("guiMainContainer", "container", None, guiBaseResize)
	guiMainContainer.borderColor = [0, 0, 0, 1]
	guiMainContainer.fade_mode = 0
	guiHeaderBar = Common_Gui.BasicContainer("guiHeaderBar", "header", None, guiBaseResize)
	guiHeaderBar.borderColor = [0,0,0,1]
	headerColor = Common_Gui.curTheme.get('buts').header
	guiHeaderBar.color = [headerColor[0]/255.0, headerColor[1]/255.0, headerColor[2]/255.0, headerColor[3]/255.0]
	guiHeaderBar.fade_mode = 0

	# Add all controls to respective containers
	guiHeaderBar.addControl(guiHeaderText)
	guiHeaderBar.addControl(guiVersionText)
	guiMainContainer.addControl(guiExportButton)
	guiMainContainer.addControl(guiRefreshButton)
	Common_Gui.addGuiControl(guiHeaderBar)
	Common_Gui.addGuiControl(guiMainContainer)
	
	# -------------------------------
	# Create tab books and tabs
	
	mainTabBook = TabBookControl(guiMainContainer)
	mainTabBook.addTab("Shape", "Shape")
	mainTabBook.addTab("Sequences", "Sequences")
	mainTabBook.addTab("General", "General")
	mainTabBook.addTab("About", "About")
	
	shapeTabBook = TabBookControl(mainTabBook.getTabSheetContainer("Shape"), "Shape")
	
	shapeTabBook.addTab("Shape Options", "ShapeOptions")
	shapeTabBook.addTab("Detail Levels", "DetailLevels")
	shapeTabBook.addTab("Nodes", "Nodes")
	shapeTabBook.addTab("Materials", "Materials")


	sequencesTabBook = TabBookControl(mainTabBook.getTabSheetContainer("Sequences"), "Sequences")
	
	sequencesTabBook.addTab("Sequence Properties", "CommonAll")
	sequencesTabBook.addTab("Visibility Animations", "Visibility")
	sequencesTabBook.addTab("IFL Animations", "IFL")
	


	# ----------------------------
	# Initialize all tab control pages
	
	
	# init controls pages, pass in containers to be used
	ShapeOptionControls = ShapeOptionsControlsClass(shapeTabBook.getTabSheetContainer("ShapeOptions"))
	DetailLevelControls = DetailLevelControlsClass(shapeTabBook.getTabSheetContainer("DetailLevels"))
	NodeControls = NodeControlsClass(shapeTabBook.getTabSheetContainer("Nodes"))
	MaterialControls = MaterialControlsClass(shapeTabBook.getTabSheetContainer("Materials"))
	SeqCommonControls = SeqCommonControlsClass(sequencesTabBook.getTabSheetContainer("CommonAll"))
	# no more action controls, we're timeline based now, baby.
	#ActionControls = ActionControlsClass(guiSeqActSubtab)
	IFLControls = IFLControlsClass(sequencesTabBook.getTabSheetContainer("IFL"))
	VisControls = VisControlsClass(sequencesTabBook.getTabSheetContainer("Visibility"))
	GeneralControls = GeneralControlsClass(mainTabBook.getTabSheetContainer("General"))
	AboutControls = AboutControlsClass(mainTabBook.getTabSheetContainer("About"))

	# associate control pages with tabs (used for refresh callbacks)
	mainTabBook.setControlPage("General", GeneralControls)
	mainTabBook.setControlPage("About", AboutControls)
	shapeTabBook.setControlPage("ShapeOptions", ShapeOptionControls)
	shapeTabBook.setControlPage("DetailLevels", DetailLevelControls)
	shapeTabBook.setControlPage("Nodes", NodeControls)
	shapeTabBook.setControlPage("Materials", MaterialControls)
	sequencesTabBook.setControlPage("CommonAll", SeqCommonControls)
	sequencesTabBook.setControlPage("IFL", IFLControls)
	sequencesTabBook.setControlPage("Visibility", VisControls)
	
	# associate parent tabs with child tab books (needed to refresh active child tab)
	mainTabBook.setChildTabBook("Shape", shapeTabBook)
	mainTabBook.setChildTabBook("Sequences", sequencesTabBook)
	
	
	# restore panel states from prefs
	mainTabBook.restoreLastActivePanel()
	shapeTabBook.restoreLastActivePanel()
	sequencesTabBook.restoreLastActivePanel()
	

# Called when gui exits
def exit_callback():
	global DetailLevelControls, SeqCommonControls, IFLControls, ActionControls, MaterialControls, NodeControls, GeneralControls, AboutControls
	Torque_Util.dump_setout("stdout")
	ShapeOptionControls.cleanup()
	DetailLevelControls.cleanup()
	#ActionControls.clearSequenceList()
	AboutControls.cleanup()
	GeneralControls.cleanup()
	NodeControls.cleanup()
	#ActionControls.cleanup()
	IFLControls.cleanup()	
	VisControls.cleanup()
	MaterialControls.cleanup()	
	
	
	DtsGlobals.Prefs.savePrefs()
