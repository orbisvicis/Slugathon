__copyright__ = "Copyright (c) 2004-2010 David Ripton"
__license__ = "GNU GPL v2"


import types

from slugathon.util.bag import bag
from slugathon.data import recruitdata
from slugathon.game import Creature, Action
from slugathon.util.Observed import Observed
from slugathon.util.log import log


class Legion(Observed):
    def __init__(self, player, markername, creatures, hexlabel):
        Observed.__init__(self)
        assert type(hexlabel) == types.IntType
        self.markername = markername
        self.creatures = creatures
        for creature in self.creatures:
            creature.legion = self
        # TODO Should we store the actual MasterHex instead?
        self.hexlabel = hexlabel  # an int not a str
        self.player = player
        self.moved = False
        self.teleported = False
        self.teleporting_lord = None
        self.entry_side = None
        self.previous_hexlabel = None
        self.recruited = False
        # List of tuples of recruiter names
        self.recruiter_names_list = []
        self.angels_pending = 0
        self.archangels_pending = 0

    @property
    def dead(self):
        """Return True iff this legion has been eliminated from battle."""
        alive = False
        for creature in self.creatures:
            if creature.dead:
                if creature.name == "Titan":
                    return True
            else:
                alive = True
        return not alive

    @property
    def living_creatures(self):
        return [creature for creature in self.creatures if not
          creature.dead]

    @property
    def living_creature_names(self):
        return [creature.name for creature in self.creatures if not
          creature.dead]

    @property
    def dead_creature_names(self):
        return [creature.name for creature in self.creatures if creature.dead]

    @property
    def any_summonable(self):
        for creature in self.creatures:
            if creature.summonable:
                return True
        return False

    @property
    def can_summon(self):
        """Return True if this legion's player has not already summoned this
        turn and any of this player's other unengaged legions has a summonable.
        """
        if len(self) >= 7 or self.player.summoned or self.dead:
            return False
        for legion in self.player.legions.itervalues():
            if legion != self and not legion.engaged and legion.any_summonable:
                return True
        return False

    @property
    def engaged(self):
        """Return True iff this legion is engaged with an enemy legion."""
        return self.hexlabel in self.player.game.engagement_hexlabels

    def __repr__(self):
        return "Legion %s in %s %s" % (self.markername, self.hexlabel,
          self.creatures)

    def __len__(self):
        """Return the number of living creatures in the legion."""
        return len(self.living_creature_names)

    def __eq__(self, other):
        return self.markername == other.markername

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def num_lords(self):
        return sum(creature.character_type == "lord" for creature in
          self.creatures)

    @property
    def first_lord_name(self):
        for creature in self.creatures:
            if creature.character_type == "lord":
                return creature.name
        return None

    @property
    def has_titan(self):
        for creature in self.creatures:
            if creature.name == "Titan":
                return True
        return False

    @property
    def lord_types(self):
        """Return a set of names of all lords in this legion."""
        types = set()
        for creature in self.creatures:
            if creature.character_type == "lord":
                types.add(creature.name)
        return types

    @property
    def creature_names(self):
        return sorted(creature.name for creature in self.creatures)

    @property
    def mobile_creatures(self):
        return [creature for creature in self.creatures if creature.mobile]

    @property
    def strikers(self):
        return [creature for creature in self.creatures if creature.can_strike]

    @property
    def forced_strikes(self):
        for creature in self.creatures:
            if (not creature.dead and not creature.struck and
              creature.engaged_enemies):
                return True
        return False

    def add_creature_by_name(self, creature_name):
        if len(self) >= 7:
            raise ValueError, "no room to add another creature"
        creature = Creature.Creature(creature_name)
        creature.legion = self
        self.creatures.append(creature)

    def remove_creature_by_name(self, creature_name):
        for creature in self.creatures:
            if creature.name == creature_name:
                self.creatures.remove(creature)
                return
        raise ValueError, "tried to remove missing creature"

    def can_be_split(self, turn):
        if turn == 1:
            return len(self) == 8
        else:
            return len(self) >= 4

    def is_legal_split(self, child1, child2):
        """Return whether this legion can be split into legions child1 and
        child2"""
        if len(self) < 4:
            return False
        if len(self) != len(child1) + len(child2):
            return False
        if len(child1) < 2 or len(child2) < 2:
            return False
        if not bag(self.creature_names) == bag(child1.creature_names +
          child2.creature_names):
            return False
        if len(self) == 8:
            if len(child1) != 4 or len(child2) != 4:
                return False
            if child1.num_lords != 1 or child2.num_lords != 1:
                return False
        return True

    def move(self, hexlabel, teleport, teleporting_lord, entry_side):
        """Move this legion on the masterboard"""
        self.moved = True
        self.previous_hexlabel = self.hexlabel
        self.hexlabel = hexlabel
        self.teleported = teleport
        self.teleporting_lord = teleporting_lord
        self.entry_side = entry_side

    def undo_move(self):
        """Undo this legion's last masterboard move"""
        if self.moved:
            self.moved = False
            # XXX This is bogus, but makes repainting the UI easier.
            (self.hexlabel, self.previous_hexlabel) = (self.previous_hexlabel,
              self.hexlabel)
            if self.teleported:
                self.teleported = False
                self.teleporting_lord = None
            self.entry_side = None

    @property
    def can_flee(self):
        return self.num_lords == 0

    def _gen_sublists(self, recruits):
        """Generate a sublist of recruits, within which up- and down-recruiting
        is possible."""
        sublist = []
        for tup in recruits:
            if tup:
                sublist.append(tup)
            else:
                yield sublist
                sublist = []
        yield sublist

    def _max_creatures_of_one_type(self):
        """Return the maximum number of creatures (not lords or demi-lords) of
        the same type in this legion."""
        counts = bag(self.creature_names)
        maximum = 0
        for name, num in counts.iteritems():
            if (num > maximum and Creature.Creature(name).character_type ==
              "creature"):
                maximum = num
        return maximum

    @property
    def can_recruit(self):
        """Return True iff the legion can currently recruit, if it moved
        or defended in a battle."""
        if len(self) >= 7 or self.recruited or self.dead:
            return False
        game = self.player.game
        mterrain = game.board.hexes[self.hexlabel].terrain
        caretaker = game.caretaker
        return bool(self.available_recruits_and_recruiters(mterrain,
          caretaker))

    def could_recruit(self, mterrain, caretaker):
        """Return True iff the legion could recruit in a masterhex with
        terrain type mterrain, if it moved there and was the right height
        and had not already recruited this turn."""
        return bool(self.available_recruits_and_recruiters(mterrain,
          caretaker))

    def available_recruits(self, mterrain, caretaker):
        """Return a list of the creature names that this legion could
        recruit in a masterhex with terrain type mterrain, if it moved there.

        The list is sorted in the same order as within recruitdata.
        """
        recruits = []
        for tup in self.available_recruits_and_recruiters(mterrain,
          caretaker):
            recruit = tup[0]
            if recruit not in recruits:
                recruits.append(recruit)
        return recruits

    def available_recruits_and_recruiters(self, mterrain, caretaker):
        """Return a list of tuples with creature names and recruiters that this
        legion could recruit in a masterhex with terrain type mterrain, if it
        moved there.

        Each tuple will contain the recruit as its first element, and the
        recruiters (if any) as its remaining elements.

        The list is sorted in the same order as within recruitdata.
        """
        result_list = []
        counts = bag(self.living_creature_names)
        recruits = recruitdata.data[mterrain]
        for sublist in self._gen_sublists(recruits):
            names = [tup[0] for tup in sublist]
            nums = [tup[1] for tup in sublist]
            for ii in xrange(len(sublist)):
                name = names[ii]
                num = nums[ii]
                if ii >= 1:
                    prev = names[ii - 1]
                else:
                    prev = None
                if prev == recruitdata.ANYTHING:
                    # basic tower creature
                    for jj in xrange(ii + 1):
                        if nums[jj] and caretaker.counts.get(names[jj]):
                            result_list.append((names[jj],))
                else:
                    if (prev == recruitdata.CREATURE and
                      self._max_creatures_of_one_type() >= num):
                        # guardian
                        recruiters = []
                        for name2, num2 in counts.iteritems():
                            if (num2 >= num and Creature.Creature(
                              name2).character_type == "creature"):
                                recruiters.append(name2)
                        for jj in xrange(ii + 1):
                            if nums[jj] and caretaker.counts.get(names[jj]):
                                for recruiter in recruiters:
                                    li = [names[jj]]
                                    for kk in xrange(num):
                                        li.append(recruiter)
                                    tup = tuple(li)
                                    result_list.append(tup)
                    if counts[prev] >= num:
                        # recruit up
                        if num and caretaker.counts.get(name):
                            li = [name]
                            for kk in xrange(num):
                                li.append(prev)
                            tup = tuple(li)
                            result_list.append(tup)
                    if counts[name] and num:
                        # recruit same or down
                        for jj in xrange(ii + 1):
                            if nums[jj] and caretaker.counts.get(names[jj]):
                                result_list.append((names[jj], name))

        def cmp_helper(tup1, tup2):
            ii = 0
            while True:
                if len(tup1) < ii + 1:
                    return -1
                if len(tup2) < ii + 1:
                    return 1
                if tup1[ii] != tup2[ii]:
                    c1 = Creature.Creature(tup1[ii])
                    c2 = Creature.Creature(tup2[ii])
                    diff = 100 * (c1.sort_value - c2.sort_value)
                    if diff != 0:
                        return int(diff)
                ii += 1

        result_list.sort(cmp=cmp_helper)
        return result_list


    def recruit(self, creature, recruiter_names):
        """Recruit creature, and notify observers."""
        log("recruit")
        player = self.player
        if self.recruited:
            log("already recruited")
            if self.creatures[-1].name == creature.name:
                # okay, don't do it twice
                pass
            else:
                raise AssertionError("legion tried to recruit twice")
        else:
            if len(self) >= 7:
                log(self)
                raise AssertionError("legion too tall to recruit")
            caretaker = self.player.game.caretaker
            if not caretaker.num_left(creature.name):
                raise AssertionError("none of creature left")
            caretaker.take_one(creature.name)
            self.creatures.append(creature)
            self.recruiter_names_list.append(recruiter_names)
            creature.legion = self
            log(self, "setting self.recruited")
            self.recruited = True
            action = Action.RecruitCreature(player.game.name, player.name,
              self.markername, creature.name, tuple(recruiter_names))
            self.notify(action)

    def undo_recruit(self):
        """Undo last recruit, and notify observers."""
        # Avoid double undo
        if not self.recruited:
            return
        player = self.player
        creature = self.creatures.pop()
        recruiter_names = self.recruiter_names_list.pop()
        log(self, "clearing self.recruited")
        self.recruited = False
        caretaker = self.player.game.caretaker
        caretaker.put_one_back(creature.name)
        action = Action.UndoRecruit(player.game.name, player.name,
          self.markername, creature.name, recruiter_names)
        self.notify(action)

    def unreinforce(self):
        """Undo reinforcement, and notify observers."""
        # Avoid double undo
        if not self.recruited:
            return
        player = self.player
        creature = self.creatures.pop()
        recruiter_names = self.recruiter_names_list.pop()
        log(self, "clearing self.recruited")
        self.recruited = False
        caretaker = self.player.game.caretaker
        caretaker.put_one_back(creature.name)
        action = Action.UnReinforce(player.game.name, player.name,
          self.markername, creature.name, recruiter_names)
        self.notify(action)

    @property
    def score(self):
        """Return the point value of this legion."""
        total = 0
        for creature in self.creatures:
            total += creature.score
        return total

    @property
    def sorted_creatures(self):
        """Return creatures, sorted in descending order of value."""
        li = reversed(sorted((creature.sort_value, creature)
          for creature in self.creatures))
        return [tup[1] for tup in li]

    @property
    def sort_value(self):
        """Return a rough indication of legion value."""
        return sum([creature.sort_value for creature in self.living_creatures])

    def die(self, scoring_legion, fled, no_points, check_for_victory=True):
        log("die", self, scoring_legion, fled, no_points, check_for_victory)
        if scoring_legion is not None and not no_points:
            points = self.score
            if fled:
                points //= 2
            scoring_legion.add_points(points, True)
        caretaker = self.player.game.caretaker
        dead_titan = False
        for creature in self.creatures:
            caretaker.kill_one(creature.name)
            if creature.name == "Titan":
                log("setting dead_titan")
                dead_titan = True
        self.player.remove_legion(self.markername)
        if dead_titan:
            self.player.die(scoring_legion, check_for_victory)

    def add_points(self, points, can_acquire):
        log("add_points", self, points, can_acquire)
        # TODO Move these to a data file
        ARCHANGEL_POINTS = 500
        ANGEL_POINTS = 100
        player = self.player
        score0 = player.score
        score1 = score0 + points
        player.score = score1
        log(player, "now has score", player.score)
        height = len(self)
        if can_acquire:
            archangels = 0
            if (height < 7 and
              score1 // ARCHANGEL_POINTS > score0 // ARCHANGEL_POINTS):
                archangels += 1
                score1 -= ANGEL_POINTS
            log("archangels %d" % archangels)
            angels = 0
            while (height + archangels + angels < 7 and
              score1 // ANGEL_POINTS > score0 // ANGEL_POINTS):
                angels += 1
                score1 -= ANGEL_POINTS
            log("angels %d" % angels)
            self.angels_pending = angels
            self.archangels_pending = archangels
            if angels + archangels > 0:
                action = Action.CanAcquire(self.player.game.name,
                  self.player.name, self.markername, angels, archangels)
                self.notify(action)


    def acquire(self, angels):
        """Acquire angels, and notify observers."""
        log("acquire", angels)
        num_archangels = num_angels = 0
        for angel in angels:
            if angel.name == "Archangel":
                num_archangels += 1
            elif angel.name == "Angel":
                num_angels += 1
        okay = (num_archangels <= self.archangels_pending and
          num_angels <= self.angels_pending + self.archangels_pending -
          num_archangels)
        if not okay:
            log("not enough angels pending")
            return
        if len(self) + num_angels + num_archangels > 7:
            raise AssertionError("legion too tall to acquire")
        caretaker = self.player.game.caretaker
        if caretaker.num_left("Archangel") < num_archangels:
            raise AssertionError("not enough Archangels left")
        if caretaker.num_left("Angel") < num_angels:
            raise AssertionError("not enough Angels left")
        self.archangels_pending -= num_archangels
        self.angels_pending -= num_angels
        for angel in angels:
            caretaker.take_one(angel.name)
            self.creatures.append(angel)
            angel.legion = self
        angel_names = [angel.name for angel in angels]
        action = Action.Acquire(self.player.game.name,
          self.player.name, self.markername, angel_names)
        self.notify(action)
        log("end of acquire", self)

    def do_not_acquire(self):
        """Do not acquire an angel, and notify observers."""
        log("do_not_acquire", self)
        if self.angels_pending or self.archangels_pending:
            self.reset_angels_pending()
            action = Action.DoNotAcquire(self.player.game.name,
              self.player.name, self.markername)
            self.notify(action)

    def reset_angels_pending(self):
        if self.angels_pending or self.archangels_pending:
            log("reset_angels_pending")
            self.angels_pending = 0
            self.archangels_pending = 0

    def enter_battle(self, hexlabel):
        for creature in self.creatures:
            creature.hexlabel = hexlabel
