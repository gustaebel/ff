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

import os
import re
import stat
from enum import Enum

from .convert import parse_size, parse_time, format_size, format_time, \
    parse_duration, format_duration


class Count(Enum):
    """Specify if a value shall be summed up (TOTAL), counted individually
       (COUNT) or raise an error (UNCOUNTABLE).
    """
    COUNT = 0
    TOTAL = 1
    UNCOUNTABLE = 2


class Type:
    """Type class that implements how an attribute interfaces with the outside
       world.
    """

    # A set of operators that this Type supports. There is a fixed number of
    # available operators. The first group is more suited for strings the
    # second group more for numbers.
    #
    #    =          equals
    #    :          contains
    #    ~          regex match
    #    %          glob match
    #
    #    +=         greater equal
    #    +          greater
    #    -=         less equal
    #    -          less
    #
    operators = ()

    # This value is used as a fallback value during sorting, when a Plugin does
    # not provide a particular attribute. It must be suitable for using it in a
    # comparison to another value of this Type, e.g. the empty string for
    # strings or 0 for integers.
    sort_none = None

    # Return how this attribute and value shall be included in the statistics.
    # If the value itself shall be summed up to a total (TOTAL) or whether each
    # individual value increases a count by 1 (COUNT). TOTAL is most suited for
    # things like size or duration whose values vary widely but are interesting
    # in total, COUNT is best for string values like e.g. extension, type etc.
    # to count how many files have a certain extension or a certain type.
    # If a type is uncountable it must use UNCOUNTABLE.
    count = Count.COUNT

    # Indicate whether this Type is a string type. This affects case
    # conversion, see test().
    string_type = False

    # Limit test values/patterns to certain choices. Should be a set of values
    # that are allowed.
    choices = None

    def __init_subclass__(cls):
        super().__init_subclass__()

        cls.name = cls.__name__.lower()

    @classmethod
    def input(cls, value):
        """Convert a value from a string from the command-line to the required
           type.
        """
        return value

    @classmethod
    def test(cls, entry, test, value):
        """Return True or False depending on whether the `test` matches `value`.
           `test` is a namedtuple with the following attributes:

                attribute           An Attribute(plugin, name) namedtuple.
                operator            The operator: '=', '~', etc.
                type                The Type class of the value.
                value               The value/pattern to test `value` against.
                ignore_case         Whether or not to consider case for string comparison,
                                    None if the Type is not a string type.

            If both string_type and `test.ignore_case` are True test.value will
            be in lowercase. It is up to you to convert `value` to lowercase as
            well.
        """
        raise NotImplementedError

    @classmethod
    def output(cls, args, modifier, value):
        # pylint:disable=unused-argument
        """Create a representation of the value for output on the screen.
           `args` is the global ArgumentParser object. At the moment it is only
           used to detect whether --si was specified or not. Modifier is either
           "h" for human readable, "o" for octal or None.
        """
        return str(value)

    @classmethod
    def check_type(cls, value):
        """Check if a value conforms to this Type class. This is used to check
           whether values returned by plugins have the correct type and is only
           used in __debug__ mode. The default implementation uses the type of
           the .sort_none attribute, but this may be insufficient, e.g. for
           compound types like lists.
        """
        return isinstance(value, type(cls.sort_none))

    @classmethod
    def sort_key(cls, value):
        """Extract a comparison key from `value` that will be used for sorting.
        """
        return value


class String(Type):
    """Simple string. Examples: 'file.ext=txt' 'mime.mime~py'
    """

    operators = ("=", ":", "~", "%")
    sort_none = ""
    count = Count.COUNT
    string_type = True

    @classmethod
    def test(cls, entry, test, value):
        # If the test is case insensitive, the test.value argument has
        # already been converted to lower case.
        if test.ignore_case:
            value = value.lower()

        if test.operator == "%":
            if test.value.match(value, value, False):
                return test.value.include
            else:
                return not test.value.include

        return test.operator == "=" and value == test.value or \
                test.operator == ":" and test.value in value or \
                test.operator == "~" and test.value.search(value) is not None

    @classmethod
    def sort_key(cls, value):
        return value.lower()


