#!/bin/sh
export PYTHONPATH=`python util/getPath.py unix`:`pwd`
echo $PYTHONPATH
blender -windowed $1 $2 $3
