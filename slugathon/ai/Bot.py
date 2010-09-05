__copyright__ = "Copyright (c) 2010 David Ripton"
__license__ = "GNU GPL v2"


"""Interface for the AI."""


from zope.interface import Interface


class Bot(Interface):
    def maybe_pick_color(game):
        """Pick a color if it's my turn."""

    def maybe_pick_first_marker(game, playername):
        """Pick my first legion marker if I know my color."""

    def choose_marker(player):
        """Choose a legion marker."""

    def split(game):
        """Split if it's my turn."""

    def move_legions(game):
        """Try to move legions."""

    def choose_engagement(game):
        """Pick an engagement to resolve next."""

    def resolve_engagement(game, hexlabel, did_not_flee):
        """Resolve the engagement in hexlabel."""

    def move_creatures(game):
        """Move creatures in battle."""

    def strike(game):
        """Choose strikes or strikebacks."""

    def carry(game, striker_name, striker_hexlabel, target_name,
      target_hexlabel, num_dice, strike_number, carries):
        """Choose how to apply one carry."""

    def recruit(game):
        """Recruit during the Muster phase."""

    def reinforce(game):
        """Muster a reinforcement during battle."""

    def reinforce_after(game):
        """Muster a reinforcement after battle."""

    def summon(game):
        """Summon angels, during battle."""

    def summon_after(game):
        """Summon angels, after battle."""

    def acquire_angel(game, markername, num_angels, num_archangels):
        """Acquire angels."""
