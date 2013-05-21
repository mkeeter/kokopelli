import threading
import operator
import random

import koko
from   koko.render import RenderTask, RefineTask, CollapseTask
from   koko.export import ExportTask, FabTask

class TaskBot(object):
    """ @class TaskBot
        @brief Manages various application threads
        @details It may hold multiple render threads, up to one export thread,
        and up to one fab subprocess.  It also keeps track of the current cad structure.
    """

    def __init__(self):
        """@brief TaskBot constructor.
        """

        ## @var cached_cad
        # Saved FabVars cad structure
        self.cached_cad     = None

        ## @var export_task
        # An ExportTask exporting the current model
        self.export_task    = None

        ## @var fab_task
        # A FabTask in charge of running the fab modules
        self.fab_task       = None

        ## @var cam_task
        # A threading.Thread generating a CAM toolpath
        self.cam_task       = None

        ## @var refine_task
        # A RefineTask or CollapseTask modifying the displayed mesh
        self.refine_task    = None

        ## @var tasks
        # A list of RenderTask objects
        self.tasks = []

    def render(self, view, script=''):
        """ @brief Begins a new render task
            @param view View Struct (from Canvas.view)
            @param script Script text (if blank, uses cached result)
        """

        self.stop_threads()
        self.join_threads()

        if script:  self.tasks += [RenderTask(view, script=script)]
        else:       self.tasks += [RenderTask(view, cad=self.cached_cad)]


    def export(self, path, resolution, decimate):
        """ @brief Begins a new export task
            @param path Filename (extension is used to determine export function)
            @param resolution Export resolution (could be ignored)
            @param decimate Boolean that determines whether ASDF leafs are merged
        """
        self.export_task = ExportTask(path, self.cached_cad,
                                      resolution, decimate)


    def start_fab(self):
        """ @brief Starts the fab modules running.
            @details The FabTask is stored in self.fab_task
        """
        if self.cached_cad is None:
            dialogs.warning('Design needs to be succesfully rendered before opening fab modules!')
            return
        self.fab_task = FabTask(self.cached_cad)

    def start_cam(self):
        """ @brief Starts a CAM path generation task
            @details The CAM thread is stored in self.cam_task.
        """
        self.cam_task = threading.Thread(target=koko.FAB.run)
        self.cam_task.daemon = True
        self.cam_task.start()

    def reset(self):
        """ @brief Attempts to halt all threads and clears cached cad data.
        """
        self.cached_cad = None
        self.stop_threads()

    def stop_threads(self):
        """ @brief Informs each thread that it should stop.
            @details Threads are collected in join_threads once they obey.
        """
        for task in self.tasks:
            task.event.set()
            task.c_event.set()

        if self.refine_task:
            self.refine_task.event.set()
            self.refine_task.c_event.set()


    def join_threads(self):
        """ @brief Joins any thread whose work is finished.

            @details Grabs the cad data structure from render threads, storing
            it as cached_cad (for later re-use).

            Re-writes the cad data structure to file if the fab modules
            are running in the fab_task thread.
        """

        for task in filter(lambda t: not t.thread.is_alive(), self.tasks):
            self.cached_cad = task.cad
            if task.script:    koko.FAB.set_input(task.cad)
            task.thread.join()
            task.thread = None

            try:   self.cached_cad.write(self.fab_task.file)
            except AttributeError:  pass

        self.tasks = filter(lambda t: t.thread is not None, self.tasks)

        if self.fab_task:
            if self.fab_task.poll() is not None:
                self.fab_task = None

        if self.cam_task and not self.cam_task.is_alive():
            self.cam_task.join()
            self.cam_task = None

        if self.export_task and not self.export_task.thread.is_alive():
            self.export_task.thread.join()
            self.export_task = None

        if self.refine_task and not self.refine_task.thread.is_alive():
            self.refine_task.thread.join()
            self.refine_task = None


    def refine(self):
        """ @brief Refines or collapses mesh as needed.
        """
        if not koko.GLCANVAS.IsShown(): return

        if (self.export_task is not None or self.refine_task is not None or
            self.fab_task is not None or self.cam_task is not None):
            return

        if koko.GLCANVAS.border:    return
        if koko.GLCANVAS.LOD_complete:  return

        # Make sure that at least one leaf is expandable.
        expandable = False
        for L in koko.GLCANVAS.leafs:
            if L.expandable():  expandable = True
        if not expandable:  return


        samples = koko.GLCANVAS.sample()

        expandable = {k:samples[k] for k in samples if k.expandable()}
        collapsible = {}
        for m in koko.GLCANVAS.meshes:
            collapsible.update(m.get_fills(samples))

        # Pick the section with the smallest voxel count that occupies
        # more than 5% of the screen's visible area
        best = None
        depths = set(v.source.depth for v in expandable)
        while depths:
            c = min(depths)
            b = max(
                expandable[v] for v in expandable if v.source.depth == c
            )
            if b >= 0.05:
                best = b
                break
            depths.remove(c)

        # Pick the section with the smallest voxel count that occupies
        # less than 2.5% of the screen's visible area
        worst = None
        depths = set(v.source.depth for v in collapsible)
        while depths:
            c = min(depths)
            b = min(
                collapsible[v] for v in collapsible if v.source.depth == c
            )
            if b <= 0.025:
                worst = b
                break
            depths.remove(c)


        if worst is not None:
            mesh = [d for d in collapsible if collapsible[d] == worst][0]
            print "Collapsing mesh",mesh,"with score",worst
            self.refine_task = CollapseTask(mesh)
        elif best is not None:
            mesh = [d for d in expandable if expandable[d] == best][0]
            print "Refining mesh",mesh,"with score",best
            self.refine_task = RefineTask(mesh)

        else:
            koko.FRAME.status = ''
            koko.GLCANVAS.LOD_complete = True

