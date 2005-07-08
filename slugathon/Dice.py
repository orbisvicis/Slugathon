import random

"""Simulate rolling dice.

Runs only on the server side, for security.
"""

_rand = random.Random()

def roll(sides=6, numrolls=1):
    """Return a list of numrolls random integers from 1..sides"""
    return [_rand.randint(1, sides) for unused in xrange(numrolls)]

def shuffle(lst):
    """Shuffle the list in place.

    Here so that we can reuse the same RNG for the whole game.
    """
    _rand.shuffle(lst)
