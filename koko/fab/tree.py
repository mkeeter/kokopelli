""" Module defining MathTree class and helper decorators. """

import  ctypes
import  os, sys
import  threading
import  math
import  Queue

from    koko.c.libfab       import libfab
from    koko.c.interval     import Interval
from    koko.c.region       import Region
from    koko.c.multithread  import multithread

################################################################################

def threadsafe(f):
    ''' A decorator that locks the arguments to a function,
        invokes the function, then unlocks the arguments and
        returns.'''
    def wrapped(*args, **kwargs):
        for a in set(list(args) + kwargs.values()):
            if isinstance(a, MathTree):
                a.lock()
        result = f(*args, **kwargs)
        for a in set(list(args) + kwargs.values()):
            if isinstance(a, MathTree):
                a.unlock()
        return result
    return wrapped

def forcetree(f):
    ''' A decorator that forces function arguments to be
        of MathTree type using MathTree.wrap

        Takes a class method (with cls as its first argument)'''
    def wrapped(*args, **kwargs):
        return f(args[0], *[MathTree.wrap(a) for a in args[1:]],
                 **{a:MathTree.wrap(kwargs[a]) for a in kwargs})
    return wrapped

def matching(f):
    ''' A decorator that ensures that MathTree properties
        (e.g. color) match across all shape inputs, raising an
        exception otherwise. '''
    def wrapped(*args):
        colors = set(a.color for a in args if isinstance(a, MathTree)
                                           and a.shape                                        and a.color is not None)
        if len(colors) > 1:
            raise ValueError(
                'Error:  Cannot combine objects with different colors.')
        out = f(*args)
        if colors:  out.color = colors.pop()
        return out
    return wrapped

################################################################################

