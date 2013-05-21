from    math import sin, cos, pi, floor, ceil

import  wx
import  numpy as np

import  koko
from    koko.prims.menu import show_menu
from    koko.struct     import Struct

class Canvas(wx.Panel):
    """ @class Canvas
        @brief Canvas based on a wx.Panel that draws images and primitives
    """

    def __init__(self, parent, app, *args, **kwargs):
        """ @brief Creates the canvas
            @param parent Parent wx.Frame
            @param app wx.App to which we'll bind callbacks
        """
        wx.Panel.__init__(self, parent, *args, **kwargs)

        ## @var mark_changed_view
        # Callback to trigger a rerender
        self.mark_changed_view = app.mark_changed_view

        # Bind ALL THE THINGS!
        self.bind_callbacks()

        ## @var click
        # Previous click position (in pixel coordinates)
        ## @var mouse
        # Current mouse position (in pixel coordinates)
        self.click = self.mouse = wx.Point()

        ## @var center
        # View center (in cad units)
        self.center = [0.0, 0.0]

        ## @var alpha
        # Rotation about z axis (non-functional)
        ## @var beta
        # Rotation about x axis (non-functional)
        self.alpha = self.beta = 0

        ## @var scale
        # View scale (in pixels/unit)
        self.scale = 20.0

        ## @var mm_per_unit
        # Real-world scale (in mm/unit)
        self.mm_per_unit = 25 # scale factor

        ## @var image
        # Merged image to draw, or None
        self.image = None

        ## @var drag_target
        # Target for left-click and drag operations
        self.drag_target = None

        ## @var dc
        # DrawCanvas variable
        self.dc     = None

        ## @var paths
        # Set of paths to draw, stored as a list of ?x2 NumPy array
        self.paths  = []

        ## @var traverses
        # Set of traverses to draw, stored as an ?x4 NumPy array
        self.traverses = None

        ## @var snap
        # When true, snap to bounds as soon as possible
        self.snap   = True

        ## @var dragged
        # Used when dragging to check if this was a click+drag or a single click

        ## @var images
        # List of images that were merged to make self.image; used in drawing bounds.

################################################################################

    def bind_callbacks(self):
        """ @brief Binds a set of Canvas callbacks.
        """
        self.Bind(wx.EVT_PAINT,         self.paint)
        self.Bind(wx.EVT_MOTION,        self.mouse_move)
        self.Bind(wx.EVT_LEFT_DOWN,     self.mouse_lclick)
        self.Bind(wx.EVT_LEFT_DCLICK,   self.mouse_dclick)
        self.Bind(wx.EVT_LEFT_UP,       self.mouse_lrelease)
        self.Bind(wx.EVT_RIGHT_DOWN,    self.mouse_rclick)
        self.Bind(wx.EVT_MOUSEWHEEL,    self.mouse_scroll)
        self.Bind(wx.EVT_SIZE,          self.mark_changed_view)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_CHAR,          self.char)

    @property
    def border(self):
        """ @brief Border property
        """
        return getattr(self, '_border', None)
    @border.setter
    def border(self, value):
        """ @brief Sets border property and calls Refresh
        """
        self._border = value
        wx.CallAfter(self.Refresh)

################################################################################

    def mouse_move(self, event):
        """ @brief  Handles a mouse move across the canvas.
            @details Drags self.drag_target if it exists
        """
        self.mouse = wx.Point(event.GetX(), event.GetY())

        x, y = self.pixel_to_pos(*self.mouse)
        if koko.PRIMS.mouse_pos(x, y):  self.Refresh()

        # Drag the current drag target around
        if self.drag_target is not None:
            self.dragged = True
            delta = self.mouse - self.click
            self.click = self.mouse
            self.drag_target.drag(delta.x/self.scale, -delta.y/self.scale)
            self.Refresh()

########################################

    def mouse_lclick(self, event):
        """ @brief Records click position and gets a drag target
            @details The drag target is stored in self.drag_target.  It may be a primitive or the canvas itself.
        """
        self.mouse = wx.Point(event.GetX(), event.GetY())
        self.click = self.mouse

        # If we were already dragging something, then dragged remains
        # true (otherwise it is false, because we're starting a new
        # drag)
        self.dragged = bool(self.drag_target)

        x, y = self.pixel_to_pos(*self.mouse)
        t = koko.PRIMS.get_target(x, y)
        if t:
            self.drag_target = t
        else:
            self.drag_target = self

