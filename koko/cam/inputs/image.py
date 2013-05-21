import wx
import wx.lib.stattext

import os

import  koko
from    koko.cam.panel import FabPanel

class ImageInputPanel(FabPanel):
    """ @class ImageInputPanel  Input FabPanel for Image-based workflow
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

        text = wx.GridSizer(2, 2)

        ## @var file
        # UI label with filename
        self.file   = wx.StaticText(self, label='.png file')

        ## @var pix
        # UI label with size in pixels
        self.pix    = wx.StaticText(self)

        ## @var file
        # UI label with size in mms
        self.mms    = wx.StaticText(self)

        ## @var file
        # UI label with size in inches
        self.ins    = wx.StaticText(self)

        text.Add(self.file)
        text.Add(self.mms, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.pix, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.ins, flag=wx.ALIGN_LEFT|wx.EXPAND)

        sizer.Add(text, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        self.SetSizerAndFit(sizer)

    @property
    def input(self):
        """ @brief Property returning self.img
        """
        return self.img

    def update(self, input):
        """ @brief Updates the current image
            @details Reloads size values
            @param input Input image
            @returns Dictionary with 'threeD' value populated
        """

        ## @var img
        #   Image data structure
        self.img = input

        if self.img.filename:   file = os.path.split(self.img.filename)[1]
        else:                   file = 'Unknown .png file'
        self.file.SetLabel(file)

        self.pix.SetLabel('%i x %i pixels' % (self.img.width, self.img.height))

        if self.img.zmin is not None and self.img.zmax is not None:
            self.mms.SetLabel('%.2g x %.2g x %.2g mm' %
                (self.img.dx, self.img.dy, self.img.dz)
            )
            self.ins.SetLabel('%.2g x %.2g x %.2g"' %
                (self.img.dx/25.4,
                 self.img.dy/25.4,
                 self.img.dz/25.4)
            )
            threeD = bool(self.img.dz)
        else:
            self.mms.SetLabel('%.2g x %.2g mm' %
                (self.img.dx, self.img.dy)
            )
            self.ins.SetLabel('%.2g x %.2g"' %
                (self.img.dx/25.4,self.img.dy/25.4)
            )
            threeD = False

        return {'threeD': threeD}

    def run(self):
        """ @brief Returns a dictionary with the stored Image
        """
        return {'img': self.img}

################################################################################

from koko.fab.image         import Image
from koko.cam.path_panels   import PathPanel, ContourPanel

TYPE = Image

WORKFLOWS = {
    None:           (ImageInputPanel,),
    PathPanel:      (ImageInputPanel,),
    ContourPanel:   (ImageInputPanel,),
}

################################################################################
