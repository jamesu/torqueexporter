#!BPY

"""
Name: 'Torque Shape (.dts)...'
Blender: 241
Group: 'Export'
Tooltip: 'Export to Torque (.dts) format.'
"""

'''
Dts_Blender.py
Copyright (c) 2003 - 2006 James Urquhart(j_urquhart@btinternet.com)

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

import Blender
from Blender import *
import os.path
import string, math, re, gc


from DTSPython import *
from DTSGUI import *
from DtsPrefs import *
from DtsSceneInfo import *
import DtsGlobals
import Common_Gui
import DtsShape_Blender
from DtsShape_Blender import *






def doExport(progressBar):
	Prefs = DtsGlobals.Prefs
	SceneInfo = DtsGlobals.SceneInfo
	Shape = BlenderShape(Prefs)
	#Scene.GetCurrent().getRenderingContext().currentFrame(Prefs['RestFrame'])
	Blender.Set('curframe', Prefs['RestFrame'])
	#try:
	# double check the base path before opening the stream
	if not os.path.exists(Prefs['exportBasepath']):
		Prefs['exportBasepath'] = basepath(Blender.Get("filename"))
	# double check the file name
	if Prefs['exportBasename'] == "":
		Prefs['exportBasename'] = noext(basename(Blender.Get("filename")))

	# make sure our path Separator is correct.
	pathSeparator = SceneInfoClass.getPathSeparator()
	#getPathSeparator(Prefs['exportBasepath'])
	Stream = DtsStream("%s%s%s.dts" % (Prefs['exportBasepath'], pathSeparator, Prefs['exportBasename']), False, Prefs['DTSVersion'])
	Torque_Util.dump_writeln("Writing shape to  '%s'." % ("%s%s%s.dts" % (Prefs['exportBasepath'], pathSeparator, Prefs['exportBasename'])))
	# Now, start the shape export process if the Stream loaded
	if Stream.fs:
		Torque_Util.dump_writeln("Processing...")

		# Import objects

		'''
		This part of the routine is split up into 4 sections:

		1) Get armatures and add them.
		2) Add every single thing from the base details that isn't an armature or special object.
		3) Add the autobillboard detail, if required.
		4) Add every single collision mesh we can find.
		'''
		#progressBar.pushTask("Importing Objects...", len(self.children), 0.4)
		progressBar.pushTask("Importing Objects...", 1, 0.4)

		# set the rest frame, this should be user-selectable in the future.
		Blender.Set('curframe', Prefs['RestFrame'])


		# add all nodes
		Shape.addAllNodes()

		# add detail levels
		for dlName in SceneInfo.detailLevels.keys():
			if dlName[0:6].upper() != 'DETAIL': continue
			dlSize = int(dlName[6:len(dlName)])
			meshDetails = SceneInfo.detailLevels[dlName]			
			Shape.addDetailLevel(meshDetails, dlSize)
		
		#add collision and loscollision detail levels
		'''
		curSize = -1		
		for marker in self.collisionMeshes:
			meshes = getAllChildren(marker)
			Shape.addCollisionDetailLevel(meshes, False, curSize)
			curSize -= 1
			progressBar.update()					
		curSize = -1
		for marker in self.losCollisionMeshes:
			meshes = getAllChildren(marker)
			Shape.addCollisionDetailLevel(meshes, True, curSize)
			curSize -= 1
			progressBar.update()
		'''
		
		# We have finished adding the regular detail levels. Now add the billboard if required.
		if Prefs['Billboard']['Enabled']:
			Shape.addBillboardDetailLevel(0,
				Prefs['Billboard']['Equator'],
				Prefs['Billboard']['Polar'],
				Prefs['Billboard']['PolarAngle'],
				Prefs['Billboard']['Dim'],
				Prefs['Billboard']['IncludePoles'],
				Prefs['Billboard']['Size'])


		progressBar.update()

		progressBar.popTask()

		progressBar.pushTask("Finalizing Geometry..." , 2, 0.6)
		# Finalize static meshes, do triangle strips
		Shape.finalizeObjects()
		Shape.finalizeMaterials()
		progressBar.update()
		if Prefs['PrimType'] == "TriStrips":
			Shape.stripMeshes(Prefs['MaxStripSize'])
		progressBar.update()

		# Add all actions (will ignore ones not belonging to shape)
		scene = Blender.Scene.GetCurrent()
		context = scene.getRenderingContext()
		actions = Armature.NLA.GetActions()

		# check the armatures to see if any are locked in rest position
		for armOb in Blender.Object.Get():
			if (armOb.getType() != 'Armature'): continue
			if armOb.getData().restPosition:
				# this popup was too long and annoying, let the standard warning/error popup handle it.
				#Blender.Draw.PupMenu("Warning%t|One or more of your armatures is locked into rest position. This will cause problems with exported animations.")
				Torque_Util.dump_writeWarning("Warning: One or more of your armatures is locked into rest position.\n This will cause problems with exported animations.")
				break

		# Process sequences
		seqKeys = Prefs['Sequences'].keys()
		if len(seqKeys) > 0:
			progressBar.pushTask("Adding Sequences..." , len(seqKeys*4), 0.8)
			for seqName in seqKeys:
				seqKey = Prefs['Sequences'][seqName]

				# does the sequence have anything to export?
				if (seqKey['NoExport']): # or not (seqKey['Action']['Enabled'] or seqKey['IFL']['Enabled'] or seqKey['Vis']['Enabled']):
					progressBar.update()
					progressBar.update()
					progressBar.update()
					progressBar.update()
					continue

				# try to add the sequence
				try: action = actions[seqName]
				except: action = None
				sequence = Shape.addSequence(seqName, seqKey, scene, action)
				if sequence == None:
					Torque_Util.dump_writeWarning("Warning : Couldn't add sequence '%s' to shape!" % seqName)
					progressBar.update()
					progressBar.update()
					progressBar.update()
					progressBar.update()
					continue
				progressBar.update()

				# Pull the triggers
				if len(seqKey['Triggers']) != 0:
					Shape.addSequenceTriggers(sequence, seqKey['Triggers'], getSeqNumFrames(seqName, seqKey))
				progressBar.update()
				progressBar.update()						

				# Hey you, DSQ!
				if seqKey['Dsq']:
					Shape.convertAndDumpSequenceToDSQ(sequence, "%s/%s.dsq" % (Prefs['exportBasepath'], seqName), Stream.DTSVersion)
					Torque_Util.dump_writeln("   Loaded and dumped sequence '%s' to '%s/%s.dsq'." % (seqName, Prefs['exportBasepath'], seqName))
				else:
					Torque_Util.dump_writeln("   Loaded sequence '%s'." % seqName)

				# Clear out matters if we don't need them
				if not sequence.has_loc: sequence.matters_translation = []
				if not sequence.has_rot: sequence.matters_rotation = []
				if not sequence.has_scale: sequence.matters_scale = []
				progressBar.update()

			progressBar.popTask()

		Torque_Util.dump_writeln("> Shape Details")
		Shape.dumpShapeInfo()
		progressBar.update()
		progressBar.popTask()

		# Now we've finished, we can save shape and burn it.
		progressBar.pushTask("Writing out DTS...", 1, 0.9)
		Torque_Util.dump_writeln("Writing out DTS...")
		Shape.finalize(Prefs['WriteShapeScript'])
		Shape.write(Stream)
		Torque_Util.dump_writeln("Done.")
		progressBar.update()
		progressBar.popTask()

		Stream.closeStream()
		del Stream
		del Shape
	else:
		Torque_Util.dump_writeErr("Error: failed to open shape stream! (try restarting Blender)")
		del Shape
		progressBar.popTask()
		return None
	'''
	except Exception, msg:
		Torque_Util.dump_writeErr("Error: Exception encountered, bailing out.")
		Torque_Util.dump_writeln(Exception)
		if tracebackImported:
			print "Dumping traceback to log..."
			Torque_Util.dump_writeln(traceback.format_exc())
		Torque_Util.dump_setout("stdout")
		if self.Shape: del self.Shape
		progressBar.popTask()
		raise
	'''



'''
	Functions to export shape and load script
