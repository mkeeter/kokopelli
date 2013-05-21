import math

from koko.c.interval    import Interval
from koko.fab.tree      import MathTree, X, Y, Z, matching

################################################################################

def circle(x0, y0, r):

    # sqrt((X-x0)**2 + (Y-y0)**2) - r
    r = abs(r)
    s = MathTree('-r+q%sq%sf%g' % (('-Xf%g' % x0) if x0 else 'X',
                                   ('-Yf%g' % y0) if y0 else 'Y', r))

    s.xmin, s.xmax = x0-r, x0+r
    s.ymin, s.ymax = y0-r, y0+r

    s.shape = True
    return s

################################################################################

def triangle(x0, y0, x1, y1, x2, y2):
    def edge(x, y, dx, dy):
        # dy*(X-x)-dx*(Y-y)
        return '-*f%(dy)g-Xf%(x)g*f%(dx)g-Yf%(y)g' % locals()

    e0 = edge(x0, y0, x1-x0, y1-y0)
    e1 = edge(x1, y1, x2-x1, y2-y1)
    e2 = edge(x2, y2, x0-x2, y0-y2)

    # -min(e0, min(e1, e2))
    s = MathTree('ni%(e0)si%(e1)s%(e2)s' % locals())

    s.xmin, s.xmax = min(x0, x1, x2), max(x0, x1, x2)
    s.ymin, s.ymax = min(y0, y1, y2), max(y0, y1, y2)

    s.shape = True
    return s

################################################################################

def rectangle(x0, x1, y0, y1):
    # max(max(x0 - X, X - x1), max(y0 - Y, Y - y1)
    s = MathTree('aa-f%(x0)gX-Xf%(x1)ga-f%(y0)gY-Yf%(y1)g' % locals())

    s.xmin, s.xmax = x0, x1
    s.ymin, s.ymax = y0, y1

    s.shape = True
    return s

def rounded_rectangle(x0, x1, y0, y1, r):
    r *= min(x1 - x0, y1 - y0)/2
    return (
        rectangle(x0, x1, y0+r, y1-r) +
        rectangle(x0+r, x1-r, y0, y1) +
        circle(x0+r, y0+r, r) +
        circle(x0+r, y1-r, r) +
        circle(x1-r, y0+r, r) +
        circle(x1-r, y1-r, r)
    )

################################################################################

def tab(x, y, width, height, angle=0, chamfer=0.2):
    tab = rectangle(-width/2, width/2, 0, height)
    cutout = triangle(width/2 - chamfer*height, height,
                      width/2, height,
                      width/2, height - chamfer*height)
    tab -= cutout + reflect_x(cutout)

    return move(rotate(tab, angle), x, y)

################################################################################

def slot(x, y, width, height, angle=0, chamfer=0.2):
    slot = rectangle(-width/2, width/2, -height, 0)
    inset = triangle(width/2, 0,
                     width/2 + height * chamfer, 0,
                     width/2, -chamfer*height)
    slot += inset + reflect_x(inset)

    return move(rotate(slot, angle), x, y)

################################################################################

def move(part, dx, dy, dz=0):
    p = part.map('-Xf%g' % dx if dx else None,
                 '-Yf%g' % dy if dy else None,
                 '-Zf%g' % dz if dz else None)
    if part.dx: p.xmin, p.xmax = part.xmin + dx, part.xmax + dx
    if part.dy: p.ymin, p.ymax = part.ymin + dy, part.ymax + dy
    if part.dz: p.zmin, p.zmax = part.zmin + dz, part.zmax + dz

    return p

################################################################################

def rotate(part, angle):

    angle *= math.pi/180
    ca, sa = math.cos(angle), math.sin(angle)
    nsa    = -sa

    p = part.map(X='+*f%(ca)gX*f%(sa)gY'  % locals(),
                 Y='+*f%(nsa)gX*f%(ca)gY' % locals())

    ca, sa = math.cos(-angle), math.sin(-angle)
    nsa    = -sa
    p.bounds = part.map_bounds(X='+*f%(ca)gX*f%(sa)gY'  % locals(),
                               Y='+*f%(nsa)gX*f%(ca)gY' % locals())

    return p

################################################################################

def reflect_x(part, x0=0):

    # X' = 2*x0-X
    p = part.map(X='-*f2f%gX' % x0 if x0 else 'nX')

    # X  = 2*x0-X'
    p.bounds = part.map_bounds(X='-*f2f%gX' % x0 if x0 else 'nX')
    return p

