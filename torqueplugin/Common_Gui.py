'''
Blender_Gui.py

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
# Event server/table class
#----------------------------------------------------------------------------
class EventTable:
	def __init__(self, startID = 1):
		#print "*** Init called."
		self.NextID = None
		self.NextID = startID
		self.IDs = {}
		#print "1. self.NextID = ", self.NextID
	def getNewID(self, objectName):
		#print "2. self.NextID = ", self.NextID
		self.IDs[objectName] = self.NextID
		self.NextID += 1
		return self.IDs[objectName]
		
	


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
	myMenu.items.append("First Menu Item")
	myMenu.items.append("Second Menu Item")
	myMenu.items.append("Third Menu Item")
	myText = Common_Gui.SimpleText("myText", "Test These Fabulous Controls!", None, myCallback)
	
	Common_Gui.addGuiControl(myText)
	Common_Gui.addGuiControl(myMenu)
	Common_Gui.addGuiControl(myButton)
'''


class BasicControl:
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		self.name = name			# Internal name of control, used for event lookup
		self.text = text			# Control's text, if any.
		self.callback = callback		# Funcion called onAction()
		self.tooltip = tooltip			# Tooltip
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
		#print str(pos)+" vs %d %d" % (self.x, self.y)
		return (((pos[0] >= self.x) and (pos[1] >= self.y)) and ((pos[0] <= (self.x+self.width)) and (pos[1] <= (self.y+self.height))))

	# Override the following functions
	def onAction(self, evt, mousepos, value):
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		pass
		
	def onContainerResize(self, newwidth, newheight):
		if self.resize_callback: self.resize_callback(self, newwidth, newheight)

	def addControl(self, control):
		print "Error: Control does not support nested items!"
	
	def removeControl(self, control):
		print "Error: Control does not support nested items!"
		return False

class BasicFrame(BasicControl):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, tooltip, evt, callback, resize_callback)
		self.width = 100
		self.height = 20
		self.borderColor = [0.0,0.0,0.0,0.0]
		
	def onDraw(self, offset):
		real_x = offset[0] + self.x
		real_y = offset[1] + self.y
		
		# Draw border
		BGL.glBegin(BGL.GL_LINES)
		BGL.glColor4f(self.borderColor[0],self.borderColor[1],self.borderColor[2], self.borderColor[3])
		# Left up
		BGL.glVertex2i(real_x,real_y)
		BGL.glVertex2i(real_x,real_y+self.height)
		# Top right
		BGL.glVertex2i(real_x,real_y+self.height)
		BGL.glVertex2i(real_x+self.width-1,real_y+self.height)
		# Right down
		BGL.glVertex2i(real_x+self.width,real_y+self.height)
		BGL.glVertex2i(real_x+self.width,real_y)
		# Bottom left
		BGL.glVertex2i(real_x+self.width,real_y)
		BGL.glVertex2i(real_x,real_y)
		
		BGL.glEnd()


class BasicButton(BasicControl):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, tooltip, evt, callback, resize_callback)
		self.width = 100
		self.height = 20
		
	def onDraw(self, offset):
		#print "self.* = ", self.text, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.tooltip
		self.data = Draw.Button(self.text, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.tooltip)

