import ctypes
import Queue
import shutil
import subprocess
import tempfile
import threading
import time
import os

import wx

import  koko
import  koko.dialogs as dialogs
from    koko.c.region     import Region

from    koko.fab.asdf     import ASDF
from    koko.fab.path     import Path
from    koko.fab.image    import Image
from    koko.fab.mesh     import Mesh

class ExportProgress(wx.Frame):
    ''' Frame with a progress bar and a cancel button.
        When the cancel button is pressed, events are set.
    '''
    def __init__(self, title, event, c_event=None):
        self.event, self.c_event = event, c_event

        wx.Frame.__init__(self, parent=koko.FRAME, title=title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.gauge = wx.Gauge(self, wx.ID_ANY, size=(200, 20))
        hbox.Add(self.gauge, flag=wx.ALL, border=10)

        cancel = wx.Button(self, label='Cancel')
        self.Bind(wx.EVT_BUTTON, self.cancel)
        hbox.Add(cancel, flag=wx.ALL, border=10)

        self.SetSizerAndFit(hbox)
        self.Show()

    @property
    def progress(self): return self.gauge.GetValue()
    @progress.setter
    def progress(self, v):  wx.CallAfter(self.gauge.SetValue, v)

    def cancel(self, event):
        self.event.set()
        if self.c_event:    self.c_event.set()

################################################################################

class ExportTask(object):
    ''' A task representing an export task.

        Requires a filename, cad structure, and resolution
        (None if irrelevant)
    '''

    def __init__(self, filename, cad, resolution=None, checked=None):

        self.filename   = filename
        self.extension  = self.filename.split('.')[-1]
        self.cad        = cad
        self.resolution = float(resolution) if resolution else None

        # The checked parameter is interpreted differently based on
        # what type of file we are exporting.
        if   self.extension == 'asdf':  self.merge_leafs = checked
        elif self.extension == 'stl':
            self.use_cms     = checked
            self.merge_leafs = True
        elif self.extension == 'svg':   self.merge_leafs = True
        elif self.extension == 'dot':   self.arrays = checked
        elif self.extension == 'png':   self.heightmap = checked

        self.event   = threading.Event()
        self.c_event = threading.Event()

        self.window = ExportProgress(
            'Exporting to %s' % self.extension, self.event, self.c_event
        )

        # Create a new thread to run the export in the background
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def export_png(self):
        ''' Exports a png using libtree.
        '''

        if self.heightmap:
            out = self.make_image(self.cad.function)
        else:
            i = 0
            imgs = []
            for e in self.cad.shapes:
                if self.event.is_set(): return
                img = self.make_image(e)
                if img is not None: imgs.append(img)
                i += 1
                self.window.progress = i*90/len(self.cad.shapes)
            out = Image.merge(imgs)

        if self.event.is_set(): return

        self.window.progress = 90
        out.save(self.filename)
        self.window.progress = 100



    def make_image(self, expr):
        ''' Renders a single expression, returning the image
        '''
        zmin = self.cad.zmin if self.cad.zmin else 0
        zmax = self.cad.zmax if self.cad.zmax else 0

        region = Region(
            (self.cad.xmin, self.cad.ymin, zmin),
            (self.cad.xmax, self.cad.ymax, zmax),
            self.resolution*self.cad.mm_per_unit
        )

        img = expr.render(
            region, mm_per_unit=self.cad.mm_per_unit, interrupt=self.c_event
        )

        img.color = expr.color
        return img


    def export_asdf(self):
        ''' Exports an ASDF file.
        '''
        asdf = self.make_asdf(self.cad.function)
        self.window.progress = 50
        if self.event.is_set(): return
        asdf.save(self.filename)
        self.window.progress = 100


    def export_svg(self):
        ''' Exports an svg file at 90 DPI with per-object colors.
        '''
        xmin = self.cad.xmin*self.cad.mm_per_unit
        dx = (self.cad.xmax - self.cad.xmin)*self.cad.mm_per_unit
        ymax = self.cad.ymax*self.cad.mm_per_unit
        dy = (self.cad.ymax - self.cad.ymin)*self.cad.mm_per_unit
        stroke = max(dx, dy)/100.


        Path.write_svg_header(self.filename, dx, dy)

        i = 0
        for expr in self.cad.shapes:
            # Generate an ASDF
            if self.event.is_set(): return
            asdf = self.make_asdf(expr, flat=True)
            i += 1
            self.window.progress = i*33/len(self.cad.shapes)

            # Find the contours of the ASDF
            if self.event.is_set(): return
            contours = self.make_contour(asdf)
            i += 2
            self.window.progress = i*33/len(self.cad.shapes)

            # Write them out to the SVG file
            for c in contours:
                c.write_svg_contour(
                    self.filename, xmin, ymax, stroke=stroke,
                    color=expr.color if expr.color else (0,0,0)
                )

        Path.write_svg_footer(self.filename)


    def export_stl(self):
        ''' Exports an stl, using an asdf as intermediary.
        '''
        i = 0
        meshes = []
        for expr in self.cad.shapes:

            if self.event.is_set(): return
            asdf = self.make_asdf(expr)
            i += 1
            self.window.progress = i*33/len(self.cad.shapes)

            if self.event.is_set(): return
            mesh = self.make_mesh(asdf)
            i += 2
            self.window.progress = i*33/len(self.cad.shapes)

            if mesh is not None:    meshes.append(mesh)

        if self.event.is_set(): return
        total = Mesh.merge(meshes)
        total.save_stl(self.filename)

    def make_asdf(self, expr, flat=False):
        ''' Renders an expression to an ASDF '''
        if flat:
            region = Region((expr.xmin - self.cad.border*expr.dx,
                             expr.ymin - self.cad.border*expr.dy,
                             0),
                            (expr.xmax + self.cad.border*expr.dx,
                             expr.ymax + self.cad.border*expr.dy,
                             0),
                             self.resolution*self.cad.mm_per_unit)
        else:
            region = Region((expr.xmin - self.cad.border*expr.dx,
                             expr.ymin - self.cad.border*expr.dy,
                             expr.zmin - self.cad.border*expr.dz),
                            (expr.xmax + self.cad.border*expr.dx,
                             expr.ymax + self.cad.border*expr.dy,
                             expr.zmax + self.cad.border*expr.dz),
                             self.resolution*self.cad.mm_per_unit)
        asdf = expr.asdf(
            region=region, mm_per_unit=self.cad.mm_per_unit,
            interrupt=self.c_event, merge_leafs=self.merge_leafs
        )
        return asdf

    def make_contour(self, asdf):
        contour = asdf.contour(interrupt=self.c_event)
        return contour

    def make_mesh(self, asdf):
        ''' Renders an ASDF to a mesh '''
        if self.use_cms:
            return asdf.triangulate_cms()
        else:
            return asdf.triangulate(interrupt=self.c_event)

    def export_dot(self):
        ''' Saves a math tree as a .dot file. '''

        # Make the cad function and C data structure
        expr = self.cad.function
        expr.ptr
        self.window.progress = 25

        # Save as a dot file
        expr.save_dot(self.filename, self.arrays)
        self.window.progress = 100

    def run(self):
        if self.extension == 'png':
            self.export_png()
        elif self.extension == 'stl':
            self.export_stl()
        elif self.extension == 'asdf':
            self.export_asdf()
        elif self.extension == 'dot':
            self.export_dot()
        elif self.extension == 'svg':
            self.export_svg()
        elif self.extension == 'math':
            self.cad.write(self.filename)

        wx.CallAfter(self.window.Destroy)


################################################################################

class FabTask(subprocess.Popen):
    def __init__(self, cad):
        self.file = tempfile.NamedTemporaryFile(suffix='.math')
        cad.write(self.file)
        self.ptime = 0
        subprocess.Popen.__init__(self, ['fab', self.file.name])

    def update(self, cad):
        cad.write(self.file)
