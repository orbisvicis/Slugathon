#!/usr/bin/env python

__copyright__ = "Copyright (c) 2006-2009 David Ripton"
__license__ = "GNU GPL v2"


import gtk
from zope.interface import implements

from slugathon.gui import icon
from slugathon.util.Observer import IObserver
from slugathon.game import Action, Phase
from slugathon.util import prefs


class StatusScreen(object):
    """Game status window."""

    implements(IObserver)


    def __init__(self, game, user, username):
        self.game = game
        self.user = user
        self.username = username

        self.contrasting = {
            "Black": "White",
            "Blue": "White",
            "Brown": "White",
            "Green": "Black",
            "Gold": "Black",
            "Red": "White",
        }
        self.status_screen_window = gtk.Window()
        vbox1 = gtk.VBox()
        self.status_screen_window.add(vbox1)
        turn_table = gtk.Table(rows=4, columns=3)
        vbox1.pack_start(turn_table)

        self.add_label(turn_table, 2, 1, "Game")
        self.add_label(turn_table, 3, 1, "Battle")
        self.add_label(turn_table, 1, 2, "Turn")
        self.add_label(turn_table, 1, 3, "Player")
        self.add_label(turn_table, 1, 4, "Phase")
        self.game_turn_label = self.add_label(turn_table, 2, 2)
        self.battle_turn_label = self.add_label(turn_table, 3, 2)
        self.game_player_label = self.add_label(turn_table, 2, 3)
        self.battle_player_label = self.add_label(turn_table, 3, 3)
        self.game_phase_label = self.add_label(turn_table, 2, 4)
        self.battle_phase_label = self.add_label(turn_table, 3, 4)

        hseparator1 = gtk.HSeparator()
        vbox1.pack_start(hseparator1)
        self.player_table = gtk.Table(rows=9, columns=len(self.game.players)
          + 1)
        vbox1.pack_start(self.player_table)

        for row, text in enumerate(["Name", "Tower", "Color", "Legions",
          "Markers", "Creatures", "Titan Power", "Eliminated", "Score"]):
            self.add_label(self.player_table, 1, row, text)

        for col, num in enumerate(xrange(len(self.game.players))):
            for row, st in enumerate(["name%d_label", "tower%d_label",
              "color%d_label", "legions%d_label", "markers%d_label",
              "creatures%d_label", "titan_power%d_label", "eliminated%d_label",
              "score%d_label"]):
                name = st % num
                label = self.add_label(self.player_table, col + 2, row)
                setattr(self, name, label)

        self.status_screen_window.connect("configure-event",
          self.cb_configure_event)

        if self.username:
            tup = prefs.load_window_position(self.username,
              self.__class__.__name__)
            if tup:
                x, y = tup
                self.status_screen_window.move(x, y)
            tup = prefs.load_window_size(self.username,
              self.__class__.__name__)
            if tup:
                width, height = tup
                self.status_screen_window.resize(width, height)

        self.default_bg = None
        self._init_players()
        self._init_turn()

        self.status_screen_window.set_icon(icon.pixbuf)
        self.status_screen_window.set_title("Game Status - %s" % self.username)
        self.status_screen_window.show_all()
        self.default_bg = \
          self.status_screen_window.get_style().copy().bg[gtk.STATE_NORMAL]


    def add_label(self, table, col, row, text=""):
        """Add a label inside an eventbox to the table."""
        label = gtk.Label(text)
        eventbox = gtk.EventBox()
        eventbox.add(label)
        label.eventbox = eventbox
        table.attach(eventbox, col, col + 1, row, row + 1)
        return label

    def set_bg(self, label, color):
        if color:
            if isinstance(color, str):
                gtkcolor = gtk.gdk.color_parse(color)
            else:
                gtkcolor = color
            label.eventbox.modify_bg(gtk.STATE_NORMAL, gtkcolor)

    def cb_configure_event(self, event, unused):
        if self.username:
            x, y = self.status_screen_window.get_position()
            prefs.save_window_position(self.username, self.__class__.__name__,
              x, y)
            width, height = self.status_screen_window.get_size()
            prefs.save_window_size(self.username, self.__class__.__name__,
              width, height)
        return False

    def _init_turn(self):
        self.game_turn_label.set_text(str(self.game.turn))
        self.game_phase_label.set_text(Phase.phase_names[self.game.phase])
        if self.game.active_player:
            if self.game.active_player.name == self.username:
                self.set_bg(self.game_player_label, "Yellow")
            else:
                self.set_bg(self.game_player_label, self.default_bg)
            self.game_player_label.set_text(self.game.active_player.name)
        self._clear_battle()
        self._color_player_columns()

    def _color_player_columns(self):
        for num, player in enumerate(self.game.players):
            bg = self.default_bg
            try:
                if player.name == self.game.active_player.name:
                    bg = "Yellow"
                elif player.dead:
                    bg = "Red"
            except AttributeError:
                pass
            player_color = self.default_bg
            try:
                if player.color is not None:
                    player_color = player.color
            except AttributeError:
                pass
            name_label = getattr(self, "name%d_label" % num)
            self.set_bg(name_label, player_color)
            tower_label = getattr(self, "tower%d_label" % num)
            self.set_bg(tower_label, bg)
            color_label = getattr(self, "color%d_label" % num)
            self.set_bg(color_label, bg)
            legions_label = getattr(self, "legions%d_label" % num)
            self.set_bg(legions_label, bg)
            markers_label = getattr(self, "markers%d_label" % num)
            self.set_bg(markers_label, bg)
            creatures_label = getattr(self, "creatures%d_label" % num)
            self.set_bg(creatures_label, bg)
            titan_power_label = getattr(self, "titan_power%d_label" % num)
            self.set_bg(titan_power_label, bg)
            eliminated_label = getattr(self, "eliminated%d_label" % num)
            self.set_bg(eliminated_label, bg)
            score_label = getattr(self, "score%d_label" % num)
            self.set_bg(score_label, bg)

    def _init_players(self):
        for num, player in enumerate(self.game.players):
            bg = self.default_bg
            try:
                if player.name == self.game.active_player.name:
                    bg = "Yellow"
                elif player.dead:
                    bg = "Red"
            except AttributeError:
                pass
            player_color = self.default_bg
            try:
                if player.color is not None:
                    player_color = player.color
            except AttributeError:
                pass
            name_label = getattr(self, "name%d_label" % num)
            self.set_bg(name_label, player_color)
            name_label.set_markup("<span foreground='%s'>%s</span>" % (
              self.contrasting.get(str(player_color), "Black"), player.name))
            tower_label = getattr(self, "tower%d_label" % num)
            tower_label.set_text(str(player.starting_tower))
            self.set_bg(tower_label, bg)
            color_label = getattr(self, "color%d_label" % num)
            color_label.set_text(str(player.color or ""))
            self.set_bg(color_label, bg)
            legions_label = getattr(self, "legions%d_label" % num)
            legions_label.set_text(str(len(player.legions)))
            self.set_bg(legions_label, bg)
            markers_label = getattr(self, "markers%d_label" % num)
            markers_label.set_text(str(len(player.markernames)))
            self.set_bg(markers_label, bg)
            creatures_label = getattr(self, "creatures%d_label" % num)
            creatures_label.set_text(str(player.num_creatures()))
            self.set_bg(creatures_label, bg)
            titan_power_label = getattr(self, "titan_power%d_label" % num)
            titan_power_label.set_text(str(player.titan_power()))
            self.set_bg(titan_power_label, bg)
            eliminated_label = getattr(self, "eliminated%d_label" % num)
            eliminated_label.set_text("".join(player.eliminated_colors))
            self.set_bg(eliminated_label, bg)
            score_label = getattr(self, "score%d_label" % num)
            score_label.set_text(str(player.score))
            self.set_bg(score_label, bg)

    def _init_battle(self):
        if self.game.battle_turn is not None:
            self.battle_turn_label.set_text(str(self.game.battle_turn))
            if self.game.battle_active_player.name == self.username:
                self.set_bg(self.battle_player_label, "Yellow")
            else:
                self.set_bg(self.battle_player_label, self.default_bg)
            self.battle_player_label.set_text(
              self.game.battle_active_player.name)
            self.battle_phase_label.set_text(Phase.battle_phase_names[
              self.game.battle_phase])
        else:
            self._clear_battle()

    def _clear_battle(self):
        self.battle_turn_label.set_text("")
        self.set_bg(self.battle_player_label, self.default_bg)
        self.battle_player_label.set_text("")
        self.battle_phase_label.set_text("")

    def update(self, observed, action):
        if isinstance(action, Action.AssignedAllTowers):
            # Players got renumbered, so re-init everything.
            self._init_players()
            self._init_turn()

        elif isinstance(action, Action.PickedColor):
            playername = action.playername
            player = self.game.get_player_by_name(playername)
            player_num = self.game.players.index(player)
            color = action.color
            color_label = getattr(self, "color%d_label" % player_num)
            color_label.set_text(color)
            name_label = getattr(self, "name%d_label" % player_num)
            self.set_bg(name_label, color)
            name_label.set_markup("<span foreground='%s'>%s</span>" % (
              self.contrasting.get(str(color), "Black"), player.name))

        elif isinstance(action, Action.AssignedAllColors):
            self._init_turn()

        elif isinstance(action, Action.CreateStartingLegion):
            playername = action.playername
            player = self.game.get_player_by_name(playername)
            player_num = self.game.players.index(player)
            legions_label = getattr(self, "legions%d_label" % player_num)
            legions_label.set_text(str(len(player.legions)))
            creatures_label = getattr(self, "creatures%d_label" % player_num)
            creatures_label.set_text(str(player.num_creatures()))
            markers_label = getattr(self, "markers%d_label" % player_num)
            markers_label.set_text(str(len(player.markernames)))

        elif (isinstance(action, Action.SplitLegion) or
          isinstance(action, Action.UndoSplit) or
          isinstance(action, Action.MergeLegions)):
            playername = action.playername
            player = self.game.get_player_by_name(playername)
            player_num = self.game.players.index(player)
            legions_label = getattr(self, "legions%d_label" % player_num)
            legions_label.set_text(str(len(player.legions)))
            markers_label = getattr(self, "markers%d_label" % player_num)
            markers_label.set_text(str(len(player.markernames)))

        elif isinstance(action, Action.RollMovement):
            self.game_phase_label.set_text(Phase.phase_names[self.game.phase])

        elif isinstance(action, Action.DoneMoving):
            self.game_phase_label.set_text(Phase.phase_names[self.game.phase])

        elif (isinstance(action, Action.RecruitCreature) or
          isinstance(action, Action.UndoRecruit) or
          isinstance(action, Action.AcquireAngel)):
            playername = action.playername
            player = self.game.get_player_by_name(playername)
            player_num = self.game.players.index(player)
            creatures_label = getattr(self, "creatures%d_label" % player_num)
            creatures_label.set_text(str(player.num_creatures()))

        elif isinstance(action, Action.DoneRecruiting):
            self._init_turn()

        elif (isinstance(action, Action.Flee) or
          isinstance(action, Action.Concede) or
          isinstance(action, Action.AcceptProposal) or
          isinstance(action, Action.RemoveLegion)):
            for num, player in enumerate(self.game.players):
                legions_label = getattr(self, "legions%d_label" % num)
                legions_label.set_text(str(len(player.legions)))
                markers_label = getattr(self, "markers%d_label" % num)
                markers_label.set_text(str(len(player.markernames)))
                creatures_label = getattr(self, "creatures%d_label" % num)
                creatures_label.set_text(str(player.num_creatures()))
                titan_power_label = getattr(self, "titan_power%d_label" % num)
                titan_power_label.set_text(str(player.titan_power()))
                score_label = getattr(self, "score%d_label" % num)
                score_label.set_text(str(player.score))

        elif (isinstance(action, Action.Fight) or
          isinstance(action, Action.DoneReinforcing) or
          isinstance(action, Action.DoneManeuvering) or
          isinstance(action, Action.DoneStriking) or
          isinstance(action, Action.DoneStrikingBack)):
            self._init_battle()

        elif (isinstance(action, Action.DoneFighting) or
          isinstance(action, Action.BattleOver)):
            self._clear_battle()
            self.game_phase_label.set_text(Phase.phase_names[self.game.phase])



