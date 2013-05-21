import os
import Queue
import sys
import weakref

import wx

# Edit the system path to find things in the lib folder
sys.path.append(os.path.join(sys.path[0], 'koko'))

################################################################################

import koko
from   koko             import NAME

print '\r'+' '*80+'\r[||||||----]    importing koko.dialogs',
sys.stdout.flush()
import koko.dialogs     as dialogs

print '\r'+' '*80+'\r[||||||----]    importing koko.frame',
sys.stdout.flush()
from   koko.frame       import MainFrame

print '\r'+' '*80+'\r[||||||||--]    importing koko.template',
sys.stdout.flush()
from   koko.template    import TEMPLATE

print '\r'+' '*80+'\r[||||||||--]    importing koko.struct',
sys.stdout.flush()
from koko.struct        import Struct

print '\r'+' '*80+'\r[||||||||--]    importing koko.taskbot',
sys.stdout.flush()
from   koko.taskbot     import TaskBot

print '\r'+' '*80+'\r[||||||||--]    importing koko.prims.core',
sys.stdout.flush()
from   koko.prims.core  import PrimSet

print '\r'+' '*80+'\r[||||||||--]    importing koko.fab',
sys.stdout.flush()
from    koko.fab.image  import Image
from    koko.fab.mesh   import Mesh
from    koko.fab.asdf   import ASDF

print '\r'+' '*80+'\r[|||||||||-]    reticulating splines',
sys.stdout.flush()

# Dummy imports so that py2app includes these files
import koko.lib.shapes
import koko.lib.shapes2d
import koko.lib.shapes3d
import koko.lib.text

################################################################################

class App(wx.App):
    def OnInit(self):

        koko.APP = weakref.proxy(self)
        koko.TASKS = TaskBot()

        self._mode = 'cad/cam'

        # Open a file from the command line
        if len(sys.argv) > 1:
            d, self.filename = os.path.split(sys.argv[1])
            self.directory = os.path.abspath(d)
        else:
            self.filename = ''
            self.directory = os.getcwd()

        # Create frame
        koko.FRAME = MainFrame(self)

        # Create a set of GUI primitives
        koko.PRIMS = PrimSet()

        # This is a brand new file
        self.saved = False
        self.reeval_required = True
        self.render_required = True

        # Snap the view to cad file bounds
        self.first_render = True

        # Show the application!
        koko.FRAME.Show()
        koko.CANVAS.SetFocus()

        # Start with the OpenGL window open to force OpenGL to
        # initialize itself, then switch back to the heightmap
        self.render_mode('3D')
        koko.GLCANVAS.init_GL()
        self.render_mode('2D')

        if self.filename:   wx.CallAfter(self.load)

        return True

    @property
    def directory(self):
        return self._directory
    @directory.setter
    def directory(self, value):
        try:
            sys.path.remove(self._directory)
        except (AttributeError, ValueError):
            pass
        self._directory = value
        if self.directory != '':
            os.chdir(self.directory)
            sys.path.append(self.directory)

    @property
    def mode(self):
        return self._mode
    @mode.setter
    def mode(self, value):
        """ @brief Switches between CAD/CAM and CAM modes
            @param value New mode (either 'cad/cam' or 'cam')
        """
        self._mode = value
        if value == 'cam':
            koko.FRAME.get_menu('File','Reload').Enable(False)
            koko.FRAME.get_menu('File','Save').Enable(False)
            koko.FRAME.get_menu('File','Save As').Enable(False)
            koko.FRAME.get_menu('View','Show script').Enable(False)
            koko.FRAME.get_menu('View','Show script').Check(False)
            koko.FRAME.show_script(False)
            koko.FRAME.get_menu('View','Show output').Enable(False)
            koko.FRAME.get_menu('View','Show output').Check(False)
            koko.FRAME.show_output(False)
            koko.FRAME.get_menu('View','Re-render').Enable(False)
            for e in ['.math','.png','.svg','.stl',
                      '.dot','.asdf','Start fab modules']:
                koko.FRAME.get_menu('Export', e).Enable(False)
            koko.FRAME.get_menu('Export','Show CAM panel').Check(True)
            koko.FRAME.show_cam(True)

        elif value == 'cad/cam':
            koko.FRAME.get_menu('File','Reload').Enable(True)
            koko.FRAME.get_menu('File','Save').Enable(True)
            koko.FRAME.get_menu('File','Save As').Enable(True)
            koko.FRAME.get_menu('View','Show script').Enable(True)
            koko.FRAME.get_menu('View','Show output').Enable(True)
            koko.FRAME.get_menu('View','Re-render').Enable(True)
            for e in ['.math','.png','.svg','.stl',
                      '.dot','.asdf','Start fab modules']:
                koko.FRAME.get_menu('Export', e).Enable(True)

