import os
import sys

import wx
import wx.lib.stattext

import  koko
from    koko.about     import show_about_box

print '\r'+' '*80+'\r[||||||----]    importing koko.canvas',
sys.stdout.flush()
from    koko.canvas    import Canvas

print '\r'+' '*80+'\r[|||||||---]    importing koko.glcanvas',
sys.stdout.flush()
from    koko.glcanvas  import GLCanvas

print '\r'+' '*80+'\r[||||||||--]    importing koko.editor',
sys.stdout.flush()
from    koko.editor    import Editor

from    koko.themes    import APP_THEME
from    koko.cam.workflow import FabWorkflowPanel

import subprocess

################################################################################

class MainFrame(wx.Frame):

    def __init__(self, app):

        wx.Frame.__init__(self, parent=None)

        # Build menus and bind callback
        self.build_menus(app)

        # Bind idle callback
        self.Bind(wx.EVT_IDLE, app.idle)

        # The main sizer for the application
        sizer = wx.BoxSizer(wx.VERTICAL)
        version = '%s %s' % (koko.NAME, koko.VERSION)
        sizer.Add(wx.StaticText(self, label=version),
                                flag=wx.ALIGN_RIGHT|wx.ALL, border=5)

        # Horizontal sizer that contains script, output, and canvases
        core = wx.BoxSizer(wx.HORIZONTAL)

        editor_panel = wx.Panel(self)
        editor_sizer = wx.BoxSizer(wx.VERTICAL)

        # Vertical sizer that contains the editor and the output panel
        koko.EDITOR = Editor(editor_panel, style=wx.NO_BORDER, size=(300, 400))
        koko.EDITOR.load_template()
        koko.EDITOR.bind_callbacks(app)

        editor_sizer.Add(koko.EDITOR, proportion=2, flag=wx.EXPAND)
        self.show_editor = lambda b: editor_sizer.ShowItems(b)

        self._output = Editor(editor_panel, margins=False,
                              style=wx.NO_BORDER, size=(300, 100))
        self._output.SetWrapStartIndent(4)
        self._output.SetReadOnly(True)
        self._output.SetCaretLineVisible(False)
        self._output.SetWrapMode(wx.stc.STC_WRAP_WORD)
        editor_sizer.Add(self._output, proportion=1, border=10,
                         flag=wx.EXPAND|wx.TOP)
        editor_panel.SetSizerAndFit(editor_sizer)

        self.show_editor = lambda b: editor_panel.Show(b)

        # Vertical / Horizontal sizer that contains the two canvases
        canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        self.set_canvas_orientation = lambda o: canvas_sizer.SetOrientation(o)

        koko.CANVAS = Canvas(self, app, size=(300, 300))
        canvas_sizer.Add(koko.CANVAS, proportion=1, flag=wx.EXPAND)
        koko.GLCANVAS = GLCanvas(self, size=(300, 300))
        canvas_sizer.Add(koko.GLCANVAS, proportion=1, flag=wx.EXPAND)
        koko.GLCANVAS.Hide()

        core.Add(editor_panel, proportion=4,
                 flag=wx.EXPAND|wx.RIGHT, border=10)
        core.Add(canvas_sizer, proportion=6,
                 flag=wx.EXPAND|wx.RIGHT, border=10)
        koko.FAB = FabWorkflowPanel(self)
        core.Add(koko.FAB, proportion=3,
                 flag=wx.EXPAND|wx.RIGHT, border=10)
        koko.FAB.Hide()

        sizer.Add(core, proportion=1, flag=wx.EXPAND)

        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._hint = wx.lib.stattext.GenStaticText(self)
        bottom_sizer.Add(self._hint, proportion=1)

        self._status = wx.lib.stattext.GenStaticText(
            self, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE
        )
        bottom_sizer.Add(self._status, proportion=1)

        sizer.Add(bottom_sizer, flag=wx.EXPAND|wx.ALL, border=10)

        self.SetSizerAndFit(sizer)
        APP_THEME.apply(self)

        self._status.SetForegroundColour(wx.Colour(100, 100, 100))

        # By default, hide the output panel
        self._output.Hide()
        self.Layout()

        """
        # Settings for screen recording
        self.SetClientSize((1280, 720))
        self.SetPosition((0,wx.DisplaySize()[1] - self.GetSize()[1]))
        """

        self.Maximize()


