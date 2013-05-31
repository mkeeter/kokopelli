from koko import NAME, VERSION, HASH

import wx

def show_about_box(event=None):
    '''Displays an About box with information about this program.'''

    info = wx.AboutDialogInfo()
    info.SetName(NAME)
    info.SetVersion(VERSION)

    if HASH is None:
        info.SetDescription('An interactive design tool for .cad files.')
    else:
        info.SetDescription(
            'An interactive design tool for .cad files.\ngit commit: ' +
            HASH
        )

    info.SetWebSite('https://github.com/mkeeter/kokopelli')
    info.SetCopyright('(C) 2012-13 MIT Center for Bits and Atoms')

    wx.AboutBox(info)