class TabButton(BasicButton):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		global curTheme
		BasicButton.__init__(self, name, text, tooltip, evt, callback, resize_callback)		
		self.height = 25		
		self.selectedColor = [169.0/255.0, 169.0/255.0, 169.0/255.0, 169.0/255.0]
		self.unselectedColor = [146.0/255.0, 146.0/255.0, 146.0/255.0, 146.0/255.0]
		self.color = self.unselectedColor
		self.borderColor = [0.0,0.0,0.0,0.0]
		self.textColor = [0.0,0.0,0.0,0.0]
		self.state = False

	def onAction(self, evt, mousepos, value):	
		if value == Draw.LEFTMOUSE:
			if not (Window.GetMouseButtons() & Window.MButs.L):
				if not self.state: self.state = True
				if self.state: self.color = self.selectedColor
				else: self.color = self.unselectedColor
				if (self.callback): self.callback(self)
		#else:
				# mouseover highlight
				#if self.state: self.color = [175.0/255.0, 175.0/255.0, 175.0/255.0, 175.0/255.0]
				#else: self.color = [152.0/255.0, 152.0/255.0, 152.0/255.0, 152.0/255.0]

		self.onDraw([self.x,self.y])
		return True
	
	def onContainerResize(self, newwidth, newheight):
		if self.resize_callback: self.resize_callback(self, newwidth, newheight)
		
	def onDraw(self, offset):
		if self.state: self.color = self.selectedColor
		else: self.color = self.unselectedColor
		real_x = offset[0] + self.x
		real_y = offset[1] + self.y
		# set color
		BGL.glBegin(BGL.GL_QUADS)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])		
		BGL.glEnd()
		BGL.glRecti(real_x, real_y, real_x+self.width, real_y+self.height)
		
		# Draw border
		BGL.glBegin(BGL.GL_LINES)
		BGL.glColor4f(self.borderColor[0],self.borderColor[1],self.borderColor[2], self.borderColor[3])
		# Left up
		BGL.glVertex2i(real_x,real_y)
		BGL.glVertex2i(real_x,real_y+self.height)
		# Top right
		BGL.glVertex2i(real_x,real_y+self.height)
		BGL.glVertex2i(real_x+self.width-1,real_y+self.height)
		# Right down
		BGL.glVertex2i(real_x+self.width,real_y+self.height)
		BGL.glVertex2i(real_x+self.width,real_y)
		if self.state:
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
		# Bottom left
		BGL.glVertex2i(real_x+self.width,real_y)
		BGL.glVertex2i(real_x,real_y)
		
		# draw inside shading		
		BGL.glColor4f(self.color[0]+0.075,self.color[1]+0.075,self.color[2]+0.075, self.color[3]+0.075)
		# top
		BGL.glVertex2i(real_x+1,real_y+self.height-1)
		BGL.glVertex2i(real_x+self.width-1,real_y+self.height-1)
		# left
		BGL.glColor4f(self.color[0]+0.075,self.color[1]+0.075,self.color[2]+0.075, self.color[3]+0.075)
		BGL.glVertex2i(real_x+self.width-1,real_y+self.height-1)
		BGL.glColor4f(self.color[0]-0.075,self.color[1]-0.075,self.color[2]-0.075, self.color[3]-0.075)
		BGL.glVertex2i(real_x+self.width-1,real_y)
		# right
		BGL.glColor4f(self.color[0]+0.075,self.color[1]+0.075,self.color[2]+0.075, self.color[3]+0.075)
		BGL.glVertex2i(real_x+1,real_y+self.height-1)
		BGL.glColor4f(self.color[0]-0.075,self.color[1]-0.075,self.color[2]-0.075, self.color[3]-0.075)
		BGL.glVertex2i(real_x+1,real_y)
		
		BGL.glEnd()
		
		
		

		BGL.glBegin(BGL.GL_QUADS)
		BGL.glColor4f(self.textColor[0], self.textColor[1], self.textColor[2], self.textColor[3])
		BGL.glEnd()
		# draw text
		# crazy hack, we have to draw the text in order to get the pixel width of the text,
		# so draw it off in nowhereland in order to determine the width >:-/
		BGL.glRasterPos2i(-99999, -99999)
		width = Draw.Text(self.text, 'normal')
		if width < self.width: drawText_x = (self.width - width) / 2		
		BGL.glRasterPos2i(real_x + drawText_x, real_y + (self.height/2)-3)
		width = Draw.Text(self.text, 'normal')
		



class ToggleButton(BasicButton):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicButton.__init__(self, name, text, tooltip, evt, callback, resize_callback)
		self.state = False

	def onAction(self, evt, mousepos, value):
		self.state = bool(self.data.val)
		if self.callback: self.callback(self)
		return True
		
	def onDraw(self, offset):
		#print "self.text = ", self.text
		self.data = Draw.Toggle(self.text, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.state, self.tooltip)

class ComboBox(BasicControl):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, tooltip, evt, callback, resize_callback)
		self.width = 150
		self.height = 20
		self.itemIndex = -1
		self.items = []

	# Constructs a menu out of a list of strings
	def constructString(self):
		ret = self.text+"%t|"
		count = 0
		for i in self.items:
			ret += str(i) + " %x" + str(count) + "|"
			count += 1
		return ret
	
	# Sets the item idx to idx of what it finds
	def setTextValue(self, value):
		for i in range(0, len(self.items)):
			if self.items[i] == value:
				self.itemIndex = i
				return
		self.itemIndex = 0
		
	# get the string corresponding to the selected item
	def getSelectedItemString(self):
		return self.items[self.itemIndex]
		
	# find a string in the list of items and return it's index
	def getItemIndexFromString(self, string):
		for i in range(0, len(self.items)):
			if self.items[i] == string:
				return i
		return -1

	def selectStringItem(self, string):
		self.itemIndex = self.getItemIndexFromString(string)
	
	def onAction(self, evt, mousepos, value):
		self.itemIndex = int(self.data.val)
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		self.data = Draw.Menu(self.constructString(), self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.itemIndex)
		
class TextBox(BasicControl):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, tooltip, evt, callback, resize_callback)
		self.width = 150
		self.height = 20
		self.value = ""
		self.length = 30
	
	def onAction(self, evt, mousepos, value):
		self.value = str(self.data.val)
		if self.callback: self.callback(self)
		return True

	def onDraw(self, offset):
		self.data = Draw.String(self.text, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.value, self.length, self.tooltip)

class NumberPicker(BasicControl):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, tooltip, evt, callback, resize_callback)
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
		self.data = Draw.Number(self.text, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.value, self.min, self.max)
		
class NumberSlider(NumberPicker):
	def __init__(self, name=None, text=None, tooltip=None, evt=None, callback=None, resize_callback=None):
		NumberPicker.__init__(self, name, text, tooltip, evt, callback, resize_callback)

	def onDraw(self, offset):
		self.data = Draw.Slider(self.text, self.evt, self.x+offset[0], self.y+offset[1], self.width, self.height, self.value, self.min, self.max)
												
