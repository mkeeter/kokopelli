import  math
import  inspect

import  wx

import  koko
from    koko.prims.evaluator import Evaluator, NameEvaluator
from    koko.prims.editpanel import EditPanel

################################################################################

class PrimSet(object):

    class PrimDict(object):
        def __init__(self, L):  self.L = L
        def __getitem__(self, name):
            if name in dir(math):   return getattr(math, name)
            found = [s for s in self.L if s.name == name]
            if found:   return found[0]
            else:       raise KeyError(name)

    def __init__(self, reconstructor=None):
        self.shapes = []
        self.map = PrimSet.PrimDict(self.shapes)
        if reconstructor:
            self.reconstruct(reconstructor)
        self.undo_stack = [[]]

    def add(self, s):
        if isinstance(s, list): self.shapes += s
        else:                   self.shapes.append(s)

    ########################################

    def reconstructor(self):
        '''Returns a set of reconstructor objects, used to regenerate
           a set of primitives.'''
        return [s.reconstructor() for s in self.shapes]

    def to_script(self):
        ''' Returns a string that can be embedded in a script;
            this is the same as a normal reconstructor, but classes
            have been replaced by their names.'''
        r = [s.reconstructor() for s in self.shapes]
        def clsname(cls):
            return cls.__module__ + '.' + cls.__name__
        r = [(clsname(q[0]), q[1]) for q in r]
        return '[' + ','.join('(%s, %s)' % q for q in r) + ']'

    ########################################

    def reconstruct(self, R):
        ''' Reload the set of shapes from a reconstructor object.
            Returns self.'''
        self.clear()
        for r in R:
            self.shapes += [r[0](**r[1])]

    ########################################

    def clear(self):
        ''' Delete all shapes. '''
        while self.shapes:
            self.delete(self.shapes[0])

    ########################################

    def delete(self, s):
        ''' Delete a particular shape.'''

        if s in self.shapes:
            s.deleted = True
            s.close_panel()
            self.shapes.remove(s)

            self.modified = True
        elif hasattr(s, 'parent'):
            self.delete(s.parent)

    ########################################

    def mouse_pos(self, x, y):
        ''' Update the hover state of nodes based on mouse movement,
            returning True if anything changed (which implies a redraw). '''

        return True

        t = self.get_target(x, y)
        changed = False
        for s in self.shapes:
            if s == t:  continue
            if s.hover: changed = True
            s.hover = False

        if t:
            if not t.hover: changed = True
            t.hover = True

        return changed

    ########################################

    def get_target(self, x, y):
        ''' Returns the shape at the given x,y coordinates
            with the lowest priority. '''

        r = 10/koko.CANVAS.scale
        found = [f for f in [s.intersects(x, y, r) for s in self.shapes]
                 if f is not None]
        if all(f is None for f in found):   return None
        min_rank = min(f.priority for f in found if f is not None)
        return [f for f in found if f.priority == min_rank][0]

    ########################################

    def draw(self, canvas):
        for s in self.shapes:
            if s.panel: s.panel.slide()

        ranked = {}
        for s in self.shapes:
            ranked[s.priority] = ranked.get(s.priority, []) + [s]
        for k in sorted(ranked.keys())[::-1]:
            for s in ranked[k]:
                s.draw(canvas)

        for s in self.shapes:
            if (s.hover or s.dragging) and not s.panel:
                s.draw_label(canvas)

    ########################################

    def push_stack(self):
        ''' Stores a reconstructor on the stack for undo functionality.'''
        R = self.reconstructor()
        if self.undo_stack == [] or R != self.undo_stack[-1]:
            self.undo_stack.append(R)
            koko.APP.savepoint(False)

    def undo(self, event=None):
        ''' Undoes the last operation.

            (He sees what's left of the Rippling Walls,
             years of work undone in an instant.)'''
        R = self.reconstructor()

        try:                target = [s for s in self.shapes if s.panel][0]
        except IndexError:  target = None

        if R != self.undo_stack[-1]:
            self.reconstruct(self.undo_stack[-1])
        elif len(self.undo_stack) >= 2:
            self.reconstruct(self.undo_stack[-2])
            self.undo_stack = self.undo_stack[:-1]

        # If we find a shape in the restored set with the same name
        # as the one with an open panel initially, then re-open the
        # panel
        try:    target = [s for s in self.shapes if s.name == target.name][0]
        except (IndexError, AttributeError):    pass
        else:   target.open_panel()

        koko.APP.savepoint(False)
        koko.APP.mark_changed_design()

    @property
    def can_undo(self):
        return (len(self.undo_stack) >= 2 or
                self.reconstructor() != self.undo_stack[-1])

    ########################################

    def get_name(self, prefix, count=1, i=0):
        '''Returns a non-colliding name with the given prefix.'''

        names = [s.name for s in self.shapes]
        results = []
        while len(results) < count:
            while '%s%i' % (prefix, i) in names:
                i += 1
            results.append('%s%i' % (prefix, i))
            names.append(results[-1])

        return results[0] if count == 1 else results

    ########################################

    def update_panels(self):
        for p in [s.panel for s in self.shapes if s.panel]:
            p.update()

    def close_panels(self):
        for s in self.shapes: s.close_panel()

    ########################################

    @property
    def dict(self):
        return dict((s.name, s) for s in self.shapes)

