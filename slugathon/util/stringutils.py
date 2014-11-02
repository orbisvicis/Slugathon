__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import stringprep
from unicodedata import ucd_3_2_0 as unicodedata
from slugathon.funcutils import compose
from slugathon.util.enumutils import StrValueEnum
import unittest


class IdentifierError(UnicodeError):
    pass


class IdentifierErrors(StrValueEnum):
    restriction_unassigned                  = "Unassigned unicode characters prohibited"
    restriction_combiners                   = "Leading unicode combiners prohibited"
    restriction_prohibited                  = "String contains prohibited unicode characters"
    restriction_bidirectional_prohibited    = "String contains prohibited bidirectional characters"
    restriction_bidirectional_mixed         = "String contains both RandALCat and LCat characters"
    restriction_bidirectional_affix         = "String must open and close with RandALCat characters"
    restriction_visible                     = "String must contain visible characters"


class Identifier:
    """
    Pseudo-RFC3454 unicode string filtering and normalization class.

    Operations performed:

        * unassigned characters are prohibited
            affected
                normalized
                display
            implementation
                returns an error

        * non-compliant unicode strings are prohibited
            affected
                display
                normalized
            implementation
                checks for leading combiners
                returns an error

        * [see table below] characters are prohibited
            affected
                display
                normalized
            implementation
                returns an error

        * check bidirectional characters
            affected
                normalized
                displayed
            implementation
                returns an error

        * non-semantic line-based characters are removed
            affected
                display
                normalized
            implementation
                stripped silently

        * non-semantic modifier characters are removed
            affected
                normalized
            unaffected
                display
            implementation
                stripped silently

        * case-mapping
            affected
                normalized
            unaffected
                display
            implementation
                KC normalization + rfc3454 B.2 mapping
                stripped silently

        * pure spaces [non-displaying] are removed
            affected
                normalized
            unaffected
                display
            implementation
                remove all whitespace characters not succeeded by combining characters
                stripped silently

        * check for visible characters
            affected
                normalized
                display
            implementation
                remove
                    all whitespace characters not succeeded by combining characters
                    all non-printing or zero-width characters
                check remaning characters count > 0
                returns an error if no characters are visible


    prohibited characters:

        * control characters
        * private use
        * non-character code points
        * surrogate codes
        * inappropriate for plain text
        * inappropriate for canonical representation
        * change display or deprecated
        * tagging characters
    """

    nonsemantic_linebased = \
        [ 0x00AD
        , 0x1806
        , 0x200B
        , 0x2060
        , 0xFEFF
        ]

    nonsemantic_modifier = \
        [ 0x034F
        , 0x180B
        , 0x180C
        , 0x180D
        , 0x200C
        , 0x200D
        ] + \
        list(range(0xFE00,0xFE0F+1))

    def __init__(self, unistr):
        self.provenance = unistr
        self.__identifier = None
        self.__normalized = None

        self.check_compliant(self.provenance)
        self.check_prohibited(self.normalized)
        self.check_unassigned(self.normalized)
        self.check_bidirectional(self.normalized)
        self.check_visible(self.normalized)

    @property
    def identifier(self):
        chain = \
            [ lambda x: self.filter_table(x, self.nonsemantic_linebased)
            , self.normalize
            ]
        if self.__identifier is None:
            self.__identifier = compose(*chain)(self.provenance)
        return self.__identifier

    @property
    def normalized(self):
        chain = \
            [ lambda x: self.filter_table(x, self.nonsemantic_linebased)
            , lambda x: self.filter_table(x, self.nonsemantic_modifier)
            , lambda x: self.casemap(x, normalize=True)
            , self.filter_spaces
            , self.normalize
            ]
        if self.__normalized is None:
            self.__normalized = compose(*chain)(self.provenance)
        return self.__normalized

    def __str__(self):
        return self.identifier()

    @staticmethod
    def check_unassigned(unistr):
        for c in unistr:
            if stringprep.in_table_a1(c):
                raise IdentifierError(IdentifierErrors.restriction_unassigned)

    @staticmethod
    def check_compliant(unistr):
        if (    unistr
            and unicodedata.combining(unistr[0]) > 0
           ):
            raise IdentifierError(IdentifierErrors.restriction_combiners)

    @staticmethod
    def check_prohibited(unistr):
        prohibited_lookup_functions = \
            [ stringprep.in_table_c21
            , stringprep.in_table_c22
            , stringprep.in_table_c3
            , stringprep.in_table_c4
            , stringprep.in_table_c5
            , stringprep.in_table_c6
            , stringprep.in_table_c7
            , stringprep.in_table_c8
            , stringprep.in_table_c9
            ]

        for c in unistr:
            for f in prohibited_lookup_functions:
                if f(c):
                    raise IdentifierError(IdentifierErrors.restriction_prohibited)

    @staticmethod
    def check_bidirectional(unistr):
        contains_randalcat = False
        contains_lcat = False

        for c in unistr:
            if stringprep.in_table_c8(c):
                raise IdentifierError(IdentifierErrors.restriction_bidirectional_prohibited)
            if stringprep.in_table_d1(c):
                contains_randalcat = True
            if stringprep.in_table_d2(c):
                contains_lcat = True

        if contains_randalcat:
            if contains_lcat:
                raise IdentifierError(IdentifierErrors.restriction_bidirectional_mixed)
            if not all(map(stringprep.in_table_d1,[unistr[0],unistr[-1]])):
                raise IdentifierError(IdentifierErrors.restriction_bidirectional_affix)

    @staticmethod
    def normalize(unistr):
        return unicodedata.normalize("NFKC", unistr)

    @staticmethod
    def casemap(unistr, normalize=True):
        if normalize:
            mapper = stringprep.map_table_b2
        else:
            mapper = stringprep.map_table_b3
        return "".join(mapper(c) for c in unistr)

    @staticmethod
    def combine(unistr):
        group = list(unistr[:1])
        for char in unistr[1:]:
            if unicodedata.combining(char):
                group.append(char)
            else:
                yield group
                group = [char]
        if group:
            yield group

    def filter_spaces(self, unistr):
        return "".join\
            ( "".join(group)
              for group in
              self.combine(unistr)
              if not stringprep.in_table_c11_c12(group[0])
                 or
                 not len(group) == 1
            )

    @staticmethod
    def filter_table(unistr, table):
        return "".join(\
            c for c in unistr
            if c not in table
            )

    @staticmethod
    def check_visible(unistr):
        if not len(unistr):
            raise IdentifierError(IdentifierErrors.restriction_visible)


