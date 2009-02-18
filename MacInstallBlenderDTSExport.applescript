-- Torque Exporter for Blender
-- Installation Script
-- TLJF Modified to no longer assume a hardcoded Blender.app path


global successMessage
global failureMessage
global blenderPath
global blenderScriptPath
global theFileList

set successMessage to "Exporter scripts have been installed"
set failureMessage to "Incorrect script folder, please select the folder with the exporter scripts"
set disasterMessage to "Blender scripts folder could not be verified, please check permissions"

-- TLJF Break out file list for easier editing
set theFileList to "DTSPython DTSGUI Dts_Blender.py Common_Gui.py DtsShape_Blender.py DtsSceneInfo.py DtsPrefs.py DtsPoseUtil.py DtsMesh_Blender.py DtsGlobals.py Dts_Blender_QuickExport.py"


-- Installation Bash Scripts
-- (AppleScript doesn't seem to like accessing the hidden blender folder)
on installScripts(scriptPath)
	try
		-- TLJF Modified to use found Blender path
		set secondCommand to "cd \"" & scriptPath & "\"
if ( [ -e Dts_Blender.py ] && [ -e DTSPython ] )
then
	if ( cp -Rfv " & theFileList & " " & quoted form of blenderScriptPath & " )
	then
		echo \"Install: Scripts successfully copied.\"
	else
		echo \"Install: Scripts could not be copied, they already exist?\"
		exit 0
	fi
else
	echo \"Install: Selected folder does not contain exporter scripts!\"
	exit 1
fi
exit 0
"
		set cmdOutput to do shell script secondCommand
		
		
	on error cmdOutput
		--display dialog cmdOutput
		return false
	end try
	--display dialog cmdOutput
	return true
end installScripts

on verifyScriptFolder()
	try
		-- TLJF Modified to use found Blender path
		set firstCommand to "if [ -e " & quoted form of blenderPath & " ] 
then
	if [ -e  " & quoted form of blenderScriptPath & " ]
	then
		echo \"Install: Scripts folder ready.\"
	else
		if ( mkdir  " & quoted form of blenderScriptPath & " )
		then
			echo \"Install: Scripts folder created.\"
		else
			echo \"Install: Scripts folder could not be created!\"
			exit 1
		fi
	fi
else
	if ( ( mkdir  " & quoted form of blenderPath & " ) && ( mkdir  " & quoted form of blenderScriptPath & ") )
	then
		echo \"Install: All folders created.\"
	else
		echo \"Install: Script folders could not be created!\"
		exit 1
	fi
fi
exit 0
"
		set cmdOutput to do shell script firstCommand
	on error cmdOutput
		--display dialog cmdOutput
		return false
	end try
	return true
end verifyScriptFolder

on doDialogProbe()
	-- Loop until user has provided us with the correct folder
	set foundPath to false
	set curMsg to "Select the folder with the exporter scripts"
	repeat while foundPath is false
		-- First hurdle, the file dialog
		try
			set scriptPath to POSIX path of (choose folder with prompt curMsg)
		on error
			return
		end try
		
		-- Now try installing from selected directory
		if installScripts(scriptPath) is true then
			display dialog successMessage buttons {"OK"}
			exit repeat
		end if
		
		-- Pester the user with a more agressive prompt
		set curMsg to failureMessage
	end repeat
end doDialogProbe

try
	-- TLJF get location of Blender.app
	tell application "Finder"
		set appname to application file id "org.blenderfoundation.blender"
		set appBundleName to name of application file id "org.blenderfoundation.blender"
		set blenderPath to container of appname as text
		set blenderPath to blenderPath & appBundleName & ":Contents:MacOS:.blender:"
		set blenderScriptPath to blenderPath & "scripts:"
		set blenderPath to POSIX path of blenderPath
		set blenderScriptPath to POSIX path of blenderScriptPath
	end tell
	
	if verifyScriptFolder() is false then
		display dialog disasterMessage buttons {"OK"}
		return
	end if
	
	-- If we are lucky, the user will have the correct folder open when he runs the script
	tell application "Finder" to set the scriptPath to POSIX path of (folder of the front window as alias)
	if installScripts(scriptPath) is true then
		display dialog successMessage buttons {"OK"}
	else
		doDialogProbe()
	end if
on error
	doDialogProbe()
end try
