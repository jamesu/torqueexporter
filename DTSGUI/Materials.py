'''
Materials.py

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
import Blender
from DtsSceneInfo import *


'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the Materials panel.
*
***************************************************************************************************
'''
class MaterialControlsClass:
	def __init__(self, guiMaterialsSubtab):
		global globalEvents
		# panel state
		self.curSeqListEvent = 40

		self.guiMaterialListTitle = Common_Gui.SimpleText("guiMaterialListTitle", "U/V Textures:", None, self.resize)
		self.guiMaterialList = Common_Gui.ListContainer("guiMaterialList", "material.list", self.handleEvent, self.resize)		
		self.guiMaterialOptions = Common_Gui.BasicContainer("guiMaterialOptions", "", None, self.resize)

		#self.guiMaterialOptionsTitle = Common_Gui.SimpleText("guiMaterialOptionsTitle", "DTS Material: None Selected", None, self.resize)
		self.guiMaterialOptionsTitle = Common_Gui.MultilineText("guiMaterialOptionsTitle", "DTS Material:\n None Selected", None, self.guiMaterialOptionsTitleResize)
		self.guiMatOptsContainerTitleBox = Common_Gui.BasicFrame(resize_callback = self.guiMatOptsContainerTitleBoxResize)



		self.guiMaterialTransFrame = Common_Gui.BasicFrame("guiMaterialTransFrame", "", None, 29, None, self.resize)
		self.guiMaterialMipFrame = Common_Gui.BasicFrame("guiMaterialMipFrame", "", None, 29, None, self.resize)
		self.guiMaterialWrapFrame = Common_Gui.BasicFrame("guiMaterialWrapFrame", "", None, 29, None, self.resize)
		self.guiMaterialDetailMapFrame = Common_Gui.BasicFrame("guiMaterialDetailMapFrame", "", None, 29, None, self.resize)
		self.guiMaterialEnvMappingFrame = Common_Gui.BasicFrame("guiMaterialEnvMappingFrame", "", None, 29, None, self.resize)
		
		self.guiMaterialAdvancedFrame = Common_Gui.BasicFrame("guiMaterialAdvancedFrame", "", None, 30, None, self.resize)
		self.guiMaterialImportRefreshButton = Common_Gui.BasicButton("guiMaterialImportRefreshButton", "Refresh", "Import Blender materials and settings", 7, self.handleEvent, self.resize)
		self.guiMaterialSWrapButton = Common_Gui.ToggleButton("guiMaterialSWrapButton", "SWrap", "SWrap", 9, self.handleEvent, self.resize)
		self.guiMaterialTWrapButton = Common_Gui.ToggleButton("guiMaterialTWrapButton", "TWrap", "TWrap", 10, self.handleEvent, self.resize)
		self.guiMaterialTransButton = Common_Gui.ToggleButton("guiMaterialTransButton", "Translucent", "Translucent", 11, self.handleEvent, self.resize)
		self.guiMaterialAddButton = Common_Gui.ToggleButton("guiMaterialAddButton", "Additive", "Blending Additive", 12, self.handleEvent, self.resize)
		self.guiMaterialSubButton = Common_Gui.ToggleButton("guiMaterialSubButton", "Subtractive", "Blending Subtractive", 13, self.handleEvent, self.resize)
		self.guiMaterialSelfIllumButton = Common_Gui.ToggleButton("guiMaterialSelfIllumButton", "Self Illuminating", "Mark material as self illuminating", 14, self.handleEvent, self.resize)
		self.guiMaterialEnvMapButton = Common_Gui.ToggleButton("guiMaterialEnvMapButton", "Environment Mapping", "Enable Environment Mapping", 15, self.handleEvent, self.resize)
		self.guiMaterialMipMapButton = Common_Gui.ToggleButton("guiMaterialMipMapButton", "Mipmap", "Allow MipMapping", 16, self.handleEvent, self.resize)
		self.guiMaterialMipMapZBButton = Common_Gui.ToggleButton("guiMaterialMipMapZBButton", "Mipmap Zero Border", "Use Zero border MipMaps", 17, self.handleEvent, self.resize)
		self.guiMaterialIFLMatButton = Common_Gui.ToggleButton("guiMaterialIFLMatButton", "IFL Material", "Use this material as an IFL material", 28, self.handleEvent, self.resize)
		self.guiMaterialDetailMapButton = Common_Gui.ToggleButton("guiMaterialDetailMapButton", "Detail Map", "Use a detail map texture", 18, self.handleEvent, self.resize)
		self.guiMaterialBumpMapButton = Common_Gui.ToggleButton("guiMaterialBumpMapButton", "Bump Map", "Use a bump map texture", 19, self.handleEvent, self.resize)
		self.guiMaterialRefMapButton = Common_Gui.ToggleButton("guiMaterialRefMapButton", "Reflectance Map", "Use a reflectance map texture", 20, self.handleEvent, self.resize)
		self.guiMaterialDetailMapMenu = Common_Gui.ComboBox("guiMaterialDetailMapMenu", "Detail Texture", "Select a texture from this list to use as a detail map", 22, self.handleEvent, self.resize)
		self.guiMaterialShowAdvancedButton = Common_Gui.ToggleButton("guiMaterialShowAdvancedButton", "Show Advanced Settings", "Show advanced material settings. USE WITH CAUTION!!", 23, self.handleEvent, self.resize)
		self.guiMaterialBumpMapMenu = Common_Gui.ComboBox("guiMaterialBumpMapMenu", "Bumpmap Texture", "Select a texture from this list to use as a bump map", 24, self.handleEvent, self.resize)
		self.guiMaterialReflectanceMapMenu = Common_Gui.ComboBox("guiMaterialReflectanceMapMenu", "Reflectance Map", "Select a texture from this list to use as a Reflectance map", 25, self.handleEvent, self.resize)
		self.guiMaterialReflectanceSlider = Common_Gui.NumberPicker("guiMaterialReflectanceSlider", "Reflectivity %", "Material reflectivity as a percentage", 26, self.handleEvent, self.resize)
		self.guiMaterialDetailScaleSlider = Common_Gui.NumberPicker("guiMaterialDetailScaleSlider", "Scale %", "Detail map scale as a percentage of original size", 27, self.handleEvent, self.resize)	


		# set initial control states and default values
		self.guiMaterialList.fade_mode = 0
		self.guiMaterialReflectanceSlider.min, self.guiMaterialReflectanceSlider.max = 0, 100
		self.guiMaterialDetailScaleSlider.min, self.guiMaterialDetailScaleSlider.max = 1, 1000
		self.guiMaterialDetailScaleSlider.value = 100
		self.guiMaterialRefMapButton.enabled = False
		self.guiMaterialBumpMapButton.enabled = False
		self.guiMaterialBumpMapMenu.enabled = False
		self.guiMaterialReflectanceMapMenu.enabled = False
		self.guiMaterialRefMapButton.visible = False
		self.guiMaterialBumpMapButton.visible = False
		self.guiMaterialBumpMapMenu.visible = False
		self.guiMaterialReflectanceMapMenu.visible = False
		self.guiMaterialOptions.enabled = False
		#guiMaterialsTab.borderColor = [0,0,0,0]
		
		
		# add controls to their respective containers
		guiMaterialsSubtab.addControl(self.guiMaterialListTitle)
		guiMaterialsSubtab.addControl(self.guiMaterialList)
		guiMaterialsSubtab.addControl(self.guiMaterialOptions)
		guiMaterialsSubtab.addControl(self.guiMaterialImportRefreshButton)

		self.guiMaterialOptions.addControl(self.guiMaterialOptionsTitle)
		self.guiMaterialOptions.addControl(self.guiMatOptsContainerTitleBox)
		
		self.guiMaterialOptions.addControl(self.guiMaterialTransFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialMipFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialWrapFrame)
		
		self.guiMaterialOptions.addControl(self.guiMaterialAdvancedFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialSWrapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialTWrapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialTransButton)
		self.guiMaterialOptions.addControl(self.guiMaterialAddButton)
		self.guiMaterialOptions.addControl(self.guiMaterialSubButton)
		self.guiMaterialOptions.addControl(self.guiMaterialSelfIllumButton)
		self.guiMaterialOptions.addControl(self.guiMaterialEnvMappingFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialEnvMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialMipMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialMipMapZBButton)
		self.guiMaterialOptions.addControl(self.guiMaterialIFLMatButton)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailMapFrame)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialBumpMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialShowAdvancedButton)
		self.guiMaterialOptions.addControl(self.guiMaterialRefMapButton)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailMapMenu)
		self.guiMaterialOptions.addControl(self.guiMaterialBumpMapMenu)
		self.guiMaterialOptions.addControl(self.guiMaterialReflectanceMapMenu)
		self.guiMaterialOptions.addControl(self.guiMaterialReflectanceSlider)
		self.guiMaterialOptions.addControl(self.guiMaterialDetailScaleSlider)

		# populate the Material list
		#self.populateMaterialList()
		self.refreshMaterialList()
		
	def cleanup(self):
		'''
		Must destroy any GUI objects that are referenced in a non-global scope
		explicitly before interpreter shutdown to avoid the dreaded
		"error totblock" message when exiting Blender.
		Note: __del__ is not guaranteed to be called for objects that still
		exist when the interpreter exits.
		'''
		del self.guiMaterialListTitle
		del self.guiMaterialList
		del self.guiMaterialOptions
		del self.guiMaterialOptionsTitle
		del self.guiMatOptsContainerTitleBox
		del self.guiMaterialTransFrame
		del self.guiMaterialMipFrame
		del self.guiMaterialAdvancedFrame
		del self.guiMaterialImportRefreshButton
		del self.guiMaterialWrapFrame
		del self.guiMaterialSWrapButton
		del self.guiMaterialTWrapButton
		del self.guiMaterialTransButton
		del self.guiMaterialAddButton
		del self.guiMaterialSubButton
		del self.guiMaterialSelfIllumButton
		del self.guiMaterialEnvMappingFrame
		del self.guiMaterialEnvMapButton
		del self.guiMaterialMipMapButton
		del self.guiMaterialMipMapZBButton
		del self.guiMaterialIFLMatButton
		del self.guiMaterialDetailMapFrame
		del self.guiMaterialDetailMapButton
		del self.guiMaterialBumpMapButton
		del self.guiMaterialRefMapButton
		del self.guiMaterialDetailMapMenu
		del self.guiMaterialShowAdvancedButton
		del self.guiMaterialBumpMapMenu
		del self.guiMaterialReflectanceMapMenu
		del self.guiMaterialReflectanceSlider
		del self.guiMaterialDetailScaleSlider
		

	def refreshAll(self):
		#self.clearMaterialList()		
		#self.populateMaterialList()
		self.refreshMaterialList()

	def guiMaterialOptionsTitleResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 5,newheight-30, 20,82

	def guiMatOptsContainerTitleBoxResize(self, control, newwidth, newheight):
		control.x, control.y, control.height, control.width = 3,newheight-35, 33,117
	
	
	def resize(self, control, newwidth, newheight):
		# handle control resize events.
		if control.name == "guiMaterialListTitle":
			control.x, control.y, control.height, control.width = 10,310, 20,150
		elif control.name == "guiMaterialList":
			control.x, control.y, control.height, control.width = 10,30, newheight - 70,150
		elif control.name == "guiMaterialOptionsTitle":
			control.x, control.y, control.height, control.width = 25,310, 20,150
		elif control.name == "guiMaterialOptions":
			control.x, control.y, control.height, control.width = 161,30, newheight - 70,328
		elif control.name == "guiMaterialImportRefreshButton":
			control.width = 75
			control.x = newwidth - (control.width + 10)
			control.y = newheight - (control.height + 10)

		elif control.name == "guiMaterialSelfIllumButton":
			control.x, control.y, control.width = 125,newheight-30, 95
		elif control.name == "guiMaterialIFLMatButton":
			control.x, control.y, control.width = 227,newheight-30, 95
		elif control.name == "guiMaterialTransFrame":
			control.x, control.y, control.height, control.width = 2,newheight-69, 27,322
		elif control.name == "guiMaterialTransButton":
			control.x, control.y, control.width = 5,newheight-66, 104
		elif control.name == "guiMaterialAddButton":
			control.x, control.y, control.width = 111,newheight-66, 104
		elif control.name == "guiMaterialSubButton":
			control.x, control.y, control.width = 217,newheight-66, 104
		elif control.name == "guiMaterialMipFrame":
			control.x, control.y, control.height, control.width = 2,newheight-107, 27,183
		elif control.name == "guiMaterialMipMapButton":
			control.x, control.y, control.width = 5,newheight-104, 50
		elif control.name == "guiMaterialMipMapZBButton":
			control.x, control.y, control.width = 57,newheight-104, 125
		elif control.name == "guiMaterialWrapFrame":
			control.x, control.y, control.height, control.width = 192,newheight-107, 27,132
		elif control.name == "guiMaterialSWrapButton":
			control.x, control.y, control.width = 195,newheight-104, 62
		elif control.name == "guiMaterialTWrapButton":
			control.x, control.y, control.width = 259,newheight-104, 62
		elif control.name == "guiMaterialDetailMapFrame":
			control.x, control.y, control.height, control.width = 2,newheight-145, 27,322
		elif control.name == "guiMaterialDetailMapButton":
			control.x, control.y, control.width = 5,newheight-142, 80
		elif control.name == "guiMaterialDetailMapMenu":
			control.x, control.y, control.width = 87,newheight-142, 125
		elif control.name == "guiMaterialDetailScaleSlider":
			control.x, control.y, control.width = 214,newheight-142, 107
		elif control.name == "guiMaterialEnvMappingFrame":
			control.x, control.y, control.height, control.width = 2,newheight-183, 27,322
		elif control.name == "guiMaterialEnvMapButton":
			control.x, control.y, control.width = 5,newheight-180, 155
		elif control.name == "guiMaterialReflectanceSlider":
			control.x, control.y, control.width = 162,newheight-180, 159
		elif control.name == "guiMaterialAdvancedFrame":
			control.x, control.y, control.height, control.width = 5,newheight-260, 60,318
		elif control.name == "guiMaterialShowAdvancedButton":
			control.x, control.y, control.width = 89,newheight-210, 150
		elif control.name == "guiMaterialRefMapButton":
			control.x, control.y, control.width = 15,newheight-235, 150
		elif control.name == "guiMaterialReflectanceMapMenu":
			control.x, control.y, control.width = 167,newheight-235, 150
		elif control.name == "guiMaterialBumpMapButton":
			control.x, control.y, control.width = 15,newheight-257, 150
		elif control.name == "guiMaterialBumpMapMenu":
			control.x, control.y, control.width = 167,newheight-257,150 


	def createMaterialListItem(self, matName, startEvent):
		guiContainer = Common_Gui.BasicContainer("", None, None)
		guiContainer.fade_mode = 0  # flat color
		guiName = Common_Gui.SizeLimitedText("", matName, 21, None, None)
		guiName.x, guiName.y = 5, 5
		guiContainer.addControl(guiName)
		return guiContainer


	def handleEvent(self, control):
		global IFLControls
		Prefs = DtsGlobals.Prefs
		guiMaterialList = self.guiMaterialList
		guiMaterialOptions = self.guiMaterialOptions

		try:matPrefs = Prefs['Materials']
		except:
			Prefs['Materials'] = {}
			matPrefs = Prefs['Materials']	


		if control.name == "guiMaterialImportRefreshButton":
			# import Blender materials and settings
			#self.clearMaterialList()
			#self.populateMaterialList()
			self.refreshAll()
			return

		materialName, matPrefs = self.getSelectedMatNameAndPrefs()
		#materialName = guiMaterialList.controls[guiMaterialList.itemIndex].controls[0].label	

		if control.name == "guiMaterialList":
			self.refreshMaterialOptions(materialName, matPrefs)



		if guiMaterialList.itemIndex == -1: return

		elif control.name == "guiMaterialSWrapButton":
			Prefs['Materials'][materialName]['SWrap'] = control.state
		elif control.name == "guiMaterialTWrapButton":
			Prefs['Materials'][materialName]['TWrap'] = control.state
		elif control.name == "guiMaterialTransButton":
			if not control.state:
				Prefs['Materials'][materialName]['Subtractive'] = False
				self.guiMaterialSubButton.state = False
				Prefs['Materials'][materialName]['Additive'] = False
				self.guiMaterialAddButton.state = False
			Prefs['Materials'][materialName]['Translucent'] = control.state
		elif control.name == "guiMaterialAddButton":
			if control.state:
				Prefs['Materials'][materialName]['Translucent'] = True
				self.guiMaterialTransButton.state = True
				Prefs['Materials'][materialName]['Subtractive'] = False
				self.guiMaterialSubButton.state = False
			Prefs['Materials'][materialName]['Additive'] = control.state
		elif control.name == "guiMaterialSubButton":
			if control.state:
				Prefs['Materials'][materialName]['Translucent'] = True
				self.guiMaterialTransButton.state = True
				Prefs['Materials'][materialName]['Additive'] = False
				self.guiMaterialAddButton.state = False
			Prefs['Materials'][materialName]['Subtractive'] = control.state
		elif control.name == "guiMaterialSelfIllumButton":
			Prefs['Materials'][materialName]['SelfIlluminating'] = control.state
		elif control.name == "guiMaterialEnvMapButton":
			if not control.state:
				Prefs['Materials'][materialName]['ReflectanceMapFlag'] = False
				self.guiMaterialRefMapButton.state = False
			Prefs['Materials'][materialName]['NeverEnvMap'] = not control.state
		elif control.name == "guiMaterialMipMapButton":
			if not control.state:
				Prefs['Materials'][materialName]['MipMapZeroBorder'] = False
				self.guiMaterialMipMapZBButton.state = False
			Prefs['Materials'][materialName]['NoMipMap'] = not control.state
		elif control.name == "guiMaterialMipMapZBButton":
			if control.state:
				Prefs['Materials'][materialName]['NoMipMap'] = False
				self.guiMaterialMipMapButton.state = True
			Prefs['Materials'][materialName]['MipMapZeroBorder'] = control.state
		elif control.name == "guiMaterialIFLMatButton":
			Prefs['Materials'][materialName]['IFLMaterial'] = control.state
		elif control.name == "guiMaterialDetailMapButton":
			Prefs['Materials'][materialName]['DetailMapFlag'] = control.state
		elif control.name == "guiMaterialBumpMapButton":
			Prefs['Materials'][materialName]['BumpMapFlag'] = control.state
		elif control.name == "guiMaterialRefMapButton":
			if control.state:
				Prefs['Materials'][materialName]['NeverEnvMap'] = False
				self.guiMaterialEnvMapButton.state = True
			Prefs['Materials'][materialName]['ReflectanceMapFlag'] = control.state
		elif control.name == "guiMaterialDetailMapMenu":
			Prefs['Materials'][materialName]['DetailTex'] = control.getSelectedItemString()
		elif control.name == "guiMaterialShowAdvancedButton":
			if control.state == True:
				self.guiMaterialRefMapButton.enabled = True
				self.guiMaterialBumpMapButton.enabled = True
				self.guiMaterialBumpMapMenu.enabled = True
				self.guiMaterialReflectanceMapMenu.enabled = True
				self.guiMaterialRefMapButton.visible = True
				self.guiMaterialBumpMapButton.visible = True
				self.guiMaterialBumpMapMenu.visible = True
				self.guiMaterialReflectanceMapMenu.visible = True
			else:
				self.guiMaterialRefMapButton.enabled = False
				self.guiMaterialBumpMapButton.enabled = False
				self.guiMaterialBumpMapMenu.enabled = False
				self.guiMaterialReflectanceMapMenu.enabled = False
				self.guiMaterialRefMapButton.visible = False
				self.guiMaterialBumpMapButton.visible = False
				self.guiMaterialBumpMapMenu.visible = False
				self.guiMaterialReflectanceMapMenu.visible = False
		elif control.name == "guiMaterialBumpMapMenu":
			Prefs['Materials'][materialName]['BumpMapTex'] = control.getSelectedItemString()
		elif control.name == "guiMaterialReflectanceMapMenu":
			Prefs['Materials'][materialName]['RefMapTex'] = control.getSelectedItemString()
		elif control.name == "guiMaterialReflectanceSlider":
			Prefs['Materials'][materialName]['reflectance'] = control.value / 100.0
		elif control.name == "guiMaterialDetailScaleSlider":
			Prefs['Materials'][materialName]['detailScale'] = control.value / 100.0


	def clearMaterialList(self):		
		guiMaterialList = self.guiMaterialList
		for i in range(0, len(guiMaterialList.controls)):
			del guiMaterialList.controls[i].controls[:]
		del guiMaterialList.controls[:]
		guiMaterialList.itemIndex = -1
		guiMaterialList.scrollPosition = 0
		if guiMaterialList.callback: guiMaterialList.callback(guiMaterialList) # Bit of a hack, but works


	def populateMaterialList(self):
		self.clearMaterialList()
		Prefs = DtsGlobals.Prefs
		#Prefs.refreshMaterialPrefs()
		guiMaterialList = self.guiMaterialList
		guiMaterialOptions = self.guiMaterialOptions
		# clear texture pulldowns
		self.guiMaterialDetailMapMenu.items = []
		self.guiMaterialBumpMapMenu.items = []
		self.guiMaterialReflectanceMapMenu.items = []
		# populate the texture pulldowns
		for imageName in SceneInfoClass.getAllBlenderImages():
			self.guiMaterialDetailMapMenu.items.append(imageName)
			self.guiMaterialBumpMapMenu.items.append(imageName)
			self.guiMaterialReflectanceMapMenu.items.append(imageName)


		# autoimport blender materials
		#Prefs.refreshMaterialPrefs()
		materials = Prefs['Materials']


		# add the materials to the list
		startEvent = 40
		for mat in materials.keys():
			self.guiMaterialList.addControl(self.createMaterialListItem(mat, startEvent))
			startEvent += 1

	def getSelectedMatNameAndPrefs(self):
		Prefs = DtsGlobals.Prefs
		
		# early out if nothing was selected
		if self.guiMaterialList.itemIndex == -1: return None, None
		
		# get material name
		materialName = self.guiMaterialList.controls[self.guiMaterialList.itemIndex].controls[0].label
		
		# get material prefs key
		try:matPrefs = Prefs['Materials'][materialName]
		except: matPrefs = None
		
		return materialName, matPrefs
		

	def refreshMaterialOptions(self, materialName, matPrefs):			
			if self.guiMaterialList.itemIndex != -1:
				self.guiMaterialOptions.enabled = True
				#materialName = self.guiMaterialList.controls[control.itemIndex].controls[0].label
				# referesh and repopulate the material option controls
				self.guiMaterialSWrapButton.state = matPrefs['SWrap']
				self.guiMaterialTWrapButton.state = matPrefs['TWrap']
				self.guiMaterialTransButton.state = matPrefs['Translucent']
				self.guiMaterialAddButton.state = matPrefs['Additive']
				self.guiMaterialSubButton.state = matPrefs['Subtractive']
				self.guiMaterialSelfIllumButton.state = matPrefs['SelfIlluminating']
				self.guiMaterialEnvMapButton.state = not matPrefs['NeverEnvMap']
				self.guiMaterialMipMapButton.state = not matPrefs['NoMipMap']
				self.guiMaterialMipMapZBButton.state = matPrefs['MipMapZeroBorder']
				self.guiMaterialIFLMatButton.state = matPrefs['IFLMaterial']
				self.guiMaterialDetailMapButton.state = matPrefs['DetailMapFlag']
				self.guiMaterialBumpMapButton.state = matPrefs['BumpMapFlag']
				self.guiMaterialRefMapButton.state = matPrefs['ReflectanceMapFlag']			
				self.guiMaterialDetailMapMenu.selectStringItem(matPrefs['DetailTex'])
				self.guiMaterialBumpMapMenu.selectStringItem(matPrefs['BumpMapTex'])
				self.guiMaterialReflectanceMapMenu.selectStringItem(matPrefs['RefMapTex'])
				self.guiMaterialReflectanceSlider.value = matPrefs['reflectance'] * 100.0
				self.guiMaterialDetailScaleSlider.value = matPrefs['detailScale'] * 100.0
				self.guiMaterialOptionsTitle.label = ("DTS Material:\n \'%s\'" % materialName)
			else:
				self.guiMaterialSWrapButton.state = False
				self.guiMaterialTWrapButton.state = False
				self.guiMaterialTransButton.state = False
				self.guiMaterialAddButton.state = False
				self.guiMaterialSubButton.state = False
				self.guiMaterialSelfIllumButton.state = False
				self.guiMaterialEnvMapButton.state = False
				self.guiMaterialMipMapButton.state = False
				self.guiMaterialMipMapZBButton.state = False
				self.guiMaterialIFLMatButton.state = False
				self.guiMaterialDetailMapButton.state = False
				self.guiMaterialBumpMapButton.state = False
				self.guiMaterialRefMapButton.state = False
				self.guiMaterialDetailMapMenu.selectStringItem("")
				self.guiMaterialBumpMapMenu.selectStringItem("")
				self.guiMaterialReflectanceMapMenu.selectStringItem("")
				self.guiMaterialReflectanceSlider.value = 0
				self.guiMaterialDetailScaleSlider.value = 100
				self.guiMaterialOptions.enabled = False
				self.guiMaterialOptionsTitle.label = "DTS Material:\n None Selected"


	## @brief Refreshes the items in the material list, preserving list selection if possible.
	def refreshMaterialList(self):
		Prefs = DtsGlobals.Prefs
		
		# make sure mat preferences are up to date		
		Prefs.refreshMaterialPrefs()
		
		# store last sequence selection
		matName = None
		matPrefs = None		
		if self.guiMaterialList.itemIndex != -1:
			matName, matPrefs = self.getSelectedMatNameAndPrefs()		
		else:
			# no valid selection, so select the first item in the list
			self.guiMaterialList.selectItem(0)
			self.guiMaterialList.scrollToSelectedItem()
			if self.guiMaterialList.callback: self.guiMaterialList.callback(self.guiMaterialList)
			matName, matPrefs = self.getSelectedMatNameAndPrefs()

		# populateSequenceList automatically clears the sequence list first.
		self.populateMaterialList()

		# restore last sequence selection
		for itemIndex in range(0, len(self.guiMaterialList.controls)):
			if self.guiMaterialList.controls[itemIndex].controls[0].label == matName:
				self.guiMaterialList.selectItem(itemIndex)
				self.guiMaterialList.scrollToSelectedItem()
				self.refreshMaterialOptions(matName, matPrefs)
				if self.guiMaterialList.callback: self.guiMaterialList.callback(self.guiMaterialList)
				return

		self.guiMaterialList.selectItem(0)
		self.guiMaterialList.scrollToSelectedItem()
		if self.guiMaterialList.callback: self.guiMaterialList.callback(self.guiMaterialList)
