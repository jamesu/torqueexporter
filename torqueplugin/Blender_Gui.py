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
from Blender import  Draw, BGL
import string
import math
import types

###########################
#   Blender Exporter For Torque
# -------------------------------
#     Export Gui for Blender
###########################

#-----------------------------------------------------------------------------
Sheets = None		# [[Controls, val_callback, evt_callback]]
CurrentSheet = 0	# Current Sheet
NewSheet = -1		# Sheet to Change To (-1 if none)
exitCallback = None	# Function called when gui has finished

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
# Quick helper functions

# Toggles visibility
def toggleControls(Controls):
	for c in Controls: c['visible'] = not c['visible']

# Constructs a menu out of a list of strings
def makeMenu(title,items):
	menuStr = title+"%t|"
	count = 0
	for i in items:
		menuStr += str(i) + " %x" + str(count) + "|"
		count += 1
	return menuStr
#----------------------------------------------------------------------------


# Function to process general events
def event(evt, val):
	global CurrentSheet, Sheets, exitCallback
	if evt == Draw.ESCKEY:
		Draw.Exit()
		del Sheets
		CurrentSheet = 0
		exitCallback()
		return
	else: return

	Draw.Redraw(1)

# Function to get values of buttons in different sheets
def passValue(val):
	global CurrentSheet
	global Sheets
	if len(Sheets) == 0: return False
	return Sheets[CurrentSheet][1](val)

# Function to process button events
# Passes event onto current handler sheet
def button_event(evt):
	global Sheets
	global CurrentSheet
	
	Sheets[CurrentSheet][2](evt)

	Draw.Redraw(1)

