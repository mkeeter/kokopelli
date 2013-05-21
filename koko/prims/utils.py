import  wx
import  koko
import  math

from    koko.prims.core import Primitive

MENU_NAME = 'Utilities'

class Slider(Primitive):
    ''' Defines a slider that you can slide. '''

    MENU_NAME = 'Slider'
    PARAMETERS = ['name','min','max','value','size']

    ################################################################
    class Handle(Primitive):
        def __init__(self, parent):
            Primitive.__init__(self, 'slider')
            self.parent = parent

        def drag(self, dx, dy):
            dx *= (self.parent.max - self.parent.min) / self.parent.size
            self.parent.parameters['value'].expr = self.parent.value + dx

        def intersects(self, x, y, r):
            if (abs(y - self.y) < 10/koko.CANVAS.scale and
                abs(x - self.x) < 5/koko.CANVAS.scale):
                return self

        @property
        def hover(self):
            if self.parent.dragging:    return False
            x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                              koko.CANVAS.GetScreenPosition()))
            r = 5 / koko.CANVAS.scale
            return self.intersects(x, y, r) == self

        @property
        def x(self):
            d = float(self.parent.max - self.parent.min)
            if d:   p = (self.parent.value - self.parent.min) / d
            else:   p = 0
            L = self.parent.size
            return self.parent.x - L/2. + L*p
        @property
        def y(self):    return self.parent.y

        def draw(self, canvas):
            if self.parent.value < self.parent.min:
                self.parent.parameters['value'].expr = self.parent.min
            if self.parent.value > self.parent.max:
                self.parent.parameters['value'].expr = self.parent.max
            x, y = canvas.pos_to_pixel(self.x, self.y)

            if self.parent.valid:
                highlight = (160, 160, 160)
                glow = (128, 128, 128, 128)
                light = (128, 128, 128)
                dark  = (64, 64, 64)
            else:
                highlight = (255, 160, 140)
                glow = (255, 80, 60, 128)
                light = (255, 80, 60)
                dark  = (255, 0, 0)

            if self.hover or self.dragging:
                self.draw_label(canvas)
                canvas.dc.SetBrush(wx.Brush(light))
                canvas.dc.SetPen(wx.Pen(glow, 6))
                canvas.dc.DrawRectangle(x - 5, y-10, 10, 20)

            canvas.dc.SetBrush(wx.Brush(light))
            canvas.dc.SetPen(wx.Pen(dark, 2))
            canvas.dc.DrawRectangle(x - 5, y-10, 10, 20)
            p = wx.Pen(highlight, 2)
            p.SetCap(wx.CAP_BUTT)
            canvas.dc.SetPen(p)
            canvas.dc.DrawLine(x+3, y-9, x+3, y+9)

        def draw_label(self, canvas):
            ''' Labels this node with its name and value.'''

            x, y = canvas.pos_to_pixel(self.x, self.y)

            canvas.dc.SetFont(wx.Font(12 + 4*self.priority,
                                      wx.FONTFAMILY_DEFAULT,
                                      wx.FONTSTYLE_NORMAL,
                                      wx.FONTWEIGHT_NORMAL))

            txt = '%s: %2g' % (self.parent.name, self.parent.value)
            w, h = canvas.dc.GetTextExtent(txt)
            x -= w/2
            y -= 14

            canvas.dc.SetBrush(wx.Brush((0, 0, 0, 150)))
            canvas.dc.SetPen(wx.TRANSPARENT_PEN)
            canvas.dc.DrawRectangle(x-5, y - h - 5, w + 10, h+10)

            canvas.dc.SetTextForeground((255,255,255))
            canvas.dc.DrawText(txt, x, y - h)

        def open_panel(self):   self.parent.open_panel()
        def close_panel(self):  self.parent.close_panel()

    ################################################################

    def __init__(self, name='point', x=0, y=0, min=0, max=1,
                 value=0.5, size=1):
        Primitive.__init__(self, name)
        self.handle = Slider.Handle(self)
        self.create_evaluators(x=(x,float), y=(y,float),
                               min=(min,float), max=(max,float),
                               value=(value, float), size=(size, float))

    @classmethod
    def new(cls, x, y, scale):
        name = koko.PRIMS.get_name('slider')
        return cls(name, x, y, size=2.5*float('%.1f' % scale))

    @property
    def hover(self):
        if self.handle.dragging:    return False
        x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                          koko.CANVAS.GetScreenPosition()))
        r = 5 / koko.CANVAS.scale
        return self.intersects(x, y, r) == self

    def drag(self, dx, dy):
        self.parameters['x'].expr = str(self.x + dx)
        self.parameters['y'].expr = str(self.y + dy)

    def intersects(self, x, y, r):
        if self.handle.intersects(x, y, r):
            return self.handle
        elif abs(y - self.y) < r and abs(x - self.x) < self.size/2 + r:
            return self

    def draw(self, canvas):
        x, y = canvas.pos_to_pixel(self.x, self.y)
        w    = canvas.pos_to_pixel(self.size)

        if self.valid:
            highlight = (128, 128, 128, 128)
            light = (128, 128, 128)
            dark  = (64, 64, 64)
        else:
            highlight = (255, 80, 60, 128)
            light = (255, 80, 60)
            dark  = (255, 0, 0)

        if self.hover:
            canvas.dc.SetPen(wx.Pen(highlight, 10))
            canvas.dc.DrawLine(x - w/2, y, x+w/2, y)
        elif self.dragging:
            canvas.dc.SetPen(wx.Pen(highlight, 8))
            canvas.dc.DrawLine(x - w/2, y, x+w/2, y)

        canvas.dc.SetPen(wx.Pen(dark, 6))
        canvas.dc.DrawLine(x - w/2, y, x+w/2, y)
        canvas.dc.SetPen(wx.Pen(light, 4))
        canvas.dc.DrawLine(x - w/2, y, x+w/2, y)

        self.handle.draw(canvas)
