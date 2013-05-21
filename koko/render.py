from    datetime    import datetime
import  Queue
import  re
import  StringIO
import  sys
import  threading
import  traceback

import  wx

import  koko
from    koko.struct         import Struct
from    koko.fab.asdf       import ASDF
from    koko.fab.tree       import MathTree
from    koko.fab.fabvars    import FabVars
from    koko.fab.mesh       import Mesh

from    koko.c.region       import Region


class RenderTask(object):
    """ @class RenderTask
        @brief A render job running in a separate thread
    """

    def __init__(self, view, script=None, cad=None):
        """ @brief Constructs and starts a render task.
            @param view Render view (Struct with xmin, xmax, ymin, ymax, zmin, zmax, and pixels_per_unit member variables)
            @param script Source script to render
            @param cad Data structure from previous run
        """

        if not (bool(script) ^ bool(cad)):
            raise Exception('RenderTask must be initialized with either a script or a cad structure.')

        ## @var view
        # Struct representing render view
        self.view    = view

        ## @var script
        # String containing design script
        self.script  = script

        ## @var cad
        # FabVars structure containing pre-computed results
        self.cad     = cad

        ## @var event
        # threading.Event used to halt rendering
        self.event   = threading.Event()

        ## @var c_event
        # threading.Event used to halt rendering in C functions
        self.c_event = threading.Event()

        ## @var output
        # String holding text to be loaded into the output panel
        self.output  = ''

        ## @var thread
        # threading.Thread that actually runs the task
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

########################################

    def run(self):
        """ @brief Runs the given task
            @details Renders file and loads results into canvas(es) if successful.
        """
        start = datetime.now()

        # Clear markings from previous runs
        koko.CANVAS.border   = None
        koko.GLCANVAS.border = None
        koko.FRAME.status = ''
        koko.EDITOR.error_marker = None

        # Add the top-level header to the output pane
        self.output += '####       Rendering image      ####\n'

        # Run cad_math to generate a cad structure
        make_mesh = self.cad is None or koko.GLCANVAS.loaded is False

        # Try to generate the cad structure, aborting if failed
        if not self.cad and not self.cad_math():     return

        # If the cad structure defines a render mode, then enforce it.
        height = koko.FRAME.get_menu('View','2D')
        shaded = koko.FRAME.get_menu('View', '3D')
        dual = koko.FRAME.get_menu('View', 'Both')

        # If the cad file overrides the render mode, then disable
        # the menu items so that the user can't change render mode.
        if self.cad.render_mode is None:
            wx.CallAfter(height.Enable, True)
            wx.CallAfter(shaded.Enable, True)
            wx.CallAfter(dual.Enable,   True)
        else:
            wx.CallAfter(height.Enable, False)
            wx.CallAfter(shaded.Enable, False)
            wx.CallAfter(dual.Enable,   False)

        if self.cad.render_mode == 'shaded' and not shaded.IsChecked():
            render_mode = 'shaded'
            wx.CallAfter(shaded.Check, True)
            wx.CallAfter(koko.APP.render_mode, '3D')
        elif self.cad.render_mode == 'height' and not height.IsChecked():
            render_mode = 'height'
            wx.CallAfter(height.Check,True)
            wx.CallAfter(koko.APP.render_mode, '2D')
        elif shaded.IsChecked():
            render_mode = 'shaded'
        elif height.IsChecked():
            render_mode = 'height'
        else:
            render_mode = ('shaded','height')

        # Render and load a height-map image
        if 'height' in render_mode:

            imgs = self.make_images()
            if self.event.is_set(): return

            # Push images to the global canvas object
            koko.CANVAS.load_images(imgs, self.cad.mm_per_unit)


        # Render and load a triangulated mesh
        if make_mesh and 'shaded' in render_mode:
            koko.GLCANVAS.loaded = False

            images = []
            meshes = []
            try:
                image_scale = max(
                    (1e6/expr.dx*expr.dy)**0.5 for expr in self.cad.shapes
                    if not expr.dz
                )
            except ValueError:
                image_scale = 1

            for e in self.cad.shapes:
                if self.event.is_set(): return

                # If this is a full 3D model, then render it
                if e.bounded:
                    meshes.append(self.make_mesh(e))

                # If it is a 2D model, then render it as an image
                elif (self.cad.dx is not None and
                      self.cad.dy is not None):
                    images.append(self.make_flat_image(e, image_scale))

                else:
                    koko.FRAME.status = (
                        'Error:  Objects must have valid bounds!'
                    )
                    koko.GLCANVAS.border = (255, 0, 0)
                    return


            if not self.event.is_set():
                koko.GLCANVAS.clear()
                if images:  koko.GLCANVAS.load_images(images)
                if meshes:  koko.GLCANVAS.load_meshes(meshes)

                koko.GLCANVAS.loaded = True


        # Update the output pane
        koko.GLCANVAS.border = None
        koko.CANVAS.border   = None
        koko.FRAME.status = ''

        # Update the output pane
        self.output += "# #    Total time: %s s\n#" % (datetime.now() - start)

        if self.event.is_set(): return
        koko.FRAME.output = self.output