'''
#-------------------------------------------------------------------------------------------------
def handleScene():	
	Prefs = DtsGlobals.Prefs
	#DtsGlobals.SceneInfo = SceneInfoClass(Prefs)
	SceneInfo = DtsGlobals.SceneInfo
	#if SceneInfo != None: SceneInfo.clear()


	#Torque_Util.dump_writeln("Processing Scene...")
	# What we do here is clear any existing export tree, then create a brand new one.
	# This is useful if things have changed.
	scn = Blender.Scene.GetCurrent()
	scn.update(1)	
	#updateOldPrefs()
	#Torque_Util.dump_writeln("Cleaning Preference Keys")
	#cleanKeys()
	#createActionKeys()
	
	Prefs.refreshSequencePrefs()
	Prefs.refreshMaterialPrefs()
	

def export():
	SceneInfo = DtsGlobals.SceneInfo
	Prefs = DtsGlobals.Prefs
	Torque_Util.dump_writeln("Exporting...")
	print "Exporting..."
	# switch out of edit mode if we are in edit mode
	Window.EditMode(0)
	handleScene()
	#importMaterialList()
	#refreshActionData()
	Prefs.savePrefs()
	
	cur_progress = Common_Gui.Progress()

	if SceneInfo != None:
		cur_progress.pushTask("Done", 1, 1.0)
		doExport(cur_progress)
		'''
		#if not export_tree.process(cur_progress):
			# try again :-)
			handleScene()
			importMaterialList()
			refreshActionData()
			savePrefs()
			#export_tree.process(cur_progress)
		'''		
		cur_progress.update()
		cur_progress.popTask()
		Torque_Util.dump_writeln("Finished.")
	else:
		Torque_Util.dump_writeErr("Error. Not processed scene yet!")
		
	del cur_progress	
	Torque_Util.dump_finish()
	
	if Torque_Util.numErrors > 0 or Torque_Util.numWarnings > 0:
		message = ("Export finished with %i error(s) and %s warning(s). Read the log file for more information." % (Torque_Util.numErrors, Torque_Util.numWarnings))
		print message
		if Prefs["ShowWarningErrorPopup"]:
			message +=  "%t|Continue|Do not show this message again"
			opt = Blender.Draw.PupMenu(message)
			if opt == 2:
				Prefs["ShowWarningErrorPopup"] = False
				# refresh the state of the button on the general panel
				GeneralControls.refreshAll()
		Torque_Util.numWarnings = 0
		Torque_Util.numErrors = 0
	else:
		print "Finished.  See generated log file for details."
		
		
		
	# Reselect any objects that are currently selected.
	# this prevents a strange bug where objects are selected after
	# export, but behave as if they are not.
	if Blender.Object.GetSelected() != None:
		for ob in Blender.Object.GetSelected():
			ob.select(True)


'''
	Entry Point
