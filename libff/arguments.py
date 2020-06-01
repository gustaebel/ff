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
import sys
import shlex
import argparse

# These imports must be absolute because of __main__.
from libff import MAX_CPU, __version__, __copyright__
from libff.exceptions import EX_OK, UsageError


class Defaults:
    """Provide the defaults for both the ArgumentParser as well as the API.
    """

    case = "smart"
    default_attribute = "name"
    default_operator = "~"
    follow_symlinks = False
    jobs = MAX_CPU
    cache = os.path.expanduser("~/.cache/ff.db")
    si = False


def type_jobs(string):
    """Parse the number of jobs using a default of MAX_CPU if it is zero.
    """
    num = type_number(string)
    if num == 0:
        num = MAX_CPU
    return max(min(num, MAX_CPU), 1)


def type_number(string):
    """Parse a number greater than zero.
    """
    num = int(string)
    if num < 0:
        raise ValueError("number must be greater than zero")
    return num


def type_list(string):
    """Parse a comma separated string into a list.
    """
    return [s.strip() for s in string.split(",")]


regex_range = re.compile(r"^(?:(?P<single>\d+)|(?P<start>\d*)-(?P<stop>\d*))$")

def type_ranges(string):
    """Parse a comma separated list of ranges.
    """
    segments = []
    for range_ in type_list(string):
        match = regex_range.match(range_)
        if match is None:
            raise ValueError("invalid range")

        if match.group("single") is not None:
            number = int(match.group("single"))
            segments.append((number, number))

        else:
            start = match.group("start")
            if start:
                start = int(start)
            else:
                start = 0

            stop = match.group("stop")
            if stop:
                stop = int(stop)
                if stop < start:
                    stop, start = start, stop
            else:
                stop = None

            segments.append((start, stop))

    return segments


