#!/bin/bash

# Verify scripts folder
if [ -e ~/.blender ] 
then
	if [ -e ~/.blender/scripts ]
	then
		echo "Install: Scripts folder ready."
	else
		if ( mkdir ~/.blender/scripts )
		then
			echo "Install: Scripts folder created."
		else
			echo "Install: Scripts folder could not be created!"
			exit 1
		fi
	fi
else
	if ( ( mkdir ~/.blender ) && ( mkdir ~/.blender/scripts ) )
	then
		echo "Install: All folders created."
	else
		echo "Install: Script folders could not be created!"
		exit 1
	fi
fi

# Now we can copy the files over
if ( [ -e Dts_Blender.py ] && [ -e DTSPython ] && [ -e DTSGUI ] )
then
	if ( cp -Rfv *.py DTSPython DTSGUI ~/.blender/scripts/ )
	then
		echo "Install: Scripts successfully copied."
	else
		echo "Install: Scripts could not be copied."
		exit 1
	fi
else
	echo "Install: Selected folder does not contain exporter scripts!"
	exit 1
fi
exit 0

