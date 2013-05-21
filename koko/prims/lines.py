import  math
import  wx

import  koko
from    koko.prims.core     import Primitive
from    koko.prims.points   import Point

MENU_NAME = 'Lines'

class Line(Primitive):
    ''' Defines a line terminated at two points.'''

    MENU_NAME = 'Line'
    PARAMETERS = ['name','A','B']

    def __init__(self, name='line', A='pt0', B='pt1'):
        Primitive.__init__(self, name)
        self.priority = 1
        self.create_evaluators(A=(A, Primitive), B=(B, Primitive))

    @property
    def x(self):    return (self.A.x + self.B.x)/2.
    @property
    def y(self):    return (self.A.y + self.B.y)/2.

    @property
    def hover(self):
        if self.A.dragging or self.B.dragging:    return False
        x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                          koko.CANVAS.GetScreenPosition()))
        r = 5 / koko.CANVAS.scale
        return self.intersects(x, y, r) == self

    @classmethod
    def new(cls, x, y, scale):
        names = koko.PRIMS.get_name('pt',2)
        A = Point(names[0], x-scale, y)
        B = Point(names[1], x+scale, y)
        return A, B, cls(koko.PRIMS.get_name('line'), *names)

    def draw(self, canvas):
        canvas.dc.SetPen(wx.Pen((100, 150, 255), 4))
        x0, y0 = canvas.pos_to_pixel(self.A.x, self.A.y)
        x1, y1 = canvas.pos_to_pixel(self.B.x, self.B.y)
        canvas.dc.DrawLine(x0, y0, x1, y1)

    def intersects(self, x, y, r):

        x0, y0 = self.A.x, self.A.y
        x1, y1 = self.B.x, self.B.y
        L = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)

        # Find unit vectors running parallel and perpendicular to the line
        try:    perp = ((y1 - y0)/L, -(x1 - x0)/L)
        except ZeroDivisionError:   perp = (float('inf'), float('inf'))
        try:    para = ((x1 - x0)/L,  (y1 - y0)/L)
        except ZeroDivisionError:   para = (float('inf'), float('inf'))

        para = -((x0 - x)*para[0] + (y0 - y)*para[1])
        if para <  -r:   return None
        if para > L+r:   return None

        # Perpendicular distance to line
        return self if abs((x0 - x)*perp[0] +
                           (y0 - y)*perp[1]) < r else None

    def drag(self, dx, dy):
        self.A.drag(dx, dy)
        self.B.drag(dx, dy)


