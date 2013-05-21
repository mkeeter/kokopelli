"""@package panel Parent classes for CAM UI panels.
"""

import os
import shutil

import wx
import wx.lib.stattext

import koko
import koko.dialogs as dialogs

class FabPanel(wx.Panel):
    """ @class FabPanel
        @brief Parent class for a CAM workflow panel.
    """

    def __init__(self, parent):
        """ @brief Initializes a FabPanel.
            @param parent   parent panel
        """
        wx.Panel.__init__(self, parent)

        ## @var parent
        # Parent UI panel
        self.parent = parent

        ## @var names
        # List of variable names
        self.names  = []

        ## @var labels
        # List of GenStaticText labels (UI elements)
        self.labels = []

        ## @var params
        # List of UI parameter widgets (textbox, choice, or check box)
        self.params = []

        ## @var types
        # List of desired parameter types
        self.types  = []

        ## @var checks
        # List of lambda functions to check parameter validity
        self.checks = []


    def construct(self, title, parameters):
        """ @brief Populates the panel with UI elements.
            @param title    Panel title
            @param parameters   List of (label, name, type, checker) tuples
        """

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label=title,
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND)

        gs = wx.FlexGridSizer(len(parameters), 2, 5, 5)
        gs.SetFlexibleDirection(wx.VERTICAL)
        gs.AddGrowableCol(0, 1)
        gs.AddGrowableCol(1, 1)
        for i in range(len(parameters)):    gs.AddGrowableRow(i)

        for P in parameters:
            if len(P) == 3:
                label, name, cls = P
                check = lambda f: True
            elif len(P) == 4:
                label, name, cls, check = P

            label = wx.StaticText(self, label=label)

            gs.Add(label, flag=wx.ALIGN_CENTER_VERTICAL)

            if cls in [int, float]:
                p = wx.TextCtrl(self, wx.ID_ANY, style=wx.NO_BORDER)
                gs.Add(p, flag=wx.ALIGN_CENTER_VERTICAL)
                p.Bind(wx.EVT_CHAR, self.parent.invalidate)
            elif cls is bool:
                p = wx.CheckBox(self)
                gs.Add(p, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
                p.Bind(wx.EVT_CHECKBOX, self.parent.invalidate)
            elif type(cls) in [list, tuple]:
                p = wx.Choice(self, wx.ID_ANY, choices=cls)
                gs.Add(p, flag=wx.CENTER|wx.ALIGN_CENTER_VERTICAL)
                p.Bind(wx.EVT_CHOICE, self.parent.invalidate)
            else:
                raise ValueError('Invalid parameter description '+str(p))

            self.names.append(name)
            self.labels.append(label)
            self.params.append(p)
            self.types.append(cls)
            self.checks.append(check)


            setattr(self, name, p)

        sizer.Add(gs, proportion=1, flag=wx.EXPAND|wx.TOP, border=5)
        self.SetSizerAndFit(sizer)


    def update(self, **kwargs):        return kwargs
    def run(self, **kwargs):           return kwargs


    def apply_defaults(self, defaults):
        """ @brief Applies a defaults dictionary to this panel.
            @param defaults Dictionary mapping parameter names to default values
        """
        if not type(self) in defaults:  return

        for p, v in defaults[type(self)]:
            if type(getattr(self, p)) is wx.TextCtrl:
                getattr(self, p).SetValue(str(v))
            elif type(getattr(self, p)) is wx.CheckBox:
                getattr(self, p).SetValue(bool(v))
            elif type(getattr(self, p)) is wx.Choice:
                i = getattr(self, p).GetStrings().index(v)
                getattr(self, p).SetSelection(i)


    def store_values(self):
        """ @brief Copies parameter values to self.values.

            @details
            This saves parameter values so that we don't have to call wx functions in a separate thread.
        """
        self.values = {}
        for name in self.names:
            i = self.names.index(name)

            # TextCtrl
            if self.types[i] in [int, float]:
                self.values[name] = self.params[i].GetValue()
            # Check box
            elif self.types[i] is bool:
                self.values[name] = self.params[i].IsChecked()
            # Choice
            elif type(self.types[i]) in [list, tuple]:
                self.values[name] = self.params[i].GetSelection()


    def get_values(self, names=None):
        """ @brief Returns a dictionary of panel values.  If a parameter cannot be acquired or a validator fails, marks the error and returns False.

            @param names Names of parameters to return (default of None gives all parameters)
        """

        if names is None:   names = self.names

        values = {}
        for name in names:
            i = self.names.index(name)
            success = True

            # TextCtrl
            if self.types[i] in [int, float]:
                try:   values[name] = self.types[i](self.values[name])
                except ValueError:  success = False
            # Check box
            elif self.types[i] is bool:
                values[name] = self.values[name]
            # Choice
            elif type(self.types[i]) in [list, tuple]:
                values[name] = self.values[name]

            # Validator function
            if success and not self.checks[i](values[name]):
                success = False

            if not success:
                wx.CallAfter(self.labels[i].SetBackgroundColour, '#853535')
                wx.CallAfter(self.labels[i].SetForegroundColour, '#ffffff')
                koko.FRAME.status = 'Invalid value for %s' % name
                return False

        return values


################################################################################

class OutputPanel(FabPanel):
    """ @class OutputPanel
        @brief Subclass of FabPanel with Generate and Save buttons
    """

    def __init__(self, parent):
        """ Initializes an OutputPanel.
            @param parent   Parent panel
        """
        FabPanel.__init__(self, parent)

    def construct(self, title=None, parameters=[], start=False):
        """ Constructs UI elements for an OutputPanel
            @param title Panel title
            @param parameters List of (label, name, type, checker) tuples
            @param start Boolean indicating if the panel should show a Start button
        """

        if title is not None:
            FabPanel.construct(self, title, parameters)

        hs = wx.BoxSizer(wx.HORIZONTAL)

        ## @var gen_button
        # wx.Button to generate toolpath
        self.gen_button = wx.Button(self, id=wx.ID_ANY, label='Generate')
        self.gen_button.Bind(wx.EVT_BUTTON, self.parent.start)

        ## @var save_button
        # wx.Button to save toolpath
        self.save_button = wx.Button(self, id=wx.ID_ANY, label='Save')
        self.save_button.Enable(False)
        self.save_button.Bind(wx.EVT_BUTTON, self.save)
        hs.Add(self.gen_button,   flag=wx.ALL, border=5)
        hs.Add(self.save_button,  flag=wx.ALL, border=5)

        ## @var start_button
        # wx.Button to start machine running (optional)
        if start:
            self.start_button = wx.Button(self, id=wx.ID_ANY, label='Start')
            self.start_button.Enable(False)
            self.start_button.Bind(wx.EVT_BUTTON, self.start)
            hs.Add(self.start_button, flag=wx.ALL, border=5)
        else:
            self.start_button = None

        sizer = self.GetSizer()
        sizer.Add(hs, flag=wx.TOP|wx.CENTER, border=5)
        self.SetSizerAndFit(sizer)

    def save(self, event=None):
        """@ brief Saves a generated toolpath file with the appropriate extension.
        """
        dir, file = dialogs.save_as(koko.APP.directory,
                                    extension=self.extension)
        if file == '':  return
        path = os.path.join(dir, file)
        shutil.copy(self.file.name, path)


    def start(self, event=None):
        """@brief Sends a file to a machine (overloaded in children)
        """
        raise NotImplementedError(
            'start needs to be overloaded in machine class'
        )

    def enable(self):
        """@brief Enables Generate, Save, and Start buttons (if present)
        """
        wx.CallAfter(self.gen_button.Enable, True)
        wx.CallAfter(self.save_button.Enable, True)
        if self.start_button:
            wx.CallAfter(self.start_button.Enable, True)

    def invalidate(self):
        """@brief  Enables Generate button and disables Save and Start buttons.
        """
        self.gen_button.Enable(True)
        self.save_button.Enable(False)
        if self.start_button:
            self.start_button.Enable(False)
