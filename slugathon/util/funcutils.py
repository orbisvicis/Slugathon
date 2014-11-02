__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import functools


def compose(*functions):
    def c2(f, g):
        return lambda *args, **kwargs: f(g(*args, **kwargs))
    return functools.reduce(c2, functions)