class SimpleText(BasicControl):
	def __init__(self, name=None, label="", callback=None, resize_callback=None):
		global curTheme
		BasicControl.__init__(self, name, label, None, None, callback, resize_callback)
		self.enabled = False
		
		curTextCol = curTheme.get('buts').text
		self.color = [curTextCol[0]/255.0,curTextCol[1]/255.0,curTextCol[2]/255.0,curTextCol[3]/255.0]
		self.label = label
		self.size = "normal"

	def onDraw(self, offset):
		# Evil hack: pretend we are drawing quad's, setting the color there
		BGL.glBegin(BGL.GL_QUADS)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])
		BGL.glEnd()
		BGL.glRasterPos2i(offset[0]+self.x, offset[1]+self.y)
		self.data = Draw.Text(self.label, self.size)
		
class MultilineText(SimpleText):
	def onDraw(self, offset):
		# Evil hack: pretend we are drawing quad's, setting the color there
		BGL.glBegin(BGL.GL_QUADS)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])
		BGL.glEnd()
		
		# Horrific hack: guess the text size considering lines
		if self.size == "normal": incY = 15
		elif self.size == "small": incY = 10
		elif self.size == "large": incY = 20
		
		curX = offset[0]+self.x
		curY = offset[1] + self.y
		
		# Essentially we draw the lines in reverse going upwards, acting like any other control
		lines = self.label.split("\n")
		lines.reverse()
		for line in lines:
			BGL.glRasterPos2i(curX, curY)
			self.data = Draw.Text(line, self.size)
			curY += incY
							
class SimpleLine(BasicControl):
	def __init__(self, name=None, text=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, None, None, callback, resize_callback)
		self.enabled = False
		self.color = [1.0,1.0,1.0,1.0]
		self.width = 100
		self.height = 1

	def onDraw(self, offset):
		BGL.glBegin(BGL.GL_LINES)
		BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
		BGL.glVertex2d(self.x+offset[0],self.y+offset[1])
		BGL.glVertex2d(self.x+self.width+offset[0],self.y+self.height+offset[1])
		BGL.glEnd()
		
class SimpleImage(BasicControl):
	def __init__(self, name=None, text=None, image=None, callback=None, resize_callback=None):
		BasicControl.__init__(self, name, text, None, None, callback, resize_callback)
		self.enabled = False
		self.color = [1.0,1.0,1.0,1.0]
		self.image = image
		self.width = 100
		self.height = 100

	def onDraw(self, offset):
		BGL.glEnable(BGL.GL_BLEND) 
		self.data = Draw.Image(self.image, self.x+offset[0], self.y+offset[1],  float(self.width) / float(self.image.size[0]), float(self.height) / float(self.image.size[1]))
		BGL.glDisable(BGL.GL_BLEND)