################################################################################

    def savepoint(self, event):
        """ @brief Callback when a save point is reached in the editor.
            @param event Either a boolean value or a StyledTextEvent
            from the callback.
        """
        if type(event) is wx.stc.StyledTextEvent:
            value = (event.EventType == wx.stc.wxEVT_STC_SAVEPOINTREACHED)
        else:
            value = event

        if value == self.saved: return

        # Modify the window titlebar.
        self.saved = value
        s = '%s:  ' % NAME
        if self.filename:
            s += self.filename
        else:
            s += '[Untitled]'

        if not self.saved:
            s += '*'

        koko.FRAME.SetTitle(s)


################################################################################

    def new(self, event=None):
        """ @brief Creates a new file from the default template. """
        if self.saved or dialogs.warn_changes():

            self.filename = ''
            self.mode = 'cad/cam'
            self.clear()

            koko.EDITOR.text = TEMPLATE

            self.first_render = True

################################################################################

    def save(self, event=None):
        """ @brief Save callback from main menu.
        """

        # If we don't have a filename, perform Save As instead
        if self.filename == '':
            self.save_as()
        else:
            # Write out the file
            path = os.path.join(self.directory, self.filename)

            if koko.PRIMS.shapes != []:
                text = ('''##    Geometry header    ##
%s
##    End of geometry header    ##
''' % koko.PRIMS.to_script()) + koko.EDITOR.text
            else:
                text = koko.EDITOR.text

            with open(path, 'w') as f:
                f.write(text)

            # Tell the editor that we've saved
            # (this invokes the callback to change title text)
            koko.EDITOR.SetSavePoint()

            # Update the status box.
            koko.FRAME.status = 'Saved file %s' % self.filename

################################################################################

    def save_as(self, event=None):
        """ @brief Save As callback from main menu.
        """

        # Open a file dialog to get target
        df = dialogs.save_as(self.directory, extension='.cad')

        if df[1] != '':
            self.directory, self.filename = df
            self.save()

################################################################################

    def reload(self, event=None):
        """ @brief Reloads the current file, warning of changes if necessary.
        """
        if self.filename != ''  and (self.saved or dialogs.warn_changes()):
            self.load()
            self.first_render = False

################################################################################

    def clear(self):
        """ @brief Clears all data from previous file.
        """
        koko.TASKS.reset()
        koko.PRIMS.clear()
        koko.CANVAS.clear()
        koko.GLCANVAS.clear()

    def load(self):
        """ @brief Loads the current design file
            @details The file is defined by self.directory and self.filename
        """
        self.clear()

        path = os.path.join(self.directory, self.filename)

        if path[-4:] == '.cad':
            with open(path, 'r') as f:
                text = f.read()
                if text.split('\n')[0] == '##    Geometry header    ##':
                    koko.PRIMS.reconstruct(eval(text.split('\n')[1]))
                    koko.PRIMS.undo_stack = [koko.PRIMS.reconstructor()]
                    text = '\n'.join(text.split('\n')[3:])
            koko.EDITOR.text = text
            koko.FRAME.status = 'Loaded .cad file'

            self.mode = 'cad/cam'
            self.first_render = True
            self.savepoint(True)

        elif path[-4:] == '.png':
            self.mode = 'cam'
            img = Image.load(path)
            koko.CANVAS.load_image(img)
            koko.GLCANVAS.load_image(img)
            koko.FAB.set_input(img)
            wx.CallAfter(self.snap_bounds)

        elif path[-4:] == '.stl':
            self.mode = 'cam'
            mesh = Mesh.load(path)
            koko.GLCANVAS.load_mesh(mesh)
            wx.CallAfter(self.snap_bounds)

        elif path[-5:] == '.asdf':
            self.render_mode('3D')
            self.mode = 'cam'

            msg = dialogs.display_message('Loading...', 'Loading ASDF.')
            msg.Raise()
            wx.Yield()

            asdf = ASDF.load(path)
            msg.txt.SetLabel('Triangulating')
            wx.Yield()

            mesh = asdf.triangulate()
            mesh.source = Struct(type=ASDF, file=path, depth=0)
            msg.Destroy()

            koko.GLCANVAS.load_mesh(mesh)
            koko.FAB.set_input(asdf)