def drawControls(controls, offset=[0,0], baseLayer=False):
	if len(controls) == 0: return
	# Set Position
	for control in controls:
		# Do not show control if its not visible
		if type(control['visible']) == types.FunctionType: 
			if not control['visible'](): continue
		else: 
			if not control['visible']: continue
	
		if control['type'] == "TOGGLE":
			# (name, event, x, y, width, height, default, tooltip)
			if baseLayer: continue
			control['instance'] = Draw.Toggle(control['name'], control['event'], control['x']+offset[0], control['y']+offset[1], control['w'], control['h'], passValue(control['value']), control['tooltip'])
		
		elif control['type'] == "NUMBER":
			# (name, event, x, y, width, height, initial, min, max, realtime=1, tooltip) 
			if baseLayer: continue
			control['instance'] = Draw.Number(control['name'], control['event'], control['x']+offset[0], control['y']+offset[1], control['w'], control['h'], passValue(control['value']), control['min'], control['max'], control['tooltip'])
		
		elif control['type'] == "MENU":
			# (name, event, x, y, width, height, default, tooltip)
			# Get default value from menu val
			# If menu has not been made yet, get it from default
			if baseLayer: continue
			if control['instance'] == None: initialVal = control['value']
			else: initialVal = control['instance'].val
			
			# Get name for menu - this may be a function in the case of dynamic menus
			if type(control['items']) == types.FunctionType: menu_name = control['items']()
			else: menu_name = control['items']
	
			control['instance'] = Draw.Menu(	menu_name,
														control['event'], 
														control['x']+offset[0], 
														control['y']+offset[1], 
														control['w'], 
														control['h'], 
														initialVal)
														#control['tooltip'])
		
		elif control['type'] == "BUTTON":
			# (name, event, x, y, width, height, tooltip)
			if baseLayer: continue
			control['instance'] = Draw.Button(control['name'], 
														control['event'], 
														control['x']+offset[0], 
														control['y']+offset[1], 
														control['w'], 
														control['h'], 
														control['tooltip'])
		
		elif control['type'] == "TEXT":
			#if baseLayer: continue
			BGL.glRasterPos2i(control['x']+offset[0], control['y']+offset[1])
			BGL.glColor3f(control['color'][0],control['color'][1],control['color'][2])
			Draw.Text(control['value'], control['size'])
		
		elif control['type'] == "STRING":
			if baseLayer: continue
			# (name, event, x, y, width, height, initial, length, [tooltip])
			control['instance'] = Draw.String(control['name'], 
														control['event'],
														control['x']+offset[0], 
														control['y']+offset[1], 
														control['w'], 
														control['h'], 
														control['value'], 
														control['length'], 
														control['tooltip'])
		
		elif control['type'] == "TEXTLINES":
			if baseLayer: continue
			BGL.glRasterPos2i(control['x']+offset[0], control['y']+offset[1])
			posy = control['y']
			BGL.glColor3f(control['color'][0],control['color'][1],control['color'][2])
			for l in control['value']:
				BGL.glRasterPos2i(control['x']+offset[0], posy+offset[1])
				Draw.Text(l, control['size'])
				posy -= 15 # Text is this high, we are going downwards
			
		elif control['type'] == "SCROLLBAR":
			# (event, x, y, width, height, initial, min, max, realtime, tooltip) 
			if baseLayer: continue
			control['instance'] = Draw.Scrollbar(control['event'], 
															control['x']+offset[0], 
															control['y']+offset[1], 
															control['w'], 
															control['h'], 
															passValue(control['value']), 
															control['min'], 
															control['max'], 
															1, 
															control['tooltip'])
		
		elif control['type'] == "SLIDER":
			# (name, event, x, y, width, height, initial, min, max, realtime=1, tooltip=None) 
			if baseLayer: continue
			control['instance'] = Draw.Slider(control['name'], 
														control['event'], 
														control['x']+offset[0], 
														control['y']+offset[1], 
														control['w'], 
														control['h'], 
														passValue(control['value']), 
														control['min'], 
														control['max'])
														#control['tooltip'])
		
		elif control['type'] == "LINE":
			if not baseLayer: continue
			BGL.glBegin(BGL.GL_LINES)
			BGL.glColor3f(control['color'][0],control['color'][1],control['color'][2])
			BGL.glVertex2d(control['x']+offset[0],control['y']+offset[1])
			BGL.glVertex2d(control['x']+control['w']+offset[0],control['y']+control['h']+offset[1])
			BGL.glEnd()
		
		elif control['type'] == "CONTAINER":
			# Draw Box to distinguish container
			real_x = offset[0] + control['x']
			real_y = offset[1] + control['y']
			if baseLayer:
				# Fade left -> right
				if control['fade_mode'] == 1:
					BGL.glBegin(BGL.GL_QUADS)
					BGL.glColor3f(control['color_in'][0],control['color_in'][1],control['color_in'][2])
					BGL.glVertex2d(real_x,real_y)
					BGL.glVertex2d(real_x,real_y+control['h'])
					BGL.glColor3f(control['color_out'][0],control['color_out'][1],control['color_out'][2])
					BGL.glVertex2d(real_x+control['w'],real_y+control['h'])
					BGL.glVertex2d(real_x+control['w'],real_y)
					BGL.glEnd()
				# Fade down -> up
				elif control['fade_mode'] == 2:
					BGL.glBegin(BGL.GL_QUADS)
					BGL.glColor3f(control['color_in'][0],control['color_in'][1],control['color_in'][2])
					BGL.glVertex2d(real_x,real_y+control['h'])
					BGL.glColor3f(control['color_out'][0],control['color_out'][1],control['color_out'][2])
					BGL.glVertex2d(real_x,real_y)
					BGL.glVertex2d(real_x+control['w'],real_y)
					BGL.glColor3f(control['color_in'][0],control['color_in'][1],control['color_in'][2])
					BGL.glVertex2d(real_x+control['w'],real_y+control['h'])
					BGL.glEnd()
				# Just draw flat rectangle
				else:
					BGL.glColor3f(control['color_in'][0],control['color_in'][1],control['color_in'][2])
					BGL.glRecti(real_x, real_y, real_x+control['w'], real_y+control['h'])
				
				#BGL.glColor3f(1.0,1.0,1.0)
				# Draw border
				if control['color_border'] != None:
					BGL.glBegin(BGL.GL_LINES)
					BGL.glColor3f(control['color_border'][0],control['color_border'][1],control['color_border'][2])
					# Left up
					BGL.glVertex2d(real_x,real_y)
					BGL.glVertex2d(real_x,real_y+control['h'])
					# Top right
					BGL.glVertex2d(real_x,real_y+control['h'])
					BGL.glVertex2d(real_x+control['w'],real_y+control['h'])
					# Right down
					BGL.glVertex2d(real_x+control['w'],real_y+control['h'])
					BGL.glVertex2d(real_x+control['w'],real_y)
					# Bottom left
					BGL.glVertex2d(real_x+control['w'],real_y)
					BGL.glVertex2d(real_x,real_y)
					
					BGL.glEnd()
			
			# Then fork
			drawControls(control['items'],[real_x,real_y], baseLayer)
		elif control['type'] == "IMAGE":
			print "TODO: Image"

# Draw Function
def gui():
	global CurrentSheet
	global Sheets
	global NewSheet

	if NewSheet != -1:
		CurrentSheet = NewSheet
		NewSheet = -1

	BGL.glClearColor(0.5,0.5,0.5,1)
	BGL.glClear(BGL.GL_COLOR_BUFFER_BIT)
	BGL.glShadeModel(BGL.GL_SMOOTH)
	
	if len(Sheets) == 0: return
	
	# Draw back layer (CONTAINER, LINE) first, *then* text
	# to fix odd blender bug.
	drawControls(Sheets[CurrentSheet][0],[0,0],True)
	drawControls(Sheets[CurrentSheet][0],[0,0],False)

def addSheet(controls, val_callback, evt_callback):
	global Sheets
	Sheets.append([controls,val_callback, evt_callback])
	return len(Sheets)-1

def initGui(callback):
	global Sheets
	Sheets = []
	
	global exitCallback
	exitCallback = callback
	
	global CurrentSheet
	global NewSheet
	CurrentSheet = 0
	NewSheet = -1
	# Register our events
	Draw.Register(gui, event, button_event)

if __name__ == "__main__":
	initGui()