'''
#-------------------------------------------------------------------------------------------------

if DtsGlobals.Profiling:
	try:
		import profile
		import __main__
		import pstats
	except:
		Profiling = False
	
def entryPoint(a):
	#global Prefs, SceneInfo, pathSeparator
	#ScneInfo = SceneInfoClass()
	DtsGlobals.Prefs = prefsClass()
	Prefs = DtsGlobals.Prefs
	# sets the global pathSeparator variable
	SceneInfoClass.getPathSeparator()
	
	#loadPrefs()
	
	if DtsGlobals.Debug:
		Torque_Util.dump_setout("stdout")
	else:
		# double check the file name before opening the log
		if Prefs['exportBasename'] == "":
			Prefs['exportBasename'] = SceneInfoClass.getDefaultBaseName()
		
		try: x = Prefs['LogToOutputFolder']
		except KeyError: Prefs['LogToOutputFolder'] = True
		if Prefs['LogToOutputFolder']:
			Torque_Util.dump_setout( "%s%s%s.log" % (Prefs['exportBasepath'], pathSeparator, Prefs['exportBasename']) )
		else:
			Torque_Util.dump_setout("%s.log" % noext(Blender.Get("filename")))
		
		
	
	Torque_Util.dump_writeln("Torque Exporter %s " % Version)
	Torque_Util.dump_writeln("Using blender, version %s" % Blender.Get('version'))
	
	#if Torque_Util.Torque_Math.accelerator != None:
	#	Torque_Util.dump_writeln("Using accelerated math interface '%s'" % Torque_Util.Torque_Math.accelerator)
	#else:
	#	Torque_Util.dump_writeln("Using unaccelerated math code, performance may be suboptimal")
	#Torque_Util.dump_writeln("**************************")
	
	
	
	if (a == 'quick'):
		handleScene()
		# Use the profiler, if enabled.
		if Profiling:
			# make the entry point available from __main__
			__main__.export = export
			profile.run('export(),', 'exporterProfilelog.txt')
		else:
			export()
		
		# dump out profiler stats if enabled
		if Profiling:
			# print out the profiler stats.
			p = pstats.Stats('exporterProfilelog.txt')
			p.strip_dirs().sort_stats('cumulative').print_stats(60)
			p.strip_dirs().sort_stats('time').print_stats(60)
			p.strip_dirs().print_callers('__getitem__', 20)
	elif a == 'normal' or (a == None):
		# Process scene and load configuration gui
		handleScene()
		initGui()
	


# Main entrypoint
if __name__ == "__main__":
	entryPoint('normal')