########################################

    def mouse_lrelease(self, event):
        """ @brief Release the current drag target.
        """
        if self.drag_target:
            if self.dragged and self.drag_target != self:
                koko.PRIMS.push_stack()
            elif not self.dragged:
                koko.PRIMS.close_panels()
            self.drag_target = None

########################################

    def mouse_rclick(self, event):
        ''' Pop up a menu to create primitives. '''
        menu = show_menu()

        menu.AppendSeparator()

        # Get the a target primitive to delete
        self.mouse = wx.Point(event.GetX(), event.GetY())
        x, y = self.pixel_to_pos(*self.mouse)
        t = koko.PRIMS.get_target(x, y)
        delete = menu.Append(wx.ID_ANY, text='Delete')
        if t is not None:
            self.Bind(wx.EVT_MENU, lambda e: koko.PRIMS.delete(t), delete)
        else:
            delete.Enable(False)

        undo = menu.Append(wx.ID_ANY, text='Undo')
        if koko.PRIMS.can_undo:
            self.Bind(wx.EVT_MENU, koko.PRIMS.undo, undo)
        else:
            undo.Enable(False)

        self.PopupMenu(menu)

########################################

    def char(self, event):
        """ @brief Keyboard callback
            @details Recognizes Ctrl+Z as Undo and Delete to delete primitive
        """
        if event.CmdDown() and event.GetKeyCode() == ord('Z'):
            if koko.PRIMS.can_undo: koko.PRIMS.undo()
        elif event.GetKeyCode() == 127:

            x, y = self.pixel_to_pos(*self.mouse)

            t = koko.PRIMS.get_target(x, y)
            koko.PRIMS.delete(t)
        else:
            event.Skip()

########################################

    def mouse_dclick(self, event):
        '''Double-click to open up the point editing box.'''
        self.mouse = wx.Point(event.GetX(), event.GetY())
        x, y = self.pixel_to_pos(*self.mouse)
        target = koko.PRIMS.get_target(x, y)
        if target is not None:
            target.open_panel()

########################################

    def mouse_scroll(self, event):
        '''Handles mouse scrolling by adjusting window scale.'''
        width, height = self.Size

        origin = ((width/2 - self.mouse[0]) / self.scale - self.center[0],
                  (self.mouse[1] - height/2) / self.scale - self.center[1])

        dScale = 1.0025
        if event.GetWheelRotation() < 0:
            dScale = 1 / dScale
        for i in range(abs(event.GetWheelRotation())):
            self.scale *= dScale
        if self.scale > (1 << 32):
            self.scale = 1 << 32

        # Reposition the center so that the point under the mouse cursor remains
        # under the mouse cursor post-zoom.
        self.center = ((width/2 - self.mouse[0]) / self.scale - origin[0],
                       (self.mouse[1] - height/2) / self.scale - origin[1])

        self.mark_changed_view()
        self.Refresh()

################################################################################

    def drag(self, dx, dy):
        ''' Drag the canvas around. '''
        self.center = (self.center[0] - dx, self.center[1] - dy)
        self.mark_changed_view()
        self.Refresh()

################################################################################

    def mm_to_pixel(self, x, y=None):
        """ @brief Converts an x, y position in mm into an i,j coordinate
            @details Uses self.mm_per_unit to synchronize scales
            @returns A 2-item tuple representing i,j position
        """
        width, height = self.Size
        xcenter, ycenter = self.center
        xcenter *= self.mm_per_unit
        ycenter *= self.mm_per_unit
        scale = self.scale / self.mm_per_unit

        if y is None:
            return int(x*scale)
        else:
            return map(int,
                [(x - xcenter) * scale + (width / 2.),
                 height/2. - (y - ycenter) * scale]
            )


    def pos_to_pixel(self, x, y=None):
        """ @brief Converts an x, y position in arbitrary units into an i,j coordinate
            @returns A 2-item tuple representing i,j position
        """

        width, height = self.Size
        xcenter, ycenter = self.center

        if y is None:
            return int(x*self.scale)
        else:
            return map(int,
                [(x - xcenter) * self.scale + (width / 2.),
                 height/2. - (y - ycenter) * self.scale]
            )

