# -----------------------------------------------------------------------
#
# ff - a tool for finding files in the filesystem
# Copyright (C) 2020 Lars Gustäbel <lars@gustaebel.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------

import re
import collections

from . import Attribute, BaseClass
from .type import Type
from .entry import Entry
from .ignore import Glob
from .exceptions import UsageError, ExpressionError, BadAttributeError


class ParserError(Exception):
    """Exception used by the Parser.
    """


class AND(list):
    """A list of tests that must all be true.
    """
    name = "AND"

    def __init__(self, obj=None):
        super().__init__()
        if obj is not None:
            self.append(obj)

    def __str__(self):
        return f"{self.name}( {', '.join(str(x) for x in self)} )"

class OR(AND):
    """A list of tests either of which must be true.
    """
    name = "OR"

class NOT(AND):
    """A list of tests with its result inverted.
    """
    name = "NOT"


class Test(collections.namedtuple("Test", "attribute operator type value ignore_case")):
    """Test object that contains all relevant information about a test.
    """

    name = "test"

    def format(self, with_type=False):
        """Return a readable representation of the Test.
        """
        if isinstance(self.value, (re.Pattern, Glob)):
            value = self.value.pattern
        else:
            value = self.value

        if with_type:
            return f"{self.attribute.fullname()}[{self.type.name}]{self.operator}{value}"
        else:
            return f"{self.attribute.fullname()}{self.operator}{value}"

    def __str__(self):
        return self.format(with_type=True)

    def __repr__(self):
        return repr(str(self))


class FlatParser(BaseClass):
    """Parse a list of test expressions into a test sequence.
    """

    expression_regex = re.compile(r"^\s*((?:\w+\.)?\w+?)\s*"\
                                  r"(=|:|~|%|>=|>|<=|<|\+=|\+|\-=|\-)"\
                                  r"(\{(?:\w+\.)?\w+?\}|\{\})?"\
                                  r"\s*(.+)\s*$")

    def __init__(self, context, tokens, attribute=None, operator=None):
        super().__init__(context)

        self.default_attribute = self.args.default_attribute if attribute is None else attribute
        self.default_operator = self.args.default_operator if operator is None else operator

        self.tokens = tokens.copy()
        self.sequence = self.parse()

    def __iter__(self):
        yield from self.sequence

    def parse(self):
        """Parse a list of tokens into a test structure.
        """
        sequences = AND()
        self.parse_sequence(sequences)
        return sequences

    def format(self, tests=None, level=0):
        """Format a list of tests for output.
        """
        if tests is None:
            tests = self

        for test in tests:
            if isinstance(test, list):
                yield ("    " * level) + test.name + "("
                yield from self.format(test, level + 1)
                yield ("    " * level) + ")"
            else:
                yield ("    " * level) + str(test)

    def parse_test(self, test):
        """Parse an expression and return a Test object.
        """
        match = self.expression_regex.match(test)
        if match is not None:
            attribute, operator, reference, value = match.groups()
            attribute = self.registry.setup_attribute(attribute)
            if reference is not None:
                reference = reference.strip("{}")

            # Normalize operators that contain > and <.
            operator = operator.replace(">", "+").replace("<", "-")

            if attribute.plugin is None:
                attribute = Attribute("file", attribute.name)

            return self.create_test(attribute, operator, reference, value)

        else:
            if self.default_attribute is None or self.default_operator is None:
                raise BadAttributeError(f"Simple patterns like {test!r} are not allowed!")

            return self.create_test(Attribute("file", self.default_attribute),
                    self.default_operator, None, test)

    def get_reference_value(self, type_cls, attribute, reference, value):
        """Fetch the value from the reference.
        """
        if reference:
            ref_attribute = self.registry.setup_attribute(reference)
        else:
            ref_attribute = attribute

        ref_type_cls = self.registry.get_attribute_type(ref_attribute)

        # Check if both attributes are comparable, i.e. they have a similar
        # type.
        try:
            self.get_common_super_type(type_cls, ref_type_cls)
        except ValueError:
            raise ExpressionError(f"{attribute} and {ref_attribute} have different types "\
                    "and cannot be compared")

        entry = Entry.as_reference(self.args, value)
        return self.registry.get_attribute(entry, ref_attribute)

    @staticmethod
    def get_common_super_type(a_type, b_type):
        """Find the common Type subclass of both Type subclasses. If both
           arguments have a common Type, i.e. Number or String, they are
           comparable.
        """
        assert issubclass(a_type, Type)
        assert issubclass(b_type, Type)

        for cls in a_type.mro():
            if cls is Type:
                break
            elif cls in b_type.mro():
                return cls
        raise ValueError("no common Type subclass found")

    def create_test(self, attribute, operator, reference, value):
        """Create the Test object. Before that, do some sanity checks, handle
           case sensitivity, prepare regular expressions and fetch the value
           from a reference file if required.
        """
        # pylint:disable=broad-except,too-many-branches
        type_cls = self.registry.get_attribute_type(attribute)

        if operator not in type_cls.operators:
            raise ExpressionError(f"Attribute {attribute} of type {type_cls.name!r} does not "\
                    f"support operator {operator!r}")

        ignore_case = None

        try:
            # We either use the provided value directly or in case of a
            # reference we use the value from after evaluating the reference.
            if reference is not None:
                value = self.get_reference_value(type_cls, attribute, reference, value)
            else:
                value = type_cls.input(value)

        except Exception as exc:
            raise UsageError(str(exc))

        if type_cls.choices is not None and value not in type_cls.choices:
            raise UsageError(f"You specified an invalid value {value!r} "\
                    f"for attribute '{attribute}'! Allowed values are: " + \
                    ",".join(sorted(type_cls.choices)) + ".")

        # Do some preparation for Type classes that claim to be string types,
        # i.e. handle case sensitivity and compile regexes.
        if type_cls.string_type:
            if self.args.case == "smart":
                # If the value is in lower case compare ignoring the case, if
                # it contains uppercase letters compare using sensitive case.
                ignore_case = value == value.lower()
            else:
                ignore_case = self.args.case == "ignore"

            if ignore_case:
                value = value.lower()

            # Pre-compile regular expressions.
            if operator == "~":
                try:
                    value = re.compile(value)
                except re.error as exc:
                    raise ExpressionError(f"Invalid regex pattern {value!r}: {exc}")

            elif operator == "%":
                value = Glob(value)
                if value.anchored:
                    if attribute == ("file", "path"):
                        # Guarantee that glob patterns are always matched against
                        # the path relative to the start directory, because that
                        # is what you want.
                        self.logger.warning(f"{value.pattern!r} is a full-path glob pattern "\
                                "that is supposed to be used relative to the start directory. "\
                                "Changing 'file.path' attribute to 'file.relpath'.",
                                tag="glob-anchored-path")
                        attribute = Attribute("file", "relpath")

                    elif attribute == ("file", "name"):
                        # If the glob pattern contains path separators it is
                        # supposed to match the whole path name, so we implicitly
                        # adjust the attribute name.
                        self.logger.warning(f"{value.pattern!r} is a full-path glob pattern "\
                                "that will not match on the basename. "\
                                "Changing 'file.name' attribute to 'file.relpath'.",
                                tag="glob-anchored-name")
                        attribute = Attribute("file", "relpath")

        return Test(attribute, operator, type_cls, value, ignore_case)

    def parse_sequence(self, sequences):
        """Parse a part of a list of tokens into a sequence of tests.
        """
        while self.tokens:
            token = self.tokens.pop(0)
            sequences.append(self.parse_test(token))


