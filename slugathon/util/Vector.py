__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import collections.abc
import itertools
import functools
import decorator
import math

import unittest

from slugathon.util.MIMD import MIMD, G, O, R
from slugathon.util.enumutils import StrValueEnum


class VectorError(Exception):
    pass


class VectorErrorValue(VectorError, ValueError):
    pass


class VectorErrorType(VectorError, TypeError):
    pass


class VectorErrorIndex(VectorError, IndexError):
    pass


class VectorErrors(StrValueEnum):
    error_value     = "Two-item iterable required"
    error_type      = "Iterable required"
    error_length    = "cardinality immutable"
    error_index     = "index out of range"


class VectorArgs(object):
    def __init__(self, *args, copy=True, copy_prefix="copy_", **kwargs):
        self.keys = args
        self.copy_default = copy
        self.copy_mapping = \
            { k[len(copy_prefix):]:v
              for k,v
              in kwargs.items()
              if k.startswith(copy_prefix)
            }

    def convert(self, key, value):
        if (    key in self.keys
           and  (   self.copy_mapping.get(key, self.copy_default)
                or  not isinstance(value, Vector)
                )
           ):
            value = Vector.from_iterable(value)
        return value

    def wrapper(self, func, *args, **kwargs):
        args = \
            [self.convert(k, v) for k,v in enumerate(args)]
        kwargs = \
            {k:self.convert(k, v) for k,v in kwargs.items()}
        return func(*args, **kwargs)

    def __call__(self, func):
        return decorator.decorator(self.wrapper, func)


class VectorOperator(object):
    def __init__(self, error_handler=True):
        self.error_handler = error_handler

    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(left, right):
            if not isinstance(right, Vector):
                try:
                    right = Vector.from_iterable(right)
                except (VectorErrorValue, VectorErrorType):
                    if self.error_handler:
                        return NotImplemented
                    else:
                        raise
            return function(left, right)
        return wrapper


class Vector(object):
    def __init__(self, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = x
        self.y = y

    @classmethod
    def from_vector(cls, vector):
        return cls(vector.x, vector.y)

    @classmethod
    def from_iterable(cls, iterable):
        if isinstance(iterable, collections.abc.Iterable):
            if isinstance(iterable, cls):
                return cls.from_vector(iterable)
            if  (   isinstance(iterable, collections.abc.Sized)
                and len(iterable) != 2
                ):
                raise VectorErrorValue(VectorErrors.error_value)
            sentinel = object()
            iterator = iter(iterable)
            x, y, z = (next(iterator, sentinel) for _ in range(3))
            if  (       x is sentinel
                or      y is sentinel
                or not  z is sentinel
                ):
                raise VectorErrorValue(VectorErrors.error_value)
            return cls(x, y)
        else:
            raise VectorErrorType(VectorErrors.error_type)

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.x, self.y)

    def __len__(self):
        """ cardinality """
        return 2

    def __bool__(self):
        return bool(self.x) or bool(self.y)

    def __neg__(self):
        return type(self)(-self.x, -self.y)

    def __pos__(self):
        return type(self)(self.x, self.y)

    def __abs__(self):
        return math.sqrt(self.x**2 + self.y**2)

    @VectorOperator()
    def __eq__(self, other):
        return  (   self.x == other.x
                and self.y == other.y
                )

    def __ne__(self, other):
        result = (self == other)
        if result is NotImplemented:
            return result
        else:
            return not result

    @VectorOperator()
    def __add__(self, other):
        return type(self)\
            ( self.x + other.x
            , self.y + other.y
            )

    def __radd__(self, other):
        return self + other

    @VectorOperator()
    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    @VectorOperator()
    def __sub__(self, other):
        return self + -other

    def __rsub__(self, other):
        return -(self - other)

    @VectorOperator()
    def __isub__(self, other):
        self += -other
        return self

    def __mul__(self, other):
        return type(self)\
            ( self.x * other
            , self.y * other
            )

    def __rmul__(self, other):
        return self * other

    def __imul__(self, other):
        self.x *= other
        self.y *= other
        return self

    def __truediv__(self, other):
        return self * (1/other)

    def __itruediv__(self, other):
        self *= (1/other)
        return self

    @VectorOperator(False)
    def dot(self, other):
        return  ( self.x * other.x
                + self.y * other.y
                )

    def __iter__(self):
        return VectorIterator(self.x, self.y)

    def __getitem__(self, key):
        items = [self.x, self.y]
        if isinstance(key, slice):
            if len(range(*key.indices(len(self)))) != len(self):
                raise VectorErrorIndex(VectorErrors.error_length)
            return self
        elif isinstance(key, int):
            if key >= len(self) or key < -len(self):
                raise VectorErrorIndex(VectorErrors.error_index)
            return items[key]
        else:
            raise VectorErrorType

    def __setitem__(self, key, value):
        setters = [lambda v, n=n: setattr(self, n, v) for n in ("x", "y")]
        if isinstance(key, slice):
            indices = range(*key.indices(len(self)))
            values = tuple(itertools.islice(value, 0, len(self)))
            if len(values) < len(indices):
                raise VectorErrorIndex(VectorErrors.error_length)
            for k, v in zip(indices, values):
                setters[k](v)
        elif isinstance(key, int):
            if key >= len(self) or key < -len(self):
                raise VectorErrorIndex(VectorErrors.error_index)
            setters[key](value)
        else:
            raise VectorErrorType


