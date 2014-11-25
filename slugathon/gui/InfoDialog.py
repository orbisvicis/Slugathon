#!/usr/bin/env python

__copyright__ = "Copyright (c) 2009-2010 David Ripton"
__license__ = "GNU GPL v2"


from gi.repository import Gtk

from slugathon.gui import icon


class InfoDialog(Gtk.MessageDialog):

    def __init__(self, parent, title, message_format):
        Gtk.MessageDialog.__init__(self, parent=parent,
                                   flags=Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   buttons=Gtk.ButtonsType.OK,
                                   message_format=message_format)
        self.set_title(title)
        self.set_icon(icon.pixbuf)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.set_transient_for(parent)
        self.set_destroy_with_parent(True)
        self.connect("response", self.cb_response)
        self.show_all()

    def cb_response(self, widget, response_id):
        self.destroy()


if __name__ == "__main__":
    from slugathon.util import guiutils

    info_dialog = InfoDialog(parent=None, title="Info",
                             message_format="Look out behind you!")
    info_dialog.connect("destroy", guiutils.exit)
    Gtk.main()
