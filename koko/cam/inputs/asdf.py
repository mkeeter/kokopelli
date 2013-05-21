import  wx
import  wx.lib.stattext

import  os

import  koko
from    koko.struct     import Struct
from    koko.cam.panel  import FabPanel
from    koko.dialogs    import RescaleDialog

from    koko.fab.image import Image

class ASDFInputPanel(FabPanel):
    """ @class ASDFInputPanel   UI Panel for ASDF loaded from a file
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Input',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        text = wx.GridSizer(2, 2)

        self.file   = wx.StaticText(self, label='.asdf file')
        self.pix    = wx.StaticText(self)
        self.mms    = wx.StaticText(self)
        self.ins    = wx.StaticText(self)

        text.Add(self.file)
        text.Add(self.mms, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.pix, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.ins, flag=wx.ALIGN_LEFT|wx.EXPAND)

        sizer.Add(text, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        resize = wx.Button(self, label='Rescale')
        sizer.Add(resize, flag=wx.CENTER|wx.ALL, border=5)
        resize.Bind(wx.EVT_BUTTON, self.resize)

        self.SetSizerAndFit(sizer)


    @property
    def input(self):
        """ @brief Property returning self.asdf """
        return self.asdf


    def resize(self, event=None):
        """ @brief Allows user to resize asdf
            @details Opens a RescaleDialog and rescales the stored asdf, then updates the UI, retriangulates the displayed mesh.
        """
        dlg = RescaleDialog('Rescale ASDF', self.asdf)
        if dlg.ShowModal() == wx.ID_OK:
            self.asdf.rescale(float(dlg.result))

            mesh = self.asdf.triangulate()
            mesh.source = Struct(type=ASDF, file=self.asdf.filename, depth=0)
            koko.GLCANVAS.load_mesh(mesh)

            self.parent.invalidate()
            self.parent.update()
        dlg.Destroy()


    def update(self, input):
        """ @brief Updates this panel
            @param input Input ASDF
            @returns Dictionary with dx, dy, and dz values
        """

        ## @var asdf
        #   ASDF data structure
        self.asdf = input

        if self.asdf.filename:   file = os.path.split(self.asdf.filename)[1]
        else:                    file = 'Unknown .asdf file'
        self.file.SetLabel(file)

        self.pix.SetLabel('%i x %i x %i voxels' % self.asdf.dimensions)

        self.mms.SetLabel(
            '%.1f x %.1f x %.1f mm' %
            (self.asdf.dx, self.asdf.dy, self.asdf.dz)
        )

        self.ins.SetLabel(
            '%.2f x %.2f x %.2f"' %
            (self.asdf.dx/25.4, self.asdf.dy/25.4, self.asdf.dz/25.4)
        )
        return {'dx': self.asdf.dx, 'dy': self.asdf.dy, 'dz': self.asdf.dz}


    def run(self):
        """ @brief Returns a dictionary with the stored asdf
        """
        return {'asdf': self.asdf}

################################################################################

class ASDFImagePanel(FabPanel):
    ''' @class ASDFImagePanel Panel to convert an ASDF data structure into a png.
    '''
    def __init__(self, parent):
        FabPanel.__init__(self, parent)
        self.construct('Lattice', [
            ('Resolution (pixels/mm)\n', 'res', float, lambda f: f > 0)])

        self.res.Bind(wx.EVT_TEXT, self.parent.update)
        self.img = Image(0,0)

    def update(self, dx, dy, dz):
        """ @brief Updates UI panel with dimensions
            @param dx   x dimension (mm)
            @param dy   y dimension (mm)
            @param dz   z dimension (mm)
        """
        try:
            scale = float(self.res.GetValue())
        except ValueError:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel(
                'Resolution (pixels/mm)\n%i x %i x %i' %
                (max(1, dx*scale),
                 max(1, dy*scale),
                 max(1, dz*scale))
            )
        return {'threeD': True}

    def run(self, asdf):
        """ @brief Renders an ASDF to an image
            @details Image is saved to self.img and appended to dictionary
            @param args Dictionary with key 'asdf'
            @returns Dictionary updated with key 'img'
        """
        koko.FRAME.status = 'Generating image'

        values = self.get_values()
        if not values:  return False

        # Render the asdf into an image
        self.img = asdf.render(resolution=values['res'])
        koko.FRAME.status = ''

        return {'img': self.img}

################################################################################

from koko.fab.asdf          import ASDF
from koko.cam.path_panels   import PathPanel, ContourPanel, MultiPathPanel

TYPE = ASDF
WORKFLOWS = {
    None:           (ASDFInputPanel,),
    PathPanel:      (ASDFInputPanel, ASDFImagePanel,),
    MultiPathPanel: (ASDFInputPanel,),
}

################################################################################
