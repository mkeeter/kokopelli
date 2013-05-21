""" Module defining Mesh class to store indexed geometry. """

import  ctypes
import  operator
import  os
import  tempfile

from    koko.struct     import Struct

class Mesh(object):
    ''' Mesh objects represent a chunk of indexed geometry.'''

    def __init__(self, ptr, color=None):
        """ @brief Initializes a mesh object from vertex and index array(s).
            @param ptr Pointer to C mesh structure
            @param color Draw color (or None)
        """

        ## @var ptr
        # Pointer to a C Mesh structure
        self.ptr = ptr

        ## @var color
        # Color for mesh drawing operations
        self.color = color

        ## @var source
        # Structure describing source of this mesh (or none)
        # Used in re-rendering operations
        self.source = None

        ## @var cached
        # Temporary file containing this mesh
        self.cached = None

        ## @var children
        # Array of mesh children (for multi-scale meshes)
        self.children = []

    def __del__(self):
        """ @brief Mesh destructor
        """
        if libfab and self.ptr:
            libfab.free_mesh(self.ptr)

    @property
    def X(self):    return self.ptr.contents.X if self.ptr else None
    @property
    def Y(self):    return self.ptr.contents.Y if self.ptr else None
    @property
    def Z(self):    return self.ptr.contents.Z if self.ptr else None

    @property
    def tcount(self):   return self.ptr.contents.tcount if self.ptr else None
    @property
    def vcount(self):   return self.ptr.contents.vcount if self.ptr else None

    @property
    def vdata(self):    return self.ptr.contents.vdata
    @property
    def tdata(self):    return self.ptr.contents.tdata

    def save_stl(self, filename):
        libfab.save_stl(self.ptr, filename)

    def save(self, filename):
        """ @brief Saves the mesh as an binary stl file or as a binary mesh file
            @param filename Target filename; if it ends in '.stl' an stl will be saved
        """
        if filename[-4:] == '.stl':
            self.save_stl(filename)
        else:
            libfab.save_mesh(filename, self.ptr)

################################################################################

    def refine(self):
        """ @brief Attempts to refine the mesh object, saving this mesh
            in a temporary file.
        """
        if self.cached is None:
            self.cached = tempfile.NamedTemporaryFile()
            self.save(self.cached.name)

        if self.source.type is MathTree:
            self.refine_math()
        elif self.source.type is ASDF:
            self.refine_asdf()


    def refine_math(self):
        """ @brief Refines a mesh based on a math tree
            @details Splits the mesh's bounding box then renders both subregions
            at a higher detail level, saving them in self.children
        """
        region = Region(
            (self.X.lower / self.source.scale,
             self.Y.lower / self.source.scale,
             self.Z.lower / self.source.scale),
            (self.X.upper / self.source.scale,
             self.Y.upper / self.source.scale,
             self.Z.upper / self.source.scale),
             depth=self.source.depth+1
        )

        subregions = region.split()
        meshes = []
        for s in subregions:
            asdf = self.source.expr.asdf(
                region=s, mm_per_unit=self.source.scale
            )
            mesh = asdf.triangulate()

            mesh.source = Struct(
                type=MathTree,
                expr=self.source.expr.clone(),
                depth=self.source.depth+1,
                scale=self.source.scale
            )
            meshes.append(mesh)

        self.children = meshes
        libfab.free_mesh(self.ptr)
        self.ptr = None


    def refine_asdf(self):
        """ @brief Refines a mesh from an .asdf file
            @details Attempts to load .asdf files at a higher recursion level
            and assigns them to self.children
        """
        meshes = []
        for i in range(8):
            filename = self.source.file.replace('.asdf', '%i.asdf' % i)
            asdf = ASDF.load(filename)
            mesh = asdf.triangulate()
            mesh.source = Struct(
                type=ASDF, file=filename, depth=self.source.depth+1
            )
            meshes.append(mesh)

        self.children = meshes
        self.vdata = self.idata = None
        self.vcount = self.icount = self.tcount = None



    def expandable(self):
        """ @brief Returns True if this mesh can be refined.
        """
        if self.source is None:
            return False
        elif self.source.type is MathTree:
            return True
        elif self.source.type is ASDF:
            return all(
                os.path.exists(
                    self.source.file.replace('.asdf', '%i.asdf' % i)
                ) for i in range(8)
            )
        return False


    def collapse(self):
        """ @brief Collapses the mesh, deleting children and re-rendering at
        the mesh's resolution.
        """
        if self.cached:
            mesh = Mesh.load(self.cached.name)
        elif self.source.type is MathTree:
            mesh = self.collapse_tree()
        elif self.source.type is ASDF:
            mesh = self.collapse_asdf()

        # Steal the mesh object by moving pointers around
        self.ptr = mesh.ptr
        mesh.ptr = None
        self.children = []


    def collapse_tree(self):
        """ @brief Re-renders from the source math tree
        """
        region = Region(
            (self.X.lower / self.source.scale,
             self.Y.lower / self.source.scale,
             self.Z.lower / self.source.scale),
            (self.X.upper / self.source.scale,
             self.Y.upper / self.source.scale,
             self.Z.upper / self.source.scale),
             depth=self.source.depth
        )

        asdf = self.source.expr.asdf(
            region=region, mm_per_unit=self.source.scale
        )
        return asdf.triangulate()


    def collapse_asdf(self):
        """ @brief Reloads from the source .asdf file
        """
        asdf = ASDF.load(self.source.file)
        return asdf.triangulate()


    def leafs(self):
        """ @brief Returns a flat list of leaf cells
            (i.e. cells without children)
        """
        if self.children:
            return reduce(operator.add, [c.leafs() for c in self.children])
        else:
            return [self]


    def get_fills(self, d):
        """ @brief Finds and saves fill percentages of cells with children.
            @param d Dictionary mapping leaf cells to fill percentages.
        """
        if not self.children:   return {}

        out = {}
        score = 0
        for c in self.children:
            out.update(c.get_fills(d))
            if c in out:    score += out[c]
            elif c in d:    score += d[c]
        out[self] = score

        return out


    @classmethod
    def load(cls, filename):
        if filename[-4:] == '.stl':
            return cls.load_stl(filename)
        return cls(libfab.load_mesh(filename))


    @classmethod
    def load_stl(cls, filename):
        return cls(libfab.load_stl(filename))


    @classmethod
    def merge(cls, meshes):
        """ @brief Efficiently combines a set of independent meshes.
            (does not perform vertex deduplication).
        """
        ptrs = (ctypes.POINTER(_Mesh) * len(meshes))(
                *[m.ptr for m in meshes]
        )
        for i in range(len(meshes)):
            meshes[i].save_stl('test%i.stl' % i)
        m = cls(libfab.merge_meshes(len(meshes), ptrs))
        return m


from    koko.c.libfab   import libfab
from    koko.c.region   import Region
from    koko.c.mesh     import Mesh as _Mesh

from    koko.fab.tree   import MathTree
from    koko.fab.asdf   import ASDF
