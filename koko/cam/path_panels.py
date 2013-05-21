import operator

import wx

import  koko
from    koko.dialogs    import error
from    koko.cam.panel  import FabPanel
from    koko.fab.path   import Path

from    koko.c.vec3f    import Vec3f
import  numpy as np

################################################################################

class ContourPanel(FabPanel):
    """ @class ContourPanel
        @brief Panel to generate a single offset contour
    """
    def __init__(self, parent):
        FabPanel.__init__(self, parent)

        self.construct('2D Path', [
            ('Diameter (mm)', 'diameter', float, lambda f: f >= 0),
            ])

    def run(self, img):
        """ @brief Generates a single offset contour
            @param img Image to contour
            @returns Dictionary with 'paths' defined
        """
        values = self.get_values()
        if not values:  return False

        koko.FRAME.status = 'Finding distance transform'
        distance = img.distance()

        ## var @paths
        #   List of Paths representing contour cut
        self.paths = distance.contour(values['diameter']/2, 1, 0)
        koko.CANVAS.load_paths(self.paths, img.xmin, img.ymin)

        return {'paths': self.paths}

################################################################################

class PathPanel(FabPanel):
    """ @class PathPanel
        @brief General-purpose 2D/3D path planning panel.
    """
    def __init__(self, parent):

        FabPanel.__init__(self, parent)

        self.construct('Path', [
            ('Diameter (mm)', 'diameter', float, lambda f: f >= 0),
            ('Offsets (-1 to fill)', 'offsets', int,
                lambda f: f == -1 or f > 0),
            ('Overlap (0 - 1)', 'overlap', float, lambda f: 0 < f < 1),
            ('3D cut', 'threeD', bool),
            ('Z depth (mm)','depth', float, lambda f: f < 0),
            ('Top height (mm)','top', float),
            ('Bottom height (mm)','bottom', float),
            ('Step height (mm)','step', float, lambda f: f > 0),
            ('Path type', 'type', ['XY','XZ + YZ']),
            ('Tool type', 'tool', ['Flat','Ball']),
            ])

        # This panel is a bit special, because modifying the checkbox
        # can actually change the panel's layout (different labels are
        # shown or hidden depending on the path type)
        self.threeD.Bind(
            wx.EVT_CHECKBOX,
            lambda e: (self.parent.update(), self.parent.invalidate())
        )
        self.type.Bind(
            wx.EVT_CHOICE,
            lambda e: (self.parent.update(), self.parent.invalidate())
        )

    def update(self, threeD):
        """ @brief Modifies visible controls based on the situation
            @param threeD Boolean defining if the previous image has z information
        """

        def hide(index):
            self.labels[index].Hide()
            self.params[index].Hide()

        def show(index):
            self.labels[index].Show()
            self.params[index].Show()

        for i in range(len(self.params)):   show(i)

        if self.threeD.IsChecked() or threeD:
            hide(4)

            # 3D models can't be evaluated as 2D toolpaths,
            # and they've got their own opinions on z bounds
            if threeD:
                hide(3)
                hide(5)
                hide(6)

            # Number of offsets only matters for xy cuts;
            # mill bit selection only matters for finish cuts
            if self.type.GetSelection() == 1:   hide(1)
            else:                               hide(9)

        else:
            for i in range(5, 10):   hide(i)

        self.parent.Layout()
        return {}


    def run(self, img):
        """ @brief Generates paths
            @param img Input image
            @returns Dictionary with 'paths' defined
        """
        if self.threeD.IsChecked():
            if self.type.GetSelection() == 0:
                return self.run_rough(img)
            else:
                return self.run_finish(img)
            return False
        else:
            return self.run_2d(img)


    def run_rough(self, img):
        """ @brief Calculates a rough cut toolpath
            @param img Input image
            @returns Dictionary with 'paths' defined
        """

        # Save image's original z values (which may have been None)
        old_zvals = img.zmin, img.zmax

        if img.zmin is not None and img.zmax is not None and img.dz:
            values = self.get_values(['diameter','offsets','step'])
            if not values:  return False
            values['top']    = img.zmax
            values['bottom'] = img.zmin
        else:
            values = self.get_values(['diameter','offsets',
                                      'top','bottom','step'])
            if not values:  return False
            img.zmin = values['bottom']
            img.zmax = values['top']

        # We only need an overlap value if we're cutting more than one offsets
        if values['offsets'] != 1:
            v = self.get_values(['overlap'])
            if not v:   return False
            values.update(v)
        else:
            values['overlap'] = 1

        # Figure out the set of z values at which to cut
        heights = [values['top']]
        while heights[-1] > values['bottom']:
            heights.append(heights[-1]-values['step'])
        heights[-1] = values['bottom']

        # Loop over z values, accumulating samples
        i = 0

        self.paths = []
        last_image = None
        last_paths = []
        for z in heights:
            i += 1
            koko.FRAME.status = 'Calculating level %i/%i' % (i, len(heights))

            L = img.threshold(z)
            L.array *= 100
            L.save('test%i.png' % i)

            if last_image is not None and L == last_image:
                paths = [p.copy() for p in last_paths]
            else:
                distance = L.distance()
                paths = distance.contour(
                    values['diameter'], values['offsets'], values['overlap']
                )

            for p in paths:    p.set_z(z-values['top'])

            last_paths = paths
            last_image = L
            self.paths += paths

        # Path offsets (to match image / mesh position)
        self.xmin = img.xmin
        self.ymin = img.ymin
        self.zmin = values['top']

        koko.GLCANVAS.load_paths(self.paths, self.xmin, self.ymin, self.zmin)
        koko.CANVAS.load_paths(self.paths, self.xmin, self.ymin)
        koko.FRAME.status = ''

        # Restore z values on image
        img.zmin, img.zmax = old_zvals

        return {'paths': self.paths}


    def run_finish(self, img):
        """ @brief Calculates a finish cut toolpath
            @param img Input image
            @returns Dictionary with 'paths' defined
        """


        koko.FRAME.status = 'Making finish cut'

        # Save image's original z values (which may have been None)
        old_zvals = img.zmin, img.zmax

        if img.zmin is not None and img.zmax is not None and img.dz:
            values = self.get_values(['diameter','overlap','tool'])
            if not values:  return False
        else:
            values = self.get_values(['diameter','overlap',
                                      'top','bottom','tool'])
            if not values:  return False
            img.zmin = values['bottom']
            img.zmax = values['top']

        self.paths = img.finish_cut(
            values['diameter'], values['overlap'], values['tool']
        )
        for p in self.paths:
            p.offset_z(img.zmin-img.zmax)

        # Path offsets (to match image / mesh position)
        self.xmin = img.xmin
        self.ymin = img.ymin
        self.zmin = img.zmax

        koko.GLCANVAS.load_paths(self.paths, self.xmin, self.ymin, self.zmin)
        koko.CANVAS.load_paths(self.paths, self.xmin, self.ymin)
        koko.FRAME.status = ''

        # Restore z values on image
        img.zmin, img.zmax = old_zvals

        return {'paths': self.paths}


    def run_2d(self, img):
        """ @brief Calculates a 2D contour toolpath
            @param img Input image
            @returns Dictionary with 'paths' defined
        """

        values = self.get_values(['diameter','offsets','depth'])
        if not values:  return False

        # We only need an overlap value if we're cutting more than one offsets
        if values['offsets'] != 1:
            v = self.get_values(['overlap'])
            if not v:   return False
            values.update(v)
        else:
            values['overlap'] = 0

        koko.FRAME.status = 'Finding distance transform'
        distance = img.distance()

        koko.FRAME.status = 'Finding contours'
        self.paths = distance.contour(values['diameter'],
                                      values['offsets'],
                                      values['overlap'])
        for p in self.paths:    p.set_z(values['depth'])


        self.xmin = img.xmin
        self.ymin = img.ymin
        self.zmin = values['depth']

        koko.GLCANVAS.load_paths(self.paths, self.xmin, self.ymin, self.zmin)
        koko.CANVAS.load_paths(self.paths, self.xmin, self.ymin)
        koko.FRAME.status = ''

        return {'paths': self.paths}

