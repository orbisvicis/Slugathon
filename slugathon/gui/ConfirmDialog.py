#!/usr/bin/env python

__copyright__ = "Copyright (c) 2010 David Ripton"
__license__ = "GNU GPL v2"


from twisted.internet import gireactor
try:
    gireactor.install()
except AssertionError:
    pass
from twisted.internet import defer, reactor
from gi.repository import Gtk

from slugathon.gui import icon


def new(parent, title, message_format):
    def1 = defer.Deferred()
    confirm_dialog = ConfirmDialog(parent, title, message_format, def1)
    return confirm_dialog, def1


class ConfirmDialog(Gtk.MessageDialog):
    """Yes / No confirmation dialog.

    The deferred fires True on Yes, False on No.
    """
    def __init__(self, parent, title, message_format, def1):
        Gtk.MessageDialog.__init__(self,
                                   parent=parent,
                                   flags=Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   buttons=Gtk.ButtonsType.YES_NO,
                                   message_format=message_format)
        self.deferred = def1
        self.set_title(title)
        self.set_icon(icon.pixbuf)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.set_transient_for(parent)
        self.set_destroy_with_parent(True)
        self.connect("response", self.cb_response)
        self.show_all()

    def cb_response(self, widget, response_id):
        retval = (response_id == Gtk.ResponseType.YES)
        self.deferred.callback(retval)
        self.destroy()


if __name__ == "__main__":
    confirm_dialog, def1 = new(parent=None,
                               title="Info",
                               message_format="Are we having fun yet?")

    def print_arg(arg):
        print(arg)
        reactor.stop()

    def1.addCallback(print_arg)
    def1.addErrback(print_arg)
    reactor.run()
