__copyright__ = "Copyright (c) 2005-2006 David Ripton"
__license__ = "GNU GPL v2"


import time

from slugathon.game import Player, Game

def test_can_exit_split_phase():
    now = time.time()
    game = Game.Game("g1", "p0", now, now, 2, 6)
    player = Player.Player("p0", game, 0)
    player.assign_starting_tower(600)
    player.assign_color("Red")
    assert len(player.markernames) == 12
    player.pick_marker("Rd01")
    assert player.selected_markername == "Rd01"
    player.create_starting_legion()
    assert len(player.legions) == 1
    assert not player.can_exit_split_phase()

    player.split_legion("Rd01", "Rd02", ["Titan", "Ogre", "Ogre", "Gargoyle"],
      ["Angel", "Centaur", "Centaur", "Gargoyle"])
    assert player.can_exit_split_phase()


def test_friendly_legions():
    now = time.time()
    game = Game.Game("g1", "p0", now, now, 2, 6)
    player = Player.Player("p0", game, 0)
    player.assign_starting_tower(100)
    player.assign_color("Red")
    player.pick_marker("Rd01")
    player.create_starting_legion()
    legion1 = player.legions["Rd01"]
    player.split_legion("Rd01", "Rd02", ["Titan", "Ogre", "Ogre", "Gargoyle"],
      ["Angel", "Gargoyle", "Centaur", "Centaur"])
    legion2 = player.legions["Rd02"]
    assert player.friendly_legions() == set([legion1, legion2])
    assert player.friendly_legions(100) == set([legion1, legion2])
    assert player.friendly_legions(200) == set()
    legion1.move(8, False, None, 1)
    assert player.friendly_legions() == set([legion1, legion2])
    assert player.friendly_legions(100) == set([legion2])
    assert player.friendly_legions(8) == set([legion1])
    assert player.friendly_legions(200) == set()
    legion2.move(200, True, "Angel", 3)
    assert player.friendly_legions() == set([legion1, legion2])
    assert player.friendly_legions(100) == set()
    assert player.friendly_legions(8) == set([legion1])
    assert player.friendly_legions(200) == set([legion2])

def test_can_exit_move_phase():
    now = time.time()
    game = Game.Game("g1", "p0", now, now, 2, 6)
    player = Player.Player("p0", game, 0)
    player.assign_starting_tower(100)
    player.assign_color("Red")
    player.pick_marker("Rd01")
    player.create_starting_legion()
    legion1 = player.legions["Rd01"]
    player.split_legion("Rd01", "Rd02", ["Titan", "Ogre", "Ogre", "Gargoyle"],
      ["Angel", "Gargoyle", "Centaur", "Centaur"])
    legion2 = player.legions["Rd02"]
    assert not player.can_exit_move_phase()
    legion1.move(8, False, None, 1)
    assert player.can_exit_move_phase()
    legion2.move(200, True, "Angel", 3)
    assert player.can_exit_move_phase()

def test_num_creatures():
    now = time.time()
    game = Game.Game("g1", "p0", now, now, 2, 6)
    player = Player.Player("p0", game, 0)
    player.assign_starting_tower(600)
    player.assign_color("Red")
    assert len(player.markernames) == 12
    player.pick_marker("Rd01")
    assert player.selected_markername == "Rd01"
    player.create_starting_legion()
    assert player.num_creatures() == 8

def test_teleported():
    now = time.time()
    game = Game.Game("g1", "p0", now, now, 2, 6)
    player = Player.Player("p0", game, 0)
    player.assign_starting_tower(600)
    player.assign_color("Red")
    assert len(player.markernames) == 12
    player.pick_marker("Rd01")
    assert player.selected_markername == "Rd01"
    player.create_starting_legion()
    assert player.num_creatures() == 8
    assert not player.teleported
    player.split_legion("Rd01", "Rd02", ["Titan", "Ogre", "Ogre", "Gargoyle"],
      ["Angel", "Gargoyle", "Centaur", "Centaur"])
    legion1 = player.legions["Rd01"]
    legion2 = player.legions["Rd02"]
    legion1.move(8, False, None, 1)
    assert not player.teleported
    legion2.move(200, True, "Angel", 3)
    assert player.teleported
    legion2.undo_move()
    assert not player.teleported