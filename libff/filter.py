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

import itertools

from . import BaseClass
from .parser import Parser


class MatcherParser(Parser):
    """The MatcherParser warns about using the file.hide/file.hidden attributes
       without using -H/--hidden.
    """

    def create_test(self, attribute, operator, reference, value):
        if self.args.hide and attribute.plugin == "file" and \
                attribute.name in ("hide", "hidden"):
            self.logger.warning("file.hide and file.hidden have no effect with -H/--hide",
                    tag="hide")
        return super().create_test(attribute, operator, reference, value)


class Filter(BaseClass):
    """Basic Filter class to build Excluder and Matcher upon.
    """

    def __init__(self, context, parser):
        super().__init__(context)
        self.parser = parser

        if self.is_empty():
            self.test = self.test_empty

    def is_empty(self):
        """Return True if the test sequence contains no tests.
        """
        return not list(itertools.chain.from_iterable(self.parser))


class Excluder(Filter):
    """Excluder class that allows to exclude Entry objects based on their
       attributes.

       The Excluder works differently from the Matcher. It is simpler and only
       supports a flat list of tests.
    """
    # pylint:disable=method-hidden

    def __init__(self, context, tokens):
        super().__init__(context, Parser(context, tokens, "name", "%"))

    def test_empty(self, entry):
        """Default test method when the list of tests is empty.
        """
        # pylint:disable=unused-argument
        return False

    def test(self, entry):
        """Evaluate the list of Test objects for the entry object. Return True
           if the entry matches and is to be excluded.
        """
        for test in itertools.chain.from_iterable(self.parser):
            try:
                value, type_cls = self.registry.get_attribute_and_type(entry, test.attribute)
            except KeyError:
                # Ignore entries that don't provide this attribute.
                continue

            # If an entry matches the test, we return immediately without
            # further going through the TestSequence.
            if type_cls.test(entry, test, value):
                return True

        return False


class Matcher(Filter):
    """Matcher class that allows filtering Entry objects based on their
       attributes.
    """
    # pylint:disable=method-hidden

    def __init__(self, context, tokens):
        super().__init__(context, MatcherParser(context, tokens))

    def test_empty(self, entry):
        """Default test method when the list of tests is empty.
        """
        # pylint:disable=unused-argument
        return True

    def test(self, entry):
        """Evaluate the main sequence of Test objects and its sub sequences for
           the attributes from the entry object. Return True if the entry
           matches.
        """
        return any(self._test(self.parser, entry))

    def _test(self, tests, entry):
        """Handle a single sub test sequence by evaluating the
           Test objects it contains.
        """
        for test in tests:
            if test.name == "AND":
                yield all(self._test(test, entry))

            elif test.name == "OR":
                yield any(self._test(test, entry))

            elif test.name == "NOT":
                yield not any(self._test(test, entry))

            else:
                # Fetch the attribute's value from the entry to test.
                try:
                    value, type_cls = self.registry.get_attribute_and_type(entry, test.attribute)
                except KeyError:
                    # The plugin was unable to provide a value for this
                    # attribute, so we remove this entry from the result.
                    yield False
                else:
                    yield type_cls.test(entry, test, value)
