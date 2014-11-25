#!/usr/bin/env python

__copyright__ = "Copyright (c) 2008-2012 David Ripton"
__license__ = "GNU GPL v2"


from twisted.python import log
from gi.repository import Gtk

from slugathon.gui import icon
from slugathon.util import prefs
from slugathon.util.NullUser import NullUser


class LoadGame(Gtk.FileChooserDialog):

    """Load saved game dialog."""

    def __init__(self, user, playername, parent):
        title = "Load Saved Game - %s" % playername
        Gtk.FileChooserDialog.__init__( self
                                      , title
                                      , parent
                                      , Gtk.FileChooserAction.OPEN
                                      , buttons = ( Gtk.STOCK_CANCEL
                                                  , Gtk.ResponseType.CANCEL
                                                  , Gtk.STOCK_OPEN
                                                  , Gtk.ResponseType.OK
                                                  )
                                      )
        self.user = user
        self.playername = playername
        self.set_icon(icon.pixbuf)
        self.set_transient_for(parent)
        self.set_destroy_with_parent(True)
        self.set_current_folder(prefs.SAVE_DIR)
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern(prefs.SAVE_GLOB)
        self.set_filter(file_filter)

        response = self.run()
        if response == Gtk.ResponseType.OK:
            self.ok()
        else:
            self.cancel()

    def ok(self):
        filename = self.get_filename()
        def1 = self.user.callRemote("load_game", filename)
        def1.addErrback(self.failure)
        self.destroy()

    def cancel(self):
        self.destroy()

    def failure(self, error):
        log.err(error)


if __name__ == "__main__":
    user = NullUser()
    playername = "test user"
    loadgame = LoadGame(user, playername, None)