class BasicContainer(BasicControl):
	def __init__(self, name=None, text=None, callback=None, resize_callback=None):
		global curTheme
		BasicControl.__init__(self, name, text, None, None, callback, resize_callback)
		self.nested = True		
		curBg = curTheme.get('buts').panel
		curBorder = curTheme.get('ui').outline
		self.color = [curBg[0]/255.0,curBg[1]/255.0,curBg[2]/255.0,curBg[3]/255.0]
		self.borderColor = [curBorder[0]/255.0, curBorder[1]/255.0, curBorder[2]/255.0, curBorder[3]/255.0]
		self.fade_mode = 0
		self.controls = []
		self.controlDict = {}
		
	def __del__(self):
		del self.controls
	
	def onAction(self, evt, mousepos, value):
		#print "onAction called... (basiccontainer)"
		#print "BASICCONTAINER CHECKING FOR evt=" + str(evt)
		newpos = [mousepos[0]-self.x, mousepos[1]-self.y]
				
		if evt == None:
			for control in self.controls:
				if (control.evt != None) or (control.enabled == False):
					continue
				if control.positionInControl(newpos):
					if control.onAction(evt, newpos, value):
						return True
			# Only send callback if event wasn't captured
			if self.callback: self.callback(self)
		else:
			for control in self.controls:
				if control.evt == evt:
					if control.enabled:
						control.onAction(evt, newpos, value)
						return True
				elif control.nested:
					if control.enabled:
						if control.onAction(evt, newpos, value):
							return True
			# Only send callback if event wasn't captured
			if self.callback: self.callback(self)
		return False

	def onDraw(self, offset):
		BGL.glRasterPos2i(offset[0]+self.x, offset[1]+self.y)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])
		
		# Draw Box to distinguish container
		real_x = offset[0] + self.x
		real_y = offset[1] + self.y
		
		fadeStyle = -1
		
		if self.fade_mode == 0:
			fadeStyle = 0
		elif self.fade_mode > 0:
			if self.fade_mode > 6:   # brighter endColor
				startColor = self.color
				endColor = [self.color[0]*0.6,self.color[1]*0.6,self.color[2]*0.6,self.color[3]]
				fadeStyle = self.fade_mode-6
			elif self.fade_mode > 3: # normal endColor
				startColor = [self.color[0]*0.2,self.color[1]*0.2,self.color[2]*0.2,self.color[3]]
				endColor = self.color
				fadeStyle = self.fade_mode-3
			else:
				startColor = self.color
				endColor = [self.color[0]*0.2,self.color[1]*0.2,self.color[2]*0.2,self.color[3]]
				fadeStyle = self.fade_mode

		BGL.glEnable(BGL.GL_BLEND)
		if fadeStyle == 0:
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			BGL.glRecti(real_x, real_y, real_x+self.width, real_y+self.height)
		elif fadeStyle == 1:
			BGL.glBegin(BGL.GL_QUADS)
			BGL.glColor4f(startColor[0],startColor[1],startColor[2], startColor[3])
			BGL.glVertex2d(real_x,real_y)
			BGL.glVertex2d(real_x,real_y+self.height)
			BGL.glColor4f(endColor[0],endColor[1],endColor[2], endColor[3])
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			BGL.glVertex2d(real_x+self.width,real_y)
			BGL.glEnd()
		elif fadeStyle == 2:
			BGL.glBegin(BGL.GL_QUADS)
			BGL.glColor4f(startColor[0],startColor[1],startColor[2], startColor[3])
			BGL.glVertex2d(real_x,real_y+self.height)
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			BGL.glColor4f(endColor[0],endColor[1],endColor[2], endColor[3])
			BGL.glVertex2d(real_x+self.width,real_y)
			BGL.glVertex2d(real_x,real_y)
			BGL.glEnd()
		elif fadeStyle == 3:
			BGL.glBegin(BGL.GL_QUADS)
			BGL.glColor4f(startColor[0],startColor[1],startColor[2], startColor[3])
			BGL.glVertex2d(real_x,real_y+self.height)
			BGL.glColor4f(endColor[0],endColor[1],endColor[2], endColor[3])
			BGL.glVertex2d(real_x+self.width,real_y+self.height)
			BGL.glColor4f(startColor[0],startColor[1],startColor[2], startColor[3])
			BGL.glVertex2d(real_x+self.width,real_y)
			BGL.glColor4f(endColor[0],endColor[1],endColor[2], endColor[3])
			BGL.glVertex2d(real_x,real_y)
			BGL.glEnd()
		BGL.glDisable(BGL.GL_BLEND) 
		
		for control in self.controls:
			if control.visible:
				control.onDraw([real_x, real_y])
				
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
		
	def onContainerResize(self, newwidth, newheight):
		BasicControl.onContainerResize(self, newwidth, newheight)
		for c in self.controls:
			c.onContainerResize(self.width, self.height)

	def addControl(self, control):
		self.controls.append(control)
		self.controlDict[control.name] = control
		
	def removeControl(self, control):
		res = False
		for i in range(0, len(self.controls)):
			if self.controls[i] == control:
				del self.controls[i]
				res = True
				break
			if Controls[i].nested:
				if self.controls[i].removeControl(control):
					res = True
					break
		return res

class TabContainer(BasicContainer):
	def __init__(self, name=None, text=None, tabButton=None, callback=None, resize_callback=None):
		global curTheme		
		BasicContainer.__init__(self, name, text, callback, resize_callback)
		self.borderColor = None
		self.tabButton = tabButton
	def onDraw(self, offset):
		self.borderColor = None
		BasicContainer.onDraw(self, offset)
		real_x = offset[0] + self.x
		real_y = offset[1] + self.y
		# Draw border
		BGL.glBegin(BGL.GL_LINES)
		BGL.glColor4f(0.0,0.0,0.0,0.0)
		# Top right
		BGL.glVertex2d(real_x,real_y+self.height)
		BGL.glVertex2d(real_x+self.width,real_y+self.height)
		# Right down
		BGL.glVertex2d(real_x+self.width,real_y+self.height)
		BGL.glVertex2d(real_x+self.width,real_y)
		# Bottom left
		BGL.glVertex2d(real_x+self.width,real_y)
		BGL.glVertex2d(real_x,real_y)
		# Left up
		BGL.glVertex2d(real_x,real_y)
		BGL.glVertex2d(real_x,real_y+self.height)
		# draw to edge of tab button
		BGL.glVertex2d(real_x,real_y+self.height)
		BGL.glVertex2d(real_x + self.tabButton.x,real_y+self.height)
		BGL.glColor4f(169.0/255.0, 169.0/255.0, 169.0/255.0, 169.0/255.0)
		# draw to other side of tab button
		BGL.glVertex2d(real_x + self.tabButton.x,real_y+self.height)
		BGL.glVertex2d(real_x + self.tabButton.x + self.tabButton.width,real_y+self.height)
		BGL.glColor4f(0.0,0.0,0.0,0.0)
		# draw from far edge of tab button to top right
		BGL.glVertex2d(real_x + self.tabButton.x + self.tabButton.width,real_y+self.height)
		BGL.glVertex2d(real_x+self.width,real_y+self.height)
		BGL.glEnd()
		