def reflect_y(part, y0=0):

    # Y' = 2*y0-Y
    p = part.map(Y='-*f2f%gY' % y0 if y0 else 'nY')

    # Y  = 2*y0-Y'
    p.bounds = part.map_bounds(Y='-*f2f%gY' % y0 if y0 else 'nY')
    return p

def reflect_xy(part):
    p = part.map(X='Y', Y='X')
    p.bounds = part.map_bounds(X='Y', Y='X')
    return p

################################################################################

def scale_x(part, x0, sx):

    # X' = x0 + (X-x0)/sx
    p = part.map(X='+f%(x0)g/-Xf%(x0)gf%(sx)g' % locals()
                    if x0 else '/Xf%g' % sx)

    # X  = (X'-x0)*sx + x0
    p.bounds = part.map_bounds(X='+f%(x0)g*f%(sx)g-Xf%(x0)g' % locals()
                               if x0 else '*Xf%g' % sx)
    return p

def scale_y(part, y0, sy):

    # Y' = y0 + (Y-y0)/sy
    p = part.map(Y='+f%(y0)g/-Yf%(y0)gf%(sy)g' % locals()
                    if y0 else '/Yf%g' % sy)

    # Y  = (Y'-y0)*sy + y0
    p.bounds = part.map_bounds(Y='+f%(y0)g*f%(sy)g-Yf%(y0)g' % locals()
                               if y0 else '*Yf%g' % sy)

    return p

def scale_xy(part, x0, y0, sxy):

    # X' = x0 + (X-x0)/sx
    # Y' = y0 + (Y-y0)/sy
    p = part.map(X='+f%(x0)g/-Xf%(x0)gf%(sxy)g' % locals()
                    if x0 else '/Xf%g' % sxy,
                 Y='+f%(y0)g/-Yf%(y0)gf%(sxy)g' % locals()
                    if y0 else '/Yf%g' % sxy)

    # X  = (X'-x0)*sx + x0
    # Y  = (Y'-y0)*sy + y0
    p.bounds = part.map_bounds(X='+f%(x0)g*f%(sxy)g-Xf%(x0)g' % locals()
                               if x0 else '*Xf%g' % sxy,
                               Y='+f%(y0)g*f%(sxy)g-Yf%(y0)g' % locals()
                               if y0 else '*Yf%g' % sxy)
    return p

################################################################################

def shear_x_y(part, y0, y1, dx0, dx1):

    dx = dx1 - dx0
    dy = y1 - y0

    # X' = X-dx0-dx*(Y-y0)/dy
    p = part.map(X='--Xf%(dx0)g/*f%(dx)g-Yf%(y0)gf%(dy)g' % locals())

    # X  = X'+dx0+(dx)*(Y-y0)/dy
    p.bounds = part.map_bounds(X='++Xf%(dx0)g/*f%(dx)g-Yf%(y0)gf%(dy)g'
                                  % locals())
    return p

################################################################################

def taper_x_y(part, x0, y0, y1, s0, s1):

    dy = y1 - y0
    ds = s1 - s0
    s0y1 = s0 * y1
    s1y0 = s1 * y0

    #   X'=x0+(X-x0)*(y1-y0)/(Y*(s1-s0)+s0*y1-s1*y0))
    X = '+f%(x0)g/*-Xf%(x0)gf%(dy)g-+*Yf%(ds)gf%(s0y1)gf%(s1y0)g' % locals()
    p = part.map(X=X)

    #   X=(X'-x0)*(Y*(s1-s0)+s0*y1-s1*y0)/(y1-y0)+x0
    p.bounds = part.map_bounds(
        X='+f%(x0)g*-Xf%(x0)g/-+*Yf%(ds)gf%(s0y1)gf%(s1y0)gf%(dy)g'
           % locals())

    return p

################################################################################

@matching
def blend(p0, p1, amount):
    if not p0.shape or not p1.shape:
        raise TypeError('Arguments must be math objects with shape=True')
    joint = p0 + p1

    # sqrt(abs(p0)) + sqrt(abs(p1)) - amount
    fillet = MathTree('-+rb%srb%sf%g' % (p0.math, p1.math, amount),
                      shape=True)
    out = joint + fillet
    out.bounds = [b for b in joint.bounds]

    return out

################################################################################

def color(part, rgb):
    p = part.clone()
    p.color = rgb
    return p