class IdentifierTest(unittest.TestCase):
    def driver_errors(input_valid, input_invalid, output):
        def tester(self):
            for i in input_invalid:
                with self.assertRaises(IdentifierError) as cm:
                    Identifier(i)
                self.assertIs(cm.exception.args[0], output)
            for i in input_valid:
                Identifier(i)
        return tester


    test_visible = driver_errors\
        ( input_valid = \
            [ " \u0300"
            ]
        , input_invalid = \
            [""
            ," "
            ,"\u200A"
            ,"\u3000"
            ]
        , output = IdentifierErrors.restriction_visible
        )

    test_combiner = driver_errors\
        ( input_valid = \
            [ "foo"
            , "foo\u0300"
            , "\u0060\u0300"
            ]
        , input_invalid = \
            [ "\u0300string"
            ]
        , output = IdentifierErrors.restriction_combiners
        )

    test_unassigned = driver_errors\
        ( input_valid = []
        , input_invalid = \
            [ "foo\u0620"
            ]
        , output = IdentifierErrors.restriction_unassigned
        )

    test_prohibited_general_and_bidirectional = driver_errors\
        ( input_valid = []
        , input_invalid = \
            [ "foo\u0009"
            , "foo\u0000"
            , "foo\u206A"
            , "foo\u202A"
            ]
        , output = IdentifierErrors.restriction_prohibited
        )

    test_bidirectional_mixed = driver_errors\
        ( input_valid = \
            [ "foo\u0386baz"
            ]
        , input_invalid = \
            [ "foo\u05BEbar"
            ]
        , output = IdentifierErrors.restriction_bidirectional_mixed
        )

    test_bidirectional_affix = driver_errors\
        ( input_valid = []
        , input_invalid = \
            [ "\u05dA\u05BE01"
            ]
        , output = IdentifierErrors.restriction_bidirectional_affix
        )


if __name__ == "__main__":
    unittest.main()
