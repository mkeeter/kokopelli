""" Module defining a container class for CAD state and settings """

import operator

from koko.lib.shapes2d  import color
from koko.fab.tree      import MathTree

class FabVars(object):
    ''' Container class to hold CAD state and settings.'''
    def __init__(self):
        self.shapes      = None
        self.render_mode = None
        self.voxel_res   = None
        self.mm_per_unit = 25.4
        self.border      = 0.05

    @property
    def shapes(self):   return self._shapes
    @shapes.setter
    def shapes(self, value):
        if value is None:
            self._shapes = value
        elif type(value) in (list, tuple):
            for v in value:
                if type(v) is not MathTree:
                    raise TypeError(
                        'cad.shapes must be of type MathTree, not %s.'
                        % type(v))
            self._shapes = list(value)
        else:
            self._shapes = [MathTree.wrap(value)]

    @property
    def render_mode(self):
        return self._render_mode
    @render_mode.setter
    def render_mode(self, value):
        if value not in ['height','shaded',None]:
            raise TypeError("render_mode must be 'height' or 'shaded'")
        self._render_mode = value

    @property
    def mm_per_unit(self):
        return self._mm_per_unit
    @mm_per_unit.setter
    def mm_per_unit(self, value):
        try:
            self._mm_per_unit = float(value)
        except TypeError:
            raise TypeError("mm_per_unit should be a number.")

    @property
    def function(self):
        if len(self.shapes) > 1:
            return reduce(operator.add,
                [color(s, None) for s in self.shapes])
        elif self.shapes:
            return self.shapes[0]
        else:
            return None
    @function.setter
    def function(self, value):
        self.shapes = value

    @property
    def xmin(self):
        try:
            dx = (max(s.xmax for s in self.shapes) -
                  min(s.xmin for s in self.shapes))
            return min(s.xmin for s in self.shapes) - dx*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def xmax(self):
        try:
            dx = (max(s.xmax for s in self.shapes) -
                  min(s.xmin for s in self.shapes))
            return max(s.xmax for s in self.shapes) + dx*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def dx(self):
        try:    return self.xmax - self.xmin
        except TypeError:   return None

    @property
    def ymin(self):
        try:
            dy = (max(s.ymax for s in self.shapes) -
                  min(s.ymin for s in self.shapes))
            return min(s.ymin for s in self.shapes) - dy*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def ymax(self):
        try:
            dy = (max(s.ymax for s in self.shapes) -
                  min(s.ymin for s in self.shapes))
            return max(s.ymax for s in self.shapes) + dy*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def dy(self):
        try:    return self.ymax - self.ymin
        except TypeError:   return None

    @property
    def zmin(self):
        try:
            dz = (max(s.zmax for s in self.shapes) -
                  min(s.zmin for s in self.shapes))
            return min(s.zmin for s in self.shapes) - dz*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def zmax(self):
        try:
            dz = (max(s.zmax for s in self.shapes) -
                  min(s.zmin for s in self.shapes))
            return max(s.zmax for s in self.shapes) + dz*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def dz(self):
        try:    return self.zmax - self.zmin
        except TypeError:   return None

    @property
    def bounded(self):
        return all(getattr(self, b) is not None for b in
                    ['xmin','xmax','ymin','ymax','zmin','zmax'])


    def write(self, filename):
        ''' Saves to a .math file.
            'filename' should be either a string or an open file handle.'''


        text = '''format: Real
mm per unit: %f
dx dy dz: %f %f %f
xmin ymin zmin: %f %f %f
expression: %s''' %  (
        self.mm_per_unit,
        self.dx,   self.dy,   self.dz   if self.dz   else 0,
        self.xmin, self.ymin, self.zmin if self.zmin else 0,
        self.function)

        if type(filename) is str:
            with open(filename,'w') as f:
                f.write(text)
        else:
            filename.seek(0)
            filename.truncate(0)
            filename.write(text)
            filename.flush()