class Path(String):
    """String containing a filesystem path or a portion thereof. Examples:
       'file.name%*.txt' 'file.dir=foo/bar'
    """

    @classmethod
    def test(cls, entry, test, value):
        if test.ignore_case:
            value = value.lower()

        if test.operator == "%":
            basename = entry.name.lower() if test.ignore_case else entry.name
            is_dir = entry.is_dir()

            if test.value.match(value, basename, is_dir):
                return test.value.include
            else:
                return not test.value.include

        return super().test(entry, test, value)

    @classmethod
    def sort_key(cls, value):
        value = value.lower()
        return os.sep.join(v.lstrip(".") for v in value.split(os.sep))


class FileType(Type):
    """String representing the type of a file. The value is one of d,
       directory, f, file, l, symlink, s, socket, p, pipe, fifo, char, block,
       door, port, whiteout or other. Example: type=f
    """

    operators = ("=",)
    sort_none = ""
    count = Count.COUNT
    choices = set(["d", "directory", "f", "file", "l", "symlink", "s",
        "socket", "p", "pipe", "fifo", "char", "block", "door", "port",
        "whiteout", "other"])

    @classmethod
    def test(cls, entry, test, value):
        test_value = test.value.lower()
        if test_value == "d":
            test_value = "directory"
        elif test_value == "f":
            test_value = "file"
        elif test_value == "l":
            test_value = "symlink"
        elif test_value == "s":
            test_value = "socket"
        elif test_value in ("p", "pipe"): # compatible to fd.
            test_value = "fifo"
        return test.operator == "=" and value == test_value


class ListOfStrings(Type):
    """List of strings.
    """

    operators = String.operators
    sort_none = []
    count = Count.UNCOUNTABLE
    string_type = True
    name = String.name + "[]"

    @classmethod
    def test(cls, entry, test, value):
        return any(String.test(entry, test, v) for v in value)

    @classmethod
    def output(cls, args, modifier, value):
        return ",".join(value)

    @classmethod
    def check_type(cls, value):
        if not isinstance(value, (list, set)):
            return False
        return all(isinstance(v, type(String.sort_none)) for v in value)


class Number(Type):
    """Simple number. Examples: 'file.uid=1000' 'file.links+=2'
    """

    operators = ("+=", "-=", "+", "-", "=")
    sort_none = 0

    @classmethod
    def input(cls, value):
        try:
            value = int(value)
        except ValueError:
            raise ValueError(f"unable to parse {value!r}")
        if value < 0:
            raise ValueError("value must not be less than 0")
        return value

    @classmethod
    def output(cls, args, modifier, value):
        if modifier == "o":
            return f"{value:o}"
        else:
            return super().output(args, modifier, value)

    @classmethod
    def test(cls, entry, test, value):
        return test.operator == "=" and value == test.value or \
                test.operator == "+=" and value >= test.value or \
                test.operator == "-=" and value <= test.value or \
                test.operator == "+" and value > test.value or \
                test.operator == "-" and value < test.value


