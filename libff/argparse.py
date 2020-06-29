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

# pylint:disable=redefined-builtin

import sys
import textwrap

from . import OUTPUT_WIDTH
from .exceptions import EX_USAGE


class ArgumentError(Exception):
    """Exception raised if the ArgumentParser is misconfigured or argument parsing fails.
    """


class Option:
    """An option container similar to the one in argparse.
    """
    # pylint:disable=too-many-instance-attributes,too-many-arguments

    def __init__(self, strings, action, help, const, choices, type, dest, default, metavar):
        if action == "arguments":
            if len(strings) > 1 or strings[0].startswith("-"):
                raise ArgumentError("misconfigured 'arguments' option")
            self.strings = strings
        else:
            self.strings = tuple(self.check_strings(strings))

        self.action = action
        self.help = help
        self.const = const
        self.choices = choices
        self.type = type
        self.default = default

        if dest is not None:
            self.dest = dest
        else:
            self.dest = self.get_name()

        if self.action in ("store", "store_optional", "append", "arguments"):
            if metavar is not None:
                self.metavar = metavar
            else:
                self.metavar = f"<{self.get_name()}>"
        else:
            self.metavar = None

    def get_name(self):
        """Get the default name for this option.
        """
        for string in self.strings:
            if not string.startswith("-") or string.startswith("--"):
                return string.lstrip("-").replace("-", "_")
        raise ArgumentError(f"missing long option {self.repr}")

    def check_strings(self, strings):
        """Check the validity of the option strings.
        """
        for string in strings:
            if not string:
                raise ArgumentError("empty option string")
            elif string.startswith("--"):
                yield string
            elif string.startswith("-"):
                if len(string) > 2:
                    raise ArgumentError(f"malformed short option {string!r}")
                yield string
            else:
                raise ArgumentError(f"invalid option {string!r}")

    @property
    def repr(self):
        """Return a representation of the option.
        """
        return "/".join(self.strings)


class Namespace(dict):
    """Container for the values assembled from the command line arguments.
    """

    def set(self, key, value):
        """Set the value for key.
        """
        self[key] = value

    def append(self, key, value):
        """Append the value to key.
        """
        container = self[key]
        if container is None:
            self[key] = []
        self[key].append(value)

    def __getattr__(self, key):
        return self[key]

    def __repr__(self):
        return f"Namespace({', '.join(f'{key}={value!r}' for key, value in sorted(self.items()))})"


