#!/usr/bin/env python

import math
try:
    import pygtk
    pygtk.require("2.0")
except (ImportError, AttributeError):
    pass
import gtk
import pango
import zope.interface

from Observer import IObserver
import BattleMap
import icon
import guiutils
import GUIBattleHex

SQRT3 = math.sqrt(3.0)


class GUIBattleMap(gtk.Window):
    """GUI representation of a battlemap.

    We spin the map so that the attacker's entry side is always on the left.

               *
            *     *
    A    *     *     *       D
    T       *     *     *    E
    T    *     *     *       F
    A       *     *     *    E
    C    *     *     *       N
    K       *     *     *    D
    E    *     *     *       E
    R       *     *          R
               *
    """

    zope.interface.implements(IObserver)

    def __init__(self, battlemap, entry_side, user=None, username=None, 
      scale=None):
        gtk.Window.__init__(self)

        self.battlemap = battlemap
        self.entry_side = entry_side
        self.user = user
        self.username = username

        self.set_icon(icon.pixbuf)
        self.set_title("Slugathon - BattleMap - %s" % self.username)
        self.connect("destroy", guiutils.die)

        self.vbox = gtk.VBox()
        self.add(self.vbox)

        if scale is None:
            self.scale = self.compute_scale()
        else:
            self.scale = scale
        self.area = gtk.DrawingArea()
        # TODO Vary background color by terrain type?
        white = self.area.get_colormap().alloc_color("white")
        self.area.modify_bg(gtk.STATE_NORMAL, white)
        self.area.set_size_request(self.compute_width(), self.compute_height())
        # TODO Vary font size with scale
        self.area.modify_font(pango.FontDescription("monospace 8"))
        self.vbox.pack_start(self.area)
        self.guihexes = {}
        for hex1 in self.battlemap.hexes.values():
            self.guihexes[hex1.label] = GUIBattleHex.GUIBattleHex(hex1, self)
        self.area.connect("expose-event", self.cb_area_expose)
        self.area.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.area.connect("button_press_event", self.cb_click)
        self.show_all()


    def compute_scale(self):
        """Return the approximate maximum scale that lets the map fit on the
        screen."""
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        # The -2 is a fudge factor to leave room on the sides.
        xscale = math.floor(width / (2 * self.battlemap.hex_width())) - 2
        # The -3 is a fudge factor for menus and toolbars.
        yscale = math.floor(height / (2 * SQRT3 * 
          self.battlemap.hex_height())) - 3
        return int(min(xscale, yscale))

    def compute_width(self):
        """Return the width of the map in pixels."""
        return int(math.ceil(self.scale * self.battlemap.hex_width() * 4)) 

    def compute_height(self):
        """Return the height of the map in pixels."""
        return int(math.ceil(self.scale * self.battlemap.hex_height() * 2 * 
          SQRT3))

    def cb_area_expose(self, area, event):
        style = self.area.get_style()
        gc = style.fg_gc[gtk.STATE_NORMAL]
        self.update_gui(gc, style)
        return True

    def cb_click(self, area, event):
        style = self.area.get_style()
        gc = style.fg_gc[gtk.STATE_NORMAL]
        for guihex in self.guihexes.values():
            if guiutils.point_in_polygon((event.x, event.y), guihex.points):
                self.clicked_on_hex(area, event, guihex)
                return True
        self.clicked_on_background(area, event)
        return True

    def clicked_on_background(self, area, event):
        print "clicked on background", area, event

    def clicked_on_hex(self, area, event, guihex):
        print "clicked on hex", area, event, guihex
        guihex.toggle_selection()
        style = self.area.get_style()
        gc = style.fg_gc[gtk.STATE_NORMAL]
        self.update_gui(gc, style, [guihex.battlehex.label])

    def update_gui(self, gc, style, hexlabels=None):
        if hexlabels is None:
            guihexes = self.guihexes.values()
        else:
            guihexes = set(self.guihexes[hexlabel] for hexlabel in hexlabels)
        for guihex in guihexes:
            guihex.update_gui(gc, style)

    def update(self, observed, action):
        print "GUIBattleMap.update", observed, action


if __name__ == "__main__":
    import random
    import battlemapdata
    import sys
    if len(sys.argv) > 1:
        terrain = sys.argv[1].title()
    else:
        terrain = random.choice(battlemapdata.data.keys())
    battlemap = BattleMap.BattleMap(terrain)
    guimap = GUIBattleMap(battlemap, 1)
    while True:
        gtk.main_iteration()