#!/usr/bin/env python

__copyright__ = "Copyright (c) 2006-2012 David Ripton"
__license__ = "GNU GPL v2"


import logging
from collections import Counter

from twisted.internet import gireactor
try:
    gireactor.install()
except AssertionError:
    pass
from twisted.internet import defer, reactor
from gi.repository import Gtk

from slugathon.gui import Chit, Marker, icon


ACCEPT = 0
REJECT = 1
FIGHT = 2


def new(playername, attacker_legion, attacker_creature_names,
        defender_legion, defender_creature_names, parent):
    """Create a Proposal dialog and return it and a Deferred."""
    def1 = defer.Deferred()
    proposal = Proposal(playername, attacker_legion, attacker_creature_names,
                        defender_legion, defender_creature_names, def1, parent)
    return proposal, def1


class Proposal(Gtk.Dialog):

    """Dialog to choose whether to accept an opponent's proposal."""

    def __init__(self, playername, attacker_legion, attacker_creature_names,
                 defender_legion, defender_creature_names, def1, parent):
        Gtk.Dialog.__init__(self, "Proposal - %s" % playername, parent)
        self.attacker_legion = attacker_legion
        self.attacker_creature_names = attacker_creature_names
        self.defender_legion = defender_legion
        self.defender_creature_names = defender_creature_names
        self.deferred = def1

        self.set_icon(icon.pixbuf)
        self.set_transient_for(parent)
        self.set_destroy_with_parent(True)
        self.vbox.set_spacing(9)

        legion_name = Gtk.Label(
            "Legion %s (%s) negotiates with %s (%s) in hex %s" % (
                attacker_legion.markerid, attacker_legion.picname,
                defender_legion.markerid, defender_legion.picname,
                defender_legion.hexlabel))
        self.vbox.pack_start(legion_name, expand=True, fill=True, padding=0)

        attacker_hbox = Gtk.HBox(spacing=15)
        self.vbox.pack_start(attacker_hbox, expand=True, fill=True, padding=0)
        attacker_marker_hbox = Gtk.HBox()
        attacker_hbox.pack_start(attacker_marker_hbox, expand=False, fill=True, padding=0)
        attacker_chits_hbox = Gtk.HBox(spacing=3)
        attacker_hbox.pack_start(attacker_chits_hbox, expand=True, fill=True, padding=0)

        attacker_marker = Marker.Marker(attacker_legion, True, scale=20)
        attacker_marker_hbox.pack_start(attacker_marker.event_box,
                                        expand=False, fill=True, padding=0)

        defender_hbox = Gtk.HBox(spacing=15)
        self.vbox.pack_start(defender_hbox, expand=True, fill=True, padding=0)
        defender_marker_hbox = Gtk.HBox()
        defender_hbox.pack_start(defender_marker_hbox, expand=False, fill=True, padding=0)
        defender_chits_hbox = Gtk.HBox(spacing=3)
        defender_hbox.pack_start(defender_chits_hbox, expand=True, fill=True, padding=0)

        defender_marker = Marker.Marker(defender_legion, True, scale=20)
        defender_marker_hbox.pack_start(defender_marker.event_box,
                                        expand=False, fill=True, padding=0)

        attacker_chits = []

        surviving_attackers = Counter(attacker_creature_names)
        surviving_defenders = Counter(defender_creature_names)

        for creature in attacker_legion.sorted_creatures:
            name = creature.name
            if surviving_attackers[name]:
                surviving_attackers[name] -= 1
                dead = False
            else:
                dead = True
            chit = Chit.Chit(creature, attacker_legion.player.color, scale=20,
                             dead=dead)
            attacker_chits_hbox.pack_start(chit.event_box, expand=False, fill=True, padding=0)
            attacker_chits.append(chit)

        defender_chits = []

        for creature in defender_legion.sorted_creatures:
            name = creature.name
            if surviving_defenders[name]:
                surviving_defenders[name] -= 1
                dead = False
            else:
                dead = True
            chit = Chit.Chit(creature, defender_legion.player.color, scale=20,
                             dead=dead)
            defender_chits_hbox.pack_start(chit.event_box, expand=False, fill=True, padding=0)
            defender_chits.append(chit)

        self.add_button("Accept", ACCEPT)
        self.add_button("Reject", REJECT)
        self.add_button("Fight", FIGHT)
        self.connect("response", self.cb_response)

        self.show_all()

    def cb_response(self, widget, response_id):
        """Fires the Deferred with the attacker, the defender, and
        the response_id."""
        self.destroy()
        self.deferred.callback((self.attacker_legion,
                                self.attacker_creature_names,
                                self.defender_legion,
                                self.defender_creature_names,
                                response_id))


if __name__ == "__main__":
    import time
    from slugathon.game import Creature, Legion, Player, Game

    now = time.time()
    game_name = "Game1"
    attacker_playername = "Roar!"
    game = Game.Game("g1", attacker_playername, now, now, 2, 6)
    attacker_player = Player.Player(attacker_playername, game, 0)
    attacker_player.color = "Black"
    attacker_creature_names = ["Titan", "Colossus", "Serpent", "Hydra",
                               "Archangel", "Angel", "Unicorn"]
    attacker_survivor_names = ["Titan", "Colossus", "Serpent", "Hydra",
                               "Archangel", "Angel"]
    attacker_creatures = Creature.n2c(attacker_creature_names)
    attacker_legion = Legion.Legion(attacker_player, "Bk01",
                                    attacker_creatures, 1)

    defender_playername = "Eek!"
    defender_player = Player.Player(defender_playername, game, 0)
    defender_player.color = "Gold"
    defender_creature_names = ["Ogre", "Centaur", "Gargoyle"]
    defender_survivor_names = []
    defender_creatures = Creature.n2c(defender_creature_names)
    defender_legion = Legion.Legion(defender_player, "Rd01",
                                    defender_creatures, 1)

    def my_callback(*args):
        logging.info("my_callback %s", args)
        reactor.stop()

    _, def1 = new(defender_playername, attacker_legion,
                  attacker_survivor_names, defender_legion,
                  defender_survivor_names, None)
    def1.addCallback(my_callback)
    reactor.run()
