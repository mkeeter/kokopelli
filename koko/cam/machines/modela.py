NAME = 'Roland Modela'

import  os
import  subprocess
import  tempfile

import  wx

import  koko
from    koko.cam.panel import FabPanel, OutputPanel

class ModelaOutput(OutputPanel):

    extension = '.rml'


    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'Modela', [
            ('Speed (mm/s)', 'speed', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('xmin (mm)', 'xmin', float, lambda f: f > 0),
            ('ymin (mm)', 'ymin', float, lambda f: f > 0)
            ])

        sizer = self.GetSizer()

        move_button = wx.Button(self, wx.ID_ANY, label='Move to xmin, ymin')
        move_button.Bind(wx.EVT_BUTTON, self.move)
        sizer.Add(move_button, flag=wx.CENTER|wx.TOP, border=5)

        # Add generate + save buttons
        self.construct(start=True)


    def run(self, paths):
        ''' Convert the path from the previous panel into a roland
            modela file (with .rml suffix)
        '''

        koko.FRAME.status = 'Converting to .rml file'

        values = self.get_values()
        if not values:  return False

        # Check to see if all of the z values are the same.  If so,
        # we can use pen up / pen down commands; if not, we'll need
        # to do full three-axis motion control
        zmin = paths[0].points[0][2]
        flat = True
        for p in paths:
            if not all(pt[2] == zmin for pt in p.points):
                flat = False


        scale = 40.
        xoffset = values['xmin']*scale
        yoffset = values['ymin']*scale

        xy  = lambda x,y:   (xoffset + scale*x, yoffset + scale*y)
        xyz = lambda x,y,z: (xoffset + scale*x, yoffset + scale*y, scale*z)

        # Create a temporary file to store the .rml stuff
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)
        self.file.write("PA;PA;")   # plot absolute

        # Set speeds
        self.file.write("VS%.1f;!VZ%.1f" % (values['speed'], values['speed']))

        # Set z1 to the cut depth (only relevant for a 2D cut)
        # and z2 to the jog height (used in both 2D and 3D)
        self.file.write("!PZ%d,%d;" % (zmin*scale, values['jog']*scale))

        self.file.write("!MC1;\n")  # turn the motor on

        for p in paths:
            # Move to the start of this path with the pen up
            self.file.write("PU%d,%d;" % xy(*p.points[0][0:2]))

            # Cut each point in the segment
            for pt in p.points:
                if flat:    self.file.write("PD%d,%d;"   % (xy(*pt[0:2])))
                else:       self.file.write("Z%d,%d,%d;" % (xyz(*pt)))

            # Lift then pen up at the end of the segment
            self.file.write("PU%d,%d;" % xy(*p.points[-1][0:2]))

        self.file.write("!MC0;"*1000) # Modela buffering bug workaround
        self.file.write("\nH;\n")
        self.file.flush()

        koko.FRAME.status = ''
        return True


    def send(self, file=None):
        if file is None:    file = self.file.name
        subprocess.call('port = /dev/ttyUSB0;' +
                        'stty -F $port raw -echo crtscts;' +
                        'cat "%s" > $port' % self.file.name,
                        shell=True)


    def move(self, event=None):
        values = self.get_values('xmin','ymin')
        if not values:  return False

        x, y = values['xmin'], values['ymin']
        with open('rml_move.rml') as f:
            f.write("PA;PA;!VZ10;!PZ0,100;PU %d %d;PD %d %d;!MC0;" %
                    (x,y,x,y))
        self.send('rml_move.rml')
        os.remove('rml_move.rml')

################################################################################

from koko.cam.path_panels   import PathPanel

INPUT = PathPanel
PANEL = ModelaOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),

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
    ModelaOutput:
        [('speed', 29),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
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
    ModelaOutput:
        [('speed', 20),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }
),

('Mill traces (1/64")', {
    PathPanel:
        [('diameter',    0.4),
         ('offsets',     4),
         ('overlap',     0.75),
         ('depth',      -0.1),
         ('threeD',      False),
         ('top',         ''),
         ('bottom',      ''),
         ],
    CadImgPanel:
        [('res', 15)],
    ModelaOutput:
        [('speed', 4),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }),

('Mill traces (0.010")', {
    PathPanel:
       [('diameter',    0.254),
        ('offsets',     4),
        ('overlap',     0.75),
        ('depth',      -0.1),
        ('threeD',      False),
        ('top',         ''),
        ('bottom',      '')
         ],
    CadImgPanel:
        [('res', 15)],
    ModelaOutput:
        [('speed', 2),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }),

('Cut out board (1/32")',
    {PathPanel:
       [('diameter',    0.79),
        ('offsets',     1),
        ('overlap',     ''),
        ('threeD',      True),
        ('top',         -0.5),
        ('bottom',      -1.7),
        ('step',        0.5),
        ('type',        'XY')
         ],
    CadImgPanel:
        [('res', 15)],
    ModelaOutput:
        [('speed', 4),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }
)
]
