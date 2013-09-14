import operator
from math import cos, sin, atan2, radians, degrees, sqrt

import koko.lib.shapes2d as s2d
from koko.lib.text import text

class PCB(object):
    def __init__(self, x0, y0, width, height):
        self.x0 = x0
        self.y0 = y0
        self.width = width
        self.height = height

        self.components  = []
        self.connections = []

    @property
    def traces(self):
        L = [c.pads for c in self.components] + [c.traces for c in self.connections]
        return reduce(operator.add, L) if L else None

    @property
    def part_labels(self):
        L = [c.label for c in self.components if c.label is not None]
        return reduce(operator.add, L) if L else None

    @property
    def pin_labels(self):
        L = [c.pin_labels for c in self.components if c.pin_labels is not None]
        return reduce(operator.add, L) if L else None

    def shapes(self, labels=True):
        if labels:
            T = []
            if self.pin_labels:
                T.append(s2d.color(self.pin_labels, (255, 90, 60)))
            if self.part_labels:
                T.append(s2d.color(self.part_labels, (20, 200, 20)))
            if self.traces:
                T.append(s2d.color(self.traces, (125, 90, 60)))
            return T
        else:
            return self.traces,

    def __iadd__(self, rhs):
        if isinstance(rhs, Component):
            self.components.append(rhs)
        elif isinstance(rhs, Connection):
            self.connections.append(rhs)
        else:
            raise TypeError("Invalid type for PCB addition (%s)" % type(rhs))
        return self

    def connectH(self, *args, **kwargs):
        ''' Connects a set of pins or points, traveling first
            horizontally then vertically
        '''
        width = kwargs['width'] if 'width' in kwargs else 0.008
        points = []
        for A, B in zip(args[:-1], args[1:]):
            if not isinstance(A, BoundPin):     A = Point(*A)
            if not isinstance(B, BoundPin):     B = Point(*B)
            points.append(A)
            if (A.x != B.x):
                points.append(Point(B.x, A.y))
        if A.y != B.y:  points.append(B)
        self.connections.append(Connection(width, *points))

    def connectV(self, *args, **kwargs):
        ''' Connects a set of pins or points, travelling first
            vertically then horizontally.
        '''
        width = kwargs['width'] if 'width' in kwargs else 0.008
        points = []
        for A, B in zip(args[:-1], args[1:]):
            if not isinstance(A, BoundPin):     A = Point(*A)
            if not isinstance(B, BoundPin):     B = Point(*B)
            points.append(A)
            if (A.y != B.y):
                points.append(Point(A.x, B.y))
        if A.x != B.x:  points.append(B)
        self.connections.append(Connection(width, *points))

################################################################################

class Component(object):
    ''' Generic PCB component.
    '''
    def __init__(self, x, y, rot=0, name=''):
        ''' Constructs a Component object
                x           X position
                y           Y position
                rotation    angle (degrees)
                name        String
        '''
        self.x = x
        self.y = y
        self.rot   = rot

        self.name = name

    def __getitem__(self, i):
        if isinstance(i, str):
            try:
                pin = [p for p in self.pins if p.name == i][0]
            except IndexError:
                raise IndexError("No pin with name %s" % i)
        elif isinstance(i, int):
            try:
                pin = self.pins[i-1]
            except IndexError:
                raise IndexError("Pin %i is not in array" %i)
        return BoundPin(pin, self)

    @property
    def pads(self):
        pads = reduce(operator.add, [p.pad for p in self.pins])
        return s2d.move(s2d.rotate(pads, self.rot), self.x, self.y)

    @property
    def pin_labels(self):
        L = []
        for p in self.pins:
            p = BoundPin(p, self)
            if p.pin.name:
                L.append(text(p.pin.name, p.x, p.y, 0.03))
        return reduce(operator.add, L) if L else None

    @property
    def label(self):
        return text(self.name, self.x, self.y, 0.05)

################################################################################

class Pin(object):
    ''' PCB pin, with name, shape, and position
    '''
    def __init__(self, x, y, shape, name=''):
        self.x      = x
        self.y      = y
        self.shape  = shape
        self.name   = name

    @property
    def pad(self):
        return s2d.move(self.shape, self.x, self.y)