########################################

    def pixel_to_pos(self, i, j):
        """ @brief Converts an i,j pixel position into an x,y coordinate in arbitrary units.
            @returns A 2-item tuple representing x,y position
        """
        width, height = self.Size
        xcenter, ycenter = self.center

        return ((i - width/2) / self.scale + xcenter,
               (height/2 - j) / self.scale + ycenter)

################################################################################

    def get_crop(self):
        ''' Calculates a cropping rectangle to discard portions of the image
            that do not fit into the current view. '''

        if self.image.xmin < self.xmin*self.mm_per_unit:
            x0 = floor(
                self.image.pixels_per_mm *
                (self.xmin*self.mm_per_unit - self.image.xmin)
            )
        else:
            x0 = 0

        if self.image.xmax > self.xmax*self.mm_per_unit:
            x1 = ceil(
                self.image.width - (self.image.pixels_per_mm *
                (self.image.xmax - self.xmax*self.mm_per_unit))
            )
        else:
            x1 = self.image.width

        if self.image.ymin < self.ymin*self.mm_per_unit:
            y1 = ceil(
                self.image.height - (self.image.pixels_per_mm *
                (self.ymin*self.mm_per_unit - self.image.ymin))
            )
        else:
            y1 = self.image.height

        if self.image.ymax > self.ymax*self.mm_per_unit:
            y0 = floor(
                self.image.pixels_per_mm *
                (self.image.ymax - self.ymax*self.mm_per_unit)
            )
        else:
            y0 = 0

        return wx.Rect(x0, y0, x1-x0, y1 - y0)

################################################################################

    def paint(self, event=None):
        '''Redraws the window.'''

        self.dc = wx.PaintDC(self)
        self.dc.SetBackground(wx.Brush((20,20,20)))
        self.dc.Clear()

        # Draw the active iamge
        self.draw_image()

        # Draw bounds only if 'Show bounds' is checked
        if koko.FRAME.get_menu('View','Show bounds').IsChecked():
            self.draw_bounds()

        # Draw x and y axes
        if koko.FRAME.get_menu('View','Show axes').IsChecked():
            self.draw_axes()

        self.draw_paths()

        # Draw border
        self.draw_border()

        koko.PRIMS.draw(self)

        self.dc = None

