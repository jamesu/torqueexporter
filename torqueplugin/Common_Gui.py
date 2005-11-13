#!BPY

"""
Name: '0 GUI TEST'
Blender: 233
Group: 'Export'
Submenu: 'Test' testGui
Tooltip: 'Test Gui Controls'
"""

'''
Blender_Gui.py

Copyright (c) 2003 - 2005 James Urquhart(j_urquhart@btinternet.com)

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
from Blender import  Draw, BGL, Window, Image
from Blender.Window import Theme
import string
import math
import types

###########################
#   Blender Exporter For Torque
# -------------------------------
#     Export Gui for Blender
###########################

#----------------------------------------------------------------------------
Controls = None		# Simple array of controls
exitCallback = None	# Function called when gui has finished
curTheme = None		# Current blender theme dict
curAreaSize = None	# Current blender area size

# Dragging
dragOffset = None
dragInitial = None
dragState = False
dragError = 10

#----------------------------------------------------------------------------
'''
Notes:

The Gui is split up into Sheets. These Sheets contain different controls for different actions.
The Sheets can all be selected via the Sheet selector menu which should be present in every sheet.
Each Sheet has its own event handler ids, and its own value handler ids.
The event handler is for handling the events (clicks, etc),
The value handler gets the value for control(when drawing) with value id "val" for use in drawing the control.

Please be warned that the blender gui system sometimes sends the wrong event number when using menu's, so watch out.
'''

#----------------------------------------------------------------------------
# Main Gui Classes
#----------------------------------------------------------------------------
'''
	Gui controls are all implemented via classes, derived from BasicControl.
	Controls can have events assigned - though this is only useful for controls that use Draw.*.
	
	Controls can have two callbacks - these are as follows:
		onAction(control) - Called when control state changes
		onContainerResize(control, newwidth, newheight) - Called to set control positions or when container resizes
	
	An example of using these controls is as follows:
	
	def myCallback(control):
		global myButton, myMenu, myText
		if control.evt == 5:
			print "Button selected! item index of menu = %d" % myMenu.itemIndex
		elif control.evt == 10:
			print "Menu item %d selected!" % control.itemIndex

	def myResizeCallback(control, newwidth, newheight):
		global myButton, myMenu, myText
		if control.evt == 5:
			myButton.x = 10
			myButton.y = 10+myButton.height 
		elif control.evt == 10:
			myMenu.x = 10
			myMenu.y = 20+myButton.height+myMenu.height
		elif control.name == "myText":
			myText.x = 10
			myText.y =  40+myButton.height+myMenu.height
			myText.label = "Resize event, width=%d, height=%d" % (newwidth, newheight)
	
	myButton = Common_Gui.BasicButton("myBut", "Click me", 5, myCallback, myResizeCallback)
	myMenu = Common_Gui.ComboBox("myMenu", "Use this menu!", 10, myCallback, myResizeCallback)
	myMenu.construct([
	"First Menu Item",
	"Second Menu Item",
	"Third Menu Item"])
	myText = Common_Gui.SimpleText("myText", "Test These Fabulous Controls!", None, myCallback)
	
	Common_Gui.addGuiControl(myText)
	Common_Gui.addGuiControl(myMenu)
	Common_Gui.addGuiControl(myButton)