class ListContainer(BasicContainer):
	'''
	This class implements a scrollable list container.
	
	The size of all child controls is controlled by this container. If freedom of
	movement is required, a BasicContainer should be added.
	Controls are drawn in order as-is on the controls list.
	
	One property of this list you can use to your advantage is that only visible controls are drawn
	and processed in onAction()'s. 
	
	To simplify things, the container only maintains one field.
	'''
	
	def __init__(self, name=None, text=None, callback=None, resize_callback=None):
		global curTheme
		BasicContainer.__init__(self, name, text, callback, resize_callback)
		
		curTextCol = curTheme.get('ui').menu_back
		self.color = [curTextCol[0]/255.0,curTextCol[1]/255.0,curTextCol[2]/255.0,curTextCol[3]/255.0]
		self.scrollPosition = 0	# Position in controls list draw starts from
		self.childHeight = 24	# Height of each child item
		self.thumbHeight = 16	# Height of the visible marker
		self.thumbPosition = 0	# Where is the marker? (to smooth things out)
		self.barWidth = 16		# Width of bar on the side
		self.dragState = False	# Are we currently dragging?
		
		self.itemIndex = -1		# Selected item
		
	def __del__(self):
		del self.controls
	
	def onAction(self, evt, mousepos, value):
		#print "SCROLLABLECONTAINER CHECKING FOR evt=" + str(evt)
		newpos = [mousepos[0]-self.x, mousepos[1]-self.y]
		
		dragEvents = [Draw.LEFTMOUSE, Draw.MOUSEX, Draw.MOUSEY]
		
		if evt == None:
			if self.needYScroll():
				# We can accept mouse wheel messages universally
				if value == Draw.WHEELUPMOUSE:
					if self.scrollPosition != 0:
						self.scrollPosition -= 1
						self.getIdealThumbPosition()
						#if self.callback: self.callback(self)
				elif value == Draw.WHEELDOWNMOUSE:
					if self.scrollPosition < (len(self.controls)-self.maxVisibleControls()):
						self.scrollPosition += 1
						self.getIdealThumbPosition()
						#if self.callback: self.callback(self)
				else:
					# Otherwise, we need to be in the scrollbar area
					if (newpos[0] >= (self.width-self.barWidth)):
						
						# We will drag, as long as dragState is true and the left mouse button is down,
						# but in order to activate we need to recieve a LEFTMOUSE event with the button
						# down.
						if value == Draw.LEFTMOUSE:
							self.dragState = Window.GetMouseButtons() & Window.MButs.L
							#print "Scrollbar drag state now " + str(self.dragState) 
						if self.dragState and (value in dragEvents):
							# Looks like we're dragging with the mouse down
							# The trick here is to realize that the top of the marker is where the value
							# is read, whilst the rest of the marker is just decoration.
							#
							# In addition, to avoid going off the list we don't consider any children near the end.
							
							if Window.GetMouseButtons() & Window.MButs.L:
								usefulChildren = len(self.controls)-self.maxVisibleControls()
								#print "Scrollbar useful children : %d" % usefulChildren
								#print str(newpos) + " | h:%d th:%d" % (self.height, self.thumbHeight)
								if newpos[1] <= self.thumbHeight:
									#print "YOU CLICKED UNDER THE THUMB HEIGHT"
									self.scrollPosition = usefulChildren
									self.thumbPosition = self.thumbHeight
								else:
									self.scrollPosition = int(( 1.0-(float(newpos[1]-self.thumbHeight) / (self.height - self.thumbHeight))) * usefulChildren)
									self.thumbPosition = newpos[1]
									
								#print "Scrollbar DRAGGING, Position calculated as : %d" % self.scrollPosition
							else:
								self.dragState = False
								#if self.callback: self.callback(self)
								#print "Scrollbar stopped DRAGGING in dragState because mouse was released somewhere."
			# Looks like we're probably clicking in the list body
			if (value == Draw.LEFTMOUSE) and (newpos[0] < (self.width-self.barWidth)):
				# Only send callback when mouse button is released!
				if not (Window.GetMouseButtons() & Window.MButs.L):
					# calculate the amount of dead space at the bottom if any
					deadSpace = self.height % self.childHeight
					# find the id of the list item that was clicked.
					idx = self.scrollPosition + int( (1.0- (float(newpos[1]-deadSpace) / (self.height-deadSpace)) ) * self.maxVisibleControls() )
					if idx >= len(self.controls) : idx = -1
					#print "Selected item %d" % idx
					self.selectItem(idx)
					if (self.callback): self.callback(self)
				
			return True
		else:
			# We don't have any callbacks here since the control state for the list hasn't been altered
			for control in self.controls:
				if control.evt == evt:
					if control.enabled:
						control.onAction(evt, newpos, value)
						return True
				elif control.nested:
					if control.enabled:
						if control.onAction(evt, newpos, value):
							return True				
		
		# Whoops
		return False
	
	def needYScroll(self):
		if len(self.controls) != 0:
			if (len(self.controls) * self.childHeight) > self.height:
				return True
		return False
		
	def maxVisibleControls(self):
		if self.height == 0: return 0
		return int(float(self.height) / self.childHeight)
		
	def getVisibleControls(self):
		if len(self.controls) == 0: return []
		maxValue = self.scrollPosition + self.maxVisibleControls()
		#print "VisibleControls: %d -> %d (len:%d)" % (self.scrollPosition, maxValue, len(self.controls))
		if maxValue > len(self.controls):
			return self.controls[self.scrollPosition:]
			#print "^^ CORRECTED"
		else:
			return self.controls[self.scrollPosition:maxValue]
			
	def getIdealThumbPosition(self):
		if len(self.controls) <= self.maxVisibleControls(): self.thumbPosition = self.thumbHeight
		#else: self.thumbPosition = self.height - int(( ((self.height - self.thumbHeight) / (len(self.controls) - self.maxVisibleControls()) ) * self.scrollPosition))
		else: self.thumbPosition = self.height - self.thumbHeight - int(( ((self.height - (self.thumbHeight * 3)) / (len(self.controls) - self.maxVisibleControls()) ) * self.scrollPosition))
			
	def selectItem(self, idx):
		if len(self.controls) == 0: return
		
		if self.itemIndex != -1: 
			curCol = curTheme.get('ui').menu_item
			curTextCol = curTheme.get('ui').menu_text
			self.controls[self.itemIndex].color = [curCol[0]/255.0, curCol[1]/255.0, curCol[2]/255.0, curCol[3]/255.0]
			if self.controls[self.itemIndex].nested:
				for c in self.controls[self.itemIndex].controls:
					if c.__class__ == SimpleText:
							c.color = [curTextCol[0]/255.0, curTextCol[1]/255.0, curTextCol[2]/255.0, curTextCol[3]/255.0]
		
		if (idx >= len(self.controls)): return
		self.itemIndex = idx
		if idx != -1:
			curCol = curTheme.get('ui').menu_hilite
			curTextCol = curTheme.get('ui').menu_text_hi
			self.controls[idx].color = [curCol[0]/255.0, curCol[1]/255.0, curCol[2]/255.0, curCol[3]/255.0]
			if self.controls[self.itemIndex].nested:
				for c in self.controls[self.itemIndex].controls:
					if c.__class__ == SimpleText:
						c.color = [curTextCol[0]/255.0, curTextCol[1]/255.0, curTextCol[2]/255.0, curTextCol[3]/255.0]

	def onDraw(self, offset):
		BGL.glRasterPos2i(offset[0]+self.x, offset[1]+self.y)
		BGL.glColor4f(self.color[0], self.color[1], self.color[2], self.color[3])
		
		# Draw Box to distinguish container
		real_x = offset[0] + self.x
		real_y = offset[1] + self.y
		
		BGL.glEnable(BGL.GL_BLEND)
		# Back to basics, just draw flat rectangle
		if self.fade_mode == 0:
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			BGL.glRecti(real_x, real_y, real_x+self.width, real_y+self.height)
		
		# Distinguished area
		BGL.glColor4f(self.borderColor[0],self.borderColor[1],self.borderColor[2], self.borderColor[3])
		BGL.glRecti(real_x+self.width-self.barWidth, real_y, real_x+self.width, real_y+self.height)
		BGL.glDisable(BGL.GL_BLEND)

		# Draw the arrowheads for the scrolling list
		BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
		BGL.glBegin(BGL.GL_TRIANGLES)
		BGL.glVertex2i (real_x + self.width - self.barWidth, real_y + self.height - self.thumbHeight)
		BGL.glVertex2i (real_x + self.width - (self.barWidth >> 1), real_y + self.height)
		BGL.glVertex2i (real_x + self.width, real_y + self.height - self.thumbHeight)

		BGL.glVertex2i (real_x + self.width - self.barWidth, real_y + self.thumbHeight)
		BGL.glVertex2i (real_x + self.width - (self.barWidth >> 1), real_y)
		BGL.glVertex2i (real_x + self.width, real_y + self.thumbHeight)
		BGL.glEnd()
		 
		# Now draw the scrollbar, if required
		if self.needYScroll():
			# Marker
			# Draw a line around the thumb to highlight it better.
			BGL.glColor4f(self.color[0] - 0.2,self.color[1] - 0.2,self.color[2] - 0.2, self.color[3])
			BGL.glRecti(real_x+self.width-self.barWidth, real_y+self.thumbPosition-self.thumbHeight, real_x+self.width, real_y+self.thumbPosition)
			BGL.glColor4f(self.color[0],self.color[1],self.color[2], self.color[3])
			#print "!!"+str(self.scrollPosition)
			#BGL.glRecti(real_x+self.width-self.barWidth, real_y+self.thumbPosition-self.thumbHeight, real_x+self.width, real_y+self.thumbPosition)
			BGL.glRecti(real_x+self.width-self.barWidth + 2, real_y+self.thumbPosition-self.thumbHeight + 1, real_x+self.width - 1, real_y+self.thumbPosition - 1)

		else:
			self.scrollPosition = 0
		
		# Draw items we need
		curY = self.height - self.childHeight
		idx = 0
		for control in self.getVisibleControls():
			control.y = curY
			orgColor = control.color
			if idx != self.itemIndex:
				if control.fade_mode == 0:
					if (idx & 1) == 0:
						control.color = [ orgColor [0] - 0.05, orgColor [1] - 0.05,
								  orgColor [2] - 0.05, orgColor [3] ]
					else:
						control.color = [ orgColor [0] + 0.05, orgColor [1] + 0.05,
								  orgColor [2] + 0.05, orgColor [3] ]
			control.onDraw([real_x, real_y])
			control.color = orgColor
			curY -= self.childHeight
			idx += 1
			
		# Draw border
		if self.borderColor != None:
			BGL.glBegin(BGL.GL_LINES)
			BGL.glColor4f(self.borderColor[0] - 0.2,self.borderColor[1] - 0.2, self.borderColor[2] - 0.2, self.borderColor[3])
			#BGL.glColor4f(self.borderColor[0],self.borderColor[1],self.borderColor[2], self.borderColor[3])
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
		
	def onContainerResize(self, newwidth, newheight):
		BasicControl.onContainerResize(self, newwidth, newheight)
		for c in self.controls:
			self.fitControlToContainer(c)
		self.getIdealThumbPosition()
		
	def fitControlToContainer(self, control):
		control.x = 0
		control.height = self.childHeight
		control.width = self.width-self.barWidth
		
	def addControl(self, control):
		BasicContainer.addControl(self, control)
		
		curCol = curTheme.get('ui').menu_item
		curTextCol = curTheme.get('ui').menu_text
		control.color = [curCol[0]/255.0, curCol[1]/255.0, curCol[2]/255.0, curCol[3]/255.0]
		
		# Conform to blender's menu text colors
		if control.nested:
			for c in control.controls:
				if c.__class__ == SimpleText:
					c.color = [curTextCol[0]/255.0, curTextCol[1]/255.0, curTextCol[2]/255.0, curTextCol[3]/255.0]
		
		self.fitControlToContainer(control)
		self.getIdealThumbPosition()
			
	def removeControl(self, control):
		BasicContainer.removeControl(self, control)
		if self.itemIndex >= len(self.controls): self.itemIndex = -1
		
		mc = self.maxVisibleControls()
		#print "List: Removing child, max controls=%d" % mc
		if len(self.controls) <= self.maxVisibleControls:
			#print "len(%d), so position = 0" % len(self.controls)
			self.scrollPosition = 0
		elif self.scrollPosition+mc > len(self.children):
			self.scrollPosition = len(self.children)-mc
			#print "len(%d), so position now = %d" % (len(self.controls), self.scrollPosition)
		self.getIdealThumbPosition()