class HelpFormatter(argparse.HelpFormatter):
    """HelpFormatter subclass that does not show arguments for short but only
       for long options and shows the argument for REMAINDER options instead of
       three dots.
    """

    def __init__(self, prog, indent_increment=2, max_help_position=27, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_action_invocation(self, action):
        # Don't show the argument for short options. This looks cleaner.
        if not action.option_strings:
            return super()._format_action_invocation(action)
        else:
            parts = []
            if action.nargs == 0:
                parts.extend(action.option_strings)
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                for i, option_string in enumerate(action.option_strings):
                    if i == 0:
                        parts.append(option_string)
                    else:
                        parts.append('%s %s' % (option_string, args_string))
            return ', '.join(parts)

    def _format_args(self, action, default_metavar):
        # Instead of three dots ... show the name of the argument for REMAINDER
        # arguments.
        result = super()._format_args(action, default_metavar)
        if action.nargs == argparse.REMAINDER:
            return self._metavar_formatter(action, default_metavar)(1)[0]
        else:
            return result


def create_parser(formatter_class=HelpFormatter):
    """Create the argparse.ArgumentParser object.
    """
    parser = argparse.ArgumentParser(prog="ff", formatter_class=formatter_class, add_help=False,
            usage="%(prog)s [<options>] [<test/directory> ... | [-D] <directory> ...]")

    group = parser.add_argument_group("Global options")

    if __debug__:
        group.add_argument("--profile", action="store_true", default=False,
                help="Do a profiling run on the given arguments and suppress the output.")
        group.add_argument("--debug", type=type_list, default=None,
                help="Show only debug messages of certain categories, default is to show all.")
    group.add_argument("--cache", default=Defaults.cache,
            help="Location of the metadata cache (default: %(default)s).")
    group.add_argument("--no-cache", action="store_const", dest="cache", const=None,
            help="Do not use the metadata cache.")
    group.add_argument("-j", "--jobs", type=type_jobs, default=Defaults.jobs, metavar="<num>",
            help="Set number of processes to use for searching and executing "\
                 "(default: the number of CPU cores).")
    group.add_argument("tests", nargs="*", metavar="<test/directory>",
            help="A test expression for matching files or a directory to search.")
    group.add_argument("-D", "--directories", nargs="+", default=[], metavar="<path>",
            help="Search entries in these paths (default is current directory).")

    group = parser.add_argument_group("Commands")
    group.add_argument("-h", "--help", nargs="?", const="all", metavar="<plugin>",
            help="Show this help message or the help message for a particular plugin.")
    group.add_argument("--version", action="store_const", const="version", dest="action",
            default=None, help="Show program's version number and exit.")
    group.add_argument("--list-attributes", action="store_const", const="attributes", dest="action",
            help="Show a list of available attributes to use for searching, sorting and output.")
    group.add_argument("--list-plugins", action="store_const", const="plugins", dest="action",
            help="Show the list of available plugins.")
    group.add_argument("--list-types", action="store_const", const="types", dest="action",
            help="Show the list of available types.")

    group = parser.add_argument_group("Search options")
    group.add_argument("-H", "--hide", action="store_true",  default=False,
            help="Do not show hidden files and directories.")
    group.add_argument("-I", "--ignore", action="store_true", default=False,
            help="Do not show files that are excluded by patterns from .(git|fd|ff)ignore files.")
    group.add_argument("-d", "--depth", type=type_ranges, default=None, metavar="<range>",
            help="Show only files that are located at a certain depth level of the directory "\
                 "tree that is within the given <range>. A <range> is a string of the form "\
                 "'<start>-<stop>'. <start> and <stop> are optional and may be omitted. "\
                 "<range> may also be a single number. It is possible to specify multiple "\
                 "ranges separated by comma.")
    group.add_argument("--no-parent-ignore", action="store_true", default=False,
            help="Do not read patterns from ignore files from parent directories.")
    group.add_argument("-e", "--exclude", action="append", default=[], metavar="<test>",
            help="Exclude entries that match the given test.")
    group.add_argument("-c", "--case", choices=["smart", "ignore", "sensitive"], dest="case",
            default=Defaults.case, metavar="<mode>",
            help="How to treat the case of text attributes (smart, ignore or sensitive).")
    group.add_argument("-L", "--follow", action="store_true", dest="follow_symlinks",
            default=Defaults.follow_symlinks, help="Follow symbolic links.")
    group.add_argument("--one-file-system", "--mount", "--xdev", action="store_true", default=False,
            help="Do not descend into different file systems.")

    group = parser.add_argument_group("Simple pattern options")
    group.add_argument("-g", "--glob", action="store_const", const="%", dest="default_operator",
            default=Defaults.default_operator, help="Treat the pattern as a literal string.")
    group.add_argument("-r", "--regex", action="store_const", const="~", dest="default_operator",
            help="Perform a regular-expression based search (default).")
    group.add_argument("-F", "--fixed-strings", action="store_const", const=":",
            dest="default_operator", help="Treat the pattern as a literal string.")
    group.add_argument("-p", "--full-path", action="store_const", const="path",
            dest="default_attribute", default=Defaults.default_attribute,
            help="Search full path (default: basename only).")

    group = parser.add_argument_group("Output options")
    group.add_argument("-x", "--exec", nargs=argparse.REMAINDER, metavar="<cmd>",
            help="Execute a command for each search result.")
    group.add_argument("-X", "--exec-batch", nargs=argparse.REMAINDER, metavar="<cmd>",
            help="Execute a command with all search results at once.")
    group.add_argument("-C", "--color", choices=["auto", "never", "always"],
            default="never" if "NO_COLOR" in os.environ else "auto",
            metavar="<when>", help="When to use colors: never, *auto*, always.")
    group.add_argument("-a", "--absolute-path", action="store_true", default=False,
            help="Show absolute instead of relative paths.")
    group.add_argument("-0", "--print0", action="store_const", const="\0", dest="newline",
            default="\n", help="Separate results by the null character.")
    group.add_argument("-v", "--verbose", action="store_const", dest="output", default=["path"],
            const=["mode:h", "links", "user:h", "group:h", "size:5h", "time:h", "path:h"],
            help="Produce output similar to `ls -l`.")
    group.add_argument("-S", "--sort", nargs="?", type=type_list, const="file.path", default=None,
            metavar="<attribute-list>", help="Sort entries by path or any other attribute.")
    group.add_argument("-R", "--reverse", action="store_true", default=False,
            help="Reverse the sort order.")
    group.add_argument("--count", nargs="?", type=type_list, const="file.size:h,file.type",
            default=None, metavar="<attribute-list>",
            help="Count the attributes from <attribute-list> and print statistics, "\
                 "instead of the result, the default is to count the total size and "\
                 "the file types of the entries found. Add --json for JSON output.")
    group.add_argument("-l", "--limit", action="store", type=type_number, default=None, metavar="N",
            help="Limit output to at most N entries.")
    group.add_argument("-1", action="store_const", const=1, dest="limit",
            help="Print only the first entry and exit immediately.")
    group.add_argument("-o", "--output", type=type_list, metavar="<attribute-list>",
            help="Print each entry by using a template of comma-separated attributes. "\
                 "The special value 'file' stands for all file attributes.")
    group.add_argument("--sep", default=" ", metavar="<string>", dest="separator",
            help="Separate each attribute of --output with <string>, default is a single space.")
    group.add_argument("--all", action="store_true", default=False,
            help="Show all entries including the ones with missing attribute values.")
    group.add_argument("--json", action="store_const", const="json", dest="json", default=None,
            help="Print attributes as one big json object to stdout.")
    group.add_argument("--jsonl", action="store_const", const="jsonl", dest="json",
            help="Print attributes as jsonl (one json object per line) to stdout.")
    group.add_argument("--si", action="store_true", default=Defaults.si,
            help="Parse and print file sizes in units of 1K=1000 bytes instead of 1K=1024 bytes.")

    return parser


def collect_arguments():
    """Join arguments for the ArgumentParser from the FF_OPTIONS environment
       variable with the ones from the command line.
    """
    ff_options = os.environ.get("FF_OPTIONS")
    if ff_options:
        argv = shlex.split(ff_options)
    else:
        argv = []
    argv += sys.argv[1:]
    return argv


class ArgumentsPostProcessor:
    """Check and postprocess the arguments in an argparse.Namespace.
    """

    def __init__(self, args):
        self.args = args

    def process(self):
        """Check and postprocess the arguments.
        """
        self.process_directories()
        self.process_arguments()
        self.check_for_errors()
        return self.collect_warnings()

    def check_for_errors(self):
        """Check some of the arguments for semantic conflicts with other arguments.
        """
        if __debug__:
            if self.args.profile and (self.args.exec or self.args.exec_batch):
                raise UsageError("You cannot use --exec or --exec-batch together with --profile!")

        if self.args.count and (self.args.exec or self.args.exec_batch):
            raise UsageError("You cannot use --exec or --exec-batch together with --count!")

        if self.args.count and self.args.limit is not None:
            raise UsageError("You cannot use --limit together with --count!")

    def collect_warnings(self):
        """Check some of the arguments for semantic conflicts with other arguments.
        """
        warnings = []

        if self.args.sort and self.args.exec and self.args.jobs != 1:
            warnings.append("Using both --sort and --exec makes no sense unless you set --jobs=1!")

        if self.args.output != ["path"] and (self.args.exec or self.args.exec_batch):
            self.args.output = ["path"]
            warnings.append(
                    "Switching off --output, it has no effect with --exec and --exec-batch.")

        if self.args.count:
            if self.args.sort:
                self.args.sort = None
                warnings.append("Switching off --sort, it has no effect with --count.")

            if self.args.output != ["path"]:
                self.args.output = ["path"]
                warnings.append("Switching off --output, it has no effect with --count.")

        return warnings

    def process_directories(self):
        """Arrange directory arguments and check them for validity.
        """
        if not self.args.directories:
            # Check which arguments are existing directories and append them to
            # self.args.directories. We allow directory arguments only at the start or
            # the end of the list of tests.
            for tests in (list(self.args.tests), reversed(self.args.tests)):
                for test in tests:
                    if os.sep in test and os.path.isdir(test):
                        self.args.tests.remove(test)
                        directory = os.path.normpath(test)
                        self.args.directories.append(directory)
                    else:
                        break

        # Default to the current directory if no directory arguments are specified
        # or detected.
        if not self.args.directories:
            self.args.directories = ["."]

        # Check if directory arguments are sub-directories of one another.
        for directory in sorted(self.args.directories, reverse=True):
            for subdir in self.args.directories:
                if subdir == directory:
                    continue
                if os.path.commonpath([directory, subdir]) == subdir:
                    raise UsageError(f"{directory!r} is a sub-directory of {subdir!r}")

    def process_arguments(self):
        """Check existing arguments and arrange them in specific ways.
        """
        if self.args.json:
            self.args.color = "never"
            self.args.absolute_path = True

        if self.args.ignore:
            self.args.exclude.append("ignored=yes")

        if self.args.one_file_system:
            self.args.exclude.append("samedev=no")

        if self.args.hide:
            self.args.exclude.append("hide=yes")

        if self.args.depth:
            # Look for an upper limit in the given ranges and exclude
            # everything above it, so we go only as deep into the tree as
            # necessary.
            if not [stop for start, stop in self.args.depth if stop is None]:
                stop = max(stop for start, stop in self.args.depth)
                self.args.exclude.append(f"depth+{stop}")

            # Construct a set of tests for all the given ranges and embed the
            # existing set of tests in it.
            tests = []
            tests.append("{{")

            for i, (start, stop) in enumerate(self.args.depth):
                if start == stop:
                    tests.append(f"depth={start}")
                else:
                    tests.append(f"depth+={start}")
                    if stop is not None:
                        tests.append(f"depth-={stop}")

                if i < len(self.args.depth) - 1:
                    tests.append("OR")

            tests.append("}}")

            if self.args.tests:
                tests.append("{{")
                tests += self.args.tests
                tests.append("}}")

            self.args.tests = tests


def parse_arguments():
    """Parse the arguments from the command line, check for conflicts and
       postprocess them for later use.
    """
    parser = create_parser()

    argv = collect_arguments()
    args = parser.parse_args(argv)

    if args.help == "all":
        # Help on plugins is taken care of in the main script.
        parser.print_help()
        raise SystemExit(EX_OK)

    elif args.action == "version":
        print(__copyright__)
        raise SystemExit(EX_OK)

    processor = ArgumentsPostProcessor(args)
    warnings = processor.process()

    return args, warnings