################################################################################

    def open(self, event=None):
        """ @brief Open a file dialog to get a target, then load it.
        """
        # Open a file dialog to get target
        if self.saved or dialogs.warn_changes():
            df = dialogs.open_file(self.directory)
            if df[1] != '':
                self.directory, self.filename = df
                self.load()

################################################################################

    def exit(self, event=None):
        """ @brief Warns of unsaved changes then exits.
        """
        if self.saved or dialogs.warn_changes():
            koko.FRAME.Destroy()

            # Delete these objects to avoid errors due to deletion order
            # during Python's cleanup stage
            del koko.FRAME
            del koko.EDITOR
            del koko.CANVAS
            del koko.GLCANVAS

################################################################################

    def snap_bounds(self, event=None):
        if koko.CANVAS.IsShown():
            koko.CANVAS.snap_bounds()
        if koko.GLCANVAS.IsShown():
            koko.GLCANVAS.snap_bounds()

    def snap_axis(self, event=None):
        axis = koko.FRAME.GetMenuBar().FindItemById(event.GetId()).GetLabel()
        if koko.CANVAS.IsShown():
            koko.CANVAS.snap_axis(axis)
        if koko.GLCANVAS.IsShown():
            koko.GLCANVAS.snap_axis(axis)

################################################################################

    def mark_changed_design(self, event=None):
        ''' Mark that the design needs to be re-evaluated and re-rendered.'''
        self.reeval_required = True

    def mark_changed_view(self, event=None):
        ''' Mark that the design needs to be re-rendered
            (usually because of a view change) '''

        self.render_required = True


################################################################################

    def idle(self, event=None):

        # Check the threads and clear out any that are dead
        koko.TASKS.join_threads()

        # Snap the bounds to the math file if this was the first render.
        if koko.TASKS.cached_cad and self.first_render:
            koko.CANVAS.snap_bounds()
            koko.GLCANVAS.snap_bounds()
            self.first_render = False
            self.render_required = True

        # We can't render until we have a valid math file
        if self.render_required and not koko.TASKS.cached_cad:
            self.render_required = False
            self.reeval_required = True

        # Recalculate math file then render
        if self.reeval_required:
            if self.mode == 'cad/cam':  self.reeval()
            self.reeval_required = False
            self.render_required = False

        # Render given valid math file
        if self.render_required:
            if self.mode == 'cad/cam':  self.render()
            self.render_required = False

        koko.TASKS.refine()


