import  wx
import  koko
from    koko.prims.core import Primitive

MENU_NAME = 'Points'

class Point(Primitive):
    ''' Defines a basic point with intersect and draw functions.'''

    MENU_NAME = 'Point'
    PARAMETERS = ['name','x','y']

    def __init__(self, name='point', x=0, y=0):
        Primitive.__init__(self, name)
        self.create_evaluators(x=(x,float), y=(y,float))

    @classmethod
    def new(cls, x, y, scale):
        name = koko.PRIMS.get_name('pt')
        return cls(name, x, y)

    def drag(self, dx, dy):
        try:    x = float(self.parameters['x'].expr)
        except ValueError:  pass
        else:   self.parameters['x'].expr = str(x+dx)

        try:    y = float(self.parameters['y'].expr)
        except ValueError:  pass
        else:   self.parameters['y'].expr = str(y+dy)

    def intersects(self, x, y, r):
        ''' Checks whether a circle with center (x,y) and radius r
            intersects this point.'''
        distance = ((x - self.x)**2 + (y - self.y)**2)**0.5
        return self if distance < r else None

    def draw(self, canvas):
        ''' Draws a vertex on the given canvas.

            A valid point is drawn as a circle, while an invalid vertex
            is drawn as a red X.  In each case, a highlight is drawn
            if the object is hovered, selected, or dragged.
        '''

        # Find canvas-space coordinates
        x, y = canvas.pos_to_pixel(self.x, self.y)

        if self.valid:
            light = (200, 200, 200)
            dark  = (100, 100, 100)
        else:
            light = (255, 80, 60)
            dark  = (255, 0, 0)

        # Valid vertexs are drawn as circles
        if self.valid:

            # Draw small marks to show if we can drag the point
            if self.dragging or self.hover:
                self.draw_handles(canvas)

            canvas.dc.SetBrush(wx.Brush(light))
            canvas.dc.SetPen(wx.Pen(dark, 2))
            canvas.dc.DrawCircle(x, y, 6)

        # Invalid vertexs are drawn as red Xs
        else:
            r = 3
            if self.hover or self.dragging:
                canvas.dc.SetPen(wx.Pen(light, 8))
                canvas.dc.DrawLine(x-r, y-r, x+r, y+r)
                canvas.dc.DrawLine(x-r, y+r, x+r, y-r)
            canvas.dc.SetPen(wx.Pen(dark, 4))
            canvas.dc.DrawLine(x-r, y-r, x+r, y+r)
            canvas.dc.DrawLine(x-r, y+r, x+r, y-r)

    def draw_handles(self, canvas):
        ''' Draws small handles based on whether we can drag this
            point around on its two axes. '''

        x, y = canvas.pos_to_pixel(self.x, self.y)

        try:    float(self.parameters['x'].expr)
        except ValueError:  x_free = False
        else:               x_free = True

        try:    float(self.parameters['y'].expr)
        except ValueError:  y_free = False
        else:               y_free = True

        x_light = (200, 200, 200) if x_free else (100, 100, 100)
        x_dark  = (100, 100, 100) if x_free else(60, 60, 60)

        y_light = (200, 200, 200) if y_free else (100, 100, 100)
        y_dark  = (100, 100, 100) if y_free else(60, 60, 60)


        canvas.dc.SetPen(wx.Pen(x_dark, 8))
        canvas.dc.DrawLine(x-10, y, x+10, y)

        canvas.dc.SetPen(wx.Pen(y_dark, 8))
        canvas.dc.DrawLine(x, y-10, x, y+10)

        canvas.dc.SetPen(wx.Pen(x_light, 4))
        canvas.dc.DrawLine(x-10, y, x+10, y)

        canvas.dc.SetPen(wx.Pen(y_light, 4))
        canvas.dc.DrawLine(x, y-10, x, y+10)
