#!/usr/bin/env python

__copyright__ = "Copyright (c) 2003-2012 David Ripton"
__license__ = "GNU GPL v2"


from gi.repository import Gtk
from twisted.python import log

from slugathon.gui import icon, InfoDialog
from slugathon.util import prefs
from slugathon.util.NullUser import NullUser
from slugathon.net import config


class NewGame(Gtk.Dialog):

    """Form new game dialog."""

    def __init__(self, user, playername, parent_window):
        Gtk.Dialog.__init__(self, "Form New Game - %s" % playername,
                            parent_window)
        self.game_name = None
        self.min_players = None
        self.max_players = None
        self.user = user
        self.playername = playername
        self.parent_window = parent_window

        self.set_icon(icon.pixbuf)
        self.set_transient_for(parent_window)
        self.set_destroy_with_parent(True)

        hbox1 = Gtk.HBox()
        self.vbox.pack_start(hbox1, expand=True, fill=True, padding=0)
        label1 = Gtk.Label("Name of game")
        hbox1.pack_start(label1, expand=False, fill=True, padding=0)
        self.name_entry = Gtk.Entry(max_length=40)
        self.name_entry.set_width_chars(40)
        hbox1.pack_start(self.name_entry, expand=False, fill=True, padding=0)

        min_adjustment = Gtk.Adjustment(2, 2, 6, 1, 0, 0)
        max_adjustment = Gtk.Adjustment(6, 2, 6, 1, 0, 0)
        ai_time_limit_adjustment = Gtk.Adjustment(config.DEFAULT_AI_TIME_LIMIT,
                                                  1, 99, 1, 0, 0)
        player_time_limit_adjustment = Gtk.Adjustment(
            config.DEFAULT_PLAYER_TIME_LIMIT, 1, 999, 1, 100, 0)

        hbox2 = Gtk.HBox()
        self.vbox.pack_start(hbox2, expand=True, fill=True, padding=0)
        label2 = Gtk.Label("Min players")
        hbox2.pack_start(label2, expand=False, fill=True, padding=0)
        self.min_players_spin = Gtk.SpinButton(adjustment=min_adjustment,
                                               climb_rate=1, digits=0)
        self.min_players_spin.set_numeric(True)
        self.min_players_spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        self.min_players_spin.set_value(2)
        hbox2.pack_start(self.min_players_spin, expand=False, fill=True, padding=0)
        label3 = Gtk.Label("Max players")
        hbox2.pack_start(label3, expand=False, fill=True, padding=0)
        self.max_players_spin = Gtk.SpinButton(adjustment=max_adjustment,
                                               climb_rate=1, digits=0)
        self.max_players_spin.set_numeric(True)
        self.max_players_spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        self.max_players_spin.set_value(6)
        hbox2.pack_start(self.max_players_spin, expand=False, fill=True, padding=0)
        label4 = Gtk.Label("AI time limit")
        hbox2.pack_start(label4, expand=False, fill=True, padding=0)
        self.ai_time_limit_spin = Gtk.SpinButton(
            adjustment=ai_time_limit_adjustment,
            climb_rate=1, digits=0)
        self.ai_time_limit_spin.set_numeric(True)
        self.ai_time_limit_spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        hbox2.pack_start(self.ai_time_limit_spin, expand=False, fill=True, padding=0)
        label5 = Gtk.Label("Player time limit")
        hbox2.pack_start(label5, expand=False, fill=True, padding=0)
        self.player_time_limit_spin = Gtk.SpinButton(
            adjustment=player_time_limit_adjustment,
            climb_rate=1, digits=0)
        self.player_time_limit_spin.set_numeric(True)
        self.player_time_limit_spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        hbox2.pack_start(self.player_time_limit_spin, expand=False, fill=True, padding=0)

        self.cancel_button = self.add_button("gtk-cancel", Gtk.ResponseType.CANCEL)
        self.cancel_button.connect("button-press-event", self.cancel)
        self.ok_button = self.add_button("gtk-ok", Gtk.ResponseType.OK)
        self.ok_button.connect("button-press-event", self.ok)

        self._init_name()

        self.show_all()

    def _init_name(self):
        last_gamename = prefs.load_last_gamename(self.playername)
        self.name_entry.set_text(last_gamename)

    def _save_name(self):
        gamename = self.name_entry.get_text()
        prefs.save_last_gamename(self.playername, gamename)

    def ok(self, widget, event):
        if self.name_entry.get_text():
            self._save_name()
            self.game_name = self.name_entry.get_text()
            self.min_players = self.min_players_spin.get_value_as_int()
            self.max_players = self.max_players_spin.get_value_as_int()
            self.ai_time_limit = self.ai_time_limit_spin.get_value_as_int()
            self.player_time_limit = \
                self.player_time_limit_spin.get_value_as_int()
            def1 = self.user.callRemote("form_game", self.game_name,
                                        self.min_players, self.max_players,
                                        self.ai_time_limit,
                                        self.player_time_limit, "Human", "")
            def1.addCallback(self.got_information)
            def1.addErrback(self.failure)
            self.destroy()

    def cancel(self, widget, event):
        self.destroy()

    def failure(self, error):
        log.err(error)

    def got_information(self, information):
        if information:
            InfoDialog.InfoDialog(self.parent_window, "Info", str(information))


if __name__ == "__main__":
    from slugathon.util import guiutils

    user = NullUser()
    playername = "test user"
    newgame = NewGame(user, playername, None)
    newgame.connect("destroy", guiutils.exit)
    Gtk.main()
