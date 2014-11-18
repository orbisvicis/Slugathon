__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import itertools
import functools

from slugathon.util.classutils import Deletable


class G(object):
    """ID: Group
    """
    def __init__(self, *args):
        self.args = args

    def __len__(self):
        return len(self.args)

    def __iter__(self):
        return iter(self.args)


class O(object):
    """ID: Omitted
    """
    pass


class R(object):
    """ID: Repeated
    """
    def __init__(self, arg, count):
        self.arg = arg
        self.count = count

    def __len__(self):
        return self.count

    def __iter__(self):
        return itertools.repeat(self.arg, self.count)


class Bind(object):
    """Function and arguments, unevaluated
    """
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def apply(self):
        args = [ ( arg.apply()
                   if isinstance(arg, type(self)) else
                   arg
                 )
                 for arg
                 in self.args
               ]
        return self.func(*args)


class MIMD(object, metaclass=Deletable):
    def __init__(self, func, *args):
        self.mapping = []
        dataslots = []
        for s in args:
            slot = []
            for d in s:
                if isinstance(d, R):
                    slot.extend(d)
                else:
                    slot.append(d)
            dataslots.append(slot)
        for p in itertools.product(func, *dataslots):
            args = [p[0]]
            for a in p[1:]:
                if not isinstance(a, O):
                    if isinstance(a, G):
                        args.extend(a)
                    else:
                        args.append(a)
            self.mapping.append(Bind(*args))

    def __iter__(self):
        return iter(self.mapping)

    def __copy__(self):
        copy = type(self).__new__(type(self))
        copy.__dict__.update(self.__dict__)
        copy.mapping = self.mapping[:]
        return copy

    @Deletable.mark
    def operator(function):
        @functools.wraps(function)
        def wrapper(left, right):
            if not isinstance(right, type(left)):
                return NotImplemented
            return function(left, right)
        return wrapper

    def apply(self):
        results = [b.apply() for b in self.mapping]
        return results

    @operator
    def __iadd__(self, other):
        self.mapping += other.mapping
        return self

    @operator
    def __add__(self, other):
        self = self.__copy__()
        self += other
        return self