if __name__ == "__main__":
    import time
    from slugathon.util import guiutils
    from slugathon.game import Game, Player, Creature
    from slugathon.data import creaturedata

    now = time.time()
    user = None
    username = "p1"
    creatures = Creature.n2c(creaturedata.starting_creature_names)
    game = Game.Game("g1", "Player 1", now, now, 2, 6)

    player1 = game.players[0]
    player1.assign_starting_tower(600)
    player1.assign_color("Red")
    player1.pick_marker("Rd01")
    player1.create_starting_legion()
    game.active_player = player1

    player2 = Player.Player("Player 2", game, 1)
    player2.assign_starting_tower(500)
    player2.assign_color("Blue")
    player2.pick_marker("Bu02")
    player2.create_starting_legion()
    game.players.append(player2)

    player3 = Player.Player("Player 3", game, 2)
    player3.assign_starting_tower(400)
    player3.assign_color("Green")
    player3.pick_marker("Gr03")
    player3.create_starting_legion()
    game.players.append(player3)

    player4 = Player.Player("Player 4", game, 3)
    player4.assign_starting_tower(300)
    player4.assign_color("Brown")
    player4.pick_marker("Br04")
    player4.create_starting_legion()
    game.players.append(player4)

    player5 = Player.Player("Player 5", game, 4)
    player5.assign_starting_tower(200)
    player5.assign_color("Black")
    player5.pick_marker("Bk05")
    player5.create_starting_legion()
    game.players.append(player5)

    player6 = Player.Player("Player 6", game, 5)
    player6.assign_starting_tower(100)
    player6.assign_color("Gold")
    player6.pick_marker("Gd06")
    player6.create_starting_legion()
    game.players.append(player6)

    status_screen = StatusScreen(game, user, username)
    status_screen.status_screen_window.connect("destroy", guiutils.exit)
    gtk.main()