'''


class BasicControl:
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		self.name = name			# Internal name of control
		self.callback = callback	# Funcion called onAction()
		self.tooltip = tooltip		# Tooltip
		self.visible = True			# Is the control visible?
		self.data = None			# Control's blender data (or array of controls if nested)
		self.nested = False			# Control nests other controls
		self.enabled = True			# Does this control accept events?
		self.evt = evt				# Control's blender event
		self.resize_callback = resize_callback
		
		self.x = 0
		self.y = 0
		self.width = 0
		self.height = 0
		
	def positionInControl(self, pos):
		return (((pos[0] >= self.x) and (pos[1] >= self.y)) and ((pos[0] <= (self.x+self.width)) and (pos[1] <= (self.y+self.height))))

	# Override the following functions
	def onAction(self, evt, mousepos, value):
		return False

	def onDraw(self, offset):
		pass
		
	def onContainerResize(self, newwidth, newheight):
		if self.resize_callback: self.resize_callback(self, newwidth, newheight)

	def addControl(self, control):
		print "Error: Control does not support nested items!"
	
	def removeControl(self, control):
		print "Error: Control does not support nested items!"
		return False

class BasicButton(BasicControl):
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, tooltip, evt, callback, resize_callback)
		self.width = 100
		self.height = 20

	def onAction(self, evt, mousepos, value):
		if self.callback: self.callback(self)
		return True
		
	def onDraw(self, offset):
		self.data = Draw.Button(self.name, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.tooltip)

class ToggleButton(BasicButton):
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicButton.__init__(self, name, tooltip, evt, callback, resize_callback)
		self.state = False

	def onAction(self, evt, mousepos, value):
		self.state = self.data.val
		if self.callback: self.callback(self)
		return True
		
	def onDraw(self, offset):
		self.data = Draw.Toggle(self.name, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.state, self.tooltip)

class ComboBox(BasicControl):
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, tooltip, evt, callback, resize_callback)
		self.width = 150
		self.height = 20
		self.itemIndex = 0
		self.construct([])

	# Constructs a menu out of a list of strings
	def construct(self, items):
		self.menuItems = self.name+"%t|"
		count = 0
		for i in items:
			self.menuItems += str(i) + " %x" + str(count) + "|"
			count += 1

	def onAction(self, evt, mousepos, value):
		self.itemIndex = self.data.val
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		self.data = Draw.Menu(self.menuItems, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.itemIndex)
		
class TextBox(BasicControl):
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, tooltip, evt, callback, resize_callback)
		self.width = 150
		self.height = 20
		self.value = ""
		self.length = 30
	
	def onAction(self, evt, mousepos, value):
		self.value = self.data.val
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		self.data = Draw.String(self.name, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.value, self.length, self.tooltip)

class NumberPicker(BasicControl):
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, tooltip, evt, callback, resize_callback)
		self.width = 150
		self.height = 20
		self.value = 0
		self.min = 0
		self.max = 255
	
	def onAction(self, evt, mousepos, value):
		self.value = self.data.val
		if self.callback: self.callback(self)
		return True
		
	def onDraw(self, offset):
		self.data = Draw.Number(self.name, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.value, self.min, self.max)
		
class NumberSlider(NumberPicker):
	def __init__(self, name=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		NumberPicker.__init__(self, name, tooltip, evt, callback, resize_callback)

	def onDraw(self, offset):
		self.data = Draw.Slider(self.name, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.value, self.min, self.max)
												
class SimpleText(BasicControl):
	def __init__(self, name=None, label="", callback=None, resize_callback=None):
		BasicControl.__init__(self, name, None, None, callback, resize_callback)
		self.enabled = False
		self.color = [1.0,1.0,1.0,1.0]
		self.label = label
		self.size = "normal"

	def onAction(self, evt, mousepos, value):
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		# Evil hack: pretend we are drawing quad's, setting the color there
		BGL.glBegin(BGL.GL_QUADS)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])
		BGL.glEnd()
		BGL.glRasterPos2i(offset[0]+self.x, offset[1]+self.y)
		self.data = Draw.Text(self.label, self.size)
							
class SimpleLine(BasicControl):
	def __init__(self, name=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, None, None, callback, resize_callback)
		self.enabled = False
		self.color = [1.0,1.0,1.0,1.0]
		self.width = 100
		self.height = 1

	def onAction(self, evt, mousepos, value):
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		BGL.glBegin(BGL.GL_LINES)
		BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
		BGL.glVertex2d(self.x+offset[0],self.y+offset[1])
		BGL.glVertex2d(self.x+self.width+offset[0],self.y+self.height+offset[1])
		BGL.glEnd()
		
class SimpleImage(BasicControl):
	def __init__(self, name=None, image=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, None, None, callback, resize_callback)
		self.enabled = False
		self.color = [1.0,1.0,1.0,1.0]
		self.image = image
		self.width = 100
		self.height = 100

	def onAction(self, evt, mousepos, value):
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		BGL.glEnable(BGL.GL_BLEND) 
		BGL.glBlendFunc(BGL.GL_SRC_ALPHA, BGL.GL_ONE_MINUS_SRC_ALPHA) 
		self.data = Draw.Image(self.image, self.x, self.y,  float(self.width) / float(self.image.size[0]), float(self.height) / float(self.image.size[1]))
		BGL.glDisable(BGL.GL_BLEND)

class BasicContainer(BasicControl):
	def __init__(self, name=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, None, None, callback, resize_callback)
		self.nested = True
		self.color = [0.6,0.6,0.6,1.0]
		self.borderColor = [0.9, 0.9, 0.9, 1.0]
		self.fade_mode = 0
		self.controls = []
		
	def __del__(self):
		del self.controls
	
	def onAction(self, evt, mousepos, value):
		print "BASICCONTAINER CHECKING FOR evt=" + str(evt)
		newpos = [mousepos[0]-self.x, mousepos[1]-self.y]
		
		if self.callback: self.callback(self)
				
		if evt == None:
			for control in self.controls:
				if control.enabled == False:
					continue
				if control.positionInControl(newpos):
					if control.onAction(evt, newpos, value):
						return True
		else:
			for control in self.controls:
				if control.evt == evt:
					if control.enabled:
						control.onAction(evt, newpos, value)
						return True
					else: break
				elif control.nested:
					if control.enabled:
						if control.onAction(evt, newpos, value):
							return True
		return False

	def onDraw(self, offset):
		BGL.glRasterPos2i(offset[0]+self.x, offset[1]+self.y)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])
		
		# Draw Box to distinguish container
		real_x = offset[0] + self.x
		real_y = offset[1] + self.y
		
		# Fade left -> right
		if self.fade_mode == 1:
			BGL.glBegin(BGL.GL_QUADS)
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			BGL.glVertex2d(real_x,real_y)
			BGL.glVertex2d(real_x,real_y+self.height)
			BGL.glColor4f(self.color[0]*0.5,self.color[1]*0.5,self.color[2]*0.5, self.color[3]*0.5)
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			BGL.glVertex2d(real_x+self.width,real_y)
			BGL.glEnd()
		# Fade down -> up
		elif self.fade_mode == 2:
			BGL.glBegin(BGL.GL_QUADS)
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			BGL.glVertex2d(real_x,real_y+self.height)
			BGL.glColor4f(self.color[0]*0.5,self.color[1]*0.5,self.color[2]*0.5, self.color[3]*0.5)
			BGL.glVertex2d(real_x,real_y)
			BGL.glVertex2d(real_x+self.width,real_y)
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			BGL.glEnd()
		# Just draw flat rectangle
		else:
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			BGL.glRecti(real_x, real_y, real_x+self.width, real_y+self.height)
			
		#BGL.glColor3f(1.0,1.0,1.0)
		# Draw border
		if self.borderColor != None:
			BGL.glBegin(BGL.GL_LINES)
			BGL.glColor4f(self.borderColor[0],self.borderColor[1],self.borderColor[2], self.borderColor[3])
			# Left up
			BGL.glVertex2d(real_x,real_y)
			BGL.glVertex2d(real_x,real_y+self.height)
			# Top right
			BGL.glVertex2d(real_x,real_y+self.height)
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			# Right down
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			BGL.glVertex2d(real_x+self.width,real_y)
			# Bottom left
			BGL.glVertex2d(real_x+self.width,real_y)
			BGL.glVertex2d(real_x,real_y)
				
		BGL.glEnd()
		
		for control in self.controls:
			if control.visible:
				control.onDraw([real_x, real_y])
		
	def onContainerResize(self, newwidth, newheight):
		BasicControl.onContainerResize(self, newwidth, newheight)
		for c in self.controls:
			c.onContainerResize(self.width, self.height)

	def addControl(self, control):
		self.controls.append(control)
		
	def removeControl(self, control):
		res = False
		for i in range(0, len(self.controls)):
			if self.controls[i] == control:
				del self.ontrols[i]
				res = True
				break
			if Controls[i].nested:
				if self.controls[i].removeControl(control):
					res = True
					break
		return res
		
# Util class for blender progress bar
'''
	The progress management is quite simple.
	Create an instance of the Progress class, then use pushTask() to assign new tasks,
	which tell the user what we are currently doing.
	
	To update the status of a task, use update(). This will also update the progress bar in blender.
	In addition, blender's "busy" cursor is displayed as long as the progress object exists.

	When you are finished with a task, simply use popTask().
	

	e.g :
		myCounter = Progress()
		myCounter.pushTask("Done", 1, 1.0)

		myCounter.pushTask("Doing something in between...", 2, 0.5)
		myCounter.update()
		myCounter.update()
		myCounter.popTask()

		myCounter.pushTask("Doing something else in between...", 2, 0.5)
		myCounter.update()
		myCounter.update()
		myCounter.popTask()

		myCounter.update()
		myCounter.popTask()