########################################

    def cad_math(self):
        """ @brief Evaluates a script to generate a FabVars data structure
            @details Stores results in self.cad and modifies UI accordingly.
            @returns True if success, False or None otherwise
        """

        koko.FRAME.status = "Converting to math string"
        now = datetime.now()

        vars = koko.PRIMS.dict
        vars['cad'] = FabVars()
        self.output += '>>  Compiling to math file\n'

        if self.event.is_set(): return

        # Modify stdout to record messages
        buffer = StringIO.StringIO()
        sys.stdout = buffer

        try:
            exec(self.script, vars)
        except:
            sys.stdout = sys.__stdout__

            # If we've failed, color the border(s) red
            koko.CANVAS.border   = (255, 0, 0)
            koko.GLCANVAS.border = (255, 0, 0)

            # Figure out where the error occurred
            errors = traceback.format_exc().split('\n')
            errors = errors[0]+'\n'+'\n'.join(errors[3:])
            for m in re.findall(r'File "<string>", line (\d+)', errors):
                error_line = int(m) - 1
            errors = errors.replace(koko.BASE_DIR, '')

            self.output += buffer.getvalue() + errors

            # Update the status line and add an error mark in the text editor
            try:
                koko.EDITOR.error_marker = error_line
                koko.FRAME.status = "cad_math failed (line %i)" % (error_line+1)
            except NameError:
                koko.FRAME.status = "cad_math failed"
        else:
            try:                self.cad = vars['cad']
            except KeyError:    self.cad = None

            self.output += buffer.getvalue()
            dT = datetime.now() - now
            self.output += "#   cad_math time: %s \n" % dT

        # Put stdout back in place
        sys.stdout = sys.__stdout__

        koko.FRAME.output = self.output

        if not self.cad:
            koko.FRAME.states = 'Error: cad_math failed'
            koko.CANVAS.border = (255, 0, 0)
            koko.GLCANVAS.border = (255, 0, 0)
            return
        elif self.cad.shapes is None:
            koko.FRAME.status = ('Error:  No shape defined!')
            koko.CANVAS.border = (255, 0, 0)
            koko.GLCANVAS.border = (255, 0, 0)
            return

        # Parse the math expression into a tree
        koko.FRAME.status = 'Converting to tree'
        for e in self.cad.shapes:
            self.output += ">>  Parsing string into tree\n"
            start = datetime.now()
            if bool(e.ptr):
                self.output += '#   parse time: %s\n' % (datetime.now() - start)
            # If we failed to parse the math expression, note the failure
            # and return False to indicate
            else:
                self.output += "Invalid math string!\n"
                koko.FRAME.status = ('Error:  Invalid math string.')
                koko.CANVAS.border = (255, 0, 0)
                self.cad = None
                return False


        koko.FRAME.output = self.output

        # Return True if we succeeded, false otherwise.
        return self.cad != None

########################################

    def make_images(self):
        """ @brief Renders a set of images from self.cad.shapes
            @returns List of Image objects
        """
        zmin = self.cad.zmin if self.cad.zmin is not None else 0
        zmax = self.cad.zmax if self.cad.zmax is not None else 0

        imgs = []
        for e in self.cad.shapes:
            if self.event.is_set(): return
            imgs.append(self.make_image(e, zmin, zmax))

        return imgs


    def make_flat_image(self, expr, scale):
        """ @brief Renders a flat single image
            @param expr MathTree expression
            @returns An Image object
        """
        region = Region(
            (expr.xmin-self.cad.border*expr.dx,
             expr.ymin-self.cad.border*expr.dy,
             0),
            (expr.xmax+self.cad.border*expr.dx,
             expr.ymax+self.cad.border*expr.dy,
             0),
            scale
        )

        koko.FRAME.status = 'Rendering with libfab'
        self.output += ">>  Rendering image with libfab\n"

        start = datetime.now()
        img = expr.render(region, interrupt=self.c_event,
                          mm_per_unit=self.cad.mm_per_unit)
        img.color = expr.color

        dT = datetime.now() - start
        self.output += "#   libfab render time: %s\n" % dT
        return img


    def make_image(self, expr, zmin, zmax):
        """ @brief Renders an expression
            @param expr MathTree expression
            @param zmin Minimum Z value (arbitrary units)
            @param zmax Maximum Z value (arbitrary units)
            @returns None for a null image, False for a failure, the Image if success.
        """

        # Adjust view bounds based on cad file scale
        # (since view bounds are in mm, we have to convert to the cad
        #  expression's unitless measure)
        xmin = self.view.xmin
        xmax = self.view.xmax
        ymin = self.view.ymin
        ymax = self.view.ymax

        if expr.xmin is None:   xmin = xmin
        else:   xmin = max(xmin, expr.xmin - self.cad.border*expr.dx)

        if expr.xmax is None:   xmax = xmax
        else:   xmax = min(xmax, expr.xmax + self.cad.border*expr.dx)

        if expr.ymin is None:   ymin = ymin
        else:   ymin = max(ymin, expr.ymin - self.cad.border*expr.dy)

        if expr.ymax is None:   ymax = ymax
        else:   ymax = min(ymax, expr.ymax + self.cad.border*expr.dy)

        region = Region( (xmin, ymin, zmin), (xmax, ymax, zmax),
                         self.view.pixels_per_unit )

        koko.FRAME.status = 'Rendering with libfab'
        self.output += ">>  Rendering image with libfab\n"

        start = datetime.now()
        img = expr.render(region, interrupt=self.c_event,
                          mm_per_unit=self.cad.mm_per_unit)

        img.color = expr.color
        dT = datetime.now() - start
        self.output += "#   libfab render time: %s\n" % dT
        return img

