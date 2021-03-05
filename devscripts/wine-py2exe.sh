#!/bin/bash

# Run with as parameter a setup.py that works in the current directory
# e.g. no os.chdir()

# Wine >=6.3 required: https://bugs.winehq.org/show_bug.cgi?id=3591

set -e

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

if [ ! -d wine-py2exe ]; then

    mkdir wine-py2exe
    cd wine-py2exe
    export WINEPREFIX=`pwd`

    echo "Downloading Python 3.8.8"
    aria2c "https://www.python.org/ftp/python/3.8.8/python-3.8.8.exe"

    # this will need to be upgraded when switching to a newer version of python
    winetricks win7

    # http://appdb.winehq.org/objectManager.php?sClass=version&iId=21957
    echo "Installing Python 3.8.8"
    wine python-3.8.8.exe /quiet InstallAllUsers=1 'DefaultAllUsersTargetDir=C:\\python38'
    
    echo "Installing py2exe"
    wine 'C:\\python38\\python.exe' -m pip install wheel
    wine 'C:\\python38\\python.exe' -m pip install py2exe
    #wine 'C:\\python38\\python.exe' -m pip install playwright===1.9.0
    #wine 'C:\\python38\\python.exe' -m playwright install
    
    #echo "Follow Microsoft Visual C++ 2008 Redistributable Package setup on screen"
    #bash winetricks vcrun2008

    rm python-3.8.8.exe

    cd -
    
else

    export WINEPREFIX="$( cd wine-py2exe && pwd )"

fi

mkdir -p build/bdist.win32/winexe/bundle-3.8/
# cp "$WINEPREFIX/drive_c/python38/python38.dll" build/bdist.win32/winexe/bundle-3.8/
echo "Making the exe file"
# cannot be piped into a file: https://forum.winehq.org/viewtopic.php?t=33992
wine 'C:\\python38\\python.exe' "$1" py2exe | tee py2exe.log