################################################################################

class BoundPin(object):
    ''' PCB pin localized to a specific component
        (so that it has correct x and y positions)
    '''
    def __init__(self, pin, component):
        self.pin = pin
        self.component = component

    @property
    def x(self):
        return (cos(radians(self.component.rot)) * self.pin.x -
                sin(radians(self.component.rot)) * self.pin.y +
                self.component.x)

    @property
    def y(self):
        return (sin(radians(self.component.rot)) * self.pin.x +
                cos(radians(self.component.rot)) * self.pin.y +
                self.component.y)

################################################################################

class Point(object):
    ''' Object with x and y member variables
    '''
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __iter__(self):
        return iter([self.x, self.y])

################################################################################

class Connection(object):
    ''' Connects two pins via a series of intermediate points
    '''
    def __init__(self, width, *args):
        self.width = width
        self.points = [
            a if isinstance(a, BoundPin) else Point(*a) for a in args
        ]

    @property
    def traces(self):
        t = []
        for p1, p2 in zip(self.points[:-1], self.points[1:]):
            d = sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
            if p2 != self.points[-1]:
                d += self.width/2
            a = atan2(p2.y - p1.y, p2.x - p1.x)
            r = s2d.rectangle(0, d, -self.width/2, self.width/2)
            t.append(s2d.move(s2d.rotate(r, degrees(a)), p1.x, p1.y))
        return reduce(operator.add, t)


################################################################################
# Discrete passive components
################################################################################

_pad_1206 = s2d.rectangle(-0.032, 0.032, -0.034, 0.034)

class R_1206(Component):
    ''' 1206 Resistor
    '''
    pins = [Pin(-0.06, 0, _pad_1206), Pin(0.06, 0, _pad_1206)]
    prefix = 'R'

class C_1206(Component):
    ''' 1206 Capacitor
    '''
    pins = [Pin(-0.06, 0, _pad_1206), Pin(0.06, 0, _pad_1206)]
    prefix = 'C'


################################################################################
# Connectors
################################################################################

_pad_USB_trace = s2d.rectangle(-0.0075, 0.0075, -0.04, 0.04)
_pad_USB_foot  = s2d.rectangle(-0.049, 0.049, -0.043, 0.043)
class USB_mini_B(Component):
    ''' USB mini B connector
        Hirose UX60-MB-5ST
    '''
    pins = [
        Pin(0.063,   0.36, _pad_USB_trace, 'G'),
        Pin(0.0315,  0.36, _pad_USB_trace),
        Pin(0,       0.36, _pad_USB_trace, '+'),
        Pin(-0.0315, 0.36, _pad_USB_trace, '-'),
        Pin(-0.063,  0.36, _pad_USB_trace, 'V'),

        Pin( 0.165, 0.33, _pad_USB_foot),
        Pin(-0.165, 0.33, _pad_USB_foot),
        Pin( 0.165, 0.12, _pad_USB_foot),
        Pin(-0.165, 0.12, _pad_USB_foot)
    ]
    prefix = 'J'

_pad_header  = s2d.rectangle(-0.06, 0.06, -0.025, 0.025)
class Header_4(Component):
    ''' 4-pin header
        fci 95278-101a04lf bergstik 2x2x0.1
    '''
    pins = [
        Pin(-0.107,  0.05, _pad_header),
        Pin(-0.107, -0.05, _pad_header),
        Pin( 0.107, -0.05, _pad_header),
        Pin( 0.107,  0.05, _pad_header)
    ]
    prefix = 'J'

class Header_ISP(Component):
    ''' ISP programming header
        FCI 95278-101A06LF Bergstik 2x3x0.1
    '''
    pins = [
        Pin(-0.107, 0.1,  _pad_header, 'GND'),
        Pin(-0.107, 0,    _pad_header, 'MOSI'),
        Pin(-0.107, -0.1, _pad_header, 'V'),
        Pin( 0.107, -0.1, _pad_header, 'MISO'),
        Pin( 0.107, 0,    _pad_header, 'SCK'),
        Pin( 0.107, 0.1,  _pad_header, 'RST')
    ]
    prefix = 'J'

