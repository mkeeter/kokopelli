import math

from koko.c.interval    import Interval
from koko.fab.tree      import MathTree, X, Y, Z, matching

import koko.lib.shapes2d as s2d

################################################################################

def extrusion(part, z0, z1):
    # max(part, max(z0-Z, Z-z1))
    s = MathTree('a%sa-f%gZ-Zf%g' % (part.math, z0, z1))
    s.bounds = part.bounds[0:4] + [z0, z1]
    s.shape = True
    s.color = part.color
    return s

def cylinder(x0, y0, z0, z1, r):
    return extrusion(s2d.circle(x0, y0, r), z0, z1)

def sphere(x0, y0, z0, r):
    s = MathTree('-r++q%sq%sq%sf%g' % (('-Xf%g' % x0) if x0 else 'X',
                                       ('-Yf%g' % y0) if y0 else 'Y',
                                       ('-Zf%g' % z0) if z0 else 'Z',
                                       r))
    s.xmin, s.xmax = x0-r, x0+r
    s.ymin, s.ymax = y0-r, y0+r
    s.zmin, s.zmax = z0-r, z0+r
    s.shape = True
    return s

def cube(x0, x1, y0, y1, z0, z1):
    return extrusion(s2d.rectangle(x0, x1, y0, y1), z0, z1)

def cone(x0, y0, z0, z1, r):
    cyl = cylinder(x0, y0, z0, z1, r)
    return taper_xy_z(cyl, x0, y0, z0, z1, 1.0, 0.0)

def pyramid(x0, x1, y0, y1, z0, z1):
    c = cube(x0, x1, y0, y1, z0, z1)
    return taper_xy_z(c, (x0+x1)/2., (y0+y1)/2., z0, z1, 1.0, 0.0)

################################################################################

move = s2d.move

def rotate_x(part, angle):

    angle *= math.pi/180
    ca, sa = math.cos(angle), math.sin(angle)
    nsa    = -sa

    p = part.map(Y='+*f%(ca)gY*f%(sa)gZ'  % locals(),
                 Z='+*f%(nsa)gY*f%(ca)gZ' % locals())

    ca, sa = math.cos(-angle), math.sin(-angle)
    nsa    = -sa
    p.bounds = part.map_bounds(Y='+*f%(ca)gY*f%(sa)gZ' % locals(),
                               Z='+*f%(nsa)gY*f%(ca)gZ' % locals())
    return p

def rotate_y(part, angle):

    angle *= math.pi/180
    ca, sa = math.cos(angle), math.sin(angle)
    nsa    = -sa

    p = part.map(X='+*f%(ca)gX*f%(sa)gZ'  % locals(),
                 Z='+*f%(nsa)gX*f%(ca)gZ' % locals())

    ca, sa = math.cos(-angle), math.sin(-angle)
    nsa    = -sa

    p.bounds = part.map_bounds(X='+*f%(ca)gX*f%(sa)gZ' % locals(),
                               Z='+*f%(nsa)gX*f%(ca)gZ' % locals())
    return p

rotate_z = s2d.rotate

################################################################################

reflect_x = s2d.reflect_x
reflect_y = s2d.reflect_y

def reflect_z(part, z0=0):
    p = part.map(Z='-*f2f%gZ' % z0 if z0 else 'nZ')
    p.bounds = part.map_bounds(Z='-*f2f%gZ' % z0 if z0 else 'nZ')
    return p

reflect_xy = s2d.reflect_xy
def reflect_xz(part):
    p = part.map(X='Z', Z='X')
    p.bounds = part.map_bounds(X='Z', Z='X')
    return p

def reflect_yz(part):
    p = part.map(Y='Z', Z='Y')
    p.bounds = part.map_bounds(Y='Z', Z='Y')
    return p

################################################################################

scale_x = s2d.scale_x
scale_y = s2d.scale_y

def scale_z(part, z0, sz):
    p = part.map(Z='+f%(z0)g/-Zf%(z0)gf%(sz)g' % locals()
                    if z0 else '/Zf%g' % sz)
    p.bounds = part.map_bounds(Z='+f%(z0)g*f%(sz)g-Zf%(z0)g' % locals()
                               if z0 else '*Zf%g' % sz)
    return p

################################################################################

shear_x_y = s2d.shear_x_y

def shear_x_z(part, z0, z1, dx0, dx1):

    #   X' = X-dx0-(dx1-dx0)*(Z-z0)/(z1-z0)
    p = part.map(X='--Xf%(dx0)g/*f%(dx)g-Zf%(z0)gf%(dz)g' % locals())

    #   X = X'+dx0+(dx1-dx0)*(Z-z0)/(z1-z0)
    p.bounds = part.map_bounds(X='++Xf%(dx0)g/*f%(dx)g-Zf%(z0)gf%(dz)g'
                                  % locals())
    return p

################################################################################

taper_x_y = s2d.taper_x_y

def taper_xy_z(part, x0, y0, z0, z1, s0, s1):

    dz = z1 - z0

    # X' =  x0 +(X-x0)*dz/(s1*(Z-z0) + s0*(z1-Z))
    # Y' =  y0 +(Y-y0)*dz/(s1*(Z-z0) + s0*(z1-Z))
    p = part.map(
        X='+f%(x0)g/*-Xf%(x0)gf%(dz)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZ'
            % locals(),
        Y='+f%(y0)g/*-Yf%(y0)gf%(dz)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZ'
            % locals())

    # X  = (X' - x0)*(s1*(Z-z0) + s0*(z1-Z))/dz + x0
    # Y  = (Y' - y0)*(s1*(Z-z0) + s0*(z1-Z))/dz + y0
    p.bounds = part.map_bounds(
        X='+/*-Xf%(x0)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZf%(dz)gf%(x0)g'
            % locals(),
        Y='+/*-Yf%(y0)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZf%(dz)gf%(y0)g'
            % locals())

    return p

################################################################################

def revolve_y(part):
    ''' Revolve a part in the XY plane about the Y axis. '''
    #   X' = sqrt(X**2 + Z**2)
    p = part.map(X='r+qXqZ')

    if part.bounds[0] and part.bounds[1]:
        p.xmin = min(-abs(part.xmin), -abs(part.xmax))
        p.xmax = max( abs(part.xmin),  abs(part.xmax))
        p.ymin, p.ymax = part.ymin, part.ymax
        p.zmin, p.zmax = p.xmin, p.xmax
    return p


def revolve_x(part):
    ''' Revolve a part in the XY plane about the X axis. '''
    #   Y' = sqrt(Y**2 + Z**2)
    p = part.map(Y='r+qYqZ')

    if part.bounds[0] and part.bounds[1]:
        p.xmin, p.xmax = part.xmin, part.xmax
        p.ymin = min(-abs(part.ymin), -abs(part.ymax))
        p.ymax = max( abs(part.ymin),  abs(part.ymax))
        p.zmin, p.zmax =  p.ymin, p.ymax
    return p

################################################################################

@matching
def loft(p0, p1, z0, z1):
    if not p0.shape or not p1.shape:
        raise TypeError('Arguments must be math objects with shape=True')
    """
    (((Z-z1)*(Z-z2)/((z0-z1)*(z0-z2))+
    0.5*(Z-z0)*(Z-z2)/((z1-z0)*(z1-z2)))*(part0)+
    (0.5*(Z-z0)*(Z-z2)/((z1-z0)*(z1-z2))+
    (Z-z0)*(Z-z1)/((z2-z0)*(z2-z1)))*(part1))
    """