################################################################################

    def draw_image(self):
        ''' Draws the current image in the dc. '''

        if not self.image:  return


        width, height = self.Size
        xcenter, ycenter = self.center[0], self.center[1]

        if self.scale / self.mm_per_unit == self.image.pixels_per_mm:

            # If the image is at the correct scale, then we're fine
            # to simply render it at its set position
            bitmap = wx.BitmapFromImage(self.image.wximg)
            xmin = self.image.xmin
            ymax = self.image.ymax
        else:

            # Otherwise, we have to rescale the image
            # (and we'll pre-emptively crop it to avoid
            #  blowing it up to a huge size)
            crop = self.get_crop()

            if crop.Width <= 0 or crop.Height <= 0:  return

            scale = self.scale / (self.mm_per_unit * self.image.pixels_per_mm)

            img = self.image.wximg.Copy().GetSubImage(crop)
            if int(img.Width*scale) == 0 or int(img.Height*scale) == 0:
                return

            img.Rescale(img.Width  * scale,
                        img.Height * scale)
            bitmap = wx.BitmapFromImage(img)

            xmin = (
                self.image.xmin +
                crop.Left*self.image.mm_per_pixel
            )
            ymax = (
                self.image.ymax -
                crop.Top*self.image.mm_per_pixel
            )

        # Draw image
        imgX, imgY = self.mm_to_pixel(xmin, ymax)

        self.dc.SetBrush(wx.Brush((0,0,0)))
        self.dc.SetPen(wx.TRANSPARENT_PEN)
        self.dc.DrawRectangle(imgX, imgY, bitmap.Width, bitmap.Height)
        self.dc.DrawBitmap(bitmap, imgX, imgY)


    def load_paths(self, paths, xmin, ymin):
        """ @brief Loads a set of toolpaths
            @details Can be called from a separate thread; uses self._load_paths to actually store data.
            @param paths List of Path objects
            @param xmin Left X coordinate (in mm) for alignment
            @param ymin Bottom Y coordinate (in mm) for alignment
        """
        cuts = []
        for p in paths:
            if p.closed:
                cuts.append(
                    np.append(p.points[:,0:2], [p.points[0,0:2]], axis=0)
                )
            else:
                cuts.append(np.copy(p.points[:,0:2]))
            cuts[-1][:,0] += xmin
            cuts[-1][:,1] += ymin

        traverses = np.empty((0, 6))
        for i in range(len(paths)-1):
            p = paths[i]
            start = p.points[0,:] if p.closed else p.points[-1,:]
            end = paths[i+1].points[0,:]
            traverses = np.append(traverses,
                [np.append(start, end)], axis=0)

        traverses[:,0] += xmin
        traverses[:,1] += ymin
        traverses[:,3] += xmin
        traverses[:,4] += ymin
        wx.CallAfter(self._load_paths, cuts, traverses)


    def _load_paths(self, paths, traverses):
        """ @brief Stores paths and traverses then refreshes canvas
            @details Should only be called from main thread
        """
        self.paths = paths
        self.traverses = traverses
        self.Refresh()


    def clear(self):
        """ @brief Clears stored images and paths; redraws canvas.
        """
        self.images = []
        self.image  = None
        self.paths = None
        self.Refresh()


    def clear_path(self):
        """ @brief Clears stored paths; redraws canvas.
        """
        self.paths = None
        self.Refresh()
        return


    def draw_paths(self):
        """ @brief Draws stored paths (and possibly traverses)
        """
        if self.paths is None:  return

        self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
        self.dc.SetPen(wx.Pen((100,255,150), 1))

        scale = self.scale / self.mm_per_unit
        center = (
            self.center[0] * self.mm_per_unit,
            self.center[1] * self.mm_per_unit
        )

        for i in range(len(self.paths)):

            d = i/float(len(self.paths))
            self.dc.SetPen(wx.Pen((100*d,200*d+50,255*(1-d)), 1))

            p = self.paths[i]
            i = (p[:,0] - center[0]) * scale + self.Size[0]/2.
            j = self.Size[1]/2. - (p[:,1] - center[1])*scale

            self.dc.DrawLines(zip(i,j))

        if koko.FRAME.get_menu('View','Show traverses').IsChecked():
            self.dc.SetPen(wx.Pen((255,100,100), 1))
            t = self.traverses
            if t is None or t.size == 0:   return

            i0 = (t[:,0] - center[0]) * scale + self.Size[0]/2.
            j0 = self.Size[1]/2. - (t[:,1] - center[1])*scale
            i1 = (t[:,3] - center[0]) * scale + self.Size[0]/2.
            j1 = self.Size[1]/2. - (t[:,4] - center[1])*scale

            self.dc.DrawLineList(zip(i0, j0, i1, j1))


################################################################################

    def draw_axes(self):
        """ @brief Draws x, y, z axes in red, green, and blue.
        """
        def spin(x, y, z, alpha, beta):
            ca, sa = cos(alpha), sin(alpha)
            x, y, z = (ca*x - sa*y, sa*x + ca*y, z)

            cb, sb = cos(beta), sin(beta)
            x, y, z = (x, cb*y + sb*z, -sb*y + cb*z)

            return x, y, z

        center = self.pos_to_pixel(0, 0)
        self.dc.SetPen(wx.Pen((255, 0, 0), 2))
        x, y, z = spin(50, 0, 0, -self.alpha, -self.beta)
        self.dc.DrawLine(center[0], center[1], center[0] + x, center[1] - y)

        self.dc.SetPen(wx.Pen((0, 255, 0), 2))
        x, y, z = spin(0, 50, 0, -self.alpha, -self.beta)
        self.dc.DrawLine(center[0], center[1], center[0] + x, center[1] - y)

        self.dc.SetPen(wx.Pen((0, 0, 255), 2))
        x, y, z = spin(0, 0, 50, -self.alpha, -self.beta)
        self.dc.DrawLine(center[0], center[1], center[0] + x, center[1] - y)

