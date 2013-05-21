import inspect

import wx

from   koko.prims.core import Primitive

import koko.prims.points
import koko.prims.utils
import koko.prims.lines

constructors = {}
for _, module in inspect.getmembers(koko.prims):
    if not inspect.ismodule(module):        continue
    try:    menu_name = module.MENU_NAME
    except AttributeError:  continue

    for _, cls in inspect.getmembers(module):
        if not inspect.isclass(cls) or not issubclass(cls, Primitive):
            continue

        if inspect.getmodule(cls) != module:    continue

        try:    name = cls.MENU_NAME
        except AttributeError:  continue

        if not name in constructors:    constructors[menu_name] = {}
        constructors[menu_name][name] = cls.new

def show_menu():
    ''' Returns a menu of constructors for a prim objects. '''

    def build_from(init):
        ''' Decorator that calls the provided method with appropriate
            values for x, y, and scale.  Results are added to the global
            PrimSet object in koko.PRIMS. '''

        koko.CANVAS.mouse = (wx.GetMousePosition() -
                             koko.CANVAS.GetScreenPosition())
        koko.CANVAS.click = koko.CANVAS.mouse
        x, y = koko.CANVAS.pixel_to_pos(*koko.CANVAS.mouse)
        scale = 100/koko.CANVAS.scale

        p = init(x, y, scale)
        if type(p) is list:         p = tuple(p)
        elif type(p) is not tuple:  p = (p,)

        koko.CANVAS.drag_target = p[-1]
        for q in p: koko.PRIMS.add(q)
        koko.PRIMS.close_panels()

    menu = wx.Menu()
    for T in sorted(constructors):
        sub = wx.Menu()
        for name in sorted(constructors[T]):
            init = constructors[T][name]
            m = sub.Append(wx.ID_ANY, text=name)
            koko.CANVAS.Bind(wx.EVT_MENU, lambda e, c=init: build_from(c), m)
        menu.AppendMenu(wx.ID_ANY, T, sub)
    return menu
