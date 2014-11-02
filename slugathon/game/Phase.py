__copyright__ = "Copyright (c) 2005-2009 David Ripton"
__license__ = "GNU GPL v2"


from slugathon.util.enumutils import StrValueEnum


"""Phase constants"""


class PhaseMaster(StrValueEnum):
    SPLIT   = "Split"
    MOVE    = "Move"
    FIGHT   = "Fight"
    MUSTER  = "Muster"


class PhaseBattle(StrValueEnum):
    REINFORCE       = "Reinforce"
    MANEUVER        = "Maneuver"
    DRIFTDAMAGE     = "Drift damage"
    STRIKE          = "Strike"
    COUNTERSTRIKE   = "Counterstrike"
    CLEANUP         = "Cleanup"
