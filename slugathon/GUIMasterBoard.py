#!/usr/bin/env python

try:
    import pygtk
    pygtk.require("2.0")
except (ImportError, AttributeError):
    pass
import gtk
import pango
import sys
import math
import zope.interface

import GUIMasterHex
import MasterBoard
import guiutils
from Observer import IObserver
import Action
import Marker
import ShowLegion

SQRT3 = math.sqrt(3.0)


class GUIMasterBoard(object):

    zope.interface.implements(IObserver)

    def __init__(self, root, board, game=None, username=None, scale=15):
        self.root = root
        self.board = board
        self.username = username

        # XXX This feels like inappropriate coupling, but I haven't thought
        # of a better way to handle the data needed for markers yet.
        self.game = game

        self.scale = scale
        self.area = gtk.DrawingArea()
        black = self.area.get_colormap().alloc_color("black")
        self.area.modify_bg(gtk.STATE_NORMAL, black)
        self.area.set_size_request(self.compute_width(), self.compute_height())
        # TODO Vary font size with scale
        self.area.modify_font(pango.FontDescription("monospace 8"))
        self.root.add(self.area)
        self.markers = []
        self.guihexes = {}
        for hex1 in self.board.hexes.values():
            self.guihexes[hex1.label] = GUIMasterHex.GUIMasterHex(hex1, self)
        self.area.connect("expose-event", self.area_expose_cb)
        self.area.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.area.connect("button_press_event", self.click_cb)
        self.area.show()
        self.root.show()

    def area_expose_cb(self, area, event):
        self.style = self.area.get_style()
        self.gc = self.style.fg_gc[gtk.STATE_NORMAL]
        self.update_gui()
        return True

    def click_cb(self, area, event):
        for marker in self.markers:
            if marker.point_inside((event.x, event.y)):
                print "clicked on", marker
                showlegion = ShowLegion.ShowLegion(self.username, 
                  marker.legion)
                return True
        for guihex in self.guihexes.values():
            if guiutils.point_in_polygon((event.x, event.y), guihex.points):
                guihex.toggle_selection()
                self.update_gui()
                return True
        return True

    def compute_width(self):
        return int(round(self.scale * (self.board.hex_width() * 4 + 2)))

    def compute_height(self):
        return int(round(self.scale * self.board.hex_height() * 4 * SQRT3))

    def markers_in_hex(self, hex):
        return [marker for marker in self.markers if marker.legion.hex == hex]

    def draw_markers(self):
        if not self.game:
            return
        # Add missing markers
        for legion in self.game.gen_all_legions():
            if legion.marker not in [marker.name for marker in self.markers]:
                marker = Marker.Marker(legion)
                self.markers.append(marker)

        chit_scale = self.markers[0].chit_scale
        hexes_done = set()
        for marker in self.markers:
            hex1 = marker.hex

            if hex1 in hexes_done:
                continue
            hexes_done.add(hex1)

            mih = self.markers_in_hex(marker.hex)
            num = len(mih)
            assert 1 <= num <= 3
            guihex = self.guihexes[hex1]
            base_location = (guihex.center[0] - chit_scale / 2,
              guihex.center[1] - chit_scale / 2)

            if num == 1:
                mih[0].location = base_location
            elif num == 2:
                mih[0].location = (base_location[0] - chit_scale / 4,
                  base_location[1] - chit_scale / 4)
                mih[1].location = (base_location[0] + chit_scale / 4,
                  base_location[1] + chit_scale / 4)
            else:
                mih[0].location = (base_location[0] - chit_scale / 2,
                  base_location[1] - chit_scale / 2)
                mih[1].location = base_location
                mih[2].location = (base_location[0] + chit_scale / 2,
                  base_location[1] + chit_scale / 2)

        for marker in self.markers:
            marker.pixbuf.render_to_drawable(self.area.window, self.gc, 0, 0, 
              marker.location[0], marker.location[1], -1, -1, 
              gtk.gdk.RGB_DITHER_NORMAL, 0, 0)


    def update_gui(self):
        for guihex in self.guihexes.values():
            guihex.update_gui(self.gc, self.style)
        self.draw_markers()

    def update(self, observed, action):
        print "GUIMasterBoard.update", self, observed, action
        if isinstance(action, Action.CreateStartingLegion):
            self.update_gui()


def quit(unused):
    sys.exit()

if __name__ == "__main__":
    root = gtk.Window()
    root.set_title("Slugathon - MasterBoard")
    root.connect("destroy", quit)

    pixbuf = gtk.gdk.pixbuf_new_from_file("../images/creature/Colossus.png")
    root.set_icon(pixbuf)

    board = MasterBoard.MasterBoard()
    guiboard = GUIMasterBoard(root, board)
    # Allow exiting with control-C, unlike mainloop()
    while True:
        gtk.main_iteration()
