NAME = '5-Axis Shopbot'

import  os
import  subprocess
import  tempfile
from    math import atan2, sqrt, degrees, pi

import numpy as np
import  wx

import  koko
from    koko.fab.path   import Path
from    koko.cam.panel  import FabPanel, OutputPanel

class Shopbot5Output(OutputPanel):
    """ @class Shopbot5Output
        @brief Output panel for a five-axis shopbot
    """

    ## @var extension
    # File extension for OpenSBP files
    extension = '.sbp'

    def __init__(self, parent):
        """ @brief Initializes the UI panel
            @param parent Parent panel
        """
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'Five-axis Shopbot', [
            ('Cut/jog speed (mm/s)', 'cut_speed',  float, lambda f: f > 0),
            ('Spindle speed (RPM)', 'spindle', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('Bit length (mm)', 'bit', float, lambda f: f > 0),
            ('Gauge length (mm)', 'gauge', float, lambda f: f > 0),
        ])

        self.construct()
        self.gauge.SetValue(str(6.787*25.4))



    def run(self, planes, axis_names):
        """ @brief Converts paths from the previous panel into a shopbot file
            @details Compensates for angles and adds safe traverses between paths
            @param planes List of list of paths.  Each interior list should be of paths on a single plane.
            @param axis_names List of names for each axis.
        """

        koko.FRAME.status = 'Converting to .sbp file'

        values = self.get_values()
        if not values:  return False
        offset = values['gauge'] + values['bit']
        jog = values['jog']
        scale = 1/25.4 # inch units

        ## @var file
        # NamedTemporaryFile containing the OpenSBP part file
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)

        def M3(x, y, z, scale=scale, offset=offset):
            self.file.write(
                "M3,%f,%f,%f\r\n" %
                (x*scale, y*scale, (z-offset)*scale)
            )


        self.file.write(
            "'This is a 5-axis Shopbot file created by kokopelli.\r\n"
        )
        self.file.write(
            "'The bit should be zeroed so that when pointing down,\r\n"
        )
        self.file.write(
            "'it touches the material at xmin, ymin, zmax.\r\n"
        )

        self.file.write("SA\r\n")   # plot absolute
        self.file.write("TR,%s,1,\r\n" % values['spindle']) # spindle speed
        self.file.write("SO,1,1\r\n") # set output number 1 to on
        self.file.write("pause,2,\r\n") # pause for spindle to spin up

        # Cut and jog speeds
        self.file.write("MS,%f,%f\r\n" %
            (values['cut_speed']*scale, values['cut_speed']*scale))

        # Make sure the head is neutrally positioned
        self.file.write("M5,,,,0,0\r\n")


        # Move up.
        M3(0, 0, jog+offset)

        for plane, axis_name in zip(planes, axis_names):

            self.file.write(
                "'Beginning of %s plane\r\n" % axis_name
            )

            v = plane[0][0][3:6]

            cut_offset = offset * plane[0][0][3:6]
            jog_offset = (offset+jog) * plane[0][0][3:6]

            # Take the first point of the path and subtract the endmill
            # length plus the jog distance.
            origin = plane[0][0][0:3] - jog_offset

            # Travel to the correct xy coordinates
            M3(origin[0], origin[1], jog+offset)

            # We can rotate the B axis in two possible directions,
            # which gives two different possible A rotations
            aM = atan2( v[1],  v[0])
            aP = atan2(-v[1], -v[0])

            # Pick whichever A rotation is smaller
            b = atan2(sqrt(v[0]**2 + v[1]**2), -v[2])
            if (abs(aM) < abs(aP)):
                a = aM
                b = -b
            else:
                a = aP

            self.file.write("M5,,,,%f,%f\r\n" % (degrees(a), degrees(b)))

            for path in plane:
                # Move to this path's start coordinates
                pos = path[0][0:3]
                start = pos - v*np.dot(pos - origin, v)
                M3(*start)

                for pt in path.points:
                    pos = pt[0:3] - cut_offset

                    depth = np.dot(pos - origin, v)
                    if depth > values['bit']:
                        pos -= v*(depth - values['bit'])

                    M3(*pos)

                # Back off to the safe cut plane
                stop = pos - v*np.dot(pos - origin, v)
                M3(*stop)

            # Pull up to above the top of the model
            M3(stop[0], stop[1], jog+offset)

            # Rotate the head back to neutral
            self.file.write("M5,,,,0,0\r\n")

        self.file.flush()

        koko.FRAME.status = ''
        return {'file': self.file}


################################################################################

from koko.cam.path_panels   import MultiPathPanel

INPUT = MultiPathPanel
PANEL = Shopbot5Output

################################################################################

from koko.cam.inputs.cad import CadASDFPanel

DEFAULTS = [
('<None>', {}),

('1/4" endmill, foam', {
    CadASDFPanel: [
        ('res', 10),
    ],
    MultiPathPanel: [
        ('res',         10),
        ('diameter',    6.35),
        ('stepover_r',  0.8),
        ('stepover_f',  0.5),
        ('step',        6),
        ('tool', 'Ball')
    ],
    Shopbot5Output: [
        ('cut_speed', 50),
        ('spindle', 10000),
        ('jog', 5),
        ('bit', 127)
    ]
}),

]
