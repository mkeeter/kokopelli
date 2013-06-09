""" Module defining a container class for CAD state and settings """

import operator

from koko.lib.shapes2d  import color
from koko.fab.tree      import MathTree

class FabVars(object):
    ''' Container class to hold CAD state and settings.'''
    def __init__(self):
        self._shapes     = []
        self._shape      = None
        self.render_mode = None
        self.mm_per_unit = 25.4
        self.border      = 0.05

    @property
    def shapes(self):   return self._shapes
    @shapes.setter
    def shapes(self, value):
        if type(value) not in (list, tuple):
            raise TypeError('cad.shapes must be a list or tuple of MathTree objects')
        value = map(MathTree.wrap, value)
        self._shapes = list(value)
        self._shape = reduce(operator.add,
            [color(s, None) for s in self.shapes]
        )

    @property
    def shape(self):    return self._shape
    @shape.setter
    def shape(self, value): self.shapes = [MathTree.wrap(value)]
    @property
    def function(self): return self.shape
    @function.setter
    def function(self, value):  self.shape = value

    @property
    def render_mode(self):
        return self._render_mode
    @render_mode.setter
    def render_mode(self, value):
        if value not in ['2D','3D',None]:
            raise TypeError("render_mode must be '2D' or '3D'")
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