class BasicGrid(BasicContainer):
	'''
	This class implements a simplistic grid control.
	
	All controls are resized during the resize event,
	taking into account properties set.
	'''
	def __init__(self, name=None, text=None, callback=None, resize_callback=None):
		BasicContainer.__init__(self, name, text, callback, resize_callback)
		
		self.minimumChildHeight = 20
		
	def __del__(self):
		del self.controls

	def onContainerResize(self, newwidth, newheight):
		BasicControl.onContainerResize(self, newwidth, newheight)
		
		if len(self.controls) == 0: return
		maxChildY = self.height / self.minimumChildHeight
		if maxChildY == 0: return
		#print "controls: %d" % len(self.controls)
		#print "maxY: %d" % maxChildY
		#print "newwidth: %d" % self.width
		#print "height: %d" % self.height
		
		# TODO: bug when len(controls) is not a multiple of maxChildY
		reminder = len(self.controls) % maxChildY
		#print "rem: %d" % reminder
		
		
		widthChildX = int(self.width / ((len(self.controls)+(maxChildY-reminder)) / maxChildY))
		#print widthChildX  # prints '150' to the console - Joe
		
		curX, curY = 0, 0
		for c in self.controls:
			if (curY == maxChildY):
				curY = 0
				curX += 1
			c.x = curX * widthChildX
			c.y = curY * self.minimumChildHeight
			c.width = widthChildX
			c.height = self.minimumChildHeight
			curY += 1
			


