"""
UI Panel for importing .vol CT data
"""

import os
from   math import log, ceil

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

        preview = wx.Button(self, label='Full preview')
        preview.Bind(wx.EVT_BUTTON, self.preview)
        vs.Add(preview, flag=wx.TOP|wx.LEFT|wx.ALIGN_CENTER, border=10)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Target region'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        hs = wx.BoxSizer()
        hs.Add(wx.StaticText(self, label='Entire region', style=wx.ALIGN_RIGHT),
                flag = wx.RIGHT, border=20, proportion=1)
        self.entire = wx.CheckBox(self)
        hs.Add(self.entire, proportion=1)
        self.entire.Bind(wx.EVT_CHECKBOX, self.edit_region)
        vs.Add(hs, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        bpanel = wx.Panel(self)
        bounds = wx.FlexGridSizer(3, 4)
        bounds.AddGrowableCol(0, 1)
        bounds.AddGrowableCol(2, 1)
        for i in ['imin','imax','jmin','jmax','kmin','kmax']:
            bounds.Add(wx.StaticText(bpanel, label=i), flag=wx.TOP|wx.LEFT, border=10, proportion=1)
            setattr(self, i, wx.TextCtrl(bpanel, style=wx.NO_BORDER))
            bounds.Add(getattr(self, i), flag=wx.TOP|wx.LEFT, border=10, proportion=1)
            getattr(self, i).Bind(wx.EVT_TEXT, lambda e: koko.GLCANVAS.Refresh())
        bpanel.SetSizerAndFit(bounds)
        self.show_bounds = lambda b: bpanel.Show(b)
        vs.Add(bpanel)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Begin import'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        run_button = wx.Button(self, label='Import')
        run_button.Bind(wx.EVT_BUTTON, self.run)


        vs.Add(run_button, flag=wx.TOP|wx.LEFT|wx.ALIGN_CENTER, border=10)

        self.SetSizerAndFit(vs)

    def set_target(self, directory, filename):
        self.directory = directory
        self.filename = os.path.join(directory, filename)
        self.file_text.SetLabel("File: %s" % filename)
        self.entire.SetValue(True)
        self.edit_region()

    def edit_region(self, event=None):
        if self.entire.IsChecked():
            self.show_bounds(False)
        else:
            self.show_bounds(True)
        koko.FRAME.Layout()
        koko.GLCANVAS.Refresh()


    def clear(self):
        self.Hide()
        koko.FRAME.Layout()
        koko.FRAME.Refresh()

    def get_params(self, show_error=True):
        try:
            ni, nj, nk = map(
                lambda d: int(d.GetValue()),
                [self.ni, self.nj, self.nk]
            )
        except ValueError:
            if show_error:   dialogs.error('Invalid size!')
            return

        size = os.path.getsize(self.filename)
        if size != ni*nj*nk*4:
            if show_error:
                dialogs.error('File size does not match provided dimensions!')
            return

        try:
            density = float(self.density.GetValue())
        except ValueError:
            if show_error:
                dialogs.error('Invalid density value (must be a floating-point number)')
            return

        try:
           mm = float(self.mm.GetValue())
        except ValueError:
            if show_error:
                dialogs.error('Invalid voxel size (must be a floating-point number)')
            return

        close_boundary = self.boundary.IsChecked()
        params = {'ni': ni, 'nj': nj, 'nk': nk,
                'density': density, 'mm': mm,
                'close_boundary':close_boundary}

        if self.entire.IsChecked():
            params.update({
                'imin': 0, 'imax': ni-1,
                'jmin': 0, 'jmax': nj-1,
                'kmin': 0, 'kmax': nk-1
            })
        else:
            for c in ['imin','jmin','kmin','imax','jmax','kmax']:
                try:
                    params[c] = (
                        int(getattr(self,c).GetValue()) -
                        (1 if 'max' in c else 0)
                    )
                except ValueError:
                    if show_error:
                        dialogs.error('Invalid parameter for %s' % c)
                    return
        return params

    def preview(self, event):
        """ @brief Load a downsampled version of the ASDF
        """
        params = self.get_params()
        if params is None:  return
        for p in params:    exec('{0} = params["{0}"]'.format(p))

        voxels = (imax - imin) * (jmax - jmin) * (kmax - kmin)

        shift = int(ceil(log(voxels / 128.**3, 8)))
        full = Region(
            (0, 0, 0), (ni-1, nj-1, nk-1), 1, dummy=True
        )
        libfab.build_arrays(
            full, 0, 0, 0, ni*mm, nj*mm, nk*mm
        )
        full.free_arrays = True

        asdf = ASDF(
            libfab.import_vol_region(
                self.filename, ni, nj, nk, full, shift, density,
                True, close_boundary
            )
        )
        mesh = asdf.triangulate()

        koko.FRAME.get_menu('View', '3D').Check(True)
        koko.APP.render_mode('3D')
        koko.GLCANVAS.load_mesh(mesh)


    def bounding_cube(self):
        params = self.get_params(show_error=False)
        if params is None or not self.IsShown() or self.entire.IsChecked():
            return

        for p in params:    exec('{0} = params["{0}"]'.format(p))
        return (imin*mm, imax*mm, jmin*mm, jmax*mm, kmin*mm, kmax*mm)

    def run(self, event):
        params = self.get_params()
        for p in params:    exec('{0} = params["{0}"]'.format(p))

        full = Region(
            (imin, jmin, kmin),
            (imax, jmax, kmax),
            1, dummy=True
        )
        libfab.build_arrays(
            full, imin*mm, jmin*mm, kmin*mm, (imax+1)*mm, (jmax+1)*mm, (kmax+1)*mm
        )
        # Position the lower corner based on imin, jmin, kmin
        full.imin = imin
        full.jmin = jmin
        full.kmin = kmin
        full.free_arrays = True

        koko.FRAME._status.SetLabel('Importing ASDF')
        wx.Yield()
        koko.FRAME.Refresh()
        wx.Yield()

        asdf = ASDF(
            libfab.import_vol_region(
                self.filename, ni, nj, nk, full, 0, density,
                True, close_boundary
            )
        )

        koko.FRAME._status.SetLabel('Triangulating')
        koko.FRAME.Refresh()
        wx.Yield()

        mesh = asdf.triangulate()
        koko.FRAME.get_menu('View', '3D').Check(True)
        koko.APP.render_mode('3D')
        koko.GLCANVAS.load_mesh(mesh)
        koko.FAB.set_input(asdf)

        koko.FRAME.status = ''
        koko.APP.mode = 'asdf'
        koko.APP.filename = None
        koko.APP.savepoint(False)
