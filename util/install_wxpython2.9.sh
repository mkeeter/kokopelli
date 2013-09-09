#!/bin/sh

set -e

echo "Using apt-get to install necessary packages"
yes | sudo apt-get install libgtk2.0-dev freeglut3-dev libsdl1.2-dev libgstreamer-plugins-base0.10-dev libwebkitgtk-dev

cd ~
echo "Downloading wxPython 2.9.5.0"
wget "http://downloads.sourceforge.net/wxpython/wxPython-src-2.9.5.0.tar.bz2"
tar xvjf wxPython-src-2.9.5.0.tar.bz2

cd wxPython-src-2.9.5.0
echo "Patching Python error in build-wxwidgets.py"
sed -i 's/extra=None/extra=\[\]/' build/tools/build-wxwidgets.py

cd wxPython
echo "Compiling wxPython 2.9.5.0"
sudo python build-wxpython.py --build_dir=../bld --install
echo "Updating library cache"
sudo ldconfig

echo "Cleaning up"
cd ~
rm wxPython-src-2.9.5.0.tar.bz2
sudo rm -rf wxPython-src-2.9.5.0

echo "Testing:"
python -c "import wx; print 'wx version =', wx.version()"
