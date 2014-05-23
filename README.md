About
=====
`kokopelli` is an open-source tool for computer-aided design and manufacturing (CAD/CAM).

It uses Python as a hardware description language for solid models.  A set of core libraries define common shapes and transforms, but users are free to extend their designs with their own definitions.

![CAD](http://i.imgur.com/L1RQUxA.png)

The CAM tools enable path planning for two, three, and five-axis machines.  At the moment, paths can be exported to Universal and Epilog laser cutters, the Roland Modela mini-mill, three and five-axis Shopbot machines, and plain G-code.  A modular workflow system makes adding new machines easy.

![CAM](http://i.imgur.com/sb0uQq5.png)

In addition, models can be saved as `.svg` and water-tight `.stl` files.

Warning
=======
`kokopelli` stores designs as Python scripts and executes them.  This means that you can do cool things like using `numpy` to process arrays, load and process images with `PIL`, or even scrape web data and use it to inform designs.

However, it also means that bad actors can write malicious scripts.

As such, **do not open a .ko file from an untrusted source** without first examining it in a text editor to confirm that it is not malicious.

Download
========
`kokopelli` has been tested on Mac OS 10.6+ and Ubuntu 12.04 LTS.  
A Mac application is available [here](http://mattkeeter.com/projects/kokopelli/kokopelli.tar.gz).  
To build from source, check out the instructions on the [wiki](https://github.com/mkeeter/kokopelli/wiki/Installing).

Background
==========
`kokopelli` grew out of the MIT course ["How to Make Something that Makes (Almost) Anything"](http://fab.cba.mit.edu/classes/S62.12/index.html).
In that course, I worked on [fast geometry solvers](http://fab.cba.mit.edu/classes/S62.12/people/keeter.matt/solver/index.html) and developed a [fairly basic UI](http://fab.cba.mit.edu/classes/S62.12/people/keeter.matt/gui/index.html).  My work expanded on the [fab modules](http://kokompe.cba.mit.edu/) project, which allows [fab lab](http://fab.cba.mit.edu/about/faq/) users to make physical artifacts on a variety of machines.

This work grew into my [Master's thesis](http://cba.mit.edu/docs/theses/13.05.Keeter.pdf) at the MIT [Center for Bits and Atoms](http://cba.mit.edu).  This thesis focused on volumetric CAD/CAM workflows.  Now that it is complete, I'm releasing this tool for others to use and develop.  It has already been used by folks in [How to Make (Almost) Anything](http://fab.cba.mit.edu/classes/863.12/) and [Fab Academy](http://www.fabacademy.org/), but I'm excited to offer it to a larger community.

Copyright
=========
(c) 2012-2013 Massachusetts Institute of Technology  
(c) 2013 Matt Keeter

