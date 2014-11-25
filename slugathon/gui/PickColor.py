#!/usr/bin/env python

__copyright__ = "Copyright (c) 2004-2012 David Ripton"
__license__ = "GNU GPL v2"


import logging

from gi.repository import Gtk, Gdk
from twisted.internet import defer

from slugathon.data.playercolordata import colors
from slugathon.gui import icon
from slugathon.util.colors import contrasting_colors


def new(playername, game, colors_left, parent):
    """Return a PickColor dialog and a Deferred."""
    def1 = defer.Deferred()
    pickcolor = PickColor(playername, game, colors_left, parent, def1)
    return pickcolor, def1


class PickColor(Gtk.Dialog):
    """Dialog to pick a player color."""
    def __init__(self, playername, game, colors_left, parent, def1):
        Gtk.Dialog.__init__(self, "Pick Color - %s" % playername, parent)
        self.playername = playername
        self.game = game
        self.deferred = def1

        self.vbox.set_spacing(9)
        label1 = Gtk.Label("Pick a color")
        self.vbox.pack_start(label1, expand=True, fill=True, padding=0)

        self.set_icon(icon.pixbuf)
        self.set_transient_for(parent)
        self.set_destroy_with_parent(True)
        self.set_keep_above(True)

        hbox = Gtk.HBox(len(colors), spacing=3)
        self.vbox.pack_start(hbox, expand=True, fill=True, padding=0)
        for button_name in colors_left:
            button = Gtk.Button(button_name)
            hbox.pack_start(button, expand=True, fill=True, padding=0)
            button.connect("button-press-event", self.cb_click)
            color_bg = button_name
            color_fg = contrasting_colors[color_bg]

            css_data = """
                GtkButton {{
                    color: {};
                    background-color: {};
                    background-image: none;
                    }}
                """.format(color_fg, color_bg)
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(css_data)
            css_context = button.get_style_context()
            css_context.add_provider\
                    ( css_provider
                    , Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                    )

        self.connect("destroy", self.cb_destroy)
        self.show_all()

    def cb_click(self, widget, event):
        color = widget.get_label()
        self.deferred.callback((self.game, color))
        self.destroy()

    def cb_destroy(self, widget):
        if not self.deferred.called:
            self.deferred.callback((self.game, None))

if __name__ == "__main__":
    import time
    from slugathon.game import Game
    from slugathon.util import guiutils

    def my_callback(result):
        game, color = result
        logging.info("picked %s", color)
        guiutils.exit()

    now = time.time()
    playername = "test user"
    game = Game.Game("test game", playername, now, now, 2, 6)
    colors_left = colors[:]
    colors_left.remove("Black")
    pickcolor, def1 = new(playername, game, colors_left, None)
    def1.addCallback(my_callback)
    pickcolor.connect("destroy", guiutils.exit)
    Gtk.main()
