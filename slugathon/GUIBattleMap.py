#!/usr/bin/env python

__copyright__ = "Copyright (c) 2005-2008 David Ripton"
__license__ = "GNU GPL v2"


import math
import random
import sys

import gtk
import pango
from zope.interface import implements

from Observer import IObserver
import BattleMap
import icon
import guiutils
import GUIBattleHex
import battlemapdata
import Chit
import Phase
import Action


SQRT3 = math.sqrt(3.0)

ui_string = """<ui>
  <menubar name="Menubar">
    <menu action="PhaseMenu">
      <menuitem action="Done"/>
      <menuitem action="Undo"/>
      <menuitem action="Redo"/>
      <separator/>
      <menuitem action="Concede Battle"/>
    </menu>
  </menubar>
  <toolbar name="Toolbar">
    <toolitem action="Done"/>
    <toolitem action="Undo"/>
    <toolitem action="Redo"/>
  </toolbar>
</ui>"""


class GUIBattleMap(gtk.Window):
    """GUI representation of a battlemap."""

    implements(IObserver)

    def __init__(self, battlemap, game=None, user=None, username=None,
      scale=None):
        gtk.Window.__init__(self)

        self.battlemap = battlemap
        self.game = game
        self.user = user
        self.username = username

        self.chits = []
        self.selected_chit = None

        self.set_icon(icon.pixbuf)
        self.set_title("Slugathon - BattleMap - %s" % self.username)
        self.connect("destroy", guiutils.exit)

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

        self.create_ui()
        self.vbox.pack_start(self.ui.get_widget("/Menubar"), False, False, 0)
        self.vbox.pack_start(self.ui.get_widget("/Toolbar"), False, False, 0)
        self.vbox.pack_start(self.area)

        self.guihexes = {}
        for hex1 in self.battlemap.hexes.itervalues():
            self.guihexes[hex1.label] = GUIBattleHex.GUIBattleHex(hex1, self)
        self.area.connect("expose-event", self.cb_area_expose)
        self.area.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.area.connect("button_press_event", self.cb_click)
        self.show_all()
        if self.game and self.game.battle_active_player.name == self.username:
            self.highlight_mobile_chits()

    def create_ui(self):
        ag = gtk.ActionGroup("BattleActions")
        # TODO confirm concession
        actions = [
          ("PhaseMenu", None, "_Phase"),
          ("Done", gtk.STOCK_APPLY, "_Done", "d", "Done", self.cb_done),
          ("Undo", gtk.STOCK_UNDO, "_Undo", "u", "Undo", self.cb_undo),
          ("Redo", gtk.STOCK_REDO, "_Redo", "r", "Redo", self.cb_redo),
          ("Concede Battle", None, "_Concede Battle", "c", "Concede Battle",
            self.cb_concede),
        ]
        ag.add_actions(actions)
        self.ui = gtk.UIManager()
        self.ui.insert_action_group(ag, 0)
        self.ui.add_ui_from_string(ui_string)
        self.add_accel_group(self.ui.get_accel_group())

    def compute_scale(self):
        """Return the approximate maximum scale that lets the map fit on the
        screen."""
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        # The -2 is a fudge factor to leave room on the sides.
        xscale = math.floor(width / (2 * self.battlemap.hex_width())) - 2
        # The -7 is a fudge factor for menus and toolbars.
        yscale = math.floor(height / (2 * SQRT3 *
          self.battlemap.hex_height())) - 7
        return int(min(xscale, yscale))

    def compute_width(self):
        """Return the width of the map in pixels."""
        return int(math.ceil(self.scale * self.battlemap.hex_width() * 3.2))

    def compute_height(self):
        """Return the height of the map in pixels."""
        return int(math.ceil(self.scale * self.battlemap.hex_height() * 2 *
          SQRT3))

    def unselect_all(self):
        """Unselect all guihexes."""
        for guihex in self.guihexes.itervalues():
            guihex.selected = False
        self.update_gui()

    def highlight_mobile_chits(self):
        """Highlight the hexes containing all creatures that can move now."""
        if not self.game:
            return
        hexlabels = set()
        for creature in self.game.battle_active_legion.creatures:
            if creature.is_mobile():
                hexlabels.add(creature.hexlabel)
        self.unselect_all()
        for hexlabel in hexlabels:
            self.guihexes[hexlabel].selected = True
        self.update_gui(hexlabels)

    def highlight_strikers(self):
        """Highlight the hexes containing creatures that can strike now."""
        if not self.game:
            return
        hexlabels = set()
        for creature in self.game.battle_active_legion.creatures:
            if creature.can_strike():
                hexlabels.add(creature.hexlabel)
        self.unselect_all()
        for hexlabel in hexlabels:
            self.guihexes[hexlabel].selected = True
        self.update_gui(hexlabels)

    def strike(self, striker, target):
        """Have striker strike target, at full strength and skill."""
        num_dice = striker.number_of_dice(target)
        strike_number = striker.strike_number(target)
        def1 = self.user.callRemote("strike", self.game.name, striker.name,
          striker.hexlabel, target.name, target.hexlabel, num_dice,
          strike_number)

    def cb_area_expose(self, area, event):
        self.update_gui()
        return True

    def cb_click(self, area, event):
        for chit in self.chits:
            if chit.point_inside((event.x, event.y)):
                self.clicked_on_chit(area, event, chit)
                return True
        for guihex in self.guihexes.itervalues():
            if guiutils.point_in_polygon((event.x, event.y), guihex.points):
                self.clicked_on_hex(area, event, guihex)
                return True
        self.clicked_on_background(area, event)
        return True

    def clicked_on_background(self, area, event):
        self.selected_chit = None
        self.unselect_all()
        if not self.game:
            return
        if self.game.battle_phase == Phase.MANEUVER:
            if self.game.battle_active_player.name == self.username:
                self.highlight_mobile_chits()
        elif (self.game.battle_phase == Phase.STRIKE
          or self.game.battle_phase == Phase.COUNTERSTRIKE):
            if self.game.battle_active_player.name == self.username:
                self.highlight_strikers()

    def clicked_on_hex(self, area, event, guihex):
        if not self.game:
            return
        phase = self.game.battle_phase
        if phase == Phase.MANEUVER:
            if self.selected_chit is not None and guihex.selected:
                creature = self.selected_chit.creature
                def1 = self.user.callRemote("move_creature",
                  self.game.name, creature.name, creature.hexlabel,
                  guihex.battlehex.label)
                def1.addErrback(self.failure)
            self.selected_chit = None
            self.unselect_all()
            if self.game.battle_active_player.name == self.username:
                self.highlight_mobile_chits()

        elif phase == Phase.STRIKE or phase == Phase.COUNTERSTRIKE:
            # TODO Allow striking by clicking hex not just chit?
            pass


    def clicked_on_chit(self, area, event, chit):
        phase = self.game.battle_phase
        if phase == Phase.MANEUVER:
            creature = chit.creature
            legion = creature.legion
            player = legion.player
            if player.name != self.username:
                return
            elif player != self.game.battle_active_player:
                return
            self.selected_chit = chit
            self.unselect_all()
            hexlabels = self.game.find_battle_moves(creature)
            for hexlabel in hexlabels:
                guihex = self.guihexes[hexlabel]
                guihex.selected = True
            self.update_gui(hexlabels)

        elif phase == Phase.STRIKE or phase == Phase.COUNTERSTRIKE:
            creature = chit.creature
            legion = creature.legion
            player = legion.player
            guihex = self.guihexes[creature.hexlabel]

            if (self.selected_chit is not None and player.name != self.username
              and guihex.selected):
                # striking enemy creature
                print "striking enemy creature"
                target = creature
                striker = self.selected_chit.creature
                # TODO choose strike penalty in order to carry
                self.strike(striker, target)

            else:
                # picking a striker
                print "picking a striker"
                if player.name != self.username:
                    return
                if player != self.game.battle_active_player:
                    return
                self.selected_chit = chit
                self.unselect_all()
                hexlabels = self.game.find_target_hexlabels(creature)
                for hexlabel in hexlabels:
                    guihex = self.guihexes[hexlabel]
                    guihex.selected = True
                self.update_gui(hexlabels)

    def _add_missing_chits(self):
        """Add chits for any creatures that lack them."""
        chit_creatures = set(chit.creature for chit in self.chits)
        for (legion, rotate) in [
          (self.game.attacker_legion, gtk.gdk.PIXBUF_ROTATE_CLOCKWISE),
          (self.game.defender_legion, gtk.gdk.PIXBUF_ROTATE_COUNTERCLOCKWISE)]:
            for creature in legion.creatures:
                if creature not in chit_creatures:
                    chit = Chit.Chit(creature, legion.player.color,
                      self.scale / 2, rotate=rotate)
                    self.chits.append(chit)

    def _compute_chit_locations(self, hexlabel):
        chits = self.chits_in_hex(hexlabel)
        num = len(chits)
        guihex = self.guihexes[hexlabel]
        chit_scale = self.chits[0].chit_scale
        bl = (guihex.center[0] - chit_scale / 2, guihex.center[1] -
          chit_scale / 2)

        if num == 1:
            chits[0].location = bl
        elif num == 2:
            chits[0].location = (bl[0], bl[1] - chit_scale / 2)
            chits[1].location = (bl[0], bl[1] + chit_scale / 2)
        elif num == 3:
            chits[0].location = (bl[0], bl[1] - chit_scale)
            chits[1].location = bl
            chits[2].location = (bl[0], bl[1] + chit_scale)
        elif num == 4:
            chits[0].location = (bl[0], bl[1] - 3 * chit_scale / 2)
            chits[1].location = (bl[0], bl[1] - chit_scale / 2)
            chits[2].location = (bl[0], bl[1] + chit_scale / 2)
            chits[3].location = (bl[0], bl[1] + 3 * chit_scale / 2)
        elif num == 5:
            chits[0].location = (bl[0], bl[1] - 2 * chit_scale)
            chits[1].location = (bl[0], bl[1] - chit_scale)
            chits[2].location = bl
            chits[3].location = (bl[0], bl[1] + chit_scale)
            chits[4].location = (bl[0], bl[1] + 2 * chit_scale)
        elif num == 6:
            chits[0].location = (bl[0], bl[1] - 5 * chit_scale / 2)
            chits[1].location = (bl[0], bl[1] - 3 * chit_scale / 2)
            chits[2].location = (bl[0], bl[1] - chit_scale / 2)
            chits[3].location = (bl[0], bl[1] + chit_scale / 2)
            chits[4].location = (bl[0], bl[1] + 3 * chit_scale / 2)
            chits[5].location = (bl[0], bl[1] + 5 * chit_scale / 2)
        elif num == 7:
            chits[0].location = (bl[0], bl[1] - 3 * chit_scale)
            chits[1].location = (bl[0], bl[1] - 2 * chit_scale)
            chits[2].location = (bl[0], bl[1] - chit_scale)
            chits[3].location = bl
            chits[4].location = (bl[0], bl[1] + chit_scale)
            chits[5].location = (bl[0], bl[1] + 2 * chit_scale)
            chits[6].location = (bl[0], bl[1] + 3 * chit_scale)
        else:
            raise AssertionError("invalid number of chits in hex")

    def _render_chit(self, chit, gc):
        drawable = self.area.window
        drawable.draw_pixbuf(gc, chit.pixbuf, 0, 0,
          int(round(chit.location[0])), int(round(chit.location[1])),
          -1, -1, gtk.gdk.RGB_DITHER_NORMAL, 0, 0)

    def chits_in_hex(self, hexlabel):
        return [chit for chit in self.chits
          if chit.creature.hexlabel == hexlabel]

    def draw_chits(self, gc):
        if not self.game:
            return
        self._add_missing_chits()
        hexlabels = set([chit.creature.hexlabel for chit in self.chits])
        for hexlabel in hexlabels:
            self._compute_chit_locations(hexlabel)
            chits = self.chits_in_hex(hexlabel)
            for chit in chits:
                self._render_chit(chit, gc)

    def cb_undo(self, action):
        if self.game:
            history = self.game.history
            if history.can_undo(self.username):
                last_action = history.actions[-1]
                def1 = self.user.callRemote("apply_action",
                  last_action.undo_action())
                def1.addErrback(self.failure)

    def cb_redo(self, action):
        if self.game:
            history = self.game.history
            if history.can_redo(self.username):
                action = history.undone[-1]
                def1 = self.user.callRemote("apply_action", action)
                def1.addErrback(self.failure)

    def cb_done(self, action):
        player = self.game.get_player_by_name(self.username)
        if player == self.game.battle_active_player:
            if self.game.battle_phase == Phase.MANEUVER:
                def1 = self.user.callRemote("done_with_maneuvers",
                  self.game.name)
                def1.addErrback(self.failure)
            elif self.game.battle_phase == Phase.STRIKE:
                # TODO Check to see if forced strikes remain
                def1 = self.user.callRemote("done_with_strikes",
                  self.game.name)
                def1.addErrback(self.failure)
            elif self.game.battle_phase == Phase.COUNTERSTRIKE:
                # TODO Check to see if forced strikes remain
                def1 = self.user.callRemote("done_with_counterstrikes",
                  self.game.name)
                def1.addErrback(self.failure)

    # TODO
    def cb_concede(self, action):
        pass

    def update_gui(self, hexlabels=None):
        gc = self.area.get_style().fg_gc[gtk.STATE_NORMAL]
        gc.line_width = int(round(0.2 * self.scale))
        if hexlabels is None:
            guihexes = self.guihexes.itervalues()
        else:
            guihexes = set(self.guihexes[hexlabel] for hexlabel in hexlabels)
        for guihex in guihexes:
            guihex.update_gui(gc)
        self.draw_chits(gc)

    def update(self, observed, action):
        if isinstance(action, Action.MoveCreature) or isinstance(action,
          Action.UndoMoveCreature):
            repaint_hexlabels = [action.old_hexlabel, action.new_hexlabel]
            self.update_gui(repaint_hexlabels)
            if action.playername == self.username:
                self.highlight_mobile_chits()

        elif isinstance(action, Action.DoneManeuvering):
            if self.game.battle_active_player.name == self.username:
                self.highlight_strikers()

        elif isinstance(action, Action.Strike):
            # XXX clean this up
            if action.hits > 0:
                for chit in self.chits:
                    if chit.creature.hexlabel == action.target_hexlabel:
                        chit._build_image()
            self.update_gui([action.target_hexlabel])
            if self.game.battle_active_player.name == self.username:
                self.highlight_strikers()

        elif isinstance(action, Action.DoneStriking):
            if self.game.battle_active_player.name == self.username:
                self.highlight_strikers()

    def failure(self, arg):
        print "GUIBattleMap.failure", arg


if __name__ == "__main__":
    entry_side = None
    if len(sys.argv) > 1:
        terrain = sys.argv[1].title()
        if len(sys.argv) > 2:
            entry_side = int(sys.argv[2])
    else:
        terrain = random.choice(battlemapdata.data.keys())
    if entry_side is None:
        if terrain == "Tower":
            entry_side = 5
        else:
            entry_side = random.choice([1, 3, 5])
    battlemap = BattleMap.BattleMap(terrain, entry_side)
    guimap = GUIBattleMap(battlemap)
    gtk.main()