class Parser(FlatParser):
    """Parse a list of test expressions and operators into a nested test
       structure.
    """

    OPENING_BRACKETS = ("(", "{{")
    CLOSING_BRACKETS = (")", "}}")

    def parse(self):
        """Parse a list of tokens into a test structure.
        """
        sequences = OR(AND())
        self.parse_sequence(sequences)
        if self.tokens:
            raise ParserError(f"superfluous closing bracket {self.tokens[0]!r}")
        return sequences

    def parse_bracket_sequence(self, sequences, sub_sequences):
        """Parse a part of a list of tokens inside brackets.
        """
        self.parse_sequence(sub_sequences)

        if not self.tokens:
            raise ParserError("incomplete sub sequence")
        self.tokens.pop(0)

        sequences[-1].append(sub_sequences)

    def parse_sequence(self, sequences):
        """Parse a part of a list of tokens into a sequence of tests.
        """
        while self.tokens:
            token = self.tokens.pop(0)
            utoken = token.upper()

            if token in self.OPENING_BRACKETS:
                self.parse_bracket_sequence(sequences, OR(AND()))

            elif token in self.CLOSING_BRACKETS:
                if not sequences[-1]:
                    raise ParserError("empty expression")
                self.tokens.insert(0, token)
                return

            elif utoken == "AND":
                pass

            elif utoken == "OR":
                sequences.append(AND())

            elif utoken == "NOT":
                if not self.tokens:
                    raise ParserError("premature eof")

                utoken = self.tokens[0].upper()

                if utoken in self.OPENING_BRACKETS:
                    self.tokens.pop(0)
                    self.parse_bracket_sequence(sequences, NOT(AND()))

                elif utoken in ("AND", "OR", "NOT") + self.CLOSING_BRACKETS:
                    raise ParserError(f"unexpected token {utoken!r}")

                else:
                    sequences[-1].append(NOT(AND(self.parse_test(self.tokens.pop(0)))))

            else:
                sequences[-1].append(self.parse_test(token))
