"""
@namespace epilog
@brief Output details and UI panel for an Epilog laser cutter.
"""


NAME = 'Epilog'

import  tempfile
import  subprocess

import  koko
from    koko.cam.panel import OutputPanel

class EpilogOutput(OutputPanel):
    """ @class EpilogOutput UI Panel for Epilog laser
    """

    """ @var extension File extension for Epilog laser file
    """
    extension = '.epi'

    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        self.construct('Epilog laser cutter', [
            ('2D power (%)', 'power', int, lambda f: 0 <= f <= 100),
            ('Speed (%)', 'speed', int, lambda f: 0 <= f <= 100),
            ('Rate','rate', int, lambda f: f > 0),
            ('xmin (mm)', 'xmin', float, lambda f: f >= 0),
            ('ymin (mm)', 'ymin', float, lambda f: f >= 0),
            ('autofocus', 'autofocus', bool)
        ], start=True)


    def run(self, paths):
        ''' Convert the path from the previous panel into an epilog
            laser file (with .epi suffix).
        '''
        values = self.get_values()
        if not values:  return False

        koko.FRAME.status = 'Converting to .epi file'

        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)
        job_name = koko.APP.filename if koko.APP.filename else 'untitled'

        self.file.write("%%-12345X@PJL JOB NAME=%s\r\nE@PJL ENTER LANGUAGE=PCL\r\n&y%iA&l0U&l0Z&u600D*p0X*p0Y*t600R*r0F&y50P&z50S*r6600T*r5100S*r1A*rC%%1BIN;XR%d;YP%d;ZS%d;\n" %
            (job_name, 1 if values['autofocus'] else 0,
             values['rate'], values['power'], values['speed']))

        scale = 600/25.4 # The laser's tick is 600 DPI
        xoffset = values['xmin']*scale
        yoffset = values['ymin']*scale
        xy = lambda x,y: (xoffset + scale*x, yoffset + scale*y)

        for path in paths:
            self.file.write("PU%d,%d;" % xy(*path.points[0][0:2]))
            for pt in path.points[1:]:
                self.file.write("PD%d,%d;" % xy(*pt[0:2]))
            self.file.write("\n")

        self.file.write("%%0B%%1BPUtE%%-12345X@PJL EOJ \r\n")
        self.file.flush()

        koko.FRAME.status = ''

        return True


    def send(self):
        subprocess.call('printer=laser; lpr -P$printer "%s"'
                        % self.file.name, shell=True)

################################################################################

from koko.cam.path_panels   import ContourPanel

INPUT = ContourPanel
PANEL = EpilogOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
    ('<None>', {}),

    ('Cardboard',
        {CadImgPanel:  [('res',5)],
         ContourPanel: [('diameter', 0.25)],
         EpilogOutput: [('power', 25), ('speed', 75),
                        ('rate', 500), ('xmin', 0), ('ymin', 0)]
        }
    )
]