################################################################################

    def make_mesh(self, expr):
        """ @brief Converts an expression into a mesh.
            @returns The mesh, or False if failure.
        """

        self.output += '>>  Generating triangulated mesh\n'

        DEPTH = 0
        while DEPTH <= 4:

            region = Region(
                (expr.xmin - self.cad.border*expr.dx,
                 expr.ymin - self.cad.border*expr.dy,
                 expr.zmin - self.cad.border*expr.dz),
                (expr.xmax + self.cad.border*expr.dx,
                 expr.ymax + self.cad.border*expr.dy,
                 expr.zmax + self.cad.border*expr.dz),
                 depth=DEPTH
            )

            koko.FRAME.status = 'Rendering to ASDF'

            start = datetime.now()
            asdf = expr.asdf(region=region, mm_per_unit=self.cad.mm_per_unit,
                             interrupt=self.c_event)

            self.output += '#   ASDF render time: %s\n' % (datetime.now() - start)
            if self.event.is_set(): return
            koko.FRAME.output = self.output

            koko.FRAME.status = 'Triangulating'
            start = datetime.now()
            mesh = asdf.triangulate(interrupt=self.c_event)

            if mesh.vcount: break
            else:           DEPTH += 1

        mesh.source = Struct(
            type=MathTree, expr=expr.clone(),
            depth=DEPTH, scale=self.cad.mm_per_unit
        )

        if self.event.is_set(): return

        self.output += '#   Meshing time: %s\n' % (datetime.now() - start)
        self.output += "Generated {:,} vertices and {:,} triangles\n".format(
            mesh.vcount if mesh else 0, mesh.tcount if mesh else 0)

        koko.FRAME.output = self.output
        return mesh

################################################################################

class RefineTask(object):
    """ @class RefineTask
        @brief Task that refines a mesh in a separate thread.
    """

    def __init__(self, mesh):
        """ @brief Constructs a refine operation on a mesh and starts running in separate thread.
            @param mesh Mesh to refine
        """
        ## @var mesh
        # Target mesh
        self.mesh  = mesh

        ## @var event
        # threading.Event used to halt rendering
        self.event   = threading.Event()

        ## @var c_event
        # threading.Event used to halt rendering in C functions
        self.c_event = threading.Event()

        ## @var thread
        # threading.Thread that actually runs the task
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        """ @brief Refines a mesh (should be run in separate thread)
        """

        koko.FRAME.status = 'Refining mesh'
        self.mesh.refine()
        koko.GLCANVAS.reload_vbos()

################################################################################

class CollapseTask(object):
    """ @class CollapseTask
        @brief Task that collapses a mesh in a separate thread.
    """

    def __init__(self, mesh):
        """ @brief Constructs a collapse operation on a mesh and starts running in separate thread.
            @param mesh Mesh to collapse
        """

        ## @var mesh
        # Target mesh
        self.mesh  = mesh

        ## @var event
        # threading.Event used to halt rendering
        self.event   = threading.Event()

        ## @var c_event
        # threading.Event used to halt rendering in C functions
        self.c_event = threading.Event()

        ## @var thread
        # threading.Thread that actually runs the task
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        """ @brief Collapses a mesh (should be run in separate thread)
        """

        koko.FRAME.status = 'Collapsing mesh'
        self.mesh.collapse()
        koko.GLCANVAS.reload_vbos()
