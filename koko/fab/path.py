""" Module defining Path class for toolpaths and contours. """

import numpy as np

class Path(object):
    def __init__(self, points, closed=False):
        self.points = points
        self.closed = closed

    def set_z(self, z):
        self.points[:,2] = z

    def offset_z(self, dz):
        self.points[:,2] += dz

    def reverse(self):
        return Path(self.points[::-1], self.closed)

    def __getitem__(self, i):
        return self.points[i]

    def copy(self):
        return Path(self.points.copy(), self.closed)

    @classmethod
    def from_ptr(cls, ptr):
        ''' Imports a path from a path linked list structure.
        '''
        xyz = lambda p: [[p.contents.x, p.contents.y, p.contents.z]]

        start = ptr
        points = np.array(xyz(ptr))

        ptr = ptr.contents.next

        while ptr.contents != start.contents:
            points = np.vstack( (points, xyz(ptr)) )

            # Advance through the linked list
            if bool(ptr.contents.next): ptr = ptr.contents.next
            else:                       break

        closed = (ptr.contents == start.contents)

        return cls(points, closed)


    @property
    def xmin(self): return float(min(self.points[:,0]))
    @property
    def xmax(self): return float(max(self.points[:,0]))
    @property
    def dx(self):   return self.xmax - self.xmin

    @property
    def ymin(self): return float(min(self.points[:,1]))
    @property
    def ymax(self): return float(max(self.points[:,1]))
    @property
    def dy(self):   return self.ymax - self.ymin


    @staticmethod
    def sort(paths):
        ''' Sorts an array of paths such that contained paths
            are before the paths than contain then, and each
            stage greedily picks the nearest valid path to come next.
        '''
        # Create an array such that if before[i,j] is True, path i
        # needs to be cut before path j (because the bounds of path i
        # are contained within the bounds of path j).
        before = np.ones((len(paths), len(paths)), dtype=np.bool)
        xmin = np.array([[p.xmin for p in paths]]*len(paths))
        before &= xmin < xmin.transpose()
        xmax = np.array([[p.xmax for p in paths]]*len(paths))
        before &= xmax > xmax.transpose()
        ymin = np.array([[p.ymin for p in paths]]*len(paths))
        before &= ymin < ymin.transpose()
        ymax = np.array([[p.ymax for p in paths]]*len(paths))
        before &= ymax > ymax.transpose()

        sorted = []

        done = [False]*len(paths)
        pos = np.array([[0, 0]])

        for i in range(len(paths)):
            # Calculate the distances from our current path to the
            # startpoints of other paths (don't have anything before
            # them and aren't already done)
            distances = [
                float('inf') if (any(before[:,i]) or done[i])
                else sum(pow(pos - paths[i].points[0][0:2], 2).flatten())
                for i in range(len(paths))
            ]
            index = distances.index(min(distances))
            done[index] = True
            before[index,:] = False
            sorted.append(paths[index])

            # New position is the end of the path
            if sorted[-1].closed:   pos = sorted[-1].points[0][0:2]
            else:                   pos = sorted[-1].points[-1][0:2]

        return sorted

    @classmethod
    def save_merged_svg(cls, filename, paths, border=0):
        xmin = min(p.xmin for p in paths)
        xmax = max(p.xmax for p in paths)
        ymin = min(p.ymin for p in paths)
        ymax = max(p.ymax for p in paths)

        if border:
            dx = xmax - xmin
            xmin -= dx * border
            xmax += dx * border
            dy = ymax - ymin
            ymin -= dy * border
            ymax += dy * border

        cls.write_svg_header(filename, xmax-xmin, ymax-ymin)
        for p in paths:
            p.write_svg_contour(filename, xmin, ymax)
        cls.write_svg_footer(filename)

    def save_svg(self, filename):
        self.write_svg_header(filename, self.dx, self.dy)
        self.write_svg_contour(filename, self.xmin, self.ymin)
        self.write_svg_footer(filename)

    @classmethod
    def write_svg_header(cls, filename, dx, dy):
        ''' Writes the header to an SVG file.
            dx and dy should be in mm.
        '''
        with open(filename, 'wb') as f:
            f.write(
"""<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>
<!-- Created with kokopelli (kokompe.cba.mit.edu) -->
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg
    xmlns   = "http://www.w3.org/2000/svg"
    width   = "{dx:g}mm"
    height  = "{dy:g}mm"
    units   = "mm"
>""".format(dx=dx, dy=dy))


    @classmethod
    def write_svg_footer(cls, filename):
        ''' Writes the footer to an SVG file.
        '''
        with open(filename, 'a') as f:  f.write('</svg>')


    def write_svg_contour(self, filename, xmin, ymax,
                          stroke=0.1, color=(0,0,0)):
        ''' Saves a single SVG contour at 90 DPI.
        '''
        scale = 90/25.4

        xy = lambda p: (scale*(p[0]-xmin), scale*(ymax-p[1]))

        with open(filename, 'a') as f:

            # Write the opening statement for this path
            f.write(
'  <path style="stroke:rgb(%i,%i,%i); stroke-width:%g; fill:none"'
                % (color[0], color[1], color[2], stroke)
            )

            # Write the first point of the path
            f.write(
'        d="M%g %g' % xy(self.points[0])
            )

            # Write the rest of the points
            for pt in self.points[1:]:  f.write(' L%g %g' % xy(pt))

            if self.closed: f.write(' Z')
            f.write('"/>\n')