class Header_FTDI(Component):
    ''' FTDI cable header
    '''
    pins = [
        Pin(0,  0.25, _pad_header, 'GND'),
        Pin(0,  0.15, _pad_header, 'CTS'),
        Pin(0,  0.05, _pad_header, 'VCC'),
        Pin(0, -0.05, _pad_header, 'TX'),
        Pin(0, -0.15, _pad_header, 'RX'),
        Pin(0, -0.25, _pad_header, 'RTS')
    ]
    prefix = 'J'


################################################################################
# SOT-23 components
################################################################################

_pad_SOT23 = s2d.rectangle(-.02,.02,-.012,.012)
class NMOS_SOT23(Component):
    ''' NMOS transistor in SOT23 package
        Fairchild NDS355AN
    '''
    pins = [
        Pin(0.045, -0.0375, 'G'),
        Pin(0.045,  0.0375, 'S'),
        Pin(-0.045, 0, 'D')
    ]
    prefix = 'Q'

class PMOS_SOT23(Component):
    ''' PMOS transistor in SOT23 package
        Fairchild NDS356AP
    '''
    pins = [
        Pin(-0.045, -0.0375, 'G'),
        Pin(-0.045,  0.0375, 'S'),
        Pin(0.045, 0, 'D')
    ]
    prefix = 'Q'

class Regulator_SOT23(Component):
    '''  SOT23 voltage regulator
    '''
    pins = [
        Pin(-0.045, -0.0375, 'Out'),
        Pin(-0.045,  0.0375, 'In'),
        Pin(0.045, 0, 'GND')
    ]
    prefix = 'U'


################################################################################
# Atmel microcontrollers
################################################################################

_pad_SOIC = s2d.rectangle(-0.041, 0.041, -0.015, 0.015)
class ATtiny45_SOIC(Component):
    pins = []
    y = 0.075
    for t in ['RST', 'PB3', 'PB4', 'GND']:
        pins.append(Pin(-0.14, y, _pad_SOIC, t))
        y -= 0.05
    for p in ['PB0', 'PB1', 'PB2', 'VCC']:
        y += 0.05
        pins.append(Pin(0.14, y, _pad_SOIC, t))
    del y
    prefix = 'U'

class ATtiny44_SOIC(Component):
    pins = []
    y = 0.15
    for t in ['VCC', 'PB0', 'PB1', 'PB3', 'PB2', 'PA7', 'PA6']:
        pad = _pad_SOIC + s2d.circle(-0.041, 0, 0.015) if t == 'VCC' else _pad_SOIC
        pins.append(Pin(-0.12, y, pad, t))
        y -= 0.05
    for t in ['PA5', 'PA4', 'PA3', 'PA2', 'PA1', 'PA0', 'GND']:
        y += 0.05
        pins.append(Pin(0.12, y, _pad_SOIC, t))
    prefix = 'U'

_pad_TQFP_h = s2d.rectangle(-0.025, 0.025, -0.008, 0.008)
_pad_TQFP_v = s2d.rectangle(-0.008, 0.008, -0.025, 0.025)

class ATmega88_TQFP(Component):
    pins = []
    y = 0.1085
    for t in ['PD3', 'PD4', 'GND', 'VCC', 'GND', 'VCC', 'PB6', 'PB7']:
        pins.append(Pin(-0.18, y, _pad_TQFP_h, t))
        y -= 0.031
    x = -0.1085
    for t in ['PD5', 'PD6', 'PD7', 'PB0', 'PB1', 'PB2', 'PB3', 'PB4']:
        pins.append(Pin(x, -0.18, _pad_TQFP_v, t))
        x += 0.031
    y = -0.1085
    for t in ['PB5', 'AVCC', 'ADC6', 'AREF', 'GND', 'ADC7', 'PC0', 'PC1']:
        pins.append(Pin(0.18, y, _pad_TQFP_h, t))
        y += 0.031
    x = 0.1085
    for t in ['PC2', 'PC3', 'PC4', 'PC5', 'PC6', 'PD0', 'PD1', 'PD2']:
        pins.append(Pin(x, 0.18, _pad_TQFP_v, t))
        x -= 0.031
    del x, y
    prefix = 'U'
    