class BoneListContainer(ListContainer):
	'''
	This class implements a fancy grid control.
	
	All controls are resized during the resize event,
	taking into account properties set.
	'''
	def __init__(self, name=None, text=None, callback=None, resize_callback=None):
		ListContainer.__init__(self, name, text, callback, resize_callback)
		self.minimumChildHeight = 20
		self.childHeight = 20	# Height of each child item

	def selectItem(self, idx):
		return



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
			dragInitial[0] = curMousePos[0] - dragOffset[0]
			dragInitial[1] = curMousePos[1] - dragOffset[1]
		return
	elif evt == Draw.RIGHTMOUSE:
		if Draw.PupMenu("Display%t|Reset Gui Offset%x1") == 1:
			 dragOffset = [0,0]
	elif dragState and (evt in [Draw.MOUSEX, Draw.MOUSEY]):
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
			dragState = False
			#print("out of window")
		#print (dragOffset)		
	elif (evt in acceptedEvents):
		#print "EVT: Unaccepted general event,checking controls for action..."
		# Move the mouse position into window space
		areaBounds = Window.GetScreenInfo(Window.Types["SCRIPT"])[0]["vertices"]
		curMousePos[0] -= areaBounds[0]
		curMousePos[1] -= areaBounds[1]
		
		# Translate mouse position using the drag transform
		curMousePos[0] -= dragOffset[0]
		curMousePos[1] -= dragOffset[1]
		
		for control in Controls:
			if control.enabled == False:
				#print "Control %s [disabled]" % control.name
				continue
			
			# Might have a usable control here...
			if (control.positionInControl(curMousePos)):
				#print "Control %s [accepted]" % control.name
				control.onAction(None, curMousePos, evt)
				break
			#else:
			#print "Control %s [incorrect position]" % control.name
	if (not (evt in [Draw.MOUSEX, Draw.MOUSEY])) or dragState:
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
	#print windowSize[0], windowSize[1]
	
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

