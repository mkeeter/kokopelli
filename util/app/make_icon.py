#!/usr/bin/env python

import subprocess
import sys
import os
import shutil

def convert(args):
    subprocess.call('convert ' + args.replace('\n',' '), shell=True)

def progress(i, j, t=4):
    print '\r' + ' '*t + '[' + '|'*i + '-'*(j-i) + ']',
    sys.stdout.flush()

def gen(side, indent=4):
    black = '-size %{0}x{0} canvas:black'.format(side)
    blank = black + ' -alpha transparent'.format(side)

    progress(0,10,indent)
    convert(blank + '''
        -fill black -draw "roundrectangle {0},{0} {1},{1} {2},{2}"
        -channel RGBA -gaussian-blur 0x{3} shadow.png'''.format(
            side/20, side - side/20, side/40, side/50
        )
    )
    
    progress(1,10,indent)
    convert(black + """
        -fill white -draw "roundrectangle {0},{0} {1},{1} {2},{2}" mask.png
        """.format(
            side/20, side - side/20, side/40
        )
    )


    progress(2,10,indent)
    convert('''
        -size {0}x{0} radial-gradient: -crop {1}x{1}+{1}+0
        -level 19.5%,20% -negate gradient.png'''.format(
            side*4, side
        )
    )

    progress(3,10,indent)
    convert('''
        gradient.png mask.png -alpha Off -compose Multiply -composite
        gradient.png
    ''')

    progress(4,10,indent)
    convert('''
        gradient.png +clone -compose CopyOpacity -composite gradient.png
    ''')

    progress(5,10,indent)
    convert(black + '''
        -fill "rgb(240,240,240)" -font {3} -pointsize {0}
        -annotate +{1}+{2} "ko" text.png'''.format(
            side*0.7, side*0.15, side*0.75, 'Myriad-Pro-Bold-SemiCondensed'
        )
    )

    progress(6,10,indent)
    convert('''text.png
        -motion-blur 0x{0}
        -motion-blur 0x{0}+-90
        -motion-blur 0x{0}+-45
        -brightness-contrast 40
        text.png
        -alpha Off -compose CopyOpacity -composite text.png'''.format(
            side/140.
        )
    )

    progress(7,10,indent)
    convert(blank + """
        -fill "rgb(110,120,125)" -draw "roundrectangle {0},{0} {1},{1} {2},{2}"
        base.png""".format(
            side/20, side - side/20, side/40
        )
    )

    progress(8,10,indent)
    convert('''shadow.png base.png -composite text.png -composite icon.png''')


    progress(9,10,indent)
    convert('''
        gradient.png icon.png -compose blend
        -define compose:args=100,20 -composite icon.png
    ''')

    progress(10,10,indent)
    shutil.copy('icon.png', 'icon%i.png' % side)

    for img in ['icon', 'gradient', 'text', 'base', 'mask', 'shadow']:
        os.remove('%s.png' % img)

if len(sys.argv) < 2:
    sizes = (16, 32, 128, 256, 512)
    for i in sizes:
        print '%i:' % i
        gen(i)
        print ''
    subprocess.call(
        ['png2icns', 'ko.icns'] +
        ['icon%i.png' % i for i in sizes[::-1]]
    )
    subprocess.call(['rm'] + ['icon%i.png' % i for i in sizes])
    
else:
    gen(int(sys.argv[1]), indent=0)