'''
About.py

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

import Common_Gui
import DtsGlobals

'''
***************************************************************************************************
*
* Class that creates and owns the GUI controls on the About control page
*
***************************************************************************************************
'''
class AboutControlsClass:
	def __init__(self, guiAboutSubtab):
		global globalEvents
		
		# initialize GUI controls
		self.guiAboutText = Common_Gui.MultilineText("guiAboutText", 
		"Torque Exporter Plugin for Blender\n" +
		"\n"
		"Written by James Urquhart, with assistance from Tim Gift, Clark Fagot, Wes Beary,\n" +
		"Ben Garney, Joshua Ritter, Emanuel Greisen, Todd Koeckeritz,\n" +
		"Ryan J. Parker, Walter Yoon, and Joseph Greenawalt.\n" +
		"GUI code written with assistance from Xen and Xavier Amado.\n" +
		"Additional thanks goes to the testers.\n" +
		"\n" +
		"Visit GarageGames at http://www.garagegames.com", None, self.guiAboutTextResize)
		
		# add controls to containers
		guiAboutSubtab.addControl(self.guiAboutText)
		

	def cleanup(self):

		# Must destroy any GUI objects that are referenced in a non-global scope
		# explicitly before interpreter shutdown to avoid the dreaded
		# "error totblock" message when exiting Blender.
		# Note: __del__ is not guaranteed to be called for objects that still
		# exist when the interpreter exits.
		del self.guiAboutText

	def refreshAll(self):
		pass
		
	def guiAboutTextResize(self, control, newwidth, newheight):
		control.x = 10
		control.y = 120

	
	# other event callbacks and helper methods go here.
