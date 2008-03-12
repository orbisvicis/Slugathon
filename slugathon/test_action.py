import Action

def test_fromstring():
    obj = Action.fromstring("MoveLegion {'markername': 'Rd01', \
'entry_side': 1, 'teleport': False, 'playername': 'player', \
'teleporting_lord': None, 'game_name': 'game', 'hexlabel': 1}")
    assert isinstance(obj, Action.MoveLegion)
    assert obj.markername == "Rd01"
    assert obj.entry_side == 1
    assert obj.teleport == False
    assert obj.playername == "player"
    assert obj.teleporting_lord == None
    assert obj.game_name == "game"
    assert obj.hexlabel == 1