################################################################################

    def build_menus(self, app):
        '''Build a set of menus and attach associated callbacks.'''

        def attach(menu, command, callback, shortcut='', help='',
                   wxID=wx.ID_ANY, attach_function = None):
            '''Helper function to add an item to a menu and bind the
               associated callback.'''

            if shortcut:    menu_text = '%s\t%s' % (command, shortcut)
            else:           menu_text = command

            if attach_function is None:
                attach_function = menu.Append

            item = attach_function(wxID, menu_text, help)
            self.Bind(wx.EVT_MENU, callback, item)

            return item

        menu_bar = wx.MenuBar()

        file = wx.Menu()
        attach(file, 'New', app.new, 'Ctrl+N', 'Start a new design', wx.ID_NEW)
        file.AppendSeparator()

        attach(file, 'Open', app.open, 'Ctrl+O', 'Open a design file', wx.ID_OPEN)
        attach(file, 'Reload', app.reload, 'Ctrl+R', 'Reload the current file')

        file.AppendSeparator()

        attach(file, 'Save', app.save, 'Ctrl+S',
               'Save the current file', wx.ID_SAVE)
        attach(file, 'Save As', app.save_as, 'Ctrl+Shift+S',
               'Save the current file', wx.ID_SAVEAS)

        if not 'Darwin' in os.uname():
            file.AppendSeparator()

        attach(file, 'About', show_about_box, '',
               'Display an About box', wx.ID_ABOUT)
        attach(file, 'Exit', app.exit, 'Ctrl+Q',
               'Terminate the program', wx.ID_EXIT)

        menu_bar.Append(file, 'File')

        view = wx.Menu()
        output = attach(view, 'Show output', self.show_output, 'Ctrl+D',
                        'Display errors in a separate pane',
                         attach_function=view.AppendCheckItem)
        script = attach(view, 'Show script', self.show_script, 'Ctrl+T',
                        'Display Python script',
                         attach_function=view.AppendCheckItem)
        script.Toggle()

        view.AppendSeparator()
        attach(view, '2D', app.render_mode,
               attach_function=view.AppendRadioItem)
        attach(view, '3D', app.render_mode,
               attach_function=view.AppendRadioItem)
        attach(view, 'Both', app.render_mode,
               attach_function=view.AppendRadioItem)

        view.AppendSeparator()

        shaders = wx.Menu()
        for s in [
            'Shaded', 'Wireframe',
            'Normals', 'Subdivision'
        ]:
            m = shaders.AppendRadioItem(wx.ID_ANY, s)
            m.Enable(False)
            if s == 'Show shaded':    m.Check(True)
            self.Bind(wx.EVT_MENU, lambda e: self.Refresh(), m)

        view.AppendSubMenu(shaders, 'Shading mode')

        view.AppendSeparator()

        attach(view, 'Show axes', lambda e: self.Refresh(),
               'Display X, Y, and Z axes on frame',
               attach_function=view.AppendCheckItem)
        attach(view, 'Show bounds', lambda e: self.Refresh(),
               'Display object bounds',
               attach_function=view.AppendCheckItem)
        attach(view, 'Show traverses', lambda e: self.Refresh(),
               'Display toolpath traverses',
               attach_function=view.AppendCheckItem)

        view.AppendSeparator()

        attach(view, 'Re-render', app.mark_changed_design, 'Ctrl+Enter',
              'Re-render the output image')


        menu_bar.Append(view, 'View')

        export = wx.Menu()
        attach(export, '.math', app.export, help='Export to .math file')
        attach(export, '.png',  app.export, help='Export to image file')
        attach(export, '.svg',  app.export, help='Export to svg file')
        attach(export, '.stl',  app.export, help='Export to stl file')
        attach(export, '.dot',  app.export, help='Export to dot / Graphviz file')
        export.AppendSeparator()
        attach(export, '.asdf', app.export, help='Export to .asdf file')
        export.AppendSeparator()
        attach(export, 'Show CAM panel', self.show_cam, 'Ctrl+M', '',
               attach_function=export.AppendCheckItem)

        if koko.BUNDLED:    fab.Enable(False)
        menu_bar.Append(export, 'Export')

        libraries = wx.Menu()

        attach(libraries, 'koko.lib.shapes2d', app.show_library,
               help='2D Shapes library')
        attach(libraries, 'koko.lib.shapes3d', app.show_library,
               help='3D Shapes library')
        attach(libraries, 'koko.lib.text', app.show_library,
               help='Text library')


        menu_bar.Append(libraries, 'Libraries')

        self.SetMenuBar(menu_bar)

        self.Bind(wx.EVT_MENU_HIGHLIGHT, self.OnMenuHighlight)
        self.Bind(wx.EVT_MENU_CLOSE, self.OnMenuClose)

################################################################################

    @property
    def status(self):
        return self._status.GetLabel()
    @status.setter
    def status(self, value):
        wx.CallAfter(self._status.SetLabel, value)
    def set_status(self, value):
        self.status = value

################################################################################

    @property
    def hint(self):
        return self._hint.GetLabel()
    @hint.setter
    def hint(self, value):
        wx.CallAfter(self._hint.SetLabel, value)
    def set_hint(self, value):
        self.hint = value

################################################################################

    @property
    def output(self):
        return self._output.text
    @output.setter
    def output(self, value):
        self._output.text = value
    def set_output(self, value):
        self.output = value

################################################################################

    def OnMenuHighlight(self, event):
        '''Sets an appropriate hint based on the highlighted menu item.'''
        id = event.GetMenuId()
        item = self.GetMenuBar().FindItemById(id)
        if not item or not item.GetHelp():
            self.hint = ''
        else:
            self.hint = item.GetHelp()

    def OnMenuClose(self, event):
        '''Clears the menu item hint.'''
        self.hint = ''

    def show_output(self, evt):
        ''' Shows or hides the output panel. '''
        if type(evt) is not bool:   evt = evt.Checked()

        if evt:
            if koko.EDITOR.IsShown():
                self._output.Show()
        else:               self._output.Hide()
        self.Layout()

    def show_script(self, evt):
        ''' Shows or hides the script panel. '''
        if type(evt) is not bool:   evt = evt.Checked()

        if evt:
            self.show_editor(True)
            self.set_canvas_orientation(wx.VERTICAL)
        else:
            self.show_editor(False)
            self.set_canvas_orientation(wx.HORIZONTAL)
        self.Layout()

    def show_cam(self, evt):
        if type(evt) is not bool:   evt = evt.Checked()
        koko.FAB.Show(evt)
        self.Layout()

    def get_menu(self, *args):
        m = [m[0] for m in self.GetMenuBar().Menus
                  if m[1] == args[0]][0]

        m = [m for m in m.GetMenuItems() if m.GetLabel() == args[1]][0]

        sub = m.GetSubMenu()
        if sub is None: return m
        else:           return sub.GetMenuItems()