################################################################################

    def render(self):
        ''' Render the image, given the existing math file.'''
        koko.TASKS.render(koko.CANVAS.view)

    def reeval(self):
        ''' Render the image, calculating a new math file.'''
        koko.TASKS.render(koko.CANVAS.view,
                          script=koko.EDITOR.text)


    def render_mode(self, event):
        if type(event) is str:
            t = event
        else:
            t = koko.FRAME.GetMenuBar().FindItemById(event.GetId()).GetLabel()

        shading = koko.FRAME.get_menu('View', 'Shading mode')

        if '3D' in t:
            for s in shading:   s.Enable(True)
            koko.CANVAS.Hide()
            koko.GLCANVAS.snap = not koko.GLCANVAS.IsShown()
            koko.GLCANVAS.Show()
        elif '2D' in t:
            for s in shading:   s.Enable(False)
            koko.GLCANVAS.Hide()
            koko.CANVAS.snap = not koko.CANVAS.IsShown()
            koko.CANVAS.Show()
        elif 'Both' in t:
            for s in shading:   s.Enable(True)
            koko.CANVAS.snap   = not koko.CANVAS.IsShown()
            koko.GLCANVAS.snap = not koko.GLCANVAS.IsShown()
            koko.CANVAS.Show()
            koko.GLCANVAS.Show()
        koko.FRAME.Layout()
        koko.FRAME.Refresh()

        self.mark_changed_view()

################################################################################

    def export(self, event):
        ''' General-purpose export callback.  Decides which export
            command to call based on the menu item text.'''

        item = koko.FRAME.GetMenuBar().FindItemById(event.GetId())
        filetype = item.GetLabel()

        cad = koko.TASKS.cached_cad

        if 'failed' in koko.FRAME.status:
            dialogs.warning('Design has errors!  Export failed.')
            return
        elif cad is None:
            dialogs.warning('Design needs to be rendered before exporting!  Export failed')
            return
        elif koko.TASKS.export_task:
            dialogs.warning('Export already in progress.')
            return
        elif filetype in ['.png','.svg'] and any(
                getattr(cad,b) is None
                for b in ['xmin','xmax','ymin','ymax']):
            dialogs.warning('Design needs to be bounded along X and Y axes ' +
                            'to export %s' % filetype)
            return
        elif filetype in ['.stl','.asdf'] and any(
                getattr(cad,b) is None
                for b in ['xmin','xmax','ymin','ymax','zmin','zmax']):
            dialogs.warning('Design needs to be bounded on all axes '+
                            'to export %s' % filetype)
            return
        elif filetype == '.svg' and cad.zmin is not None:
            dialogs.warning('Design must be flat (without z bounds)'+
                            ' to export .svg')
            return


        # Open up a dialog box to get the export resolution or settings
        if filetype == '.asdf':
            dlg = dialogs.ResolutionDialog(10, '.asdf export',
                                   cad, 'Merge leaf cells')
        elif filetype == '.stl':
            dlg = dialogs.ResolutionDialog(10, '.stl export',
                                   cad, 'Watertight')
        elif filetype == '.png':
            dlg = dialogs.ResolutionDialog(10, '.stl export',
                                   cad, 'Heightmap')
        elif filetype in '.svg':
            dlg = dialogs.ResolutionDialog(10, '%s export' % filetype,
                                    cad)
        elif filetype == '.dot':
            dlg = dialogs.CheckDialog('.dot export', 'Packed arrays')
        else:
            dlg = None

        if dlg and dlg.ShowModal() == wx.ID_OK:
            resolution = dlg.result
            checked    = dlg.checked
            success = True
        elif dlg:
            success = False
        else:
            resolution = None
            checked = None
            success = True
        if dlg: dlg.Destroy()

        # If we didn't get a valid resolution, then abort
        if not success:  return

        # Open up a save as dialog to get the export target
        df = dialogs.save_as(self.directory, extension=filetype)
        if df[1] == '':     return
        path = os.path.join(*df)

        koko.TASKS.export(path, resolution, checked)

################################################################################

    def start_fab(self, event=None):
        ''' Starts the fab modules.'''
        koko.TASKS.start_fab()

################################################################################

    def show_library(self, event):

        item = koko.FRAME.GetMenuBar().FindItemById(event.GetId())
        name = item.GetLabel()

        if koko.BUNDLED:
            path = koko.BASE_DIR + name.split('.')[-1] + '.py'
        else:
            v = {}
            exec('import %s as module' % name.replace('koko.',''), v)
            path = v['module'].__file__.replace('.pyc','.py')

        dialogs.TextFrame(name, path)