class Mode(Type):
    """File permissions. Either octal numbers or symbolic notation is
       supported. Examples: 'file.perm=a+rwx' 'file.perm-u+x' 'file.perm+700'
    """

    operators = ("=", ":", "~")
    sort_none = 0
    count = Count.COUNT

    regex = re.compile(r"([ugoa]*)([-+=])([rwxXst]+)|([-+=])?([0-7]+)$")

    MODE_ALL = stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX | \
               stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO

    @classmethod
    def parse_mode(cls, value):
        """Parse an octal or symbolic file mode.
        """
        # pylint:disable=too-many-branches
        affected = 0
        result = 0
        for part in value.split(","):
            val = 0

            match = cls.regex.match(part)
            if match is None:
                raise ValueError(f"unable to parse {value!r}")

            if match.group(1) is not None:
                affected_str, operator, value_str = match.groups()[:3]

                if not affected_str:
                    affected_str = "a"

                for char in affected_str:
                    if char == "u":
                        affected |= stat.S_ISUID | stat.S_IRWXU
                    elif char == "g":
                        affected |= stat.S_ISGID | stat.S_IRWXG
                    elif char == "o":
                        affected |= stat.S_ISVTX | stat.S_IRWXO
                    elif char == "a":
                        affected |= cls.MODE_ALL

                if value_str == "u":
                    val |= stat.S_IRWXU
                elif value_str == "g":
                    val |= stat.S_IRWXG
                elif value_str == "o":
                    val |= stat.S_IRWXO
                else:
                    for char in value_str:
                        if char == "r":
                            val |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
                        elif char == "w":
                            val |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
                        elif char == "x":
                            val |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                        elif char == "s":
                            val |= stat.S_ISUID | stat.S_ISGID
                        elif char == "t":
                            val |= stat.S_ISVTX

            else:
                operator, val = match.groups()[3:]
                if not operator:
                    operator = "="
                affected = cls.MODE_ALL
                val = int(val, 8)

            if operator in "+=":
                result |= val
            elif operator == "-":
                result &= ~val

        return affected & result

    @classmethod
    def input(cls, value):
        return cls.parse_mode(value)

    @classmethod
    def output(cls, args, modifier, value):
        if modifier == "h":
            return stat.filemode(value)
        elif modifier == "o":
            return f"{value:o}"
        else:
            return super().output(args, modifier, value)

    @classmethod
    def test(cls, entry, test, value):
        test_value = test.value & cls.MODE_ALL
        value = value & cls.MODE_ALL
        return test.operator == "=" and value == test_value or \
               test.operator == ":" and value & test_value == test_value or \
               test.operator == "~" and value & test_value != 0


class Size(Number):
    """File size. Example: 'file.size+=100M'
    """

    count = Count.TOTAL

    @classmethod
    def input(cls, value):
        return parse_size(value)

    @classmethod
    def output(cls, args, modifier, value):
        if modifier == "h":
            return format_size(value, base=1000 if args.si else 1024)
        else:
            return super().output(args, modifier, value)


class Time(Number):
    """Time in seconds since 1970-01-01 00:00:00. Examples:
       'file.time=1589234400' 'file.time+=2020-05-12' 'file.time+=1d12h'
    """

    @classmethod
    def input(cls, value):
        return parse_time(value)

    @classmethod
    def output(cls, args, modifier, value):
        if modifier == "h":
            return format_time(value)
        else:
            return super().output(args, modifier, value)


class Duration(Number):
    """Duration in seconds. Example: 'medium.duration+=1h30m'
    """

    count = Count.TOTAL

    @classmethod
    def input(cls, value):
        return parse_duration(value)

    @classmethod
    def output(cls, args, modifier, value):
        if modifier == "h":
            return format_duration(value)
        else:
            return super().output(args, modifier, value)


class Boolean(Type):
    """Boolean value. May be one of (true, t, 1, yes, y, on) or (false, f, 0,
       no, n, off). The case is ignored. Example: 'empty=yes'
    """

    operators = ("=",)
    sort_none = False
    count = Count.COUNT

    true = ("true", "t", "1", "yes", "y", "on")
    false = ("false", "f", "0", "no", "n", "off")

    @classmethod
    def input(cls, value):
        assert value.lower() in cls.true + cls.false
        return value.lower() in cls.true

    @classmethod
    def output(cls, args, modifier, value):
        return str(value).lower()

    @classmethod
    def test(cls, entry, test, value):
        return test.operator == "=" and value is test.value