'''
class Progress:
	def __init__(self):
		self.stack = []		# [name, increment, max]
		self.cProgress = 0.0
		Blender.Window.WaitCursor(True)

	def __del__(self):
		del self.stack
		Blender.Window.WaitCursor(False)

	def pushTask(self, name, maxItems, maxProgress):
		self.stack.append([name, (maxProgress - self.cProgress) / maxItems, maxProgress])
		Window.DrawProgressBar(self.cProgress, self.stack[-1][0])

	def popTask(self):
		#print "DBG: Popping", self.stack[-1]
		if len(self.stack) > 0: del self.stack[-1]
		else: Torque_Util.dump_writeln("Warning: popTask() with no task!")

	def curMax(self):
		return self.stack[-1][2]

	def curInc(self):
		return self.stack[-1][-1]

	def update(self):
		self.cProgress += self.stack[-1][1]
		if self.cProgress > self.stack[-1][2]:
			self.cProgress = self.stack[-1][2]

		#print "Updated Progress, Task '%s', %f/%f" % (self.stack[-1][0],self.cProgress,self.stack[-1][2])
		Window.DrawProgressBar(self.cProgress, self.stack[-1][0])

		
#----------------------------------------------------------------------------
# Drawing, Event handling, and Util functions
#----------------------------------------------------------------------------

# Function to process general events
def event(evt, val):
	global Controls, exitCallback, dragOffset, dragInitial, dragState, dragError
	
	acceptedEvents = [Draw.LEFTMOUSE, Draw.MIDDLEMOUSE, Draw.MOUSEX, Draw.MOUSEY, Draw.WHEELDOWNMOUSE, Draw.WHEELUPMOUSE]
	curMousePos = [Window.GetMouseCoords()[0], Window.GetMouseCoords()[1]]
	
	if evt == Draw.ESCKEY:
		destroyGui()
	elif evt == Draw.MIDDLEMOUSE:
		if not val: dragState = False
		else:
			dragState = True
			dragInitial[0] = Window.GetMouseCoords()[0] - dragOffset[0]
			dragInitial[1] = Window.GetMouseCoords()[1] - dragOffset[1]
		return
	elif evt == Draw.RIGHTMOUSE:
		if Draw.PupMenu("Display%t|Reset Gui Offset%x1") == 1:
			 dragOffset = [0,0]
	elif evt == Draw.MOUSEX or evt == Draw.MOUSEY:
		if dragState:
			areaBounds = Window.GetScreenInfo(Window.Types["SCRIPT"])[0]["vertices"]

			#print (GetMouseCoords()[0] - area[0]["vertices"][0])
			#print (GetMouseCoords()[1] - area[0]["vertices"][1])
			#mouseCoords = Window.GetMouseCoords()
			#print (mouseCoords)
			#print (area[0]["vertices"])

			# Make sure mouse is still inside script window
			if (curMousePos[0] > (areaBounds[0]+dragError) and curMousePos[0] < (areaBounds[2]-dragError)) and (curMousePos[1] > (areaBounds[1]+dragError) and curMousePos[1] < (areaBounds[3]-dragError)):
				dragOffset[0] = curMousePos[0] - dragInitial[0] #- lastRecordedMouseCoords[0] #- area[0]["vertices"][0]
				dragOffset[1] = curMousePos[1] - dragInitial[1] #- lastRecordedMouseCoords[1] #- area[0]["vertices"][1]
			else:
				dragGui = False
				#print("out of window")

			#print (dragOffset)
	elif (evt in acceptedEvents):
		# Translate mouse position using the drag transform
		curMousePos[0] += dragOffset[0]
		curMousePos[1] += dragOffset[1]
		
		for control in Controls:
			if control.enabled == False:
				continue
			# Might have a usable control here...
			if (control.positionInControl(curMousePos)):
				control.onAction(None, Window.GetMouseCoords(), evt)
				break
	Draw.Redraw(1)

# Function to process button events
# Passes event onto current handler sheet
def button_event(evt):
	global Controls, dragOffset
	
	# Translate mouse position using the drag transform
	curMousePos = [Window.GetMouseCoords()[0], Window.GetMouseCoords()[1]]
	curMousePos[0] += dragOffset[0]
	curMousePos[1] += dragOffset[1]
	
	for c in Controls:
		if c.evt == evt:
			if c.enabled == True:
				c.onAction(evt, curMousePos, -1)
			break
		elif c.nested:
			if c.enabled == True:
				c.onAction(evt, curMousePos, -1)

	Draw.Redraw(1)
	
def addGuiControl(control):
	global Controls
	Controls.append(control)
	
def removeGuiControl(control):
	global Controls
	res = False
	for i in range(0, len(Controls)):
		if Controls[i] == control:
			del Controls[i]
			res = True
			break
		if Controls[i].nested:
			if Controls[i].removeControl(control):
				res = True
				break
	return res

def drawGuiControls(baseLayer=False):
	global Controls, curAreaSize, dragOffset
	if len(Controls) == 0: return
	
	windowSize = Blender.Window.GetAreaSize()
	print windowSize[0], windowSize[1]
	
	if (curAreaSize[0] != windowSize[0]) or (curAreaSize[1] != windowSize[1]):
		curAreaSize = windowSize
		for control in Controls:
			if (control == None):
				continue
			control.onContainerResize(curAreaSize[0], curAreaSize[1])
	
	
	for control in Controls:
		if (control == None) or (control.visible == False):
			continue
		control.onDraw(dragOffset)
	
'''
	elif control['type'] == "TEXTLINES":
		if baseLayer: continue
		BGL.glRasterPos2i(control['x']+offset[0], control['y']+offset[1])
		posy = control['y']
		BGL.glColor3f(control['color'][0],control['color'][1],control['color'][2])
		for l in control['value']:
			BGL.glRasterPos2i(control['x']+offset[0], posy+offset[1])
			Draw.Text(l, control['size'])
			posy -= 15 # Text is this high, we are going downwards
