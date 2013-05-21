import wx

import koko
from koko.themes          import APP_THEME
from koko.prims.evaluator import Evaluator

class EditPanel(wx.Panel):
    ''' Panel that allows us to edit parameters of a Primitive.
        Child of the global canvas instance.'''

    def __init__(self, target):
        wx.Panel.__init__(self, koko.CANVAS)

        self.target = target

        sizer = wx.FlexGridSizer(
            rows=len(target.PARAMETERS)+2,
            cols = 2)

        txt = wx.StaticText(self, label='type', size=(-1, 25),
                            style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        sizer.Add(txt, border=3, flag=wx.BOTTOM|wx.TOP|wx.RIGHT|wx.EXPAND)

        # Add this panel's class
        classTxt =  wx.StaticText(self, size=(-1, 25),
                                  label=target.__class__.__name__)
        classTxt.SetFont(wx.Font(14, family=wx.FONTFAMILY_DEFAULT,
                                 style=wx.ITALIC, weight=wx.BOLD))
        sizer.Add(classTxt, border=1, flag=wx.BOTTOM|wx.TOP|wx.LEFT|wx.EXPAND)

        boxes = []
        for p in target.PARAMETERS:
            boxes.append(self.add_row(sizer, p))
        self.update = lambda: [b.pull() for b in boxes]

        outer = wx.BoxSizer()
        outer.Add(sizer, border=10, flag=wx.ALL)
        self.SetSizerAndFit(outer)
        APP_THEME.apply(self)

        koko.CANVAS.Refresh()

    ########################################

    def add_row(self, sizer, label):
        ''' Helper function to add a row to a sizer.

            Returns a TextCtrl with extra field 'label'.
        '''

        # Create label
        labelTxt = wx.StaticText(self, label=label,
                                 style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE,
                                 size=(-1, 25))
        sizer.Add(labelTxt, border=3,
                  flag=wx.BOTTOM|wx.TOP|wx.RIGHT|wx.EXPAND)

        # Create input box
        inputBox = wx.TextCtrl(self, size=(150, 25),
                               style=wx.NO_BORDER|wx.TE_PROCESS_ENTER)
        sizer.Add(inputBox, border=3,
                  flag=wx.BOTTOM|wx.TOP|wx.LEFT|wx.EXPAND)

        # Add extra field to input box
        inputBox.label = label

        # Silly hack to avoid selecting all of the text when
        # this row gets focus.
        def focus(event):
            txt = event.GetEventObject()
            txt.SetSelection(0,0)
            if hasattr(txt, 'lastInsertionPoint'):
                txt.SetInsertionPoint(txt.lastInsertionPoint)
                del txt.lastInsertionPoint
        def lost_focus(event):
            txt = event.GetEventObject()
            txt.lastInsertionPoint = txt.GetInsertionPoint()

        inputBox.Bind(wx.EVT_SET_FOCUS, focus)
        inputBox.Bind(wx.EVT_KILL_FOCUS, lost_focus)

        # pull() synchronizes the text in the box with the
        # parameter or property referred to in the target object
        def pull():
            try:
                a = self.target.parameters[label]
                if a.expr != inputBox.GetValue():
                    ip = inputBox.GetInsertionPoint()
                    inputBox.SetValue(a.expr)
                    inputBox.SetInsertionPoint(ip)
            except KeyError:
                a = getattr(self.target, label)
                if str(a) != inputBox.GetValue():
                    inputBox.SetValue(str(a))
        inputBox.pull = pull

        # push() synchronizes the parameter expression in the
        # target object with the text in the input box.
        def push():
            a = self.target.parameters[label]
            a.set_expr(inputBox.GetValue())
            a.eval()
            inputBox.SetForegroundColour(APP_THEME.foreground
                                         if a.valid else
                                         wx.Colour(255, 80, 60))
        inputBox.push = push

        inputBox.pull()

#        inputBox.Bind(wx.EVT_CHAR, self.char)
        inputBox.Bind(wx.EVT_TEXT, self.changed)
        inputBox.Bind(wx.EVT_TEXT_ENTER, self.target.close_panel)

        return inputBox

    ########################################

    def changed(self, event):

        event.GetEventObject().push()
        koko.CANVAS.Refresh()

    ########################################

    def slide(self):
        pt = (wx.Point(*koko.CANVAS.pos_to_pixel(self.target.x, self.target.y)) +
              wx.Point(4,4))
        self.Move(pt)

