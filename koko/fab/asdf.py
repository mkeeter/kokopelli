""" Module defining a distance field class. """

import ctypes
from datetime       import datetime
import threading
from math           import sin, cos, radians, log, ceil
import os
import Queue

from koko.c.multithread    import multithread, monothread

from koko.struct    import Struct
from koko.c.libfab  import libfab
from koko.c.asdf    import ASDF as _ASDF
from koko.c.path    import Path as _Path
from koko.c.region  import Region
from koko.c.vec3f   import Vec3f

################################################################################

class ASDF(object):
    ''' Wrapper class that contains an ASDF pointer and
        automatically frees it upon destruction.'''

    def __init__(self, ptr, free=True, color=None):
        """ @brief Creates an ASDF wrapping the given pointer
            @param ptr Target pointer
            @param free Boolean determining if the ASDF is freed upon destruction
            @param color ASDF's color (or None)
        """

        ## @var ptr
        # Pointer to a C ASDF structure
        self.ptr        = ptr

        ## @var free
        # Boolean determining whether the pointer is freed
        self.free       = free

        ## @var color
        # Tuple representing RGB color (or None)
        self.color      = color

        ## @var filename
        # Filename if ASDF was loaded from a file
        self.filename   = None


    def __del__(self):
        """ @brief ASDF destructor which frees ASDF is necessary
        """
        if self.free and libfab is not None:
            libfab.free_asdf(self.ptr)

    def interpolate(self, x, y, z):
        """ @brief Interpolates based on ASDF corners
        """
        return libfab.interpolate(
            self.ptr.contents.d, x, y, z,
            self.X.lower, self.Y.lower, self.Z.lower,
            self.X.upper - self.X.lower,
            self.Y.lower - self.Y.upper,
            self.Z.lower - self.Z.upper
        )

    @property
    def branches(self):
        """ @returns 8-item list, where each item is a branch or None
        """
        b = []
        for i in range(8):
            try:
                self.ptr.contents.branches[i].contents.X
            except ValueError:
                b += [None]
            else:
                b += [ASDF(self.ptr.contents.branches[i], free=False)]
        return b

    @property
    def state(self):
        """ @returns A string describing ASDF state """
        return ['FILLED','EMPTY','BRANCH','LEAF'][self.ptr.contents.state]
    @property
    def d(self):
        """ @returns Array of eight distance samples """
        return [self.ptr.contents.d[i] for i in range(8)]
    @property
    def X(self):
        """ @returns X bounds as an Interval """
        return self.ptr.contents.X
    @property
    def Y(self):
        """ @returns Y bounds as an Interval """
        return self.ptr.contents.Y
    @property
    def Z(self):
        """ @returns Z bounds as Interval """
        return self.ptr.contents.Z

    @property
    def xmin(self):
        """ @returns Minimum x bound (in mm) """
        return self.ptr.contents.X.lower
    @property
    def xmax(self):
        """ @returns Maximum x bound (in mm) """
        return self.ptr.contents.X.upper
    @property
    def dx(self):
        """ @returns X size (in mm) """
        return self.xmax - self.xmin

    @property
    def ymin(self):
        """ @returns Minimum y bound (in mm) """
        return self.ptr.contents.Y.lower
    @property
    def ymax(self):
        """ @returns Maximum y bound (in mm) """
        return self.ptr.contents.Y.upper
    @property
    def dy(self):
        """ @returns Y size (in mm) """
        return self.ymax - self.ymin

    @property
    def zmin(self):
        """ @returns Minimum z bound (in mm) """
        return self.ptr.contents.Z.lower
    @property
    def zmax(self):
        """ @returns Maximum y bound (in mm) """
        return self.ptr.contents.Z.upper
    @property
    def dz(self):
        """ @returns Z size (in mm) """
        return self.zmax - self.zmin



    def rescale(self, mult):
        """ @brief Rescales the ASDF by the given scale factor
            @param mult Scale factor (1 is no change)
            @returns None
        """
        libfab.asdf_scale(self.ptr, mult)

    @property
    def depth(self):
        """ @returns The depth of this ASDF
        """
        return libfab.get_depth(self.ptr)

    @property
    def dimensions(self):
        """ @returns ni, nj, nk tuple of lattice dimensions
        """
        ni = ctypes.c_int()
        nj = ctypes.c_int()
        nk = ctypes.c_int()

        libfab.find_dimensions(self.ptr, ni, nj, nk)
        return ni.value, nj.value, nk.value

    @property
    def cell_count(self):
        """ @returns Number of cells in this ASDF
        """
        return libfab.count_cells(self.ptr)

    @property
    def ram(self):
        """ @returns Number of bytes in RAM this ASDF occupies
        """
        return self.cell_count * ctypes.sizeof(_ASDF)


    def save(self, filename):
        """ @brief Saves the ASDF to file
        """
        libfab.asdf_write(self.ptr, filename)


    @classmethod
    def load(cls, filename):
        """ @brief Loads an ASDF file from disk
            @param cls Class (automatic argument)
            @param filename Filename (string)
            @returns An ASDF loaded from the file
        """
        asdf = cls(libfab.asdf_read(filename))
        asdf.filename = filename
        return asdf


    @classmethod
    def from_vol(cls, filename, ni, nj, nk, offset, mm_per_voxel,
                 merge_leafs=True):
        """ @brief Imports a .vol file
            @param cls Class (automatic argument)
            @param filename Name of .vol file
            @param ni Number of samples in x direction
            @param nj Number of samples in y direction
            @param nk Number of samples in z direction
            @param offset Isosurface density
            @param mm_per_voxel Scaling factor (mm/voxel)
            @param merge_leafs Boolean determining whether leaf cells are merged
            @returns An ASDF representing an isosurface of the .vol data
        """
        asdf = cls(
            libfab.import_vol(
                filename, ni, nj, nk,
                offset, mm_per_voxel, merge_leafs
            )
        )
        return asdf

    @classmethod
    def from_pixels(cls, img, offset, merge_leafs=False):
        """ @brief Imports an Image
            @param cls Class (automatic argument)
            @param img Image object
            @param offset Isosurface level
            @param merge_leafs Boolean determining whether leaf cells are merged
            @returns An ASDF representing the original image
        """
        asdf = cls(libfab.import_lattice(img.pixels, img.width, img.height,
                                          offset, 1/img.pixels_per_mm,
                                          merge_leafs))
        return asdf


    def slice(self, z):
        """ @brief Finds a 2D ASDF at a given z height
            @param z Z height at which to slice the ASDF
            @returns 2D slice of original ASDF
        """
        return ASDF(libfab.asdf_slice(self.ptr, z), color=self.color)

    def bounds(self, alpha=0, beta=0):
        ''' Find the largest possible bounding box for this ASDF
            rotated with angles alpha and beta. '''

        # Create an array of the eight cube corners
        corners = [Vec3f(self.X.upper if (i & 4) else self.X.lower,
                         self.Y.upper if (i & 2) else self.Y.lower,
                         self.Z.upper if (i & 1) else self.Z.lower)
                   for i in range(8)]

        # Project the corners around
        M = (ctypes.c_float*4)(cos(radians(alpha)), sin(radians(alpha)),
                               cos(radians(beta)),  sin(radians(beta)))
        corners = [libfab.project(c, M) for c in corners]

        # Find and return the bounds
        return Struct(
            xmin=min(c.x for c in corners),
            xmax=max(c.x for c in corners),
            ymin=min(c.y for c in corners),
            ymax=max(c.y for c in corners),
            zmin=min(c.z for c in corners),
            zmax=max(c.z for c in corners)
        )


    def bounding_region(self, resolution, alpha=0, beta=0):
        """ @brief Finds a bounding region with the given rotation
            @param resolution Region resolution (voxels/unit)
            @param alpha Rotation about Z axis
            @param beta Rotation about X axis
        """
        b = self.bounds(alpha, beta)
        return Region(
            (b.xmin, b.ymin, b.zmin),
            (b.xmax, b.ymax, b.zmax),
            resolution
        )


    #
    #   Render to image
    #
    def render(self, region=None, threads=8, alpha=0, beta=0, resolution=10):
        """ @brief Renders to an image
            @param region Render region (default bounding box)
            @param threads Threads to use (default 8)
            @param alpha Rotation about Z axis (default 0)
            @param beta Rotation about X axis (default 0)
            @param resolution Resolution in voxels per mm
            @returns A height-map Image
        """
        return self.render_multi(region, threads, alpha, beta, resolution)[0]


    def render_multi(self, region=None, threads=8,
                     alpha=0, beta=0, resolution=10):
        """ @brief Renders to an image
            @param region Render region (default bounding box)
            @param threads Threads to use (default 8)
            @param alpha Rotation about Z axis (default 0)
            @param beta Rotation about X axis (default 0)
            @resolution Resolution in voxels per mm
            @returns A tuple with a height-map, shaded image, and image with colored normals
        """
        if region is None:
            region = self.bounding_region(resolution, alpha, beta)

        depth   = Image(
            region.ni, region.nj, channels=1, depth=16,
        )
        shaded  = Image(
            region.ni, region.nj, channels=1, depth=16,
        )
        normals = Image(
            region.ni, region.nj, channels=3, depth=8,
        )

        subregions = region.split_xy(threads)

        M = (ctypes.c_float*4)(cos(radians(alpha)), sin(radians(alpha)),
                               cos(radians(beta)), sin(radians(beta)))
        args = [
            (self.ptr, s, M, depth.pixels, shaded.pixels, normals.pixels)
            for s in subregions
        ]
        multithread(libfab.render_asdf_shaded, args)

        for image in [depth, shaded, normals]:
            image.xmin = region.X[0]
            image.xmax = region.X[region.ni]
            image.ymin = region.Y[0]
            image.ymax = region.Y[region.nj]
            image.zmin = region.Z[0]
            image.zmax = region.Z[region.nk]
        return depth, shaded, normals


    def render_distance(self, resolution=10):
        """ @brief Draws the ASDF as a distance field (used for debugging)
            @param resolution Image resolution
            @returns An 16-bit, 1-channel Image showing the distance field
        """
        region = self.bounding_region(resolution)
        image = Image(region.ni, region.nj, channels=1, depth=16)
        image.xmin = region.X[0]
        image.xmax = region.X[region.ni]
        image.ymin = region.Y[0]
        image.ymax = region.Y[region.nj]
        image.zmin = region.Z[0]
        image.zmax = region.Z[region.nk]

        minimum = libfab.asdf_get_min(self.ptr)
        maximum = libfab.asdf_get_max(self.ptr)

        libfab.draw_asdf_distance(
            self.ptr, region, minimum, maximum, image.pixels
        )
        return image


    #
    #   Triangulation functions
    #
    def triangulate(self, threads=True, interrupt=None):
        """ @brief Triangulates an ASDF, returning a mesh
            @param threads Boolean determining multithreading
            @param interrupt threading.Event used to abort
            @returns A Mesh containing the triangulated ASDF
        """
        # Create an event to interrupt the evaluation
        if interrupt is None:   interrupt = threading.Event()

        # Shared flag to interrupt rendering
        halt = ctypes.c_int(0)

        # Create a set of arguments
        if threads:
            q = Queue.Queue()
            args = []
            for b in self.branches:
                if b is None:   continue
                args.append( (b, halt, q) )

            # Run the triangulation operation in parallel
            multithread(ASDF._triangulate, args, interrupt, halt)

            results = []
            while True:
                try:                results.append(q.get_nowait())
                except Queue.Empty: break
        else:
            results = [self._triangulate(halt)]
        m = Mesh.merge(results)
        m.color = self.color
        return m


    def _triangulate(self, halt, queue=None):
        ''' Triangulates a mesh, storing data in the vdata and idata
            arrays.  Pushes results to the queue.'''

        mesh = Mesh(libfab.triangulate(self.ptr, halt))
        if queue:   queue.put(mesh)
        else:       return mesh

    def triangulate_cms(self):
        return Mesh(libfab.triangulate_cms(self.ptr))

    def contour(self, interrupt=None):
        """ @brief Contours an ASDF
            @returns A set of Path objects
            @param interrupt threading.Event used to abort run
        """
        # Create an event to interrupt the evaluation
        if interrupt is None:   interrupt = threading.Event()

        # Shared flag to interrupt rendering
        halt = ctypes.c_int(0)

        ptr = ctypes.POINTER(ctypes.POINTER(_Path))()
        path_count = monothread(
            libfab.contour, (self.ptr, ptr, halt), interrupt, halt
        )

        paths = [Path.from_ptr(ptr[i]) for i in range(path_count)]
        libfab.free_paths(ptr, path_count)

        return paths


    def histogram(self):
        """ @brief Generates a histogram of cell distribution
            @returns A list of lists of cell counts
        """
        bins = ((ctypes.c_int*4)*self.depth)()

        libfab.asdf_histogram(self.ptr, bins, 0)

        return zip(*map(list, bins))


    def offset(self, o, resolution=10):
        """ @brief Offsets an ASDF
            @details Uses a variation on the Meijster distance transform
            @param o Offset distance (in mm)
            @param resolution Offset render resolution
        """
        return ASDF(libfab.asdf_offset(self.ptr, o, resolution))

################################################################################

from koko.fab.image import Image
from koko.fab.mesh  import Mesh
from koko.fab.path  import Path
