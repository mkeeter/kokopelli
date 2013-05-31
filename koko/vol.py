import os

import wx
import wx.lib.stattext

import  koko
from    koko.fab.asdf   import ASDF
from    koko.c.region   import Region
from    koko.c.libfab   import libfab
from    koko.themes     import DARK_THEME
import  koko.dialogs as dialogs

class ImportPanel(wx.Panel):
    def __init__(self, app, parent):
        wx.Panel.__init__(self,parent)

        vs = wx.BoxSizer(wx.VERTICAL)

        title = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Import .vol'
        )
        title.header = True
        vs.Add(title, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        self.file_text = wx.StaticText(self, wx.ID_ANY, '')

        vs.Add(self.file_text, flag=wx.TOP|wx.LEFT, border=10)

        gs = wx.GridSizer(6, 2)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Parameters'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        for t in [('X samples','ni'),('Y samples','nj'),
                ('Z samples','nk'), ('Density threshold','density'),
                ('Voxel size (mm)','mm')]:
            gs.Add(
                wx.StaticText(self, wx.ID_ANY, t[0]),
                flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT, border=10)
            setattr(self, t[1], wx.TextCtrl(self, style=wx.NO_BORDER))
            gs.Add(getattr(self, t[1]), flag=wx.TOP|wx.LEFT, border=10)

        gs.Add(wx.StaticText(self, label='Close boundary'),
            flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT, border=10)
        self.boundary = wx.CheckBox(self)
        gs.Add(self.boundary, flag=wx.TOP|wx.LEFT, border=10)
        vs.Add(gs)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Target region'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)
        hs = wx.BoxSizer()
        hs.Add(wx.StaticText(self, label='Entire region'), proportion=1)
        entire = wx.CheckBox(self)
        hs.Add(entire, proportion=1)
        entire.Bind(wx.EVT_CHECKBOX, self.change_region)
        vs.Add(hs, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Begin import'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        self.run_button = wx.Button(self, label='Import')
        self.run_button.Bind(wx.EVT_BUTTON, self.run)

        self.info = wx.StaticText(self, label='')

        vs.Add(self.run_button, flag=wx.TOP|wx.LEFT, border=10)
        vs.Add(self.info, flag=wx.TOP|wx.LEFT|wx.BOTTOM, border=10)

        self.SetSizerAndFit(vs)

    def set_target(self, directory, filename):
        self.directory = directory
        self.filename = os.path.join(directory, filename)
        self.file_text.SetLabel("File: %s" % filename)

    def change_region(self, event):
        print "CHECKED"

    def clear(self):
        self.Hide()
        koko.FRAME.Layout()
        koko.FRAME.Refresh()

    def check(self):
        try:
            ni, nj, nk = map(
                lambda d: int(d.GetValue()),
                [self.ni, self.nj, self.nk]
            )
        except ValueError:
            dialogs.error('Invalid size!')
            return

        size = os.path.getsize(self.filename)
        if size != ni*nj*nk*4:
            dialogs.error('File size does not match provided dimensions!')
            return

        try:
            density = float(self.density.GetValue())
        except ValueError:
            dialogs.error('Invalid density value (must be a floating-point number)')
            return

        try:
           mm = float(self.mm.GetValue())
        except ValueError:
            dialogs.error('Invalid voxel size (must be a floating-point number)')
            return

        close_boundary = self.boundary.IsChecked()

        return {'ni': ni, 'nj': nj, 'nk': nk,
                'density': density, 'mm': mm,
                'close_boundary':close_boundary}


    def run(self, event):
        params = self.check()
        for p in params:    exec('{0} = params["{0}"]'.format(p))

        df = dialogs.save_as(self.directory, extension='.asdf')
        if df[1] == '': return

        full = Region(
            (0, 0, 0),
            (ni-1, nj-1, nk-1),
            1, dummy=True
        )
        libfab.build_arrays(
            full, 0, 0, 0, ni*mm, nj*mm, nk*mm
        )
        full.free_arrays = True


        self.info.SetLabel('Importing ASDF')
        wx.Yield()
        asdf = ASDF(
            libfab.import_vol_region(
                self.filename, ni, nj, nk, full, 0, density,
                True, close_boundary
            )
        )

        self.info.SetLabel('Saving ASDF')
        wx.Yield()
        asdf.save(os.path.join(*df))

        self.info.SetLabel('')
        koko.APP.directory, koko.APP.filename = df
        koko.APP.load()
