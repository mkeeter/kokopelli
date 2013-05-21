""" @module CAM workflow module
"""
import sys

import wx
import wx.lib.stattext

import koko

from koko.cam.inputs    import INPUTS
from koko.cam.machines  import MACHINES

from koko.cam.panel     import OutputPanel

from koko.themes       import APP_THEME

################################################################################

class OutputSelector(wx.Panel):
    """ @class OutputSelector
        @brief  Contains a wx.Choice panel to select between machines.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Output',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        self.machines = MACHINES

        menu = wx.Choice(self, wx.ID_ANY,
                         choices=[m.NAME for m in self.machines])
        self.Bind(wx.EVT_CHOICE, self.choice)
        sizer.Add(menu, flag=wx.CENTER|wx.TOP, border=5)

        self.SetSizerAndFit(sizer)

    def choice(self, event):
        """ Regenerates CAM workflow UI based on the selected machine
            @param event wx.Event for choice selection
        """
        self.parent.set_output(self.machines[event.GetSelection()])

################################################################################

class DefaultSelector(wx.Panel):
    """ @class DefaultSelector
        @brief  Contains a wx.Choice panel to select between defaults.
    """

    def __init__(self, parent, defaults):
        """ @brief Creates a DefaultSelector panel
            @param parent Parent UI panel
            @param defaults List of defaults
        """
        wx.Panel.__init__(self, parent)

        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY,
            label='Defaults', style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        menu = wx.Choice(self, wx.ID_ANY, choices=[d[0] for d in defaults])
        self.defaults = [d[1] for d in defaults]

        self.Bind(wx.EVT_CHOICE, self.choice)
        sizer.Add(menu, flag=wx.CENTER|wx.TOP, border=5)

        self.SetSizerAndFit(sizer)

    def choice(self, evt):
        """ @brief Applies the selected defaults
            @param evt  wx.Event from the wx.Choice selection
        """
        self.parent.apply_defaults(self.defaults[evt.GetSelection()])

################################################################################

class FabWorkflowPanel(wx.Panel):
    """ @brief CAM UI Workflow panel
    """

    def __init__(self, parent):
        """ @brief Creates a FabWorkflowPanel
            @param parent Parent wx.Frame object
        """
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(OutputSelector(self),
                       flag=wx.EXPAND|wx.TOP,  border=10)

        self.SetSizerAndFit(self.sizer)

        """
        @var input  Input module (initially None)
        @var output Output module (initially null)
        @var panels List of FabPanels in workflow
        @var defaults   DefaultSelector panel
        """
        self.input      = None
        self.output     = MACHINES[0]
        self.panels     = []
        self.defaults   = None

    def regenerate(self, input, output):
        """ @brief Regenerates the workflow UI
            @param input    Input data structure
            @param output   Output module
        """

        self.input = [i for i in INPUTS if i.TYPE == type(input)][0]

        # Make sure we can find a path from the start panel to
        # the desired path panel.
        if output.INPUT in self.input.WORKFLOWS:
            self.output = output

        # If that fails, then load the None machine as our output
        else:
            self.output = MACHINES[0]

        for p in self.panels:   p.Destroy()
        if self.defaults:       self.defaults.Destroy()
        self.panels = []
        self.defaults = None

        if self.output.DEFAULTS:
            self.defaults = DefaultSelector(self, output.DEFAULTS)
            self.sizer.Add(self.defaults, flag=wx.EXPAND|wx.TOP, border=10)

        workflow = (
            self.input.WORKFLOWS[self.output.INPUT] +
            (self.output.INPUT, self.output.PANEL)
        )

        for p in workflow:
            if p is None:   continue

            panel = p(self)

            self.panels.append(panel)
            self.sizer.Add(panel, flag=wx.EXPAND|wx.TOP, border=10)

        APP_THEME.apply(self)
        self.Layout()


    def set_input(self, input):
        """ @brief Loads an input data structure, regenerating the workflow if necessary
            @param input Input data structure
        """
        if input is None:
            return
        elif self.input is None or self.input.TYPE != type(input):
            self.regenerate(input, self.output)
        elif self.panels:
            self.invalidate()
        self.update(input)


    def update(self, input=None):
        """ @brief Updates each panel based on input data structure
            @details If input is None or a wx.Event structure, uses most recent input (extracted from first panel in workflow).
            @param input Input data structure
        """
        if input is None or isinstance(input, wx.Event):
            input = self.panels[0].input

        i = {'input': input}
        for p in self.panels:
            i = p.update(**i)


    def set_output(self, machine):
        """ @brief Sets the output machine, regenerating the workflow if necessary
            @param machine Module describing output
        """
        input = self.panels[0].input
        if self.output != machine:
            if self.panels: self.invalidate()
            self.regenerate(self.panels[0].input, machine)
        self.update(input)

    def apply_defaults(self, defaults):
        """ @brief Applies a set of defaults to UI panels
            @param defaults Default settings
        """
        self.invalidate()
        for p in self.panels:
            p.apply_defaults(defaults)
        self.update()


    def start(self, event=None):
        """ @brief Runs the CAM workflow in a separate thread
        """
        self.panels[-1].gen_button.SetLabel('Running...')
        self.panels[-1].gen_button.Enable(False)

        # Save the wx widget values to local dictionaries
        # (since wx functions don't like being called by
        #  threads other than the main thread)
        for p in self.panels:   p.store_values()

        # Start the CAM workflow generation running in a
        # separate thread.
        koko.TASKS.start_cam()


    def run(self):
        """ @brief Generates a toolpath
            @detail This function should be called in a separate thread to avoid stalling the UI
        """
        success = True
        result = {}
        for p in self.panels:
            result = p.run(**result)
            if result is False: break
        else:
            self.panels[-1].enable()

        wx.CallAfter(self.panels[-1].gen_button.SetLabel, 'Generate')
        wx.CallAfter(self.panels[-1].gen_button.Enable, True)


    def invalidate(self, event=None):
        """ @brief Invalidates final panel in workflow
            @details Disables Save and Start buttons, and deletes paths from canvases to indicate that a generated path is no longer valid.
        """
        APP_THEME.apply(self)
        if isinstance(self.panels[-1], OutputPanel):
            self.panels[-1].invalidate()
        koko.CANVAS.clear_path()
        koko.GLCANVAS.clear_path()
        if event:   event.Skip()
