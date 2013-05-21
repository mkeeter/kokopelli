NAME = 'Shopbot'

import  os
import  subprocess
import  tempfile

import  wx

import  koko
from    koko.fab.path   import Path
from    koko.cam.panel  import FabPanel, OutputPanel

class ShopbotOutput(OutputPanel):
    """ @class ShopbotOutput
        @brief Panel for a three-axis Shopbot machine.
    """
    extension = '.sbp'

    def __init__(self, parent):
        """ @brief Panel constructor
            @param parent Parent UI panel
        """
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'Shopbot', [
            ('Cut speed (mm/s)', 'cut_speed',  float, lambda f: f > 0),
            ('Jog speed (mm/s)', 'jog_speed',  float, lambda f: f > 0),
            ('Spindle speed (RPM)', 'spindle', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('Cut type', 'type', ['Conventional', 'Climb']),
            ('File units', 'units', ['inches', 'mm'])
        ])

        self.construct()


    def run(self, paths):
        """ @brief Convert the path from the previous panel into a shopbot file.
            @param paths List of Paths
        """

        koko.FRAME.status = 'Converting to .sbp file'

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

        ## @var file
        # tempfile.NamedTemporaryFile to store OpenSBP commands
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)

        self.file.write("SA\r\n")   # plot absolute
        self.file.write("TR,%s,1,\r\n" % values['spindle']) # spindle speed
        self.file.write("SO,1,1\r\n") # set output number 1 to on
        self.file.write("pause,2,\r\n") # pause for spindle to spin up

        scale = 1 if values['units'] else 1/25.4 # mm vs inch units

        # Cut and jog speeds
        self.file.write("MS,%f,%f\r\n" %
            (values['cut_speed']*scale, values['cut_speed']*scale))
        self.file.write("JS,%f,%f\r\n" %
            (values['jog_speed']*scale, values['jog_speed']*scale))

        self.file.write("JZ,%f\r\n" % (values['jog']*scale)) # Move up

        xy  = lambda x,y:   (scale*x, scale*y)
        xyz = lambda x,y,z: (scale*x, scale*y, scale*z)


        for p in paths:

            # Move to the start of this path with the pen up
            self.file.write("J2,%f,%f\r\n" % xy(*p.points[0][0:2]))

            if flat:    self.file.write("MZ,%f\r\n" % (zmin*scale))
            else:       self.file.write("M3,%f,%f,%f\r\n" % xyz(*p.points[0]))

            # Cut each point in the segment
            for pt in p.points:
                if flat:    self.file.write("M2,%f,%f\r\n" % xy(*pt[0:2]))
                else:       self.file.write("M3,%f,%f,%f\r\n" % xyz(*pt))

            # Lift then pen up at the end of the segment
            self.file.write("MZ,%f\r\n" % (values['jog']*scale))

        self.file.flush()

        koko.FRAME.status = ''
        return True


################################################################################

from koko.cam.path_panels   import PathPanel

INPUT = PathPanel
PANEL = ShopbotOutput

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
        ('step',        1.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ShopbotOutput:
        [('cut_speed', 20),
         ('jog_speed', 5.0),
         ('spindle', 10000),
         ('jog', 5)]
    }
),

('Wax rough cut (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     -1),
        ('overlap',     0.25),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        1.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ShopbotOutput:
        [('cut_speed', 20),
         ('jog_speed', 5.0),
         ('spindle', 10000),
         ('jog', 5)]
    }
),

('Wax finish cut (1/8")', {
    PathPanel:
        [('diameter',    3.175),
         ('offsets',     -1),
         ('overlap',     0.5),
         ('threeD',      True),
         ('type',        'XZ + YZ'),
         ('step',        1.5),
         ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ShopbotOutput:
        [('cut_speed', 20),
         ('jog_speed', 5.0),
         ('spindle', 10000),
         ('jog', 5)]
    }
)
]
