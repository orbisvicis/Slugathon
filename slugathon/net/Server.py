#!/usr/bin/env python

__copyright__ = "Copyright (c) 2003-2012 David Ripton"
__license__ = "GNU GPL v2"


import os
import time
import argparse
import tempfile
import sys
import random
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from collections import Counter

from twisted.spread import pb
from twisted.cred.portal import Portal
from twisted.internet import reactor, protocol, defer
from twisted.python import log
from zope.interface import implementer

from slugathon.net import Realm, config, Results
from slugathon.game import Game, Action, Phase
from slugathon.util.Observed import Observed
from slugathon.util.Observer import IObserver
from slugathon.net.UniqueFilePasswordDB import UniqueFilePasswordDB
from slugathon.net.UniqueNoPassword import UniqueNoPassword
from slugathon.util import prefs


TEMPDIR = tempfile.gettempdir()


defer.setDebugging(True)


@implementer(IObserver)
class Server(Observed):

    """A Slugathon server, which can host multiple games in parallel."""

    def __init__(self, no_passwd, passwd_path, port, log_path):
        Observed.__init__(self)
        self.no_passwd = no_passwd
        self.passwd_path = passwd_path
        self.port = port
        self.games = []
        self.playernames = set()
        self.results = Results.Results()
        # {game_name: set(ainame) we're waiting for
        self.game_to_waiting_ais = {}
        self._setup_logging(log_path)

    def _setup_logging(self, log_path):
        log_observer = log.PythonLoggingObserver()
        log_observer.start()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d "
            "%(message)s")
        if not log_path:
            logdir = os.path.join(TEMPDIR, "slugathon")
            if not os.path.exists(logdir):
                os.makedirs(logdir)
            log_path = os.path.join(logdir, "slugathon-server-%d.log" %
                                    self.port)
        file_handler = RotatingFileHandler(filename=log_path,
                                           maxBytes=100000000, backupCount=99)
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def __repr__(self):
        return "Server"

    def add_observer(self, user):
        playername = user.name
        Observed.add_observer(self, user, playername)
        self.playernames.add(playername)
        action = Action.AddUsername(playername)
        self.notify(action)

    def remove_observer(self, user):
        Observed.remove_observer(self, user)
        playername = user.name
        if playername in self.playernames:
            self.playernames.remove(playername)
            action = Action.DelUsername(playername)
            self.notify(action)

    def logout(self, user):
        playername = user.name
        self.remove_observer(user)
        for game in self.games:
            if playername in game.playernames:
                self.withdraw(playername, game.name)

    def name_to_game(self, game_name):
        for game in self.games:
            if game.name == game_name:
                return game
        return None

    def get_game_info_tuples(self):
        """Return a list of Game.info_tuple for each current or recent game."""
        results = []
        num_wanted = 100
        num_from_db = max(0, num_wanted - len(self.games))
        if num_from_db:
            results = self.results.get_game_info_tuples(num_from_db)
        for game in self.games[-num_wanted:]:
            results.append(game.info_tuple)
        return results

    def send_chat_message(self, source, dest, text):
        """Send a chat message from user source to users in dest.

        source is a playername.  dest is a set of playernames.
        If dest is None, send to all users
        """
        message = "%s: %s" % (source, text)
        if dest is not None:
            dest.add(source)
        action = Action.ChatMessage(source, message)
        self.notify(action, names=dest)

    def form_game(self, playername, game_name, min_players, max_players,
                  ai_time_limit, player_time_limit, player_class, player_info):
        """Form a new game.

        Return None normally, or an error string if there's a problem.
        """
        logging.info("%s %s %s %s %s %s %s %s", playername, game_name,
                     min_players, max_players, ai_time_limit,
                     player_time_limit, player_class, player_info)
        if not game_name:
            st = "Games must be named"
            logging.warning(st)
            return st
        game_names_reserved = set\
                ( game.name
                  for game in self.games
                  if not game.started or not game.over
                )
        if game_name in game_names_reserved:
            st = 'The game name "%s" is currently in use' % game_name
            logging.warning(st)
            return st
        if min_players > max_players:
            st = "min_players must be <= max_players"
            logging.warning(st)
            return st
        now = time.time()
        GAME_START_DELAY = 5 * 60
        game = Game.Game(game_name, playername, now, now + GAME_START_DELAY,
                         min_players, max_players, master=True,
                         ai_time_limit=ai_time_limit,
                         player_time_limit=player_time_limit,
                         player_class=player_class,
                         player_info=player_info)
        self.games.append(game)
        game.add_observer(self)
        action = Action.FormGame(playername, game.name, game.create_time,
                                 game.start_time, game.min_players,
                                 game.max_players, ai_time_limit,
                                 player_time_limit, player_class, player_info)
        self.notify(action)

    def join_game(self, playername, game_name, player_class, player_info):
        """Join an existing game that hasn't started yet.

        Return True on success, False on failure.
        """
        logging.info("%s %s %s %s", playername, game_name, player_class,
                     player_info)
        game = self.name_to_game(game_name)
        if game:
            try:
                game.add_player(playername, player_class, player_info)
            except AssertionError:
                logging.exception("join_game caught an exception")
                return False
            else:
                action = Action.JoinGame(playername, game.name, player_class,
                                         player_info)
                self.notify(action)
            set1 = self.game_to_waiting_ais.get(game_name)
            if set1:
                set1.discard(playername)
                if not set1:
                    game = self.name_to_game(game_name)
                    reactor.callLater(1, game.start, game.owner.name)
            return True
        return False

    def start_game(self, playername, game_name):
        """Start an existing game."""
        logging.info("%s %s", playername, game_name)
        game = self.name_to_game(game_name)
        if game:
            if playername != game.owner.name:
                logging.warning("start_game called by non-owner")
                return
            if game.num_players < game.min_players:
                self._spawn_ais(game)
                # Reschedule this in case spawning AIs fails.
                reactor.callLater(1, self.start_game, playername, game_name)
                return
            else:
                if not game.started:
                    game.start(playername)
        else:
            logging.warning("game %s does not exist", game_name)

    def _passwd_for_playername(self, playername):
        try:
            with open(self.passwd_path, "r") as fil:
                for line in fil:
                    user, passwd = line.strip().split(":")
                    if user == playername:
                        return passwd
            return None
        except IOError:
            return None

    def _add_playername_with_random_password(self, ainame):
        password = hashlib.md5(str(random.random())).hexdigest()
        with open(self.passwd_path, "a") as fil:
            fil.write("%s:%s\n" % (ainame, password))

    def _spawn_ais(self, game):
        logging.debug(game.name)
        excludes = set()
        for game3 in self.games:
            if not game3.over:
                for player in game3.players:
                    player_id = self.results.get_player_id(player.player_info)
                    excludes.add(player_id)
        for game_name, waiting_ais in self.game_to_waiting_ais.items():
            game2 = self.name_to_game(game_name)
            if game2 and not game2.over and game2 != game:
                for ainame in waiting_ais:
                    player_id = int(ainame[2:])
                    excludes.add(player_id)
        num_ais = game.min_players - game.num_players
        logging.debug("%s min_players %d num_players %d num_ais_needed %s",
                      game.name, game.min_players, game.num_players, num_ais)
        logging.debug("%s excludes %s", game.name, sorted(excludes))
        ainames = []
        for unused in range(num_ais):
            player_id = self.results.get_weighted_random_player_id(
                excludes=excludes, highest_mu=game.any_humans)
            excludes.add(player_id)
            ainame = "ai%d" % player_id
            ainames.append(ainame)
        for ainame in ainames:
            if self._passwd_for_playername(ainame) is None:
                self._add_playername_with_random_password(ainame)
        logging.debug("%s ainames %s", game.name, ainames)
        # Add all AIs to the wait list first, to avoid a race.
        self.game_to_waiting_ais[game.name] = set(ainames)
        if hasattr(sys, "frozen"):
            # TODO Find the absolute path.
            executable = "slugathon.exe"
        else:
            executable = sys.executable
        logdir = os.path.join(TEMPDIR, "slugathon")
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        for ainame in ainames:
            pp = AIProcessProtocol(self, game.name, ainame)
            args = [executable]
            if hasattr(sys, "frozen"):
                args.extend(["ai"])
            else:
                args.extend(["-m", "slugathon.ai.AIClient"])
            args.extend([
                "--playername", ainame,
                "--port", str(self.port),
                "--game-name", game.name,
                "--log-path", os.path.join(logdir, "slugathon-%s-%s.log" %
                                           (game.name, ainame)),
                "--ai-time-limit", str(game.ai_time_limit),
            ])
            if not self.no_passwd:
                aipass = self._passwd_for_playername(ainame)
                if aipass is None:
                    logging.warning(
                        "user %s is not in %s; ai will fail to join" % (
                            ainame, self.passwd_path))
                else:
                    args.extend(["--password", aipass])
            logging.info("spawning AI process for %s %s", game, ainame)
            reactor.spawnProcess(pp, executable, args=args, env=os.environ)

    def pick_color(self, playername, game_name, color):
        """Pick a player color."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if player is None:
                logging.warning("no such player")
                return
            if player.color == color:
                logging.warning("color already assigned")
                return
            if playername != game.next_playername_to_pick_color:
                logging.warning("not this player's turn")
                return
            if color not in game.colors_left:
                logging.warning("invalid color")
                return
            game.assign_color(playername, color)

    def pick_first_marker(self, playername, game_name, markerid):
        """Pick a player's first legion marker."""
        game = self.name_to_game(game_name)
        if game:
            game.assign_first_marker(playername, markerid)

    def split_legion(self, playername, game_name, parent_markerid,
                     child_markerid, parent_creature_names,
                     child_creature_names):
        """Split a legion."""
        logging.info("%s %s %s %s %s %s", playername, game_name,
                     parent_markerid, child_markerid, parent_creature_names,
                     child_creature_names)
        game = self.name_to_game(game_name)
        if not game:
            logging.warning("no game")
            return
        parent = game.find_legion(parent_markerid)
        if parent is None:
            logging.warning("no legion")
            return
        player = game.get_player_by_name(playername)
        if player is not game.active_player:
            logging.warning("wrong player")
            return
        if game.phase is not Phase.PhaseMaster.SPLIT:
            logging.warning("wrong phase")
            return
        parent = player.markerid_to_legion.get(parent_markerid)
        if parent is None:
            logging.warning("no parent")
            return
        if child_markerid not in player.markerids_left:
            logging.warning("no marker")
            return
        if len(parent_creature_names) < 2:
            logging.warning("parent too short")
            return
        if len(parent_creature_names) > 5:
            logging.warning("parent too tall")
            return
        if len(child_creature_names) < 2:
            logging.warning("child too short")
            return
        if len(child_creature_names) > 5:
            logging.warning("child too tall")
            return
        if (    Counter(parent_creature_names) + Counter(child_creature_names) !=
                Counter(parent.creature_names)
           ):
            logging.warning("wrong creatures")
        game.split_legion(playername, parent_markerid, child_markerid,
                          parent_creature_names, child_creature_names)

    def undo_split(self, playername, game_name, parent_markerid,
                   child_markerid):
        """Undo a split."""
        game = self.name_to_game(game_name)
        if game:
            game.undo_split(playername, parent_markerid, child_markerid)

    def done_with_splits(self, playername, game_name):
        """Finish the split phase."""
        game = self.name_to_game(game_name)
        if game:
            game.done_with_splits(playername)

    def take_mulligan(self, playername, game_name):
        """Take a mulligan and reroll movement."""
        game = self.name_to_game(game_name)
        if game:
            game.take_mulligan(playername)

    def move_legion(self, playername, game_name, markerid, hexlabel,
                    entry_side, teleport, teleporting_lord):
        """Move one legion on the masterboard."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            legion = player.markerid_to_legion.get(markerid)
            if legion is None:
                logging.warning("no legion")
                return
            if not game.can_move_legion(player, legion, hexlabel, entry_side,
                                        teleport, teleporting_lord):
                logging.warning("cannot move")
                return
            game.move_legion(playername, markerid, hexlabel, entry_side,
                             teleport, teleporting_lord)

    def undo_move_legion(self, playername, game_name, markerid):
        """Undo one legion move."""
        game = self.name_to_game(game_name)
        if game:
            game.undo_move_legion(playername, markerid)

    def done_with_moves(self, playername, game_name):
        """Finish the masterboard movement phase."""
        game = self.name_to_game(game_name)
        game = self.name_to_game(game_name)
        if game:
            game.done_with_moves(playername)
        else:
            logging.warning("done_with_moves for bad game %s", game_name)

    def resolve_engagement(self, playername, game_name, hexlabel):
        """Pick the next engagement to resolve."""
        logging.info("Server.resolve_engagement %s %s %s", playername,
                     game_name, hexlabel)
        game = self.name_to_game(game_name)
        if game:
            game.resolve_engagement(playername, hexlabel)

    def flee(self, playername, game_name, markerid):
        """Flee from an engagement."""
        game = self.name_to_game(game_name)
        if game:
            legion = game.find_legion(markerid)
            if not legion:
                logging.warning("flee with no legion %s", markerid)
                return
            hexlabel = legion.hexlabel
            for enemy_legion in game.all_legions(hexlabel):
                if enemy_legion != legion:
                    break
            # Enemy illegally managed to concede before we could flee.
            if enemy_legion == legion:
                logging.warning("illegal concede before flee")
                return
            player = game.get_player_by_name(playername)
            if player == game.active_player:
                logging.warning("attacker tried to flee")
                return
            if legion.player != player:
                logging.warning("wrong player tried to flee")
                return
            if not legion.can_flee:
                logging.warning("illegal flee attempt")
                return
            enemy_markerid = enemy_legion.markerid
            action = Action.Flee(game.name, markerid, enemy_markerid,
                                 legion.hexlabel)
            game.update(self, action, None)

    def do_not_flee(self, playername, game_name, markerid):
        """Do not flee from an engagement."""
        game = self.name_to_game(game_name)
        if game:
            legion = game.find_legion(markerid)
            hexlabel = legion.hexlabel
            player = game.get_player_by_name(playername)
            if player == game.active_player:
                logging.warning("attacker tried to not flee")
                return
            legion = player.markerid_to_legion.get(markerid)
            if legion is None:
                logging.warning("no legion")
                return
            if legion.player != player:
                logging.warning("wrong player tried to not flee")
                return
            for enemy_legion in game.all_legions(hexlabel):
                if enemy_legion != legion:
                    break
            enemy_markerid = enemy_legion.markerid
            action = Action.DoNotFlee(game.name, markerid, enemy_markerid,
                                      hexlabel)
            game.update(self, action, None)

    def concede(self, playername, game_name, markerid, enemy_markerid,
                hexlabel):
        """Concede an engagement."""
        game = self.name_to_game(game_name)
        if game:
            game.concede(playername, markerid)

    def make_proposal(self, playername, game_name, attacker_markerid,
                      attacker_creature_names, defender_markerid,
                      defender_creature_names):
        """Make a proposal to settle an engagement."""
        game = self.name_to_game(game_name)
        if game:
            game.make_proposal(playername, attacker_markerid,
                               attacker_creature_names, defender_markerid,
                               defender_creature_names)

    def accept_proposal(self, playername, game_name, attacker_markerid,
                        attacker_creature_names, defender_markerid,
                        defender_creature_names):
        """Accept a previous proposal to settle an engagement."""
        game = self.name_to_game(game_name)
        if game:
            game.accept_proposal(playername, attacker_markerid,
                                 attacker_creature_names, defender_markerid,
                                 defender_creature_names)

    def reject_proposal(self, playername, game_name, attacker_markerid,
                        attacker_creature_names, defender_markerid,
                        defender_creature_names):
        """Reject a previous proposal to settle an engagement."""
        game = self.name_to_game(game_name)
        if game:
            game.reject_proposal(playername, attacker_markerid,
                                 attacker_creature_names, defender_markerid,
                                 defender_creature_names)

    def no_more_proposals(self, playername, game_name, attacker_markerid,
                          defender_markerid):
        """Indicate that this player will make no more proposals to settle the
        current engagement."""
        game = self.name_to_game(game_name)
        if game:
            game.no_more_proposals(playername, attacker_markerid,
                                   defender_markerid)

    def fight(self, playername, game_name, attacker_markerid,
              defender_markerid):
        """Fight the current current engagement."""
        logging.info("Server.fight %s %s %s %s", playername, game_name,
                     attacker_markerid, defender_markerid)
        game = self.name_to_game(game_name)
        if game:
            attacker_legion = game.find_legion(attacker_markerid)
            attacker_legion = game.find_legion(attacker_markerid)
            defender_legion = game.find_legion(defender_markerid)
            if (not attacker_legion or not defender_legion or playername not in
                    [attacker_legion.player.name,
                     defender_legion.player.name]):
                logging.warning("illegal fight call from %s", playername)
                return
            if (defender_legion.can_flee and not
                    game.defender_chose_not_to_flee):
                logging.warning(
                    "Illegal fight call while defender can still flee")
                return
            action = Action.Fight(game.name, attacker_markerid,
                                  defender_markerid, attacker_legion.hexlabel)
            logging.info("Server.fight calling game.update")
            game.update(self, action, None)

    def move_creature(self, playername, game_name, creature_name, old_hexlabel,
                      new_hexlabel):
        """Move one creature on the battle map."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if player is None:
                logging.warning("no player")
                return
            if player != game.battle_active_player:
                logging.warning("out of turn")
                return
            legion = game.battle_active_legion
            if not legion:
                logging.warning("no battle legion")
                return
            creature = legion.find_creature(creature_name, old_hexlabel)
            if not creature:
                logging.warning("no such creature")
                return
            if new_hexlabel not in game.find_battle_moves(creature):
                logging.warning("invalid move")
                return
            game.move_creature(playername, creature_name, old_hexlabel,
                               new_hexlabel)

    def undo_move_creature(self, playername, game_name, creature_name,
                           new_hexlabel):
        """Undo one creature move on the battle map."""
        game = self.name_to_game(game_name)
        if game:
            game.undo_move_creature(playername, creature_name, new_hexlabel)

    def done_with_reinforcements(self, playername, game_name):
        """Finish the reinforcement battle phase."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if (player is not None and player == game.battle_active_player and
                    game.battle_phase is Phase.PhaseBattle.REINFORCE):
                game.done_with_reinforcements(playername)

    def done_with_maneuvers(self, playername, game_name):
        """Finish the maneuver battle phase."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if (player is not None and player == game.battle_active_player and
                    game.battle_phase is Phase.PhaseBattle.MANEUVER):
                game.done_with_maneuvers(playername)

    def strike(self, playername, game_name, striker_name, striker_hexlabel,
               target_name, target_hexlabel, num_dice, strike_number):
        """Make one battle strike or strikeback."""
        game = self.name_to_game(game_name)
        if game:
            game.strike(playername, striker_name, striker_hexlabel,
                        target_name, target_hexlabel, num_dice, strike_number)

    def done_with_strikes(self, playername, game_name):
        """Finish the strike battle phase."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if (player is not None and player == game.battle_active_player and
                    game.battle_phase is Phase.PhaseBattle.STRIKE):
                game.done_with_strikes(playername)

    def done_with_counterstrikes(self, playername, game_name):
        """Finish the counterstrike battle phase."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if (player is not None and player == game.battle_active_player and
                    game.battle_phase is Phase.PhaseBattle.COUNTERSTRIKE):
                game.done_with_counterstrikes(playername)

    def acquire_angels(self, playername, game_name, markerid, angel_names):
        """Acquire angels and/or archangels after an engagement."""
        game = self.name_to_game(game_name)
        if game:
            legion = game.find_legion(markerid)
            if not legion:
                logging.warning("no such legion")
                return
            num_archangels = num_angels = 0
            for angel_name in angel_names:
                if angel_name == "Archangel":
                    num_archangels += 1
                elif angel_name == "Angel":
                    num_angels += 1
            caretaker = game.caretaker
            okay = (num_archangels <= legion.archangels_pending and
                    num_angels <= legion.angels_pending +
                    legion.archangels_pending -
                    num_archangels)
            if not okay:
                logging.warning("not enough angels pending")
                logging.info("angels %s", angel_names)
                logging.info("angels_pending %s", legion.angels_pending)
                logging.info("archangels_pending %s",
                             legion.archangels_pending)
                game.do_not_acquire_angels(playername, markerid)
                return
            if len(legion) >= 7:
                logging.warning("acquire_angels 7 high")
                game.do_not_acquire_angels(playername, markerid)
                return
            if len(legion) + num_angels + num_archangels > 7:
                logging.warning("acquire_angels would go over 7 high")
                game.do_not_acquire_angels(playername, markerid)
                return
            if caretaker.num_left("Archangel") < num_archangels:
                logging.warning("not enough Archangels left")
                game.do_not_acquire_angels(playername, markerid)
                return
            if caretaker.num_left("Angel") < num_angels:
                logging.warning("not enough Angels left")
                game.do_not_acquire_angels(playername, markerid)
                return
            game.acquire_angels(playername, markerid, angel_names)

    def do_not_acquire_angels(self, playername, game_name, markerid):
        """Do not acquire angels and/or archangels after an engagement."""
        logging.info("do_not_acquire_angels %s %s %s %s", self, playername,
                     game_name, markerid)
        game = self.name_to_game(game_name)
        if game:
            game.do_not_acquire_angels(playername, markerid)

    def done_with_engagements(self, playername, game_name):
        """Finish the engagement phase."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if not player:
                logging.warning("no such player")
                return
            if player != game.active_player:
                logging.warning("out of turn")
                return
            if (game.pending_summon or game.pending_reinforcement or
                    game.pending_acquire):
                logging.warning("waiting on something")
                return
            if game.phase is not Phase.PhaseMaster.FIGHT:
                logging.warning("wrong phase")
                return
            game.done_with_engagements(playername)

    def recruit_creature(self, playername, game_name, markerid, creature_name,
                         recruiter_names):
        """Recruit one creature."""
        game = self.name_to_game(game_name)
        if game:
            player = game.get_player_by_name(playername)
            if player:
                legion = player.markerid_to_legion.get(markerid)
                if legion and not legion.recruited:
                    caretaker = game.caretaker
                    hexlabel = legion.hexlabel
                    masterhex = game.board.hexes[hexlabel]
                    mterrain = masterhex.terrain
                    lst = list(recruiter_names[:])
                    lst.insert(0, creature_name)
                    tup = tuple(lst)
                    if tup in legion.available_recruits_and_recruiters(
                            mterrain, caretaker):
                        action = Action.RecruitCreature(game.name,
                                                        player.name,
                                                        markerid,
                                                        creature_name,
                                                        tuple(recruiter_names))
                        game.update(self, action, None)

    def undo_recruit(self, playername, game_name, markerid):
        """Undo one recruit."""
        game = self.name_to_game(game_name)
        if game:
            game.undo_recruit(playername, markerid)

    def done_with_recruits(self, playername, game_name):
        """Finish the recruitment phase."""
        game = self.name_to_game(game_name)
        if game:
            game.done_with_recruits(playername)

    def summon_angel(self, playername, game_name, markerid, donor_markerid,
                     creature_name):
        """Summon an angel or archangel."""
        game = self.name_to_game(game_name)
        if game:
            game.summon_angel(playername, markerid, donor_markerid,
                              creature_name)

    def do_not_summon_angel(self, playername, game_name, markerid):
        """Do not summon an angel or archangel."""
        game = self.name_to_game(game_name)
        if game:
            game.do_not_summon_angel(playername, markerid)

    def do_not_reinforce(self, playername, game_name, markerid):
        """Do not recruit a reinforcement."""
        game = self.name_to_game(game_name)
        if game:
            game.do_not_reinforce(playername, markerid)

    def carry(self, playername, game_name, carry_target_name,
              carry_target_hexlabel, carries):
        """Carry over excess hits to another adjacent enemy."""
        logging.info("carry %s %s %s", carry_target_name,
                     carry_target_hexlabel, carries)
        game = self.name_to_game(game_name)
        if game:
            game.carry(playername, carry_target_name, carry_target_hexlabel,
                       carries)

    def save(self, playername, game_name):
        """Save the game to a file."""
        game = self.name_to_game(game_name)
        if game:
            game.save(playername)

    def withdraw(self, playername, game_name):
        """Withdraw a player from the game."""
        game = self.name_to_game(game_name)
        if game:
            if game.started:
                game.withdraw(playername)
            else:
                try:
                    game.remove_player(playername)
                except AssertionError:
                    pass
                else:
                    if len(game.players) == 0:
                        if game in self.games:
                            self.games.remove(game)
                        action = Action.RemoveGame(game.name)
                        self.notify(action)
                    else:
                        action = Action.Withdraw(playername, game.name)
                        self.notify(action)

    def pause_ai(self, playername, game_name):
        """Pause AI players."""
        game = self.name_to_game(game_name)
        if game:
            game.pause_ai(playername)

    def resume_ai(self, playername, game_name):
        """Unpause AI players."""
        game = self.name_to_game(game_name)
        if game:
            game.resume_ai(playername)

    def get_player_data(self):
        """Return a list of player dicts for all players in the database."""
        return self.results.get_player_data()

    def _finish_with_game(self, game):
        game.remove_observer(self)
        if game in self.games:
            self.results.save_game(game)
            self.games.remove(game)

    def update(self, observed, action, names):
        logging.info("%s %s %s", observed, action, names)
        if isinstance(action, Action.GameOver):
            game = self.name_to_game(action.game_name)
            if game in self.games:
                # Wait to ensure that EliminatePlayer got through.
                reactor.callLater(1, self._finish_with_game, game)
        self.notify(action, names)


class AIProcessProtocol(protocol.ProcessProtocol):

    def __init__(self, server, game_name, ainame):
        self.server = server
        self.game_name = game_name
        self.ainame = ainame

    def connectionMade(self):
        logging.info("%s %s", self.game_name, self.ainame)
        # We don't use stdin, so reduce the number of open files.
        self.transport.closeStdin()

    def processExited(self, status):
        logging.debug("%s %s %s", self.game_name, self.ainame, status)

    def processEnded(self, status):
        logging.debug("%s %s %s", self.game_name, self.ainame, status)


def add_arguments(parser):
    parser.add_argument("-p", "--port", action="store", type=int,
                        default=config.DEFAULT_PORT, help="listening TCP port")
    parser.add_argument("--passwd-path", action="store", type=str,
                        default=prefs.passwd_path(),
                        help="path to passwd file")
    parser.add_argument("-n", "--no-passwd", action="store_true",
                        help="do not check passwords")
    parser.add_argument("-l", "--log-path", action="store", type=str,
                        help="path to logfile")


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args, extras = parser.parse_known_args()
    port = args.port
    server = Server(args.no_passwd, args.passwd_path, args.port, args.log_path)
    realm = Realm.Realm(server)
    if args.no_passwd:
        checker = UniqueNoPassword(None, server=server)
    else:
        checker = UniqueFilePasswordDB(args.passwd_path, server=server)
    portal = Portal(realm, [checker])
    pbfact = pb.PBServerFactory(portal, unsafeTracebacks=True)
    reactor.listenTCP(port, pbfact)
    logging.info("main calling reactor.run")
    reactor.run()


if __name__ == "__main__":
    main()
