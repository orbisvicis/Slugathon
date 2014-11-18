__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import functools

import unittest

from slugathon.util.MIMD import MIMD, G, O, R
from slugathon.util.Vector import Vector, VectorOperator, VectorArgs, VectorError
from slugathon.util.enumutils import StrValueEnum


class RectangleError(Exception):
    pass


class RectangleErrorValue(RectangleError, ValueError):
    pass


class RectangleErrorType(RectangleError, TypeError):
    pass


class RectangleErrorIndex(RectangleError, IndexError):
    pass


class RectangleErrors(StrValueEnum):
    error_type          = "Rectangle required"
    error_index_type    = "index components must be integers"
    error_index_range   = "index out of range"


class RectangleOperator(object):
    def __init__(self, error=False):
        self.error = error

    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(left, right):
            if not isinstance(right, Rectangle):
                if self.error:
                    raise RectangleErrorType(RectangleErrors.error_type)
                else:
                    return NotImplemented
            else:
                return function(left, right)
        return wrapper


class Rectangle(object):
    @VectorArgs(1,2)
    def __init__(self, location, size, *args, **kwargs):
        """ size (width, height) always positive
        """
        super().__init__(*args, **kwargs)
        self.location = location
        self.size = size
        self.resize()

    @classmethod
    @VectorArgs(1,2)
    def from_absolute(cls, location_a, location_b):
        return cls(location_a, location_b - location_a)

    @classmethod
    @RectangleOperator(error=True)
    def from_rectangle(cls, rectangle):
        return cls(rectangle.location, rectangle.size)

    def resize(self, size=None):
        if size is None:
            size = self.size
        elif not isinstance(key, Vector):
            size = Vector.from_iterable(size)
        for i,(l,d) in enumerate(zip(self.location, size)):
            self.location[i] = min(l, l + d)
            self.size[i] = abs(d)

    @property
    def area(self):
        return self.size.x * self.size.y

    @property
    def perimeter(self):
        return ( self.size.x * 2
               + self.size.y * 2
               )

    @property
    def width(self):
        return self.size.x

    @width.setter
    def width(self, value):
        self.size.x = value
        self.resize()

    @property
    def height(self):
        return self.size.y

    @height.setter
    def height(self, value):
        self.size.y = value
        self.resize()

    @property
    def top(self):
        return self[1:1].y

    @top.setter
    def top(self, value):
        self.height = value - self.location.y

    @property
    def bottom(self):
        return self[0:0].y

    @bottom.setter
    def bottom(self, value):
        top = self.top
        self.location.y = value
        self.height = top - value

    @property
    def left(self):
        return self[0:0].x

    @left.setter
    def left(self, value):
        right = self.right
        self.location.x = value
        self.width = right - value

    @property
    def right(self):
        return self[1:1].x

    @right.setter
    def right(self, value):
        self.width = value - self.location.x

    def __repr__(self):
        return "{cls.__name__}({obj.location!r}, {obj.size!r})".format\
            ( cls=type(self)
            , obj=self
            )

    def __len__(self):
        """ sides
        """
        return 4

    def __getitem__(self, key):
        """ 2x2 matrix of Vectors, row-major order
        """
        if isinstance(key, int):
            key = Vector(*divmod(key, 2))
        elif isinstance(key, slice):
            key = Vector(key.start, key.stop)
        elif not isinstance(key, Vector):
            key = Vector.from_iterable(key)
        for i in key:
            if not isinstance(i, int):
                raise RectangleErrorType(RectangleErrors.error_index_type)
            if i not in range(-2,2):
                raise RectangleErrorIndex(RectangleErrors.error_index_range)
        key =\
            [ bool(i+2 if i < 0 else i)
              for i
              in key
            ]
        offset =\
            [ d if i else 0
              for i,d
              in zip(key, self.size)
            ]
        return self.location + offset

    def __iter__(self):
        return RectangleIterator(self)

    @VectorArgs(1, copy=False)
    def contains(self, point, closed=True):
        return all\
            ( ( l1 <= l2 <= l3
                if closed else
                l1 < l2 < l3
              )
              for l1, l2, l3
              in zip(self[0:0], point, self[1:1])
            )

    def __contains__(self, point):
        try:
            return self.contains(point)
        except VectorError:
            return False

    @RectangleOperator()
    def __ge__(self, other):
        return all\
            ( self.contains(p)
              for p
              in (other[0:0], other[1:1])
            )

    @RectangleOperator()
    def __gt__(self, other):
        return\
        (   self.__ge__(other)
        and any\
            ( self.contains(p, closed=False)
              for p
              in (other[0:0], other[1:1])
            )
        )

    @RectangleOperator()
    def __eq__(self, other):
        return\
            (   self.location == other.location
            and self.size == other.size
            )

    def __ne__(self, other):
        result = (self == other)
        if result is NotImplemented:
            return result
        else:
            return not result

    @RectangleOperator()
    def __lt__(self, other):
        return (other > self)

    @RectangleOperator()
    def __le__(self, other):
        return (other >= self)

    def issubset(self, other):
        return (self <= other)

    def issuperset(self, other):
        return (self >= other)

    @RectangleOperator(error=True)
    def isdisjoint(self, other):
        return\
            (   self.right < other.left
            or  self.left > other.right
            or  self.top < other.bottom
            or  self.bottom > other.top
            )

    def __bool__(self):
        return bool(self.area)

    def __neg__(self):
        """ flip across axes
        """
        return type(self)(-self.location, self.size)

    def __pos__(self):
        return type(self)(self.location, self.size)

    @VectorOperator()
    def __add__(self, other):
        return type(self)\
            ( self.location + other
            , self.size
            )

    def __radd__(self, other):
        return self + other

    @VectorOperator()
    def __iadd__(self, other):
        self.location += other
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
        """ scale
        """
        return type(self)(self.location, self.size * other)

    def __rmul__(self, other):
        return self * other

    def __imul__(self, other):
        self.size *= other
        return self

    def __truediv__(self, other):
        return self * (1/other)

    def __itruediv__(self, other):
        self *= (1/other)
        return self


