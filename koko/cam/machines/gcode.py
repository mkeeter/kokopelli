NAME = 'G-code'

import  os
import  subprocess
import  tempfile

import  wx

import  koko
from    koko.fab.path   import Path

from    koko.cam.panel  import FabPanel, OutputPanel

class GCodeOutput(OutputPanel):

    extension = '.g'

    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'G-Code', [
            ('Cut speed (mm/s)', 'feed',  float, lambda f: f > 0),
            ('Plunge rate (mm/s)', 'plunge',  float, lambda f: f > 0),
            ('Spindle speed (RPM)', 'spindle', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('Cut type', 'type', ['Conventional', 'Climb']),
            ('Tool number', 'tool', int, lambda f: f > 0),
            ('Coolant', 'coolant', bool)
        ])

        self.construct()


    def run(self, paths):
        ''' Convert the path from the previous panel into a g-code file
        '''

        koko.FRAME.status = 'Converting to .g file'

        values = self.get_values()
        if not values:  return False

        # Reverse direction for climb cutting
        if values['type']:
            paths = Path.sort([p.reverse() for p in paths])


        # Check to see if all of the z values are the same.  If so,
        # we can use 2D cutting commands; if not, we'll need
        # to do full three-axis motion control
        zmin = paths[0].points[0][2]
        flat = True
        for p in paths:
            if not all(pt[2] == zmin for pt in p.points):
                flat = False

        # Create a temporary file to store the .sbp instructions
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)

        self.file.write("%%\n")     # tape start
        self.file.write("G17\n")    # XY plane
        self.file.write("G20\n")    # Inch mode
        self.file.write("G40\n")    # Cancel tool diameter compensation
        self.file.write("G49\n")    # Cancel tool length offset
        self.file.write("G54\n")    # Coordinate system 1
        self.file.write("G80\n")    # Cancel motion
        self.file.write("G90\n")    # Absolute programming
        self.file.write("G94\n")    # Feedrate is per minute

        scale = 1/25.4 # inch units

        self.file.write("T%dM06\n" % values['tool']) # Tool selection + change
        self.file.write("F%0.4f\n" % (60*scale*values['feed']))  # Feed rate
        self.file.write("S%0.4f\n" % values['spindle']) # spindle speed
        if values['coolant']:   self.file.write("M08\n") # coolant on

        # Move up before starting spindle
        self.file.write("G00Z%0.4f\n" % (scale*values['jog']))
        self.file.write("M03\n") # spindle on (clockwise)
        self.file.write("G04 P1\n") # pause one second to spin up spindle

        xy  = lambda x,y:   (scale*x, scale*y)
        xyz = lambda x,y,z: (scale*x, scale*y, scale*z)


        for p in paths:

            # Move to the start of this path at the jog height
            self.file.write("G00X%0.4fY%0.4fZ%0.4f\n" %
                            xyz(p.points[0][0], p.points[0][1], values['jog']))

            # Plunge to the desired depth
            self.file.write("G01Z%0.4f F%0.4f\n" %
                            (p.points[0][2]*scale, 60*scale*values['plunge']))

            # Restore XY feed rate
            self.file.write("F%0.4f\n" % (60*scale*values['feed']))

            # Cut each point in the segment
            for pt in p.points:
                if flat:    self.file.write("X%0.4fY%0.4f\n" % xy(*pt[0:2]))
                else:       self.file.write("X%0.4fY%0.4fZ%0.4f\n" % xyz(*pt))

            # Lift the bit up to the jog height at the end of the segment
            self.file.write("Z%0.4f\n" % (scale*values['jog']))

        self.file.write("M05\n") # spindle stop
        if values['coolant']:   self.file.write("M09\n") # coolant off
        self.file.write("M30\n") # program end and reset
        self.file.write("%%\n")  # tape end
        self.file.flush()

        koko.FRAME.status = ''
        return True


################################################################################

from koko.cam.path_panels   import PathPanel

INPUT = PathPanel
PANEL = GCodeOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),

('Flat cutout (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     1),
        ('overlap',     ''),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        1),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    GCodeOutput:
        [('feed', 20),
         ('plunge', 2.5),
         ('spindle', 10000),
         ('jog', 5),
         ('tool', 1),
         ('coolant', False)]
    }
),

('Wax rough cut (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     -1),
        ('overlap',     0.25),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        0.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    GCodeOutput:
        [('feed', 20),
         ('plunge', 2.5),
         ('spindle', 10000),
         ('jog', 5),
         ('tool', 1),
         ('coolant', False)]
    }
),

('Wax finish cut (1/8")', {
    PathPanel:
        [('diameter',    3.175),
         ('offsets',     -1),
         ('overlap',     0.5),
         ('threeD',      True),
         ('type',        'XZ + YZ'),
         ('step',        0.5),
         ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    GCodeOutput:
        [('feed', 20),
         ('plunge', 2.5),
         ('spindle', 10000),
         ('jog', 5),
         ('tool', 1),
         ('coolant', False)]
    }
)
]