################################################################################

class Primitive(object):
    '''Defines a geometric object that the user can interact with.'''

    def __init__(self, name='primitive'):

        self.parameters = {'name': NameEvaluator(name)}

        # Variables related to user interaction.
        self.deleted    = False

        self.panel      = None

        # Priority for selection (lower is more important)
        self.priority = 0

    @property
    def name(self):
        ''' Returns the primitive's name.'''
        return self.parameters['name'].eval()

    @property
    def valid(self):
        '''Returns true if all parameters are valid.'''
        return all(p.valid for p in self.parameters.itervalues())

    @property
    def modified(self):
        ''' Returns true if any parameters are modified.'''
        return any(p.modified for p in self.parameters.itervalues())

    @modified.setter
    def modified(self, value):
        ''' Sets the modified flag of each parameter to the provided value.'''
        for p in self.parameters.itervalues():
            p.modified = value

    # Child classes should redefine these to appropriate values.
    @property
    def x(self): return 0
    @property
    def y(self): return 0

    @property
    def hover(self):
        x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                          koko.CANVAS.GetScreenPosition()))
        r = 5 / koko.CANVAS.scale
        return self.intersects(x, y, r) == self

    @property
    def dragging(self):
        return koko.CANVAS.drag_target == self

    def drag(self, dx, dy):
        ''' This function should drag a point by the given offsets.'''
        pass

    def reconstructor(self):
        ''' Function that defines how to reconstruct this object.

            Returns a tuple containing the object class and a
            dictionary mapping parameter names to their expressions.'''

        argspec = inspect.getargspec(self.__class__.__init__)
        args = argspec.args[1:]
        return (self.__class__,
                dict((k, self.parameters[k].expr) for k in self.parameters
                if k in args))


    def create_evaluators(self, **kwargs):
        ''' Create a set of evaluators with initial values and types.

            Arguments should be of the form
                name = (expression, type)
            e.g.
                child = ('otherPoint', Point)
                x = (12.3, float)

            The evaluators live in self.parameters, and are also added
            to the class as a property (so they can be accessed as
            self.child, self.x, etc.)
           '''

        for arg in kwargs.keys():

            # Create an evaluator with initial expression and desired type
            self.parameters[arg] = Evaluator(*kwargs[arg])

            # Create a property to automatically get a value from
            # the evaluator.  The lambda is a bit strange looking to
            # prevent problems with for loop variable binding.
            prop = property(lambda instance, p=arg:
                                instance.parameters[p].eval())
            setattr(self.__class__, arg, prop)

    def draw_label(self, canvas):
        ''' Labels this node with its name.'''

        x, y = canvas.pos_to_pixel(self.x, self.y)

        canvas.dc.SetFont(wx.Font(12 + 4*self.priority,
                                  wx.FONTFAMILY_DEFAULT,
                                  wx.FONTSTYLE_NORMAL,
                                  wx.FONTWEIGHT_NORMAL))

        w, h = canvas.dc.GetTextExtent(self.name)

        canvas.dc.SetBrush(wx.Brush((0, 0, 0, 150)))
        canvas.dc.SetPen(wx.TRANSPARENT_PEN)
        canvas.dc.DrawRectangle(x, y - h - 10, w + 10, h+10)

        canvas.dc.SetTextForeground((255,255,255))
        canvas.dc.DrawText(self.name, x + 5, y - h - 5)

    def close_panel(self, event=None):

        # Close the panel itself
        if self.panel:
            koko.PRIMS.push_stack()
            self.panel.Destroy()
        self.panel = None
        koko.CANVAS.Refresh()

    def open_panel(self, event=None):
        self.close_panel()
        self.panel = EditPanel(self)
        koko.CANVAS.Refresh()