class MathTree(object):
    """ @class MathTree
        @brief Represents a distance metric math expression.

        @details
        Arithmetic operators are overloaded to extend the tree with
        either distance metric arithmetic or shape logical expressions,
        depending on the value of the instance variable 'shape'
    """

    def __init__(self, math, shape=False, color=None):
        """ @brief MathTree constructor
            @param math Math string (in prefix notation)
            @param shape Boolean modifying arithmetic operators
            @param color Color tuple or None
        """

        ## @var math
        # Math string (in sparse prefix syntax)
        self.math   = math

        ## @var shape
        # Boolean modify the behavior of arithmetic operators
        self.shape  = shape

        ## @var color
        # Assigned color, or None
        self.color  = color

        self._ptr    = None

        ## @var bounds
        # X, Y, Z bounds (or None)
        self.bounds  = [None]*6

        self._str   = None
        self._lock  = threading.Lock()

    def __del__(self):
        """ @brief MathTree destructor """
        if self._ptr is not None and libfab is not None:
            libfab.free_tree(self.ptr)

    def lock(self):
        """ @brief Locks the MathTree to prevent interference from other threads
        """
        self._lock.acquire()
    def unlock(self):
        """ @brief Unlocks the MathTree
        """
        self._lock.release()

    @property
    def ptr(self):
        """ @brief Parses self.math and returns a pointer to a MathTree structure
        """
        if self._ptr is None:
            self._ptr = libfab.parse(self.math)
        return self._ptr

    ############################################################################

    @property
    def dx(self):
        try:                return self.xmax - self.xmin
        except TypeError:   return None
    @property
    def dy(self):
        try:                return self.ymax - self.ymin
        except TypeError:   return None
    @property
    def dz(self):
        try:                return self.zmax - self.zmin
        except TypeError:   return None

    @property
    def bounds(self):
        return [self.xmin, self.xmax,
                self.ymin, self.ymax,
                self.zmin, self.zmax]
    @bounds.setter
    def bounds(self, value):
        for b in ['xmin','xmax','ymin','ymax','zmin','zmax']:
            setattr(self, b, value.pop(0))

    @property
    def xmin(self): return self._xmin
    @xmin.setter
    def xmin(self, value):
        if value is None:   self._xmin = None
        else:
            try:    self._xmin = float(value)
            except: raise ValueError('xmin must be a float')
    @property
    def xmax(self): return self._xmax
    @xmax.setter
    def xmax(self, value):
        if value is None:   self._xmax = None
        else:
            try:    self._xmax = float(value)
            except: raise ValueError('xmax must be a float')

    @property
    def ymin(self): return self._ymin
    @ymin.setter
    def ymin(self, value):
        if value is None:   self._ymin = None
        else:
            try:    self._ymin = float(value)
            except: raise ValueError('ymin must be a float')
    @property
    def ymax(self): return self._ymax
    @ymax.setter
    def ymax(self, value):
        if value is None:   self._ymax = None
        else:
            try:    self._ymax = float(value)
            except: raise ValueError('ymax must be a float')

    @property
    def zmin(self): return self._zmin
    @zmin.setter
    def zmin(self, value):
        if value is None:   self._zmin = None
        else:
            try:    self._zmin = float(value)
            except: raise ValueError('zmin must be a float')
    @property
    def zmax(self): return self._zmax
    @zmax.setter
    def zmax(self, value):
        if value is None:   self._zmax = None
        else:
            try:    self._zmax = float(value)
            except: raise ValueError('zmax must be a float')

    @property
    def bounded(self):
        return all(d is not None for d in [self.dx, self.dy, self.dz])

    ############################################################################

    @property
    def color(self):    return self._color
    @color.setter
    def color(self, rgb):
        named = {'red':     (255, 0,   0  ),
                 'blue':    (0,   0,   255),
                 'green':   (0,   255, 0  ),
                 'white':   (255, 255, 255),
                 'grey':    (128, 128, 128),
                 'black':   (0,   0,   0  ),
                 'yellow':  (255, 255, 0  ),
                 'cyan':    (0,   255, 255),
                 'magenta': (255, 0,   255),
                 'teal':    (0, 255, 255),
                 'pink':    (255, 0, 255),
                 'brown':   (145, 82, 45),
                 'tan':     (125, 90, 60),
                 'navy':    (0, 0, 128)}
        if type(rgb) is str and rgb in named:
                self._color = named[rgb]
        elif type(rgb) in [tuple, list] and len(rgb) == 3:
            self._color = tuple(rgb)
        elif rgb is None:
            self._color = rgb
        else:
            raise ValueError('Invalid color (must be integer 3-value tuple or keyword)')

    ############################################################################

    @staticmethod
    def wrap(value):
        ''' Converts a value to a MathTree.

            None values are left alone,
            Strings are assumed to be valid math strings and wrapped
            Floats / ints are converted'''
        if isinstance(value, MathTree):
            return value
        elif value is None:
            return value
        elif type(value) is str:
            return MathTree(value)
        elif type(value) is not float:
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise TypeError('Wrong type for MathTree arithmetic (%s)' %
                                type(value))
        return MathTree.Constant(value)


    @classmethod
    @forcetree
    def min(cls, A, B): return cls('i'+A.math+B.math)

    @classmethod
    @forcetree
    def max(cls, A, B): return cls('a'+A.math+B.math)

    @classmethod
    @forcetree
    def pow(cls, A, B): return cls('p'+A.math+B.math)

    @classmethod
    @forcetree
    def sqrt(cls, A):   return cls('r'+A.math)

    @classmethod
    @forcetree
    def abs(cls, A):    return cls('b'+A.math)

    @classmethod
    @forcetree
    def square(cls, A): return cls('q'+A.math)

    @classmethod
    @forcetree
    def sin(cls, A):    return cls('s'+A.math)

    @classmethod
    @forcetree
    def cos(cls, A):    return cls('c'+A.math)

    @classmethod
    @forcetree
    def tan(cls, A):    return cls('t'+A.math)

    @classmethod
    @forcetree
    def asin(cls, A):   return cls('S'+A.math)

    @classmethod
    @forcetree
    def acos(cls, A):   return cls('C'+A.math)

    @classmethod
    @forcetree
    def atan(cls, A):   return cls('T'+A.math)

    #########################
    #  MathTree Arithmetic  #
    #########################

    # If shape is set, then + and - perform logical combination;
    # otherwise, they perform arithmeic.
    @matching
    @forcetree
    def __add__(self, rhs):
        if self.shape or (rhs and rhs.shape):

            if rhs is None: return self.clone()

            t = MathTree('i'+self.math+rhs.math, True)

            if self.dx is not None and rhs.dx is not None:
                t.xmin = min(self.xmin, rhs.xmin)
                t.xmax = max(self.xmax, rhs.xmax)
            if self.dx is not None and rhs.dy is not None:
                t.ymin = min(self.ymin, rhs.ymin)
                t.ymax = max(self.ymax, rhs.ymax)
            if self.dz is not None and rhs.dz is not None:
                t.zmin = min(self.zmin, rhs.zmin)
                t.zmax = max(self.zmax, rhs.zmax)

            return t
        else:
            return MathTree('+' + self.math + rhs.math)
    @matching
    @forcetree
    def __radd__(self, lhs):
        if lhs is None:     return self.clone()

        if self.shape or (lhs and lhs.shape):

            t = MathTree('i'+lhs.math+self.math)
            if self.dx is not None and lhs.dx is not None:
                t.xmin = min(self.xmin, lhs.xmin)
                t.xmax = max(self.xmax, lhs.xmax)
            if self.dy is not None and lhs.dy is not None:
                t.ymin = min(self.ymin, lhs.ymin)
                t.ymax = max(self.ymax, lhs.ymax)
            if self.dz is not None and lhs.dz is not None:
                t.zmin = min(self.zmin, lhs.zmin)
                t.zmax = max(self.zmax, lhs.zmax)
            return t
        else:
            return MathTree('+' + lhs.math + self.math)

    @matching
    @forcetree
    def __sub__(self, rhs):
        if self.shape or (rhs and rhs.shape):

            if rhs is None: return self.clone()

            t = MathTree('a'+self.math+'n'+rhs.math, True)
            for i in ['xmin','xmax','ymin','ymax','zmin','zmax']:
                setattr(t, i, getattr(self, i))
            return t
        else:
            return MathTree('-'+self.math+rhs.math)

    @matching
    @forcetree
    def __rsub__(self, lhs):
        if self.shape or (lhs and lhs.shape):

            if lhs is None: return MathTree('n' + self.math)

            t = MathTree('a'+lhs.math+'n'+self.math, True)
            for i in ['xmin','xmax','ymin','ymax','zmin','zmax']:
                setattr(t, i, getattr(lhs, i))
            return t
        else:
            return MathTree('-'+lhs.math+self.math)

    @matching
    @forcetree
    def __and__(self, rhs):
        if self.shape or rhs.shape:
            t = MathTree('a' + self.math + rhs.math, True)
            if self.dx is not None and rhs.dx is not None:
                t.xmin = max(self.xmin, rhs.xmin)
                t.xmax = min(self.xmax, rhs.xmax)
            if self.dy is not None and rhs.dy is not None:
                t.ymin = max(self.ymin, rhs.ymin)
                t.ymax = min(self.ymax, rhs.ymax)
            if self.dz is not None and rhs.dz is not None:
                t.zmin = max(self.zmin, rhs.zmin)
                t.zmax = min(self.zmax, rhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '& operator is undefined for non-shape math expressions.')

    @matching
    @forcetree
    def __rand__(self, lhs):
        if self.shape or lhs.shape:
            t = MathTree('a' + lhs.math + self.math, True)
            if self.dx is not None and lhs.dx is not None:
                t.xmin = max(self.xmin, lhs.xmin)
                t.xmax = min(self.xmax, lhs.xmax)
            if self.dy is not None and lhs.dy is not None:
                t.ymin = max(self.ymin, lhs.ymin)
                t.ymax = min(self.ymax, lhs.ymax)
            if self.dz is not None and lhs.dz is not None:
                t.zmin = max(self.zmin, lhs.zmin)
                t.zmax = min(self.zmax, lhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '& operator is undefined for non-shape math expressions.')


    @matching
    @forcetree
    def __or__(self, rhs):
        if self.shape or rhs.shape:
            t = MathTree('i' + self.math + rhs.math, True)
            if self.dx is not None and rhs.dx is not None:
                t.xmin = min(self.xmin, rhs.xmin)
                t.xmax = max(self.xmax, rhs.xmax)
            if self.dy is not None and rhs.dy is not None:
                t.ymin = min(self.ymin, rhs.ymin)
                t.ymax = max(self.ymax, rhs.ymax)
            if self.dz is not None and rhs.dz is not None:
                t.zmin = min(self.zmin, rhs.zmin)
                t.zmax = max(self.zmax, rhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '| operator is undefined for non-shape math expressions.')


    @matching
    @forcetree
    def __ror__(self, lhs):
        if self.shape or lhs.shape:
            t = MathTree('i' + lhs.math + self.math, True)
            if self.dx is not None and lhs.dx is not None:
                t.xmin = min(self.xmin, lhs.xmin)
                t.xmax = max(self.xmax, lhs.xmax)
            if self.dy is not None and lhs.dy is not None:
                t.ymin = min(self.ymin, lhs.ymin)
                t.ymax = max(self.ymax, lhs.ymax)
            if self.dz is not None and lhs.dz is not None:
                t.zmin = min(self.zmin, lhs.zmin)
                t.zmax = max(self.zmax, lhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '| operator is undefined for non-shape math expressions.')

    @forcetree
    def __mul__(self, rhs):
        return MathTree('*' + self.math + rhs.math)

    @forcetree
    def __rmul__(self, lhs):
        return MathTree('*' + lhs.math + self.math)

    @forcetree
    def __div__(self, rhs):
        return MathTree('/' + self.math + rhs.math)

    @forcetree
    def __rdiv__(self, lhs):
        return MathTree('/' + lhs.math + self.math)

    @forcetree
    def __neg__(self):
        return MathTree('n' + self.math, shape=self.shape)


    ###############################
    ## String and representation ##
    ###############################

    def __str__(self):
        if self._str is None:
            self._str = self.make_str()
        return self._str

    def make_str(self, verbose=False):
        """ @brief Converts the object into an infix-notation string

            @details
            Creates a OS pipe, instructs the object to print itself into the pipe, and reads the output in chunks of maximum size 1024.
        """

        # Create a pipe to get the printout
        read, write = os.pipe()

        # Start the print function running in a separate thread
        # (so that we can eat the output and avoid filling the pipe)
        if verbose: printer = libfab.fdprint_tree_verbose
        else:       printer = libfab.fdprint_tree
        t = threading.Thread(target=printer, args=(self.ptr, write))
        t.daemon = True
        t.start()

        s = r = os.read(read, 1024)
        while r:
            r = os.read(read, 1024)
            s += r
        t.join()

        os.close(read)

        return s

    def __repr__(self):
        return "'%s' (tree at %s)" % (self, hex(self.ptr.value))

    def verbose(self):
        return self.make_str(verbose=True)

    def save_dot(self, filename, arrays=False):
        """ @brief Converts math expression to .dot graph description
        """
        if arrays:
            libfab.dot_arrays(self.ptr, filename)
        else:
            libfab.dot_tree(self.ptr, filename)

    @property
    def node_count(self):
        return libfab.count_nodes(self.ptr)

    #################################
    ## Tree manipulation functions ##
    #################################
    @forcetree
    def map(self, X=None, Y=None, Z=None):
        """ @brief Applies a map operator to a tree
            @param X New X function or None
            @param Y New Y function or None
            @param Z New Z function or None
        """
        return MathTree('m'+
                           (X.math if X else ' ')+
                           (Y.math if Y else ' ')+
                           (Z.math if Z else ' ')+
                           self.math,
                      shape=self.shape, color=self.color)

    @forcetree
    def map_bounds(self, X=None, Y=None, Z=None):
        """ @brief Calculates remapped bounds
            @returns Array of remapped bounds
            @param X New X function or None
            @param Y New Y function or None
            @param Z New Z function or None
            @details Note that X, Y, and Z should be the inverse
            of a coordinate mapping to properly transform bounds.
        """
        if self.dx is not None: x = Interval(self.xmin, self.xmax)
        else:                   x = Interval(float('nan'))
        if self.dy is not None: y = Interval(self.ymin, self.ymax)
        else:                   y = Interval(float('nan'))
        if self.dz is not None: z = Interval(self.zmin, self.zmax)
        else:                   z = Interval(float('nan'))

        if self.dx is not None: a = Interval(self.xmin, self.xmax)
        else:                   a = Interval(float('nan'))
        if self.dy is not None: b = Interval(self.ymin, self.ymax)
        else:                   b = Interval(float('nan'))
        if self.dz is not None: c = Interval(self.zmin, self.zmax)
        else:                   c = Interval(float('nan'))

        if X:
            X_p = libfab.make_packed(X.ptr)
            a = libfab.eval_i(X_p, x, y, z)
            libfab.free_packed(X_p)

        if Y:
            Y_p = libfab.make_packed(Y.ptr)
            b = libfab.eval_i(Y_p, x, y, z)
            libfab.free_packed(Y_p)

        if Z:
            Z_p = libfab.make_packed(Z.ptr)
            c = libfab.eval_i(Z_p, x, y, z)
            libfab.free_packed(Z_p)

        bounds = []
        for i in [a,b,c]:
            if math.isnan(i.lower) or math.isnan(i.upper):
                bounds += [None, None]
            else:
                bounds += [i.lower, i.upper]

        return bounds

    @threadsafe
    def clone(self):
        m = MathTree(self.math, shape=self.shape, color=self.color)
        m.bounds = [b for b in self.bounds]
        if self._ptr is not None:
            m._ptr = libfab.clone_tree(self._ptr)
        return m

    #################################
    #    Rendering functions        #
    #################################

    def render(self, region=None, resolution=None, mm_per_unit=None,
               threads=8, interrupt=None):
        """ @brief Renders a math tree into an Image
            @param region Evaluation region (if None, taken from expression bounds)
            @param resolution Render resolution in voxels/unit
            @param mm_per_unit Real-world scale
            @param threads Number of threads to use
            @param interrupt threading.Event that aborts rendering if set
            @returns Image data structure
        """

        if region is None:
            if self.dx is None or self.dy is None:
                raise Exception('Unknown render region!')
            elif resolution is None:
                raise Exception('Region or resolution must be provided!')
            region = Region(
                (self.xmin, self.ymin, self.zmin if self.zmin else 0),
                (self.xmax, self.ymax, self.zmax if self.zmax else 0),
                resolution
            )

        try:
            float(mm_per_unit)
        except ValueError, TypeError:
            raise ValueError('mm_per_unit must be a number')

        if interrupt is None:   interrupt = threading.Event()
        halt = ctypes.c_int(0)  # flag to abort render
        image = Image(
            region.ni, region.nj, channels=1, depth=16,
        )

        # Divide the task to share among multiple threads
        clones = [self.clone() for i in range(threads)]
        packed = [libfab.make_packed(c.ptr) for c in clones]

        subregions = region.split_xy(threads)

        # Solve each region in a separate thread
        args = zip(packed, subregions, [image.pixels]*threads, [halt]*threads)

        multithread(libfab.render16, args, interrupt, halt)

        for p in packed:    libfab.free_packed(p)

        image.xmin = region.X[0]*mm_per_unit
        image.xmax = region.X[region.ni]*mm_per_unit
        image.ymin = region.Y[0]*mm_per_unit
        image.ymax = region.Y[region.nj]*mm_per_unit
        image.zmin = region.Z[0]*mm_per_unit
        image.zmax = region.Z[region.nk]*mm_per_unit

        return image


    def asdf(self, region=None, resolution=None, mm_per_unit=None,
             merge_leafs=True, interrupt=None):
        """ @brief Constructs an ASDF from a math tree.
            @details Runs in up to eight threads.
            @param region Evaluation region (if None, taken from expression bounds)
            @param resolution Render resolution in voxels/unit
            @param mm_per_unit Real-world scale
            @param merge_leafs Boolean determining whether leaf cells are combined
            @param interrupt threading.Event that aborts rendering if set
            @returns ASDF data structure
        """

        if region is None:
            if not self.bounded:
                raise Exception('Unknown render region!')
            elif resolution is None:
                raise Exception('Region or resolution must be provided!')
            region = Region(
                (self.xmin, self.ymin, self.zmin if self.zmin else 0),
                (self.xmax, self.ymax, self.zmax if self.zmax else 0),
                resolution
            )

        if interrupt is None:   interrupt = threading.Event()

        # Shared flag to interrupt rendering
        halt = ctypes.c_int(0)

        # Split the region into up to 8 sections
        split = region.octsect(all=True)
        subregions = [split[i] for i in range(8) if split[i] is not None]
        ids = [i for i in range(8) if split[i] is not None]

        threads = len(subregions)
        clones  = [self.clone() for i in range(threads)]
        packed  = [libfab.make_packed(c.ptr) for c in clones]

        # Generate a root for the tree
        asdf = ASDF(libfab.asdf_root(packed[0], region), color=self.color)

        # Multithread the solver process
        q = Queue.Queue()
        args = zip(packed, ids, subregions, [q]*threads)

        # Helper function to construct a single branch
        def construct_branch(ptree, id, region, queue):
            asdf = libfab.build_asdf(ptree, region, merge_leafs, halt)
            queue.put((id, asdf))

        # Run the constructor in parallel to make the branches
        multithread(construct_branch, args, interrupt, halt)
        for p in packed:    libfab.free_packed(p)

        # Attach the branches to the root
        for s in subregions:
            try:                id, branch = q.get_nowait()
            except Queue.Empty: break
            else:               asdf.ptr.contents.branches[id] = branch
        libfab.get_d_from_children(asdf.ptr)
        libfab.simplify(asdf.ptr, merge_leafs)

        # Set a scale on the ASDF if one was provided
        if mm_per_unit is not None:     asdf.rescale(mm_per_unit)

        return asdf


    def triangulate(self, region=None, resolution=None,
                    mm_per_unit=None, merge_leafs=True, interrupt=None):
        """ @brief Triangulates a math tree (via ASDF)
            @details Runs in up to eight threads
            @param region Evaluation region (if not, taken from expression)
            @param resolution Render resolution in voxels/unit
            @param mm_per_unit Real-world scale
            @param merge_leafs Boolean determining whether leaf cells are combined
            @param interrupt threading.Event that aborts rendering if set
            @returns Mesh data structure
        """
        asdf = self.asdf(region, resolution, mm_per_unit, merge_leafs, interrupt)
        return asdf.triangulate()


    @staticmethod
    def Constant(f):   return MathTree('f%g' % f)

    @staticmethod
    def X():    return MathTree('X')

    @staticmethod
    def Y():    return MathTree('Y')

    @staticmethod
    def Z():    return MathTree('Z')

if libfab:
    X = MathTree.X()
    Y = MathTree.Y()
    Z = MathTree.Z()


from    koko.fab.image      import Image
from    koko.fab.asdf       import ASDF