class ArgumentParser:
    """Parse command line arguments in way similar to argparse.ArgumentParser.
    """

    usage = "ff [<options>] [<test/directory> ... | -D <directory> ...]"

    def __init__(self):
        self.help_output = []
        self.options = []
        self.namespace = Namespace()

    def error(self, message):
        """Print an error message to standard error output and exit with EX_USAGE.
        """
        print(f"usage: {self.usage}", file=sys.stderr)
        print(f"ff: error: {message}", file=sys.stderr)
        sys.exit(EX_USAGE)

    def print_usage(self, file=sys.stdout):
        """Print the usage to standard output.
        """
        print(self.usage, file=file)

    def print_help(self, file=sys.stdout):
        """Print the help to standard output.
        """
        print(f"usage: {self.usage}", file=file)

        for item in self.help_output:
            if isinstance(item, Option):
                option_string = self.format_option(item)

                help_text = textwrap.fill(item.help, width=OUTPUT_WIDTH - 27,
                        subsequent_indent=" " * 27)

                if len(option_string) > 25:
                    print(f"  {option_string}", file=file)
                    print(f"                           {help_text}", file=file)
                else:
                    print(f"  {option_string:25s}{help_text}", file=file)
            else:
                print(file=file)
                print(f"{item}:", file=file)

    def format_option(self, option):
        """Format an Option object.
        """
        if option.metavar is not None:
            if option.action == "arguments":
                return f"{option.metavar}"
            elif option.action == "store_optional":
                return f"{', '.join(option.strings)} [{option.metavar}]"
            else:
                return f"{', '.join(option.strings)} {option.metavar}"
        else:
            return f"{', '.join(option.strings)}"

    def print_manpage_help(self, file):
        """Produce help output suitable for inclusion in the manual page.
        """
        for item in self.help_output:
            if isinstance(item, Option):
                option_string = self.format_option(item)
                print(f"    {option_string}  {item.help}", file=file)
            else:
                print(file=file)
                print(f"    {item}:", file=file)

    def add_group(self, group_name):
        """Add a group separator the help output.
        """
        self.help_output.append(group_name)

    def add_option(self, *strings, action="store", help, const=None, choices=None, type=str,
            dest=None, default=None, metavar=None):
        """Add an option to the ArgumentParser.
        """
        # Check if all the option strings are unique.
        for string in strings:
            for option in self.options:
                if string in option.strings:
                    raise ArgumentError(f"option {string!r} already exists")

        # The "arguments" action must be specified only once.
        if action == "arguments":
            if any(o.action == "arguments" for o in self.options):
                raise ArgumentError("no support for more than one 'arguments' action")

        # Implicitly use an empty list for certain actions.
        if action in ("append", "arguments") and default is None:
            default = []

        # Create the Option object and add it to the list of options and the help output.
        option = Option(strings, action, help, const, choices, type, dest, default, metavar)
        self.options.append(option)
        self.help_output.append(option)

    def initialize(self):
        """Prepare the namespace with default values.
        """
        for option in self.options:
            if option.dest not in self.namespace:
                self.namespace.set(option.dest, option.default)

    def get_option(self, string):
        """Return an Option object for a specific string.
        """
        for option in self.options:
            if option.action == "arguments":
                continue
            elif string in option.strings:
                return option

        raise ArgumentError(f"unknown option {string!r}")

    def get_arguments_option(self):
        """Return the Option object that contains the positional arguments.
        """
        for option in self.options:
            if option.action == "arguments":
                return option

        raise ArgumentError("argument found but parser takes no arguments")

    def parse_combined_short_options(self, argv):
        """Disassemble a bundle of short options.
        """
        arg = argv.pop(0)[1:]
        i = 0
        while arg:
            short_option = f"-{arg[0]}"
            option = self.get_option(short_option)

            if option.action in ("store", "store_optional", "append"):
                argv.insert(i, short_option)
                argv.insert(i + 1, arg[1:])
                break
            else:
                argv.insert(i, short_option)

            arg = arg[1:]
            i += 1
        return argv

    def parse_long_option_with_value(self, argv):
        """Parse a long option with an attached argument.
        """
        arg = argv.pop(0)

        long_option, value = arg.split("=", 1)
        option = self.get_option(long_option)

        if option.action in ("store", "store_optional", "append"):
            argv.insert(0, long_option)
            argv.insert(1, value)
        else:
            raise ArgumentError(f"option {long_option} does not take an argument")

        return argv

    def parse_args(self, argv):
        """Parse a list of command line arguments.
        """
        argv = argv.copy()

        self.initialize()

        try:
            while argv:
                arg = argv[0]

                if arg.startswith("-"):
                    if arg[:2] != "--" and len(arg) > 2:
                        # This is not a long option but a bundle of short options.
                        argv = self.parse_combined_short_options(argv)

                    elif arg[:2] == "--" and "=" in arg:
                        # This is a long option with an attached argument.
                        argv = self.parse_long_option_with_value(argv)

                    self.parse_option(argv)

                else:
                    self.parse_arguments(argv)

        except ArgumentError as exc:
            self.error(exc)

        return self.namespace

    def get_argument(self, option, argv):
        """Fetch the next argument from the argument list.
        """
        if not argv or argv[0].startswith("-"):
            raise ArgumentError(f"{option.repr} requires an argument")
        else:
            return option.type(argv.pop(0))

    def parse_option(self, argv):
        """Parse a single option and act according to its action.
        """
        option = self.get_option(argv.pop(0))

        if option.action == "store_true":
            self.namespace.set(option.dest, True)

        elif option.action == "store_false":
            self.namespace.set(option.dest, True)

        elif option.action == "store_const":
            self.namespace.set(option.dest, option.const)

        elif option.action == "append":
            self.namespace.append(option.dest, self.get_argument(option, argv))

        elif option.action == "store":
            self.namespace.set(option.dest, self.get_argument(option, argv))

        elif option.action == "store_optional":
            if argv and not argv[0].startswith("-"):
                self.namespace.set(option.dest, self.get_argument(option, argv))
            else:
                self.namespace.set(option.dest, option.type(option.const))

        elif option.action == "store_remainder":
            while argv:
                self.namespace.append(option.dest, argv.pop(0))

        else:
            raise ArgumentError(f"unknown action {option.action!r}")

    def parse_arguments(self, argv):
        """Parse the positional arguments.
        """
        option = self.get_arguments_option()

        if self.namespace.get(option.dest):
            raise ArgumentError("intermixing arguments with options is not supported")

        while argv and not argv[0].startswith("-"):
            self.namespace.append(option.dest, argv.pop(0))
