from koko import NAME, VERSION, CHANGESET

import wx

def show_about_box(event=None):
    '''Displays an About box with information about this program.'''

    info = wx.AboutDialogInfo()
    info.SetName(NAME)
    info.SetVersion(VERSION)

    if CHANGESET is None:
        info.SetDescription('An interactive design tool for .cad files.')
    else:
        info.SetDescription(
            'An interactive design tool for .cad files.\nhg revision: ' +
            CHANGESET
        )

    info.SetWebSite('http://kokompe.cba.mit.edu')
    info.SetCopyright('(C) 2012-13 MIT Center for Bits and Atoms')

    wx.AboutBox(info)