################################################################################

    def draw_border(self):
        """ @brief If self.border is set, draw a rectangular border around canvas.
        """
        if self.border:
            self.dc.SetPen(wx.TRANSPARENT_PEN)
            self.dc.SetBrush(wx.Brush(self.border))

            border_width = 3
            self.dc.DrawRectangle(0, 0, self.Size[0], border_width)
            self.dc.DrawRectangle(0, self.Size[1]-border_width,
                                  self.Size[0], border_width)
            self.dc.DrawRectangle(0, 0, border_width, self.Size[1])
            self.dc.DrawRectangle(self.Size[0]-border_width, 0,
                                  border_width, self.Size[1])

################################################################################

    def draw_bounds(self):
        """ @brief Draws rectangular border around individual images.
        """
        for i in self.images:
            scale = self.scale / self.mm_per_unit
            xmin, ymin = self.pos_to_pixel(
                i.xmin / self.mm_per_unit, i.ymin / self.mm_per_unit
            )
            xmax, ymax = self.pos_to_pixel(
                i.xmax / self.mm_per_unit, i.ymax / self.mm_per_unit
            )

            self.dc.SetPen(wx.Pen((128, 128, 128)))
            self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
            self.dc.DrawRectangle(xmin, ymin, xmax-xmin, ymax-ymin)


################################################################################

    @property
    def xmin(self):
        """ @brief Position of left edge (in arbitrary units) """
        return self.center[0] - self.Size[0]/2./self.scale
    @property
    def xmax(self):
        """ @brief Position of right edge (in arbitrary units) """
        return self.center[0] + self.Size[0]/2./self.scale
    @property
    def ymin(self):
        """ @brief Position of bottom edge (in arbitrary units) """
        return self.center[1] - self.Size[1]/2./self.scale
    @property
    def ymax(self):
        """ @brief Position of top edge (in arbitrary units) """
        return self.center[1] + self.Size[1]/2./self.scale

    @property
    def view(self):
        """ @brief Gets global view description
            @returns Struct with xmin, ymin, xmax, ymax, and pixels_per_unit variables."""
        return Struct(xmin=self.xmin, xmax=self.xmax,
                      ymin=self.ymin, ymax=self.ymax,
                      alpha=self.alpha, beta=self.beta,
                      pixels_per_unit=self.scale)

################################################################################

    def load_image(self, img, mm_per_unit=1):
        """ @brief Loads a single image and sets canvas real-space scale
        """
        self.load_images([img], mm_per_unit)

    def load_images(self, imgs, mm_per_unit=1):
        """ @brief Loads a list of images and sets canvas real-space scale
            @details Thread-safe, using self._load_images to store data
        """
        merged = imgs[0].merge(imgs)
        wx.CallAfter(self._load_images, imgs, merged, mm_per_unit)

    def _load_images(self, imgs, merged, mm_per_unit=1):
        """ @brief Stores a new set of images, merged image, and scale factor.
            @details Should only be called from main thread
        """
        self.images = imgs
        self.image = merged

        if self.snap:
            self.snap_bounds()
            self.snap = False

        self.mm_per_unit = mm_per_unit
        self.Refresh()

################################################################################

    def snap_bounds(self):
        """ @brief Snaps to view centered on the current image.
        """

        if not self.image:  return

        width, height = self.Size

        try:
            self.center = [
                (self.image.xmin + self.image.dx/2.) / self.mm_per_unit,
                (self.image.ymin + self.image.dy/2.) / self.mm_per_unit
            ]

            self.scale = float(
                min(width/(self.image.dx/self.mm_per_unit),
                    height/(self.image.dy/self.mm_per_unit))
            )
            self.alpha = self.beta = 0
        except TypeError:
            pass
        else:
            self.mark_changed_view()

        self.Refresh()


    def snap_axis(self, axis):
        """ @brief Snaps to view along a particular axis.
        """

        if axis == '+x':
            self.alpha, self.beta = pi/2, -pi/2
        elif axis == '+y':
            self.alpha, self.beta = 0, pi/2
        elif axis == '+z':
            self.alpha, self.beta = 0, 0
        elif axis == '-x':
            self.alpha, self.beta = -pi/2, -pi/2
        elif axis == '-y':
            self.alpha, self.beta = 0, -pi/2
        elif axis == '-z':
            self.alpha, self.beta = 0, pi
        self.mark_changed_view()

        self.Refresh()