class VectorIterator(object):
    def __init__(self, *args):
        self.items = args
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.items):
            raise StopIteration
        item = self.items[self.index]
        self.index += 1
        return item


class TestVector(unittest.TestCase):
    def setUp(self):
        self.l1 = [1, 2]
        self.v1 = Vector(*self.l1)
        self.s1 = "Vector({}, {})".format(*self.l1)

    def test_from_vector(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [self.v1]
                , [Vector.from_vector(self.v1)]
            )
        ).apply()

    def test_from_iterable(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [self.v1]
                , MIMD( [Vector.from_iterable]
                       , [self.v1, self.l1]
                  )
            ) +
            MIMD( [self.assertRaises]
                , [G(VectorErrorValue, Vector.from_iterable)]
                , [self.l1[1:], itertools.cycle(self.l1)]
            ) +
            MIMD( [self.assertRaises]
                , [G(VectorErrorType, Vector.from_iterable)]
                , [55]
            )
        ).apply()

    def test_repr(self):
        self.assertEqual\
            ( str(self.v1)
            , self.s1
            )

    def test_len(self):
        self.assertEqual\
            ( len(self.v1)
            , 2
            )

    def test_bool(self):
        self.assertTrue\
            ( self.v1
            )
        self.assertFalse\
            (self.v1 - self.v1
            )

    def test_neg(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [--self.v1]
                , [self.v1]
            )
        ).apply()

    def test_pos(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [+self.v1]
                , [self.v1]
            )
        ).apply()

    def test_abs(self):
        self.assertEqual\
            ( abs(self.v1)
            , math.sqrt(sum(x*x for x in self.l1))
            )

    def test_eq(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [Vector(*self.l1)]
                , [Vector(*self.l1)]
            )
        ).apply()

    def test_ne(self):
        return (
            MIMD( [self.assertNotEqual, self.assertIsNot]
                , [Vector(*self.l1)]
                , [Vector(*reversed(self.l1))]
            )
        ).apply()

    def test_add_sub(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [self.v1]
                , MIMD( [lambda x: self.v1 + x, lambda x: self.v1 - x]
                      , [(0,0), Vector(0,0)]
                  )
            )
        ).apply()

    def test_radd_rsub(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [self.v1]
                , [(0,0) + self.v1, (0,0) - -self.v1]
            )
        ).apply()

    def test_iadd_isub(self):
        return (
            MIMD( [self.assertEqual, self.assertIs]
                , [self.v1]
                , [self.v1.__iadd__((0,0)), self.v1.__isub__((0,0))]
            )
        ).apply()

    def test_mul_div(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [self.v1]
                , [self.v1 * 1, self.v1 / 1]
            )
        ).apply()

    def test_rmul(self):
        return (
            MIMD( [self.assertEqual, self.assertIsNot]
                , [self.v1]
                , [1 * self.v1]
            )
        ).apply()

    def test_imul_idiv(self):
        return (
            MIMD( [self.assertEqual, self.assertIs]
                , [self.v1]
                , [self.v1.__imul__(1), self.v1.__itruediv__(1)]
            )
        ).apply()

    def test_dot(self):
        self.assertEqual\
            ( self.v1.dot((0,0))
            , 0
            )
        self.assertEqual\
            ( self.v1.dot(self.v1)
            , sum(map(lambda x,y: x*y, *[self.l1]*2))
            )

    def test_iter(self):
        self.assertEqual\
            ( self.l1
            , list(self.v1)
            )

    def test_get(self):
        return (
            MIMD( [self.assertRaises]
                , [G(VectorErrorIndex, lambda k: self.v1[k])]
                , [slice(0,0), slice(0,1), slice(1,20), slice(1, None), 2, -3]
            ) +
            MIMD( [self.assertIs]
                , [self.v1]
                , MIMD( [lambda k: self.v1[k]]
                      , [slice(0,2), slice(0,None), slice(0,20), slice(-2,2)]
                  )
            ) +
            MIMD( [self.assertEqual]
                , [G(*MIMD( [lambda i: list(i[j] for j in range(-len(i), len(i)))]
                          , [self.l1, self.v1]
                      )
                   )
                  ]
            )
        ).apply()

    def test_set(self):
        def tester(k, v):
            self.v1[k] = v
            return self.v1
        return (
            MIMD( [self.assertRaises]
                , [G(VectorErrorIndex, self.v1.__setitem__)]
                , [2, -3, slice(0,1), slice(0,2), slice(0,3)]
                , [[]]
            ) +
            MIMD( [self.assertRaises]
                , [G(VectorErrorType, self.v1.__setitem__)]
                , ["asdf", range(0,2)]
                , [[]]
            ) +
            MIMD( [self.assertEqual]
                , [Vector(*self.l1)]
                , MIMD( [tester]
                      , [slice(None, None), slice(-2,2), slice(0,0), slice(0,1), slice(0,2), slice(0,3)]
                      , [itertools.cycle(self.l1)]
                  ) +
                  MIMD( [lambda k,i: tester(k, i[k])]
                      , range(-len(self.v1), len(self.v1))
                      , [self.l1]
                  )
            )
        ).apply()


if __name__ == "__main__":
    unittest.main()
