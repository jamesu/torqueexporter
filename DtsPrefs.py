'''
DtsPrefs.py

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

from DtsSceneInfo import *
import DTSPython
from DTSPython import *
import DtsGlobals
import re, os.path
import Blender
from Blender import *




# Our preferences class inherits from the built-in dictionary type
# but also provides "setter" methods that do validation on user input
# from the GUI.  Other than the dictionary portion, this class is stateless.
# NOTE: This should be the only place that input validation happens.
# NOTE: If any methods in this class need to get data from blender, they should
#  call SceneInfoClass methods to get it; they should not talk to blender directly or
# NOTE: The global SceneInfo object does not exist when initialization happens, so methods
#  called in or by __init__ must only call static methods of SceneInfoClass.

class prefsClass(dict):
	def __init__(self):
		self.Prefs_keyname = 'TorqueExporterPlugin_%s' % prefsClass.__pythonizeFileName(SceneInfoClass.getDefaultBaseName())
		# todo - read in prefs from text buffer here?
		self.loadPrefs()
		#self.initPrefs()
		pass
	
	#################################################
	#  Preference loading/saving and initialization 
	#################################################

	def __createNewPrefs(self):
		#todo - implement
		pass
	
	def initPrefs(self):

		self['Version'] = 97 # NOTE: change version if anything *major* is changed.
		self['DTSVersion'] = 24
		self['WriteShapeScript'] = False
		self['Sequences'] = {}
		self['Materials'] = {}
		self['PrimType'] = 'Tris'
		self['MaxStripSize'] = 6
		self['ClusterDepth'] = 1
		self['AlwaysWriteDepth'] = False
		self['Billboard'] = {'Enabled' : False,'Equator' : 10,'Polar' : 10,'PolarAngle' : 25,'Dim' : 64,'IncludePoles' : True, 'Size' : 20.0}
		self['BannedNodes'] = []
		self['CollapseRootTransform'] = True
		self['TSEMaterial'] = False
		self['exportBasename'] = SceneInfoClass.getDefaultBaseName()
		self['exportBasepath'] = SceneInfoClass.getDefaultBasePath()
		self['LastActivePanel'] = 'Shape'
		self['LastActiveSubPanel'] = 'DetailLevels'
		self['RestFrame'] = 1
		self['DetailLevels'] = {'Detail1':[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]}
		self['ExportScale'] = 1.0
		self['ShowWarningErrorPopup'] = True
		#return Prefs

	# Loads preferences
	def loadPrefs(self):
		Prefs = Registry.GetKey(self.Prefs_keyname, True)
		if not Prefs:
			
			#print ("Registry key '%s' could not be loaded, resorting to text object." % self.Prefs_keyname)

			loadedFromBuffer = True
			try: text_doc = Text.Get(DtsGlobals.textDocName)
			except:
				# No registry, no text, so need new prefs
				#print "No Registry and no text objects, must be new."
				self.initPrefs()
				# save new prefs
				self.savePrefs()
				loadedFromBuffer = False
				print "Created new preferences."
				
			if loadedFromBuffer:
				# Load preferences from the text buffer
				execStr = "loadPrefs = "
				for line in text_doc.asLines():
					execStr += line
				try:
					exec(execStr)
				except:
					return False

				Prefs = loadPrefs
				print "Loaded Preferences from text buffer."
		else:
			print "Loaded Preferences from Blender registry."
			
		# store the loaded prefs (if any) in this object
		self.__initFromDict(Prefs)
		
		# make sure the output path is valid.		
		if not os.path.exists(self['exportBasepath']):
			self['exportBasepath'] = SceneInfoClass.getDefaultBasePath()

		# initialize the global sceneinfo object
		if DtsGlobals.SceneInfo == None: DtsGlobals.SceneInfo = SceneInfoClass(self)
		
		# clean up visibility track lists
		self.cleanVisTracks()
		
		# save cleaned preferences back to disk
		self.savePrefs()


	def __initFromDict(self, dictionary):
		if dictionary == None: return
		for pair in dictionary.items():
			key, val = pair
			self[key] = val

	# Saves preferences to registry and text object
	def savePrefs(self):
		global Prefs_keyname
		Registry.SetKey(self.Prefs_keyname, dict(self), False) # must NOT cache the data to disk!!!
		self.saveTextPrefs()

	# Saves preferences to a text buffer
	def saveTextPrefs(self):
		global textDocName
		# We need a blank buffer
		try: text_doc = Text.Get(DtsGlobals.textDocName)
		except: text_doc = Text.New(DtsGlobals.textDocName)
		text_doc.clear()

		# Use python's amazing str() function to create a string based
		# representation of the config dictionary
		text_doc.write(str(dict(self)))

	
	#################################################
	#  Detail Levels
	#################################################

	# reassigns a given layer to a different detail level
	# this method makes sure that a given layer can be assigned to only one dl at a time.
	def setLayerAssignment(self, dlName, newLayer):
		# remove any existing assignment
		# (nevermind, allow overlapping layers for DLs)
		#self.removeLayerAssignment(newLayer)
		# assign layer to detail level
		self['DetailLevels'][dlName].append(newLayer)
			
	def removeLayerAssignment(self, layerNum):
		# remove any existing assignment
		for dl in self['DetailLevels'].values():
			for i in range(len(dl)-1, -1, -1):
				layer = dl[i]
				if layer == layerNum:
					del dl[i]

	def renameDetailLevel(self, oldName, newName):
		if newName != oldName and newName in self['DetailLevels'].keys():
			message = "A detail level with size of "+str(prefsClass.getTrailingNumber(newName))+" already exists.%t|Cancel"
			x = Blender.Draw.PupMenu(message)
			del x
		else:
			self['DetailLevels'][newName] = self['DetailLevels'][oldName]
			del self['DetailLevels'][oldName]

	# returns the detail level name that a given layer is assigned to, or none if not assigned
	def getLayerAssignment(self, layerNum):
		for dlName in self['DetailLevels'].keys():
			dl = self['DetailLevels'][dlName]
			if layerNum in dl:
				return dlName

	# gets the highest LOD visibility number
	def getHighestLODSize(self, DLType='Detail'):
		largest = 0
		for dlName in filter(lambda x: x[0:len(DLType)].lower() == DLType.lower(),  self['DetailLevels'].keys()):
			size = abs(prefsClass.getTrailingNumber(dlName))
			print "** size=",size
			if size > largest: largest = size
		if largest == 0: largest = None
		return largest


	
	# adds a new detail level to the preferences
	# if we are given an explicit size number, use that, otherwise
	# there is some convoluted logic for picking a new (unique) size
	# number that should make some kind of sense :-)
	def addDetailLevel(self, dlName='Detail', size=None, layers=None):
		if dlName == 'Detail': self.addVisibleDetailLevel()
		elif dlName == 'Collision': self.addCollisionDetailLevel()
		elif dlName == 'LOSCollision': self.addLosCollisionDetailLevel()

	def addVisibleDetailLevel(self, size=None, layers=None):
		dlName = 'Detail'
		# ---------------		
		# Pick a size, any size! Step right up, everyone's a winner!
		if size == None:
			# no size was specified, so create a unique
			# size number automatically.
			highest = self.getHighestLODSize()
			# there's already at least one detail level
			if highest != None and highest > 1:
				size = int(round(float(highest) / 2.0))
			else:
				# highest dl has size of 1?
				if highest != None:
					size = highest * 2
				# no detail levels?
				else:
					size = 1
		fullName = dlName + str(size)
		# make sure that the auto sized detail level dosen't already exist
		# go down by 1/2
		while fullName in self['DetailLevels'].keys() and size > 1:
			size = int(round(float(size)/2.0))
			fullName = dlName + str(size)			
		# go up by 2x
		while fullName in self['DetailLevels'].keys() and size < 1024:
			size *= 2
			fullName = dlName + str(size)
		# if we still don't have a valid number, just start again from one
		# and count up until we find a number that's not in use
		if fullName in self['DetailLevels'].keys():
			size = 1
			fullName = dlName + str(size)
			while fullName in self['DetailLevels'].keys() and size < 1024:
				size += 1
				fullName = dlName + str(size)
		# we should have a valid size and dl name at this point
		# ---------------
		
		# create the new detail level
		if layers == None: layers = []
		self['DetailLevels'][fullName] = layers


	
	def addCollisionDetailLevel(self, layers=None):
		dlName = 'Collision'
		# ---------------		
		highest = self.getHighestLODSize(dlName)
		if highest == None: highest = 0
		number = highest + 1
		fullName = dlName + '-' + str(number)

		if layers == None: layers = []
		self['DetailLevels'][fullName] = layers


	def addLosCollisionDetailLevel(self, layers=None):
		dlName = 'LOSCollision'
		# ---------------		
		highest = self.getHighestLODSize(dlName)
		if highest == None: highest = 0
		number = highest + 1
		fullName = dlName + '-' + str(number)
		if layers == None: layers = []
		self['DetailLevels'][fullName] = layers

				
	def delDetailLevel(self, dlName):
		try: del self['DetailLevels'][dlName]
		except: pass
	
		
	
	#################################################
	#  Sequences
	#################################################

	def setSeqDuration(self, seqName, duration):
		seqKey = self['Sequences'][seqName]
		seqKey['Duration'] = float(duration)
		self.__recalcFPS(seqName, seqKey)
		self.__updateSeqDurationAndFPS(seqName)
		return self['Sequences'][seqName]['Duration']

	# todo - implement
	def setSeqFPS(self, seqName, FPS):
		seqKey = self['Sequences'][seqName]
		seqKey['FPS'] = float(FPS)
		self.__recalcDuration(seqName, seqKey)
		self.__updateSeqDurationAndFPS(seqName)
		return self['Sequences'][seqName]['FPS']

		
	# lock sequence duration when frame count changes
	def lockDuration(self, seqName):
		self['Sequences'][seqName]['DurationLocked'] = True
		self['Sequences'][seqName]['FPSLocked'] = False
		pass
	
	# lock sequence fps when frame count changes
	def lockFPS(self, seqName):
		self['Sequences'][seqName]['DurationLocked'] = False
		self['Sequences'][seqName]['FPSLocked'] = True
		pass
		
	# gets current sequence data from bender and updates preferences
	def refreshSequencePrefs(self):
		seqInfo = SceneInfoClass.getSequenceInfo()		
		
		# check current sequences against prefs and update prefs
		for seqName in seqInfo.keys():
			seq = seqInfo[seqName]
			seqStart = seq[0]
			seqEnd = seq[1]
			# getSeqKey adds a new key if one does not exist
			key = self.getSeqKey(seqName)
			
			# adjust start and end of existing sequences to match current values
			key['StartFrame'] = seq[0]
			key['EndFrame'] = seq[1]


			# adjust duration or fps according to which is locked
			self.__updateSeqDurationAndFPS(seqName)
		
		# find any old sequences that no longer exist and get rid of them
		curSequences = seqInfo.keys()
		prefsSequences = self['Sequences'].keys()
		for seqName in prefsSequences:
			if not seqName in curSequences:
				del self['Sequences'][seqName]

	# Cleans up extra sequence keys that may not be used anymore (e.g. action deleted)
	# also calls cleanVisTracks to get rid of unused visibility tracks
	def cleanKeys():
		global Prefs
		# clean visibility tracks
		cleanVisTracks()
		# Sequences
		for keyName in Prefs['Sequences'].keys():
			key = getSequenceKey(keyName)
			actionFound = False
			try: actEnabled = key['Action']['Enabled']
			except: actEnabled = False
			# if action is enabled for the sequence
			if actEnabled:
				for actionName in Armature.NLA.GetActions().keys():
					if actionName == keyName:
						# we found a (hopefully) valid action
						actionFound = True
						break
			# if we didn't find a valid action
			if not actionFound:
				key['Action']['Enabled'] = False
				# see if any of the other sequence types are enabled
				VisFound = False
				IFLFound = False
				try: IFLFound = Prefs['Sequences'][keyName]['IFL']['Enabled']
				except: IFLFound = False
				try: VisFound = Prefs['Sequences'][keyName]['Vis']['Enabled']
				except: VisFound = False
				# if no sequence type is enabled for the key, get rid of it.
				if VisFound == False and IFLFound == False:
					del Prefs['Sequences'][keyName]			

	# Gets a sequence key, creating it if it does not exist.
	# todo - implement
	def getSeqKey(self, seqName):
		try: retVal = self['Sequences'][seqName]
		except: retVal = self.__addNewSeqPref(seqName)
		return retVal
		
	def getSeqNumFrames(self, seqName):
		seqKey = self['Sequences'][seqName]
		seqStart = seqKey['StartFrame']
		seqEnd = seqKey['EndFrame']
		return seqEnd - seqStart
	
	def getSeqDuration(self, seqName):
		seqKey = self['Sequences'][seqName]
		return seqKey['Duration']
	
	def getSeqFPS(self, seqName):
		seqKey = self['Sequences'][seqName]
		return seqKey['FPS']

	def __validateGroundFrames(self, seqName):
		seqKey = self['Sequences'][seqName]
		numFrames = self.getSeqNumFrames(seqName)
		groundFrames = seqKey['NumGroundFrames']
		# make sure that the number of ground frames is in range
		if groundFrames > numFrames:
			Prefs['Sequences'][seqName]['NumGroundFrames'] = numFrames
	
	
	# called by getSeqKey
	def __addNewSeqPref(self, seqName):
		# todo - should use global timeline fps value for new sequences
		newSeq =\
		{
			'StartFrame': 1,
			'EndFrame': 2,
			'NumGroundFrames': 0,
			'Dsq': False,
			'Cyclic': False,
			'NoExport': False,
			'Priority': 0,
			'TotalFrames': 2,
			'Duration': 2.0 / 25.0,
			'DurationLocked': False,
			'FPS': 25,
			'FPSLocked': True,
			'Blend': False,
			'BlendRefPoseFrame': 1,
			'Triggers': []
		}
		self['Sequences'][seqName] = newSeq
		self['Sequences'][seqName]['IFL'] = { 'Enabled': False,'Material': None,'NumImages': 0,'TotalFrames': 0,'IFLFrames': [], 'WriteIFLFile': True}
		self['Sequences'][seqName]['Vis'] = { 'Enabled': False,'Tracks':{}}
		return self['Sequences'][seqName]

	# This function makes sure that the FPS and Duration values are in a valid range.
	def __validateSeqDurationAndFPS(self, seqName, seqPrefs):
		numFrames = self.getSeqNumFrames(seqName)
		if numFrames == 0: numFrames = 1
		maxDuration = 3600.0
		minDuration = 0.00392 # minimum duration = 1/255 of a second
		maxFPS = 255.0
		minFPS = 0.00027777778 # minimum fps = 1 frame for every 3600 seconds	

		if seqPrefs['Duration'] < minDuration:
			seqPrefs['Duration'] = minDuration
			seqPrefs['FPS'] = float(numFrames) / minDuration
		if seqPrefs['Duration'] > maxDuration:
			seqPrefs['Duration'] = maxDuration
			seqPrefs['FPS'] = float(numFrames) / maxDuration
		if seqPrefs['FPS'] < minFPS:
			seqPrefs['FPS'] = minFPS
			seqPrefs['Duration'] = float(numFrames) / minFPS
		if seqPrefs['FPS'] > maxFPS:
			seqPrefs['FPS'] = maxFPS
			seqPrefs['Duration'] = float(numFrames) / maxFPS

		# better safe than sorry :-)
		if seqPrefs['FPS'] < minFPS:
			seqPrefs['FPS'] = minFPS
		if seqPrefs['FPS'] > maxFPS:
			seqPrefs['FPS'] = maxFPS
		if seqPrefs['Duration'] < minDuration:
			seqPrefs['Duration'] = minDuration # minimum duration = 1/255 of a second
		if seqPrefs['Duration'] > maxDuration:
			seqPrefs['Duration'] = maxDuration # minimum duration = 1/255 of a second




	def __recalcDuration(self, seqName, seqPrefs):
		self.__validateSeqDurationAndFPS(seqName, seqPrefs)
		seqPrefs['Duration'] = float(self.getSeqNumFrames(seqName)) / float(seqPrefs['FPS'])


	def __recalcFPS(self, seqName, seqPrefs):
		self.__validateSeqDurationAndFPS(seqName, seqPrefs)
		seqPrefs['FPS'] = float(self.getSeqNumFrames(seqName)) / float(seqPrefs['Duration'])



	#  When number of frames changes, or may have changed, this method is called to
	#  update either duration or FPS for the sequence, depending on which is locked.
	def __updateSeqDurationAndFPS(self, seqName):
		seqPrefs = self['Sequences'][seqName]
		numFrames = self.getSeqNumFrames(seqName)
		# validate to avoid zero division
		self.__validateSeqDurationAndFPS(seqName, seqPrefs)
		# just an extra check here to make sure that we don't end up with both
		# duration and fps locked at the same time
		if seqPrefs['DurationLocked'] and seqPrefs['FPSLocked']:
			seqPrefs['DurationLocked'] = False
		# do we need to recalculate FPS, or Duration?
		if seqPrefs['DurationLocked']:
			# recalc FPS
			seqPrefs['FPS'] = float(numFrames) / seqPrefs['Duration']
		elif seqPrefs['FPSLocked']:
			# recalc duration
			seqPrefs['Duration'] = float(numFrames) / seqPrefs['FPS']
		# validate resulting values
		self.__validateSeqDurationAndFPS(seqName, seqPrefs)


	#################################################
	#  Visibility animations
	#################################################


	## @brief Creates a new visibility track key.
	#  @param objName The name of the object for which we are creating the visibility track.
	#  @param seqName The name of the sequence to which we are adding the visibility track.
	def createVisTrackKey(self, objName, seqName):
		seqKey = self['Sequences'][seqName]
		seqKey['Vis']['Tracks'][objName] = {}
		seqKey['Vis']['Tracks'][objName]['hasVisTrack'] = True
		seqKey['Vis']['Tracks'][objName]['IPOType'] = 'Object'
		seqKey['Vis']['Tracks'][objName]['IPOChannel'] = 'LocZ'
		seqKey['Vis']['Tracks'][objName]['IPOObject'] = None

	def deleteVisTrackKey(self, objName, seqName):
		del self['Sequences'][seqName]['Vis']['Tracks'][objName]

	# Cleans up unused and invalid visibility tracks
	def cleanVisTracks(self):
		for keyName in self['Sequences'].keys():
			key = self['Sequences'][keyName]
			VisFound = False
			try: VisFound = key['Vis']['Enabled']
			except: VisFound = False
			if not VisFound: continue
			visKey = key['Vis']
			# make a list of mesh objects in the highest detail level.
			DtsObjList = DtsGlobals.SceneInfo.getDtsObjectNames()
			# check each track in the prefs and see if it's enabled.
			# if it's not enabled, get rid of the track key.  Also,
			# check to make sure that objects still exist :-)
			for trackName in visKey['Tracks'].keys():
				track = visKey['Tracks'][trackName]
				try: hasTrack = track['hasVisTrack']
				except: hasTrack = False
				if not hasTrack:
					del self['Sequences'][keyName]['Vis']['Tracks'][trackName]
					continue
				# does the blender object still exist in the highest DL?
				if not trackName in DtsObjList:
					del self['Sequences'][keyName]['Vis']['Tracks'][trackName]
					continue

	#################################################
	#  Image File List animations
	#################################################

	# adds an IFL animation to a given sequence.
	def addIFLAnim(self, seqName):
		# add ifl pref key w/ default values
		seq = self['Sequences'][seqName]
		seq['IFL'] = {}
		seq['IFL']['Enabled'] = True
		seq['IFL']['Material'] = None
		seq['IFL']['NumImages'] = 1
		seq['IFL']['TotalFrames'] = 1
		seq['IFL']['IFLFrames'] = []
		seq['IFL']['WriteIFLFile'] = True
		pass
	
	# delete the IFL animation from a sequence
	def delIFLAnim(self, seqName):
		del self['Sequences'][seqName]['IFL']

	
	# changes the name of the ifl material and renames the image frames in an ifl animation
	def changeSeqIFLMaterial(self, seqName, newMatName):
		seq = self['Sequences'][seqName]
		ifl = seq['IFL']
		ifl['Material'] = newMatName
		matNameText = prefsClass.__getIFLMatTextPortion(newMatName)
		startNum = prefsClass.__determineIFLMatStartNumber(newMatName)
		numPadding = prefsClass.__determineIFLMatNumberPadding(newMatName)
		# replace existing frame names with new ones
		i = 0
		for i in range(0, len(ifl['IFLFrames'])):
			imageFrame = ifl['IFLFrames'][i]
			imageName = imageFrame[0]
			holdCount = imageFrame[1]
			textPortion = prefsClass.__getIFLMatTextPortion(imageName)
			newImageName = matNameText + prefsClass.__numToPaddedString(startNum + i, numPadding)
			ifl['IFLFrames'][i] = [newImageName, holdCount]
			

	# change the number of images in an IFL animation
	def changeSeqIFLImageCount(self, seqName, newCount, holdCount=1):
		self['Sequences'][seqName]['IFL']['NumImages'] = newCount
		oldCount = len(self['Sequences'][seqName]['IFL']['IFLFrames'])
		change = newCount - oldCount
		if change > 0:
			self.__addIFLImages(seqName, change, holdCount)
		elif change < 0:
			self.__deleteIFLImages(seqName, abs(change))
	
	# adds n frames to the end of an IFL animation's frames list
	def __addIFLImages(self, seqName, n, holdCount=1):
		for i in range(0, n):
			self.__addIFLImage(seqName, holdCount)
		
	# deletes n frames from the end of the IFL animation frames list
	def __deleteIFLImages(self, seqName, n):
		for i in range(0, n):
			self.__deleteLastIFLImage(seqName)

	# adds a new image frame to an ifl animation with a given hold count
	def __addIFLImage(self, seqName, holdCount=1):
		seq = self['Sequences'][seqName]
		ifl = seq['IFL']
		iflMatName = ifl['Material']
		matNameText = prefsClass.__getIFLMatTextPortion(iflMatName)
		startNum = prefsClass.__determineIFLMatStartNumber(iflMatName)
		numPadding = prefsClass.__determineIFLMatNumberPadding(iflMatName)
		newNum = startNum + len(ifl['IFLFrames'])
		imageName = matNameText + prefsClass.__numToPaddedString(newNum, numPadding)
		ifl['IFLFrames'].append([imageName, holdCount])
		

	# deletes the last image frame from an IFL animation
	def __deleteLastIFLImage(self, seqName):
		frames = self['Sequences'][seqName]['IFL']['IFLFrames']
		del frames[len(frames)-1]
		
	
	## @brief Returns the text portion of the passed in image name
	#     sans trailing number.
	#  @param matName The material name to be examined
	def __getIFLMatTextPortion(matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		textPortion = matName[0:i]
		if len(textPortion) > 0:
			return textPortion
		else:
			return ""
			
	__getIFLMatTextPortion = staticmethod(__getIFLMatTextPortion)


	## @brief Determines the starting number for the IFL sequence based
	#     on the trailing number in the passed in material name.
	#  @note If the material name does not contain a trailing number,
	#     zero is returned.
	def __determineIFLMatStartNumber(matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		digitPortion = matName[i:len(matName)]
		if len(digitPortion) > 0:
			return int(digitPortion)
		else:
			return 0
	
	__determineIFLMatStartNumber = staticmethod(__determineIFLMatStartNumber)
	
	## @brief Determines the number of zeros padding the trailing number
	#     contained in the passed in material name
	#  @note If the material name does not contain a trailing number,
	#     zero is returned.
	#  @param matName The material name to be examined
	def __determineIFLMatNumberPadding(matName):
		i = len(matName)-1
		while matName[i:len(matName)].isdigit() and i > -1: i -= 1
		i += 1
		digitPortion = matName[i:len(matName)]
		return len(matName) - i
		
	__determineIFLMatNumberPadding = staticmethod(__determineIFLMatNumberPadding)

	## @brief Converts a passed in integer into a zero padded string
	#     with the desired length.
	#  @param num The integer to be converted.
	#  @param padding The desired lenght of the generated string.
	def __numToPaddedString(num, padding):
		retVal = '0' * (padding - len(str(num)))
		retVal += str(num)
		return retVal
		
	__numToPaddedString = staticmethod(__numToPaddedString)


	#################################################
	#  Materials
	#################################################
		

	# gets current dts material data from blender and updates preferencees
	def refreshMaterialPrefs(self):
		SceneInfo = DtsGlobals.SceneInfo
		SceneInfo.refreshAll()
		imageList = SceneInfo.getDtsMaterials()
		materials = self['Materials']

		# remove unused materials from the prefs
		for imageName in materials.keys()[:]:
			if not (imageName in imageList): del materials[imageName]

		if len(imageList)==0: return

		# populate materials list with all blender materials
		for imageName in imageList:
			bmat = None
			# Do we have a blender material that matches the image name?
			try: bmat = Blender.Material.Get(imageName)
			except NameError:
				# No blender material, do we have a prefs key for this material?
				try: x = self['Materials'][imageName]
				except KeyError:
					# no corresponding blender material and no existing texture material, so use reasonable defaults.
					self['Materials'][imageName] = {}
					pmi = self['Materials'][imageName]
					pmi['SWrap'] = True
					pmi['TWrap'] = True
					pmi['Translucent'] = False
					pmi['Additive'] = False
					pmi['Subtractive'] = False
					pmi['SelfIlluminating'] = False
					pmi['NeverEnvMap'] = True
					pmi['NoMipMap'] = False
					pmi['MipMapZeroBorder'] = False
					pmi['IFLMaterial'] = False
					pmi['DetailMapFlag'] = False
					pmi['BumpMapFlag'] = False
					pmi['ReflectanceMapFlag'] = False
					pmi['BaseTex'] = imageName
					pmi['DetailTex'] = None
					pmi['BumpMapTex'] = None
					pmi['RefMapTex'] = None
					pmi['reflectance'] = 0.0
					pmi['detailScale'] = 1.0
				continue

			# We have a blender material, do we have a prefs key for it?
			try: x = self['Materials'][bmat.name]			
			except:
				# No prefs key, so create one.
				self['Materials'][bmat.name] = {}
				pmb = self['Materials'][bmat.name]
				# init everything to make sure all keys exist with sane values
				pmb['SWrap'] = True
				pmb['TWrap'] = True
				pmb['Translucent'] = False
				pmb['Additive'] = False
				pmb['Subtractive'] = False
				pmb['SelfIlluminating'] = False
				pmb['NeverEnvMap'] = True
				pmb['NoMipMap'] = False
				pmb['MipMapZeroBorder'] = False
				pmb['IFLMaterial'] = False
				pmb['DetailMapFlag'] = False
				pmb['BumpMapFlag'] = False
				pmb['ReflectanceMapFlag'] = False
				pmb['BaseTex'] = imageName
				pmb['DetailTex'] = None
				pmb['BumpMapTex'] = None
				pmb['RefMapTex'] = None
				pmb['reflectance'] = 0.0
				pmb['detailScale'] = 1.0

				if bmat.getEmit() > 0.0: pmb['SelfIlluminating'] = True
				else: pmb['SelfIlluminating'] = False

				pmb['RefMapTex'] = None
				pmb['BumpMapTex'] = None
				pmb['DetailTex'] = None

				# Look at the texture channels if they exist
				textures = bmat.getTextures()
				if len(textures) > 0:
					if textures[0] != None:
						if textures[0].tex.image != None:						
							pmb['BaseTex'] = stripImageExtension(textures[0].tex.image.getName())
						else:
							pmb['BaseTex'] = None

						if (textures[0] != None) and (textures[0].tex.type == Texture.Types.IMAGE):
							# Translucency?
							if textures[0].mapto & Texture.MapTo.ALPHA:
								pmb['Translucent'] = True
								if bmat.getAlpha() < 1.0: pmb['Additive'] = True
								else: pmb['Additive'] = False
							else:
								pmb['Translucent'] = False
								pmb['Additive'] = False
							# Disable mipmaps?
							if not (textures[0].tex.imageFlags & Texture.ImageFlags.MIPMAP):
								pmb['NoMipMap'] = True
							else:pmb['NoMipMap'] = False

							if bmat.getRef() > 0 and (textures[0].mapto & Texture.MapTo.REF):
								pmb['NeverEnvMap'] = False

					pmb['ReflectanceMapFlag'] = False
					pmb['DetailMapFlag'] = False
					pmb['BumpMapFlag'] = False
					for i in range(1, len(textures)):
						texture_obj = textures[i]					
						if texture_obj == None: continue
						# Figure out if we have an Image
						if texture_obj.tex.type != Texture.Types.IMAGE:
							continue

						# Determine what this texture is used for
						# A) We have a reflectance map
						if (texture_obj.mapto & Texture.MapTo.REF):
							# We have a reflectance map
							pmb['ReflectanceMapFlag'] = True
							pmb['NeverEnvMap'] = False
							if textures[0].tex.image != None:
								pmb['RefMapTex'] = stripImageExtension(textures[i].tex.image.getName())
							else:
								pmb['RefMapTex'] = None
						# B) We have a normal map (basically a 3d bump map)
						elif (texture_obj.mapto & Texture.MapTo.NOR):
							pmb['BumpMapFlag'] = True
							if textures[0].tex.image != None:
								pmb['BumpMapTex'] = stripImageExtension(textures[i].tex.image.getName())
							else:
								pmb['BumpMapTex'] = None
						# C) We have a texture; Lets presume its a detail map (since its laid on top after all)
						else:
							pmb['DetailMapFlag'] = True
							if textures[0].tex.image != None:
								pmb['DetailTex'] = stripImageExtension(textures[i].tex.image.getName())
							else:
								pmb['DetailTex'] = None
	





	
	#################################################
	#  Misc/Util
	#################################################
	

	

	# converts a file name into a legal python variable name.
	# this is need for blender registry support.
	def __pythonizeFileName(filename):
		# replace all non-alphanumeric chars with _
		p = re.compile('\W')
		return p.sub('_', filename)

	__pythonizeFileName = staticmethod(__pythonizeFileName)

	# gets a trailing number in a string
	def getTrailingNumber(string):
		for i in range(len(string)-1, -1, -1):
			if string[i].isalpha(): break
		retVal = int(string[i+1:len(string)])
		return retVal
	
	getTrailingNumber = staticmethod(getTrailingNumber)

	# gets the text portion of a string (with a trailing number)
	def getTextPortion(string):
		for i in range(len(string)-1, -1, -1):
			if string[i].isalpha(): break
		retVal = string[0:i+1]
		return retVal

	getTextPortion = staticmethod(getTextPortion)