class RectangleIterator(object):
    def __init__(self, rectangle):
        self.iterator = iter\
            ( rectangle.location + (i,j)
              for i in (0,rectangle.size.x)
                for j in (0,rectangle.size.y)
            )

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.iterator)


class TestRectangle(unittest.TestCase):
    def setUp(self):
        self.v1_1 = Vector(1,2)
        self.v1_2 = Vector(8,10)
        self.r1 = Rectangle(self.v1_1, self.v1_2)
        self.s1 = "Rectangle({}, {})".format(self.v1_1, self.v1_2)

    def test_init(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [ G(self.v1_1, self.r1.location)
                , G(self.v1_2, self.r1.size)
                ]
              )
        ).apply()

    def test_from_absolute(self):
        r2 = Rectangle.from_absolute(self.v1_1, self.v1_2)
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [ G(self.v1_1, r2.location)
                , G(self.v1_2, r2[1:1])
                ]
              )
        ).apply()

    def test_from_rectangle(self):
        r2 = Rectangle.from_rectangle(self.r1)
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [ G(self.r1.location, r2.location)
                , G(self.r1.size, r2.size)
                ]
              )
        ).apply()

    def test_resize(self):
        self.assertEqual\
            ( self.r1
            , Rectangle(self.r1[1:1], -self.r1.size)
            )

    def test_area(self):
        self.assertEqual\
            ( self.v1_2[0] * self.v1_2[1]
            , self.r1.area
            )

    def test_perimeter(self):
        self.assertEqual\
            ( sum(x*2 for x in self.v1_2)
            , self.r1.perimeter
            )

    def test_width(self):
        self.assertEqual\
            ( self.v1_2.x
            , self.r1.width
            )

    def test_width_setter(self):
        self.r1.width = -self.v1_2.x
        ( MIMD( [self.assertEqual]
              , [ G(self.v1_2, self.r1.size)
                , G(self.v1_1 - (self.v1_2.x, 0), self.r1.location)
                ]
              )
        ).apply

    def test_height(self):
        self.assertEqual\
            ( self.v1_2.y
            , self.r1.height
            )

    def test_height_setter(self):
        self.r1.height = -self.v1_2.y
        ( MIMD( [self.assertEqual]
              , [ G(self.v1_2, self.r1.size)
                , G(self.v1_1 - (0, self.v1_2.y), self.r1.location)
                ]
              )
        ).apply()

    def test_top(self):
        self.assertEqual\
            ( (self.v1_1 + self.v1_2)[1]
            , self.r1.top
            )

    def test_top_setter(self):
        location = self.v1_1 - (0, self.v1_2.y)
        self.r1.top = location.y
        ( MIMD( [self.assertEqual]
              , [ G(self.v1_1, self.r1[0:1])
                , G(location, self.r1.location)
                ]
              )
        ).apply()

    def test_bottom(self):
        self.assertEqual\
            ( self.v1_1.y
            , self.r1.bottom
            )

    def test_bottom_setter(self):
        location = self.v1_1 + (0, self.v1_2.y * 2)
        self.r1.bottom = location.y
        ( MIMD( [self.assertEqual]
              , [ G(self.v1_1 + self.v1_2, self.r1[1:0])
                , G(location, self.r1[0:1])
                ]
              )
        ).apply()

    def test_left(self):
        self.assertEqual\
            ( self.v1_1.x
            , self.r1.left
            )

    def test_left_setter(self):
        location = self.v1_1 + (self.v1_2.x * 2,  0)
        self.r1.left = location.x
        ( MIMD( [self.assertEqual]
              , [ G(self.v1_1 + self.v1_2, self.r1[0:1])
                , G(location, self.r1[1:0])
                ]
              )
        ).apply()

    def test_right(self):
        self.assertEqual\
            ( (self.v1_1 + self.v1_2)[0]
            , self.r1.right
            )

    def test_right_setter(self):
        location = self.v1_1 - (self.v1_2.x, 0)
        self.r1.right = location.x
        ( MIMD( [self.assertEqual]
              , [ G(self.v1_1, self.r1[1:0])
                , G(location, self.r1.location)
                ]
              )
        ).apply()

    def test_repr(self):
        self.assertEqual\
            ( self.s1
            , repr(self.r1)
            )

    def test_len(self):
        self.assertEqual\
            ( len(self.r1)
            , 4
            )

    def test_getitem(self):
        ( MIMD( [self.assertRaises]
              , [G(VectorError, lambda k: self.r1[k])]
              , [[1,2,3], object()]
              ) +
          MIMD( [self.assertRaises]
              , [G(RectangleErrorType, lambda k: self.r1[k])]
              , ["ab", slice("a","b")]
              ) +
          MIMD( [self.assertRaises]
              , [G(RectangleErrorIndex, lambda k: self.r1[k])]
              , [-5, 4, slice(0,2), slice(2,2), slice(2,0), slice(0,-3), slice(-3,-3), slice(-3,0)]
              ) +
          MIMD( [self.assertEqual]
              , [list(self.r1)]
              , MIMD( [lambda i: [self.r1[j] for j in i]]
                    , [ range(0,4)
                      , range(-4,0)
                      ] +
                      MIMD( [ lambda i: (slice(*j) for j in i)
                            , lambda i: (i)
                            , lambda i: (Vector(*j) for j in i)
                            ]
                          , MIMD( [lambda i: ((x,y) for x in i for y in i)]
                                , [(0,1), (-2,-1)]
                                )
                          ).mapping
                    )
              )
        ).apply()

    def test_iter(self):
        self.assertEqual\
            ( [ self.v1_1
              , self.v1_1 + (0, self.v1_2.y)
              , self.v1_1 + (self.v1_2.x, 0)
              , self.v1_1 + self.v1_2
              ]
            , list(self.r1)
            )

    def test_contains(self):
        ( MIMD( [self.assertRaises]
              , [G(VectorError, self.r1.contains)]
              , [object(), (1,2,3)]
              ) +
          MIMD( [lambda i: self.assertTrue(self.r1.contains(i))]
              , [self.r1[0:0], self.r1[1:1], self.r1[0:0] + self.r1[1:1] / 2]
              ) +
          MIMD( [lambda i: self.assertFalse(self.r1.contains(i, closed=False))]
              , [self.r1[0:0], self.r1[1:1]]
              )
        ).apply()

    def test_contains_operator(self):
        ( MIMD( [lambda i: self.assertFalse(i in self.r1)]
              , [(1,2,3), object()]
              )
        ).apply()

    def ordering(self, try_gt=True, or_equal=False, function=None):
        function =\
            ( ( lambda a,b:\
                ( (a >= b if or_equal else a>b)
                    if try_gt else
                  (a <= b if or_equal else a<b)
                )
              )
                if function is None else
              ( function
              )
            )
        at =\
            [ [self.r1]
            , [ (self.r1 / 2)
              , (self.r1 / 2) + (self.r1.size / 4)
              , (self.r1 / 2) + (self.r1.size / 2)
              ] +
              [self.r1] if or_equal else []
            ]
        af =\
            [ [self.r1]
            , [ self.r1 + (self.r1.size / 2)
              ] +
              [] if or_equal else [self.r1]
            ]
        ( MIMD( [lambda a,b: self.assertTrue(function(a,b))]
              , *(at if try_gt else reversed(at))
              ) +
          MIMD( [lambda a,b: self.assertFalse(function(a,b))]
              , *(af if try_gt else reversed(af))
              ) +
          MIMD( [self.assertRaises]
              , [G(TypeError, function)]
              , [self.r1]
              , [self.v1_1, 55, (1,2,3), object()]
              )
        ).apply()


    def test_gt(self):
        self.ordering(try_gt=True, or_equal=False)

    def test_ge(self):
        self.ordering(try_gt=True, or_equal=True)

    def test_eq(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [Rectangle(self.v1_1, self.v1_2)]
              , [Rectangle(self.v1_1, self.v1_2)]
              )
        ).apply()

    def test_ne(self):
        ( MIMD( [self.assertNotEqual, self.assertIsNot]
              , [Rectangle(self.v1_1, self.v1_2)]
              , [Rectangle(self.v1_2, self.v1_1)]
              )
        ).apply()

    def test_lt(self):
        self.ordering(try_gt=False, or_equal=False)

    def test_le(self):
        self.ordering(try_gt=False, or_equal=True)

    def test_issubset(self):
        self.ordering(try_gt=False, or_equal=True, function=Rectangle.issubset)

    def test_issuperset(self):
        self.ordering(try_gt=True, or_equal=True, function=Rectangle.issuperset)

    def test_isdisjoint(self):
        s = self.r1 / 3
        b = self.r1 * 3
        t = Rectangle(self.v1_1, (self.v1_2.x / 3, self.v1_2.y * 3))
        w = Rectangle(self.v1_1, (self.v1_2.x * 3, self.v1_2.y / 3))
        ( MIMD( [lambda a,b: self.assertFalse(a.isdisjoint(b))]
              , [self.r1]
              , [ b - self.r1.size
                , s + s.size
                , t + (t.size.x, -self.r1.size.y)
                , t + (-t.size.x / 2, -self.r1.size.y)
                , w + (-self.r1.size.x, w.size.y)
                , w + (-self.r1.size.x, -w.size.y / 2)
                , s + (s.size.x * (5/2), s.size.y)
                , s + (s.size.x, s.size.y * (5/2))
                , s + (s.size * (5/2))
                , s + (s.size * -(1/2))
                , s + (s.size.x / -2, s.size.y * (5/2))
                , s + (s.size.x * (5/2), s.size.y / -2)
                , s * -3
                ]
              ) +
          MIMD( [lambda a,b: self.assertTrue(a.isdisjoint(b))]
              , [self.r1]
              , [self.r1 + self.r1.size * 2]
              )
        ).apply()

    def test_bool(self):
        ( MIMD( [self.assertTrue]
              , [self.r1]
              ) +
          MIMD( [self.assertFalse]
              , [ self.r1 * 0
                , Rectangle((0,0), (0,0))
                ]
              )
        ).apply()

    def test_neg(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [self.r1]
              , [--self.r1]
              )
        ).apply()

    def test_pos(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [self.r1]
              , [+self.r1]
              )
        ).apply()

    def test_add_sub(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [self.r1]
              , [self.r1 + (0,0), self.r1 - (0,0)]
              )
        ).apply()

    def test_radd_rsub(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [self.r1]
              , [(0,0) + self.r1, (0,0) - -self.r1]
              )
        ).apply()

    def test_iadd_isub(self):
        ( MIMD( [self.assertEqual, self.assertIs]
              , [self.r1]
              , [self.r1.__iadd__((0,0)), self.r1.__isub__((0,0))]
              )
        ).apply()

    def test_mul_div(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [self.r1]
              , [self.r1 * 1, self.r1 / 1]
              )
        ).apply()

    def test_rmul(self):
        ( MIMD( [self.assertEqual, self.assertIsNot]
              , [self.r1]
              , [1 * self.r1]
              )
        ).apply()

    def test_imul_idiv(self):
        ( MIMD( [self.assertEqual, self.assertIs]
              , [self.r1]
              , [self.r1.__imul__(1), self.r1.__itruediv__(1)]
              )
        ).apply()


if __name__ == "__main__":
    unittest.main()
