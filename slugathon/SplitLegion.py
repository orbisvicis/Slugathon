#!/usr/bin/env python 

try:
    import pygtk
    pygtk.require("2.0")
except (ImportError, AttributeError):
    pass
import gtk
import gtk.glade
import Chit
import Marker
import creaturedata
import Creature
import Legion
import Player
import icon
import guiutils
import rules


class SplitLegion(object):
    """Dialog to split a legion."""
    def __init__(self, username, player, legion, callback):
        print "SplitLegion.__init__", username, player, legion
        self.old_legion = legion
        self.callback = callback
        self.glade = gtk.glade.XML("../glade/splitlegion.glade")
        self.widgets = ["split_legion_dialog", "old_marker_hbox", 
          "old_chits_hbox", "new_marker_hbox", "new_chits_hbox",
          "legion_name"]
        for widget_name in self.widgets:
            setattr(self, widget_name, self.glade.get_widget(widget_name))

        self.split_legion_dialog.set_icon(icon.pixbuf)
        self.split_legion_dialog.set_title("SplitLegion - %s" % (username))

        self.legion_name.set_text("Splitting legion %s in hex %s" % (
          legion.markername, legion.hexlabel))

        self.old_marker = Marker.Marker(legion, scale=20)
        self.old_marker_hbox.pack_start(self.old_marker.image, expand=False,
          fill=False)
        self.old_marker.show()

        self.new_legion1 = Legion.Legion(player, legion.markername,
          legion.creatures[:], legion.hexlabel)
        self.new_legion2 = Legion.Legion(player, player.selected_markername, 
          [], legion.hexlabel)
        self.new_marker = Marker.Marker(self.new_legion2, scale=20)
        self.new_marker_hbox.pack_start(self.new_marker.image, expand=False,
          fill=False)
        self.new_marker.show()

        for creature in legion.creatures:
            chit = Chit.Chit(creature, player.color, scale=20)
            chit.show()
            self.old_chits_hbox.pack_start(chit.event_box, expand=False,
              fill=False)
            chit.connect("button_press_event", self.cb_click)

        self.okbutton = self.split_legion_dialog.action_area.get_children()[0]
        self.okbutton.set_sensitive(False)

        self.split_legion_dialog.connect("response", self.cb_response)
        self.split_legion_dialog.show()


    def cb_click(self, widget, event):
        """Move the clicked-on Chit's EventBox to the other hbox."""
        eventbox = widget
        if eventbox in self.old_chits_hbox.get_children():
            prev = self.old_chits_hbox
            next = self.new_chits_hbox
            prev_legion = self.new_legion1
            next_legion = self.new_legion2
        else:
            prev = self.new_chits_hbox
            next = self.old_chits_hbox
            prev_legion = self.new_legion2
            next_legion = self.new_legion1
        prev.remove(eventbox)
        next.pack_start(eventbox, expand=False, fill=False)
        chit = eventbox.chit
        prev_legion.creatures.remove(chit.creature)
        next_legion.creatures.append(chit.creature)
        legal = rules.is_legal_split(self.old_legion, self.new_legion1,
          self.new_legion2)
        self.okbutton.set_sensitive(legal)

    def cb_response(self, widget, response_id):
        print "SplitLegion.cb_response", widget, response_id
        self.callback(self.old_legion, self.new_legion1, self.new_legion2)


if __name__ == "__main__":
    creatures = [Creature.Creature(name) for name in 
      creaturedata.starting_creature_names]
    
    username = "test"
    player = Player.Player(username, "Game1", 0)
    player.color = "Red"
    legion = Legion.Legion(player, "Rd01", creatures, 1)
    player.selected_markername = "Rd02"
    splitlegion = SplitLegion(username, player, legion, guiutils.die)
    splitlegion.split_legion_dialog.connect("destroy", guiutils.die)

    gtk.main()