################################################################################

class MultiPathPanel(FabPanel):
    """ @class MultiPathPanel
        @brief Path planning panel for multiple face cuts.
        @details The resulting paths are normalized so that xmin = 0, ymin = 0, and zmax = 0 (so cutting z values are negative, going into the material).
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)

        self.construct('Custom plane path', [
            ('Resolution (pixels/mm)\n? x ? x ?',
                'res', float, lambda f: f>0),
            ('Diameter (mm)', 'diameter', float, lambda f: f >= 0),
            ('Rough stepover (0-1)', 'stepover_r', float, lambda f: 0 < f < 1),
            ('Finish stepover (0-1)', 'stepover_f', float, lambda f: 0 < f < 1),
            ('Step height (mm)','step', float, lambda f: f > 0),
            ('Tool type', 'tool', ['Flat','Ball']),
            ('Cut type', 'cut', ['Rough','Finish','Both']),
            ('Mode', 'mode', ['Faces', 'From view', '3x2']),
            ('Cuts per 180 degrees', 'cuts_per', int, lambda f: f > 1),
            ('Alpha', 'alpha', float),
            ('Beta', 'beta', float, lambda f: f >= 0 and f <= 90),
            ])

        sizer = self.GetSizer()

        hs = wx.BoxSizer(wx.HORIZONTAL)
        get_button = wx.Button(
            self, wx.ID_ANY, label='Get rotation')
        set_button = wx.Button(
            self, wx.ID_ANY, label='Set rotation')
        get_button.Bind(wx.EVT_BUTTON, self.get_spin)
        set_button.Bind(wx.EVT_BUTTON, self.set_spin)
        hs.Add(get_button, flag=wx.LEFT|wx.TOP, border=5)
        hs.Add(set_button, flag=wx.LEFT|wx.TOP, border=5)
        sizer.Add(hs, flag=wx.CENTER|wx.BOTTOM, border=5)
        self._buttons = set_button, get_button

        self.SetSizerAndFit(sizer)

        self.res.Bind(wx.EVT_TEXT, self.parent.update)
        self.mode.Bind(
            wx.EVT_CHOICE,
            lambda e: (self.parent.update(), self.parent.invalidate())
        )


    def get_spin(self, event=None):
        """ @brief Copies alpha and beta values from GLCanvas
        """
        self.alpha.SetValue(str(koko.GLCANVAS.alpha))
        self.beta.SetValue(str(min(90,koko.GLCANVAS.beta)))
        self.parent.invalidate()

    def set_spin(self, event=None):
        """ @brief Copies alpha and beta values to GLCanvas
        """
        self.store_values()
        values = self.get_values(['alpha', 'beta'])
        if not values:  return
        koko.GLCANVAS.alpha = values['alpha']
        koko.GLCANVAS.beta = values['beta']
        koko.GLCANVAS.Refresh()


    def update(self, dx, dy, dz):
        """ @brief Modifies UI panel based on the situation
            @param dx x size of input ASDF (mm)
            @param dy y size of input ASDF (mm)
            @param dz z size of input ASDF (mm)
            @details Updates image size text and shows/hides parts of the UI based on selections.
        """

        def hide(index):
            self.labels[index].Hide()
            self.params[index].Hide()

        def show(index):
            self.labels[index].Show()
            self.params[index].Show()

        if self.mode.GetSelection() == 0:
            hide(8)
            hide(9)
            hide(10)
            [b.Show(False) for b in self._buttons]
        elif self.mode.GetSelection() == 1:
            hide(8)
            show(9)
            show(10)
            [b.Show(True) for b in self._buttons]
        else:
            show(8)
            hide(9)
            hide(10)
            [b.Show(False) for b in self._buttons]

        self.parent.Layout()

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
        return {}


    def run(self, asdf):
        """ @brief Generates one or more toolpaths
            @param asdf Input ASDF data structure
            @returns Dictionary with 'planes' (list of list of paths) and 'axis_names' (list of strings) items
        """
        # Parameters used by all operators
        values = self.get_values(
            ['mode','res','diameter','stepover_r',
             'tool','step','stepover_f','cut']
        )
        if not values:  return False

        # Get more parameters based on mode
        if values['mode'] == 1:
            v = self.get_values(['alpha','beta'])
            if not v:   return False
            values.update(v)
        elif values['mode'] == 2:
            v = self.get_values(['cuts_per'])
            if not v:   return False
            values.update(v)

        ## @var planes
        # List of lists of paths.  Each list of paths represent a set of cuts on a given plane.
        self.planes = []

        ## @var axis_names
        # List of strings representing axis names.
        self.axis_names = []

        if values['mode'] == 0:
            target_planes = [
                (0, 0, '+Z'), (180, 90, '+Y'), (0, 90, '-Y'),
                (90, 90, '-X'), (270, 90,'+X')
            ]
        elif values['mode'] == 1:
            target_planes = [
                (values['alpha'], values['beta'], 'view')
            ]
        elif values['mode'] == 2:
            cuts = values['cuts_per']
            alphas = [-90 + 180*v/float(cuts-1) for v in range(cuts)]
            betas = [360*v/float(cuts*2-2) for v in range(2*cuts-2)]
            target_planes = []
            for a in alphas:
                for b in betas:
                    target_planes.append( (a, b, '%g, %g' % (a, b)) )

        for a, b, axis in target_planes:
            koko.FRAME.status = 'Rendering ASDF on %s axis' % axis

            # Find endmill pointing vector
            v = -Vec3f(0,0,1).deproject(a, b)

            # Render the ASDF to a bitmap at the appropriate resolution
            img = asdf.render_multi(
                resolution=values['res'], alpha=a, beta=b
            )[0]
            img.save('test%s.png' % axis)

            # Find transformed ADSF bounds
            bounds = asdf.bounds(a, b)


            paths = []
            if values['cut'] in [0, 2]:
                paths += self.rough_cut(
                    img, values['diameter'], values['stepover_r'],
                    values['step'], bounds, axis
                )


            if values['cut'] in [1,2]:
                paths += self.finish_cut(
                    img, values['diameter'], values['stepover_f'],
                    values['tool'], bounds, axis
                )



            # Helper function to decide whether a path is inside the
            # ASDF's bounding box
            def inside(pt, asdf=asdf):
                d = values['diameter']
                return (
                    pt[0] >= -2*d and
                    pt[0] <= asdf.X.upper - asdf.X.lower + 2*d and
                    pt[1] >= -2*d and
                    pt[1] <= asdf.Y.upper - asdf.Y.lower + 2*d and
                    pt[2] <= 2*d and
                    pt[2] >= -(asdf.Z.upper - asdf.Z.lower)
                )


            culled = []
            for p in paths:
                for i in range(len(p.points)):
                    p.points[i,:] = list(Vec3f(p.points[i,:]).deproject(a, b))
                    p.points[i,:] -= [asdf.xmin, asdf.ymin, asdf.zmax]
                p.points = np.hstack(
                    (p.points, np.array([list(v)]*p.points.shape[0]))
                )
                current_path = []
                for pt in p.points:
                    if inside(pt):
                        current_path.append(pt)
                    elif current_path:
                        culled.append(Path(np.vstack(current_path)))
                        current_path = []
                if current_path:
                    culled.append(Path(np.vstack(current_path)))

            self.planes.append(culled)
            self.axis_names.append(axis)

        paths = reduce(operator.add, self.planes)
        koko.GLCANVAS.load_paths(
            paths, asdf.xmin, asdf.ymin, asdf.zmax
        )

        return {'planes': self.planes, 'axis_names': self.axis_names}



    def rough_cut(self, img, diameter, stepover, step, bounds, axis=''):
        """ @brief Calculates a rough cut
            @param img Image to cut
            @param diameter Endmill diameter
            @param stepover Stepover between passes
            @param step Z step amount
            @param bounds Image bounds
            @param axis Name of target axis
            @returns A list of cut paths
        """

        heights = [img.zmax]
        while heights[-1] > img.zmin:
            heights.append(heights[-1]-step)
        heights[-1] = img.zmin

        # Loop over z values, accumulating samples
        i = 0
        total = []
        for z in heights:
            i += 1
            if axis:
                koko.FRAME.status = (
                    'Calculating level %i/%i on %s axis'
                    % (i, len(heights), axis)
                )
            else:
                koko.FRAME.status = (
                    'Calculating level %i/%i on %s axis'
                    % (i, len(heights))
                )

            L = img.threshold(z)
            distance = L.distance()
            paths = distance.contour(diameter, -1, stepover)

            for p in paths:
                p.points[:,0] += bounds.xmin
                p.points[:,1] += bounds.ymin
                p.points[:,2]  = z

            total += paths
        return total


    def finish_cut(self, img, diameter, stepover, tool, bounds, axis=''):
        """ @brief Calculates a finish cut on a single image.
            @param img Image to cut
            @param diameter Endmill diameter
            @param stepover Stepover between passes
            @param tool Tool type (0 for flat-end, 1 for ball-end)
            @param bounds Image bounds
            @param axis Name of target axis
            @returns A list of cut paths
        """
        koko.FRAME.status = 'Making finish cut on %s axis' % axis
        finish = img.finish_cut(diameter, stepover, tool)

        # Special case to make sure that the safe plane
        # for the finish cut is good.
        finish[0].points = np.vstack(
            [finish[0].points[0,:], finish[0].points]
        )
        finish[0].points[0,2] = img.zmax - img.zmin

        for p in finish:
            for i in range(len(p.points)):
                p.points[i,0:3] += [bounds.xmin, bounds.ymin, bounds.zmin]
        return finish