'''

# Draw Function
def gui():
	global curTheme
	curTheme = Theme.Get()[0]
	
	BGL.glClearColor(0.5,0.5,0.5,1)
	BGL.glClear(BGL.GL_COLOR_BUFFER_BIT)
	BGL.glShadeModel(BGL.GL_SMOOTH)
	
	drawGuiControls()

def initGui(callback):
	global Controls, curAreaSize, dragOffset, dragInitial, dragState
	Controls = []
	curAreaSize = [-1,-1]
	
	dragOffset = [0,0]
	dragInitial = [0,0]
	dragState = False
	
	global exitCallback
	exitCallback = callback
	
	# Register our events
	Draw.Register(gui, event, button_event)
	
def destroyGui():
	global Controls
	Draw.Exit()
	del Controls
	Controls = None
	exitCallback()
	return

#----------------------------------------------------------------------------
# Test GUI routines and entrypoint
#----------------------------------------------------------------------------

testGuiButton, testGuiMenu, testGuiText = None, None, None
testGuiOtherButton, testGuiOtherMenu, testGuiOtherText, testGuiContainer = None, None, None, None

def testGuiCallback(control):
	global testGuiButton, testGuiMenu, testGuiText
	global testGuiOtherButton, testGuiOtherMenu, testGuiOtherText
	if control.evt == 5:
		print "Button selected! item index of menu = %d" % testGuiMenu.itemIndex
	elif control.evt == 10:
		print "Menu item %d selected!" % control.itemIndex
	elif control.evt == 15:
		print "Other button selected! item index of other menu = %d" % testGuiOtherMenu.itemIndex		
	elif control.evt == 20:
		print "Other menu item %d selected!" % control.itemIndex

def testGuiResizeCallback(control, newwidth, newheight):
	global testGuiButton, testGuiMenu, testGuiText
	global testGuiOtherButton, testGuiOtherMenu, testGuiOtherText
	if control.evt == 5:
		control.x = 10
		control.y = 10 
	elif control.evt == 10:
		control.x = 10
		control.y = 20+testGuiButton.height
	elif control.name == "myText":
		control.x = 10
		control.y =  30+testGuiButton.height+testGuiMenu.height
		control.label = "Resize event, width=%d, height=%d" % (newwidth, newheight)
	elif control.name == "myContainer":
		control.x = 10
		control.y = testGuiText.y + 10
		control.width = 300
		control.height= 200
	elif control.evt == 15:
		control.x = 10
		control.y = 10+testGuiOtherButton.height 
	elif control.evt == 20:
		control.x = 10
		control.y = 20+testGuiOtherButton.height+testGuiOtherMenu.height
	elif control.name == "otherText":
		control.x = 10
		control.y =  50+testGuiOtherButton.height+testGuiOtherMenu.height
		control.label = "Resize event, width=%d, height=%d" % (newwidth, newheight)
	elif control.name == "myImage":
		control.x = 50+testGuiMenu.width
		control.y = 10
		control.width = 50
		control.height = 50

def testGuiExit():
	print "Gui Exited successfully."

def testGui():
	global testGuiButton, testGuiMenu, testGuiText
	global testGuiOtherButton, testGuiOtherMenu, testGuiOtherText
	initGui(testGuiExit)
	
	testGuiButton = BasicButton("myBut", "Click me", 5, testGuiCallback, testGuiResizeCallback)
	testGuiMenu = ComboBox("myMenu", "Use this menu!", 10, testGuiCallback, testGuiResizeCallback)
	testGuiMenu.construct([
	"First Menu Item",
	"Second Menu Item",
	"Third Menu Item"])
	testGuiText = SimpleText("myText", "Test These Fabulous Controls!", None, testGuiResizeCallback)
	
	
	myImage = Image.Load("/Users/jamesu/test-image.png")
	testGuiImage = SimpleImage("myImage", myImage, None, testGuiResizeCallback)
	
	# Container with the same controls in, using different events
	testGuiContainer = BasicContainer("myContainer", None, testGuiResizeCallback)
	testGuiOtherButton = BasicButton("otherBut", "Click me", 15, testGuiCallback, testGuiResizeCallback)
	testGuiOtherMenu = ComboBox("otherMenu", "Use this other menu!", 20, testGuiCallback, testGuiResizeCallback)
	testGuiOtherMenu.construct([
	"Other First Menu Item",
	"Other Second Menu Item",
	"Other Third Menu Item"])
	testGuiOtherText = SimpleText("otherText", "Test These Fabulous Nested Controls!", None, testGuiResizeCallback)
	
	testGuiContainer.addControl(testGuiOtherText)
	testGuiContainer.addControl(testGuiOtherMenu)
	testGuiContainer.addControl(testGuiOtherButton)
	
	addGuiControl(testGuiText)
	addGuiControl(testGuiMenu)
	addGuiControl(testGuiButton)
	addGuiControl(testGuiImage)
	addGuiControl(testGuiContainer)

if __name__ == "__main__":
	testGui()

