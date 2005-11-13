// Blender Exporter for Torque
// Windows installation script

var blenderPath;
var fso;
var WSHShell;

WSHShell = WScript.CreateObject("WScript.Shell");
fso = new ActiveXObject("Scripting.FileSystemObject");

// Get location of blender install
try {
	blenderPath = WSHShell.RegRead("HKEY_LOCAL_MACHINE\\SOFTWARE\\BlenderFoundation\\Install_Dir");
	blenderPath += "\\.blender";
} catch (jsException) {
	WSHShell.Popup("Couldn't locate blender folder!", 0, "Error", 16);
	WScript.quit(1);
}

// Verify scripts folder
if (fso.FolderExists(blenderPath)) {
	if (!fso.FolderExists(blenderPath + "\\scripts")) {
		if (!fso.CreateFolder(blenderPath + "\\scripts")) {
			WSHShell.Popup("Blender \"scripts\" folder could not be created!", 0, "Error", 16);
			WScript.quit(1);
		}
	}
} else {
	if (! (fso.CreateFolder(blenderPath) && fso.CreateFolder(blenderPath + "\\scripts")) ) {
		WSHShell.Popup("Blender script folders could not be created!", 0, "Error", 16);
		WScript.quit(1);
	}
}

// Now we can copy the files3 over
if ( fso.FileExists("Dts_Blender.py") && fso.FolderExists("DTSPython") ) {
	try
	{
		fso.CopyFile("Dts_Blender.py", blenderPath + "\\scripts\\", true);
		fso.CopyFile("DtsShape_Blender.py", blenderPath + "\\scripts\\", true);
		fso.CopyFile("DtsMesh_Blender.py", blenderPath + "\\scripts\\", true);
		fso.CopyFile("Common_Gui.py", blenderPath + "\\scripts\\", true);
        fso.CopyFolder("DTSPython",   blenderPath + "\\scripts\\", true);
		WSHShell.Popup("Scripts successfully copied.", 0, "Installation", 64);
	} catch (jsException) {
		WSHShell.Popup("Scripts could not be copied! ", 0, "Error", 16);
		WScript.quit(1);
	}
} else {
	WSHShell.Popup("Current folder does not contain exporter scripts!", 0, "Error", 16);
	WScript.quit(0);
}

WScript.quit(0);
