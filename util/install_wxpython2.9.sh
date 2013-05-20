echo "Using apt-get to install necessary packages"
yes | sudo apt-get install dpkg-dev build-essential swig python2.7-dev libwebkitgtk-dev libjpeg-dev libtiff-dev checkinstall ubuntu-restricted-extras freeglut3 freeglut3-dev libgtk2.0-dev  libsdl1.2-dev libgstreamer-plugins-base0.10-dev 

cd ~
echo "Downloading wxPython 2.9.4.0"
wget "http://downloads.sourceforge.net/project/wxpython/wxPython/2.9.4.0/wxPython-src-2.9.4.0.tar.bz2"

echo "Downloading wxPython 2.9.4.1 patch"
wget "http://downloads.sourceforge.net/project/wxpython/wxPython/2.9.4.0/wxPython-src-2.9.4.1.patch"
echo "Unzipping wxPython 2.9.4.0"
tar xvjf wxPython-src-2.9.4.0.tar.bz2

echo "Applying wxPython 2.9.4.1 patch"
patch -p 0 -d wxPython-src-2.9.4.0/ < wxPython-src-2.9.4.1.patch
cd wxPython-src-2.9.4.0/wxPython

echo "Compiling wxPython 2.9.4.1"
sudo python build-wxpython.py --build_dir=../bld --install
echo "Updating library cache"
sudo ldconfig

echo "Cleaning up"
cd ~
rm wxPython-src-2.9.4.0.tar.bz2
rm wxPython-src-2.9.4.1.patch
sudo rm -rf wxPython-src-2.9.4.0

echo "Testing:"
python -c "import wx; print 'wx version =', wx.version()"