# Draw Function
def gui():
	global curTheme
	
	bgCol = curTheme.get('buts').back
	BGL.glClear(BGL.GL_COLOR_BUFFER_BIT & BGL.GL_DEPTH_BUFFER_BIT)
	BGL.glClearColor(bgCol[0],bgCol[1],bgCol[2],bgCol[3])
	BGL.glShadeModel(BGL.GL_SMOOTH)
	BGL.glBlendFunc(BGL.GL_SRC_ALPHA, BGL.GL_ONE_MINUS_SRC_ALPHA) 
	
	drawGuiControls()

def initGui(callback):
	global Controls, curAreaSize, dragOffset, dragInitial, dragState, curTheme
	Controls = []
	curAreaSize = [-1,-1]
	
	dragOffset = [0,0]
	dragInitial = [0,0]
	dragState = False
	
	global exitCallback
	exitCallback = callback
	
	curTheme = Theme.Get()[0]
	
	# Register our events
	Draw.Register(gui, event, button_event)
	
def destroyGui():
	global Controls
	Draw.Exit()
	del Controls[:]
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
	elif control.name == "myList":
		control.x = 450
		control.y = 100
		control.width = 200
		control.height = 24*3
	elif control.name == "myGrid":
		control.x = 450
		control.y = 300
		control.width = 200
		control.height = 24*3
		
def testGuiListCallback(control):
	global testGuiListContainer
	print "Callback: remove %s" % control.name
	testGuiListContainer.removeControl(control)

def testGuiExit():
	print "Gui Exited successfully."

def testGui():
	global testGuiButton, testGuiMenu, testGuiText
	global testGuiOtherButton, testGuiOtherMenu, testGuiOtherText
	global testGuiListContainer
	initGui(testGuiExit)
	
	testGuiButton = BasicButton("myBut", "Click me", 5, testGuiCallback, testGuiResizeCallback)
	testGuiMenu = ComboBox("myMenu", "Use this menu!", 10, testGuiCallback, testGuiResizeCallback)
	testGuiMenu.items.append("First Menu Item")
	testGuiMenu.items.append("Second Menu Item")
	testGuiMenu.items.append("Third Menu Item")
	testGuiText = SimpleText("myText", "Test These Fabulous Controls!", None, testGuiResizeCallback)
	
	
	myImage = Image.Load("/Users/jamesu/test-image.png")
	testGuiImage = SimpleImage("myImage", myImage, None, testGuiResizeCallback)
	
	# Container with the same controls in, using different events
	testGuiContainer = BasicContainer("myContainer", None, testGuiResizeCallback)
	testGuiOtherButton = BasicButton("otherBut", "Click me", 15, testGuiCallback, testGuiResizeCallback)
	testGuiOtherMenu = ComboBox("otherMenu", "Use this other menu!", 20, testGuiCallback, testGuiResizeCallback)
	testGuiOtherMenu.items.append("Other First Menu Item")
	testGuiOtherMenu.items.append("Other Second Menu Item")
	testGuiOtherMenu.items.append("Other Third Menu Item")
	testGuiOtherText = SimpleText("otherText", "Test These Fabulous Nested Controls!", None, testGuiResizeCallback)
	
	testGuiContainer.addControl(testGuiOtherText)
	testGuiContainer.addControl(testGuiOtherMenu)
	testGuiContainer.addControl(testGuiOtherButton)
	
	# Simple list control, to test list code
	testGuiListContainer = ListContainer("myList", None, testGuiResizeCallback)
	but1 = BasicButton("but1", "Button 1", 23, testGuiListCallback, None)
	but2 = BasicButton("but2", "Button 2", 24, testGuiListCallback, None)
	but3 = BasicButton("but3", "Button 3", 25, testGuiListCallback, None)
	but4 = BasicButton("but4", "Button 4", 26, testGuiListCallback, None)
	but5 = BasicButton("but5", "Button 5", 27, testGuiListCallback, None)
	testGuiListContainer.addControl(but1)
	testGuiListContainer.addControl(but2)
	testGuiListContainer.addControl(but3)
	testGuiListContainer.addControl(but4)
	testGuiListContainer.addControl(but5)
	
	# Simple grid control, to test grid code
	testGuiGridContainer = BasicGrid("myGrid", None, testGuiResizeCallback)
	for i in range(0, 4):
		testGuiGridContainer.addControl(BasicButton("testBut%d" % i, "Click me", 50, None, None))
	
	addGuiControl(testGuiText)
	addGuiControl(testGuiMenu)
	addGuiControl(testGuiButton)
	addGuiControl(testGuiImage)
	addGuiControl(testGuiContainer)
	addGuiControl(testGuiListContainer)
	addGuiControl(testGuiGridContainer)

if __name__ == "__main__":
	testGui()

