NAME = 'Universal laser cutter'

import  tempfile
import  subprocess

import  koko
from    koko.cam.panel import OutputPanel

class UniversalOutput(OutputPanel):

    extension = '.uni'

    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        self.construct('Universal laser cutter', [
            ('2D power (%)', 'power', int, lambda f: 0 <= f <= 100),
            ('Speed (%)', 'speed', int, lambda f: 0 <= f <= 100),
            ('Rate','rate', int, lambda f: f > 0),
            ('xmin (mm)', 'xmin', float, lambda f: f >= 0),
            ('ymin (mm)', 'ymin', float, lambda f: f >= 0)
        ], start=True)


    def run(self, paths):
        ''' Convert the path from the previous panel into an epilog
            laser file (with .epi suffix).
        '''
        values = self.get_values()
        if not values:  return False

        koko.FRAME.status = 'Converting to .uni file'

        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)
        job_name = koko.APP.filename if koko.APP.filename else 'untitled'

        self.file.write("Z") # initialize
        self.file.write("t%s~;" % job_name) # job name
        self.file.write("IN;DF;PS0;DT~") # initialize
        self.file.write("s%c" % (values['rate']/10)) # ppi

        speed_hi = chr((648*values['speed']) / 256)
        speed_lo = chr((648*values['speed']) % 256)
        self.file.write("v%c%c" % (speed_hi, speed_lo))

        power_hi = chr((320*values['power']) / 256)
        power_lo = chr((320*values['power']) % 256)
        self.file.write("p%c%c" % (power_hi, power_lo))

        self.file.write("a%c" % 2)

        scale = 1000/25.4 # The laser's tick is 600 DPI
        xoffset = values['xmin']*scale
        yoffset = values['ymin']*scale
        xy = lambda x,y: (xoffset + scale*x, yoffset + scale*y)

        for path in paths:
            self.file.write("PU;PA%d,%d;PD;" % xy(*path.points[0][0:2]))
            for pt in path.points[1:]:
                self.file.write("PA%d,%d;" % xy(*pt[0:2]))
            self.file.write("\n")

        self.file.write("e") # end of file
        self.file.flush()

        koko.FRAME.status = ''

        return True


    def send(self):
        subprocess.call('printer=laser; lpr -P$printer "%s"'
                        % self.file.name, shell=True)

################################################################################

from koko.cam.path_panels import ContourPanel

INPUT = ContourPanel
PANEL = UniversalOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),
('Cardboard',
    {CadImgPanel:  [('res',5)],
     ContourPanel: [('diameter', 0.25)],
     UniversalOutput: [('power', 25), ('speed', 75),
                       ('rate', 500), ('xmin', 0), ('ymin', 0)]
    }
)
]
