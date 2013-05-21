import wx
import wx.py
import wx.stc

class Theme:
    def __init__(self, txt, background, header, foreground, txtbox):
        self.txt = txt
        self.background = background
        self.header = header
        self.foreground = foreground
        self.txtbox = txtbox


    def apply(self, target, depth=0):
        ''' Recursively apply the theme to a frame or sizer. '''
        if isinstance(target, wx.Sizer):
            sizer = target
        else:
            if isinstance(target, wx.py.editwindow.EditWindow):
                for s in self.txt:
                    if len(s) == 3:
                        target.StyleSetBackground(s[0], s[1])
                        target.StyleSetForeground(s[0], s[2])
                    else:
                        target.StyleSetBackground(s[0], self.background)
                        target.StyleSetForeground(s[0], s[1])
            elif isinstance(target, wx.TextCtrl):
                target.SetBackgroundColour(self.txtbox)
                target.SetForegroundColour(self.foreground)
            elif hasattr(target, 'header'):
                try:
                    target.SetBackgroundColour(self.header)
                    target.SetForegroundColour(self.foreground)
                except AttributeError:
                    pass
            elif hasattr(target, 'immune'):
                pass
            else:
                try:
                    target.SetBackgroundColour(self.background)
                    target.SetForegroundColour(self.foreground)
                except AttributeError:
                    pass
            sizer = target.Sizer

        if sizer is None:   return

        for c in sizer.Children:
            if c.Window is not None:
                self.apply(c.Window, depth+1)
            elif c.Sizer is not None:
                self.apply(c.Sizer, depth+1)

DARK_THEME = Theme(
    txt=[
        (wx.stc.STC_STYLE_DEFAULT,    '#000000', '#000000'),
        (wx.stc.STC_STYLE_LINENUMBER, '#303030', '#c8c8c8'),
        (wx.stc.STC_P_CHARACTER,      '#000000', '#ff73fd'),
        (wx.stc.STC_P_CLASSNAME,      '#000000', '#96cbfe'),
        (wx.stc.STC_P_COMMENTBLOCK,   '#000000', '#7f7f7f'),
        (wx.stc.STC_P_COMMENTLINE,    '#000000', '#a8ff60'),
        (wx.stc.STC_P_DEFAULT,        '#000000', '#ffffff'),
        (wx.stc.STC_P_DEFNAME,        '#000000', '#96cbfe'),
        (wx.stc.STC_P_IDENTIFIER,     '#000000', '#ffffff'),
        (wx.stc.STC_P_NUMBER,         '#000000', '#ffffff'),
        (wx.stc.STC_P_OPERATOR,       '#000000', '#ffffff'),
        (wx.stc.STC_P_STRING,         '#000000', '#ff73fd'),
        (wx.stc.STC_P_STRINGEOL,      '#000000', '#ffffff'),
        (wx.stc.STC_P_TRIPLE,         '#000000', '#ff6c60'),
        (wx.stc.STC_P_TRIPLEDOUBLE,   '#000000', '#96cbfe'),
        (wx.stc.STC_P_WORD,           '#000000', '#b5dcff')
    ],
    background='#252525',
    header='#303030',
    foreground='#c8c8c8',
    txtbox='#353535')

SOLARIZED_THEME = Theme(
     txt=[
        (wx.stc.STC_STYLE_DEFAULT,    '#002b36' '#002b36'), # base00
        (wx.stc.STC_STYLE_LINENUMBER, '#073642','#839496'),
        (wx.stc.STC_P_CHARACTER,      '#d33682'), # magenta
        (wx.stc.STC_P_CLASSNAME,      '#268bd2'), # blue
        (wx.stc.STC_P_COMMENTBLOCK,   '#586e75'), # base01
        (wx.stc.STC_P_COMMENTLINE,    '#859900'), # base0
        (wx.stc.STC_P_DEFAULT,        '#657b83'), # base00
        (wx.stc.STC_P_DEFNAME,        '#268bd2'), # blue
        (wx.stc.STC_P_IDENTIFIER,     '#657b83'), # base00
        (wx.stc.STC_P_NUMBER,         '#657b83'), # base00
        (wx.stc.STC_P_OPERATOR,       '#657b83'), # base00
        (wx.stc.STC_P_STRING,         '#d33682'), # magenta
        (wx.stc.STC_P_STRINGEOL,      '#657b83'), # base00
        (wx.stc.STC_P_TRIPLE,         '#dc322f'), # red
        (wx.stc.STC_P_TRIPLEDOUBLE,   '#268bd2'), # blue
        (wx.stc.STC_P_WORD,           '#b5dcff')  # blue
    ],
    background='#002b36',   # base03
    header='#073642',       # base02
    foreground='#839496',   # base0
    txtbox='#073642'        # base02
)
# http://www.zovirl.com/2011/07/22/solarized_cheat_sheet/

APP_THEME = DARK_THEME
