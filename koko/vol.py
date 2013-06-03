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
from    koko.glcanvas   import DragHandler
from    koko.themes     import DARK_THEME
import  koko.dialogs as dialogs

class ImportPanel(wx.Panel):
    def __init__(self, app, parent):
        wx.Panel.__init__(self,parent)

        vs = wx.BoxSizer(wx.VERTICAL)

        title = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='.vol to ASDF import'
        )
        title.header = True
        vs.Add(title, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        self.file_text = wx.StaticText(self, wx.ID_ANY, '')
        hs.Add(self.file_text, flag=wx.EXPAND, proportion=1)

        preview = wx.Button(self, label='Preview')
        preview.Bind(wx.EVT_BUTTON, self.preview)
        hs.Add(preview, flag=wx.LEFT|wx.ALIGN_CENTER, border=10, proportion=1)
        vs.Add(hs, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        gs = wx.GridSizer(3, 2)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='File parameters'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        for t in [('X samples','ni'),('Y samples','nj'),
                ('Z samples','nk')]:
            gs.Add(
                wx.StaticText(self, wx.ID_ANY, t[0]),
                flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT|wx.EXPAND, border=10)
            txt = wx.TextCtrl(self, style=wx.NO_BORDER)
            setattr(self, t[1], txt)
            gs.Add(txt, flag=wx.TOP|wx.LEFT, border=10)
            txt.Bind(wx.EVT_TEXT, self.update_size)

        vs.Add(gs, flag=wx.EXPAND)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Import settings'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        gs = wx.GridSizer(3, 2)
        for t in [('Density threshold','density'),
                ('Voxel size (mm)','mm')]:
            gs.Add(
                wx.StaticText(self, wx.ID_ANY, t[0]),
                flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT|wx.EXPAND, border=10)
            setattr(self, t[1], wx.TextCtrl(self, style=wx.NO_BORDER))
            gs.Add(getattr(self, t[1]), flag=wx.TOP|wx.LEFT, border=10)
            if 'samples' in t[0]:
                getattr(self, t[1]).Bind(wx.EVT_TEXT, self.update_size)
        gs.Add(wx.StaticText(self, label='Close boundary'),
            flag=wx.TOP|wx.LEFT, border=10)
        self.boundary = wx.CheckBox(self)
        self.boundary.SetValue(True)
        gs.Add(self.boundary, flag=wx.TOP|wx.LEFT, border=10)
        vs.Add(gs, flag=wx.EXPAND)


        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Target region'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        hs = wx.BoxSizer()
        hs.Add(wx.StaticText(self, label='Entire region'),
                flag = wx.RIGHT, border=20, proportion=1)
        self.entire = wx.CheckBox(self)
        hs.Add(self.entire, proportion=1)
        self.entire.Bind(wx.EVT_CHECKBOX, self.edit_region)
        vs.Add(hs, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        bpanel = wx.Panel(self)
        bounds = wx.FlexGridSizer(6, 3)
        bounds.AddGrowableCol(0, 1)
        bounds.AddGrowableCol(2, 1)
        self.bounds = {}
        self.bounds_sliders = {}
        for i in ['imin','imax','jmin','jmax','kmin','kmax']:
            s = wx.Slider(bpanel, name=i)
            s.Bind(wx.EVT_SCROLL, lambda e, q=i: self.sync_text(q))
            self.bounds_sliders[i] = s
            bounds.Add(s, flag=wx.LEFT|wx.TOP, border=10)

            t = wx.TextCtrl(bpanel, style=wx.NO_BORDER)
            t.Bind(wx.EVT_TEXT, lambda e, q=i: self.sync_slider(q))
            self.bounds[i] = t
            bounds.Add(t, flag=wx.LEFT|wx.TOP, border=10)

            bounds.Add(wx.StaticText(bpanel, label=i),
                    flag=wx.TOP|wx.LEFT, border=10, proportion=1)

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

    def sync_text(self, t):
        self.bounds[t].SetValue(str(self.bounds_sliders[t].GetValue()))
        koko.GLCANVAS.Refresh()

    def sync_slider(self, t):
        try:
            i = int(self.bounds[t].GetValue())
        except ValueError:
            return
        else:
            self.bounds_sliders[t].SetValue(i)
        koko.GLCANVAS.Refresh()

    class CornerDrag(DragHandler):
        """ @brief Handle to drag corner from GLCanvas
        """
        def __init__(self, corner):
            DragHandler.__init__(self)
            self.corner = corner
        def drag(self, dx, dy):
            proj = self.deproject(dx, dy)
            for b, d in zip(['i','j','k'], proj):
                try:
                    new_value = (
                        int(koko.IMPORT.bounds[b+self.corner].GetValue()) +
                        int(d*10)
                    )
                except ValueError:  continue

                if new_value < 0:           new_value = 0
                max_value = koko.IMPORT.bounds_sliders[b+self.corner].GetMax()
                if new_value > max_value:   new_value = max_value
                koko.IMPORT.bounds[b+self.corner].SetValue(str(new_value))
                koko.IMPORT.sync_slider(b+self.corner)

    def top_drag(self):
        return self.CornerDrag('max')
    def bottom_drag(self):
        return self.CornerDrag('min')


    def update_size(self, evt):
        for a in 'ijk':
            try:                i = int(getattr(self, 'n'+a).GetValue())
            except ValueError:  continue
            self.bounds_sliders[a+'min'].SetMax(i)
            self.bounds_sliders[a+'max'].SetMax(i)
            self.sync_text(a+'min')
            self.sync_text(a+'max')


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
            for a in 'ijk':
                self.bounds_sliders[a+'min'].SetValue(0)
                self.bounds_sliders[a+'max'].SetValue(
                    self.bounds_sliders[a+'max'].GetMax()
                )
                self.sync_text(a+'min')
                self.sync_text(a+'max')
        koko.FRAME.Layout()
        koko.GLCANVAS.Refresh()


    def clear(self):
        self.Hide()
        koko.FRAME.Layout()
        koko.FRAME.Refresh()

    def get_params(self, show_error=True, get_bounds=True):
        try:
            ni, nj, nk = map(
                lambda d: int(d.GetValue()),
                [self.ni, self.nj, self.nk]
            )
        except ValueError:
            if show_error:   dialogs.error('Invalid sample count.')
            return

        size = os.path.getsize(self.filename)
        if size != ni*nj*nk*4:
            if show_error:
                dialogs.error('File size does not match provided dimensions.')
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

        if get_bounds is False: return params

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
                        int(self.bounds[c].GetValue()) -
                        (1 if 'max' in c else 0)
                    )
                except ValueError:
                    if show_error:
                        dialogs.error('Invalid parameter for %s' % c)
                    return
        for a in 'ijk':
            if params[a+'min'] >= params[a+'max']:
                if show_error:
                    dialogs.error('%smin cannot be larger than %smax' % (a,a))
                return

        return params

    def preview(self, event):
        """ @brief Load a downsampled version of the full ASDF
        """
        params = self.get_params(get_bounds=False)
        if params is None:  return
        for p in params:    exec('{0} = params["{0}"]'.format(p))

        voxels = ni * nj * nk

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
        koko.GLCANVAS.snap = True


    def bounding_cube(self):
        if not self.IsShown() or self.entire.IsChecked():   return
        params = self.get_params(show_error=False)
        if params is None:  return

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

        koko.FRAME.status = 'Importing ASDF'
        wx.Yield()

        asdf = ASDF(
            libfab.import_vol_region(
                self.filename, ni, nj, nk, full, 0, density,
                True, close_boundary
            )
        )

        koko.FRAME.status = 'Triangulating'
        wx.Yield()

        mesh = asdf.triangulate()
        koko.FRAME.get_menu('View', '3D').Check(True)
        koko.APP.render_mode('3D')
        koko.GLCANVAS.load_mesh(mesh)
        koko.GLCANVAS.snap = True
        koko.FAB.set_input(asdf)

        koko.FRAME.status = ''
        koko.APP.mode = 'asdf'
        koko.APP.filename = None
        koko.APP.savepoint(False)
