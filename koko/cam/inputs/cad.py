import wx
import wx.lib.stattext

import  koko

from    koko.struct     import Struct
from    koko.dialogs    import error
from    koko.fab.image  import Image
from    koko.c.region   import Region

from    koko.cam.panel  import FabPanel

################################################################################

class CadInputPanel(FabPanel):
    """ @class CadInputPanel  Input FabPanel for script-based workflow
    """

    def __init__(self, parent):
        """ @brief Initializes the panel
            @param Parent UI panel
        """
        FabPanel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Input',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)
        self.label = wx.StaticText(self, label='.cad file')
        sizer.Add(self.label,
                  flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        self.SetSizerAndFit(sizer)

    @property
    def input(self):
        """ @brief Property returning self.cad """
        return self.cad

    def update(self, input):
        """ @brief Updates the current cad structure
            @param input Input cad structure
            @returns Dictionary with 'cad' populated
        """

        ## @var cad
        # FabVars data structure
        self.cad = input

        if self.cad.dx: x = '%g' % (self.cad.dx*self.cad.mm_per_unit)
        else:           x = '?'
        if self.cad.dy: y = '%g' % (self.cad.dy*self.cad.mm_per_unit)
        else:           y = '?'
        if self.cad.dz: z = '%g' % (self.cad.dz*self.cad.mm_per_unit)
        else:           z = 0

        self.label.SetLabel('.cad file     (%s x %s x %s mm)' %  (x, y, z))
        return {'cad': self.cad}

    def run(self):
        """ @brief Returns a dictionary with the stored cad structure
        """
        koko.FRAME.status = 'Checking cad expression'
        if not bool(self.cad.function.ptr):
            wx.CallAfter(self.label.SetBackgroundColour, '#853535')
            wx.CallAfter(self.label.SetForegroundColour, '#ffffff')
            koko.FRAME.status = 'Error: Failed to parse math expression!'
            return False
        if self.cad.dx is None or self.cad.dy is None:
            wx.CallAfter(self.label.SetBackgroundColour, '#853535')
            wx.CallAfter(self.label.SetForegroundColour, '#ffffff')
            koko.FRAME.status = 'Error: invalid XY bounds on expression'
            return False
        return {'cad': self.cad}

################################################################################

class CadImgPanel(FabPanel):
    """ @class CadImgPanel  Panel to convert cad structure to image
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)
        self.construct('Lattice', [
            ('Resolution (pixels/mm)\n', 'res', float, lambda f: f > 0)])

        self.res.Bind(wx.EVT_TEXT, self.parent.update)
        self.img = Image(0,0)


    def update(self, cad):
        """ @brief Updates displayed dimensions
            @param cad cad data structure
            @returns Dictionary with 'threeD' defined
        """
        try:
            scale = float(self.res.GetValue()) * cad.mm_per_unit
        except ValueError:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n%i x %i x %i' %
                                (max(1, cad.dx*scale if cad.dx else 1),
                                 max(1, cad.dy*scale if cad.dy else 1),
                                 max(1, cad.dz*scale if cad.dz else 1)))
        return {'threeD': cad.dz}


    def run(self, cad):
        """ @brief Generates image
            @param cad Input cad data structure
            @returns Dictionary with 'img' defined
        """
        koko.FRAME.status = 'Generating image'

        values = self.get_values()
        if not values:  return False

        # Render the expression into an image
        expr = cad.function

        zmin = expr.zmin if expr.zmin else 0
        zmax = expr.zmax if expr.zmax else 0
        dz   = zmax - zmin

        border = cad.border
        region = Region( (expr.xmin-border*expr.dx,
                          expr.ymin-border*expr.dy,
                          zmin-border*dz),
                         (expr.xmax+border*expr.dx,
                          expr.ymax+border*expr.dy,
                          zmax+border*dz),
                          values['res']*cad.mm_per_unit)

        self.img = expr.render(region=region,
                               mm_per_unit=cad.mm_per_unit)
        koko.FRAME.status = ''

        return {'img': self.img}


class CadASDFPanel(FabPanel):
    """ @class CadASDFPanel  Panel to convert cad structure to ASDF
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)
        self.construct('ASDF', [
            ('Resolution (voxels/mm)\n', 'res', float, lambda f: f > 0)])

        self.res.Bind(wx.EVT_TEXT, self.parent.update)


    def update(self, cad):
        """ @brief Updates size labels
            @param cad Input cad structure
            @returns Dictionary with dx, dy, dz values
        """
        try:
            scale = float(self.res.GetValue()) * cad.mm_per_unit
        except ValueError:
            self.labels[0].SetLabel('Resolution (voxels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel('Resolution (voxels/mm)\n%i x %i x %i' %
                                (max(1, cad.dx*scale if cad.dx else 1),
                                 max(1, cad.dy*scale if cad.dy else 1),
                                 max(1, cad.dz*scale if cad.dz else 1)))

        # Return ASDF structure with correct dimensions
        return {
            'dx': cad.dx*cad.mm_per_unit,
            'dy': cad.dy*cad.mm_per_unit,
            'dz': cad.dz*cad.mm_per_unit,
        }


    def run(self, cad):
        """ @brief Generates ASDF from cad structure
            @param cad Input cad data structure
            @returns Dictionary with 'asdf' defined
        """
        koko.FRAME.status = 'Generating ASDF'

        values = self.get_values()
        if not values:  return False

        # Render the expression into an image
        expr = cad.function

        zmin = expr.zmin if expr.zmin else 0
        zmax = expr.zmax if expr.zmax else 0
        dz   = zmax - zmin

        border = cad.border
        region = Region( (expr.xmin-border*expr.dx,
                          expr.ymin-border*expr.dy,
                          zmin-border*dz),
                         (expr.xmax+border*expr.dx,
                          expr.ymax+border*expr.dy,
                          zmax+border*dz),
                          values['res']*cad.mm_per_unit)

        self.asdf = expr.asdf(
            region=region, mm_per_unit=cad.mm_per_unit
        )

        koko.FRAME.status = ''

        return {'asdf': self.asdf}

################################################################################

from koko.fab.fabvars       import FabVars
from koko.cam.path_panels   import PathPanel, ContourPanel, MultiPathPanel

TYPE = FabVars
WORKFLOWS = {
    None:           (CadInputPanel,),
    PathPanel:      (CadInputPanel, CadImgPanel),
    ContourPanel:   (CadInputPanel, CadImgPanel),
    MultiPathPanel: (CadInputPanel, CadASDFPanel),
}

################################################################################
