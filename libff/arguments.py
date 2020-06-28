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

from . import MAX_CPU
from .argparse import ArgumentParser
from .exceptions import EX_OK, UsageError


class Defaults:
    """Provide the defaults for both the ArgumentParser as well as the API.
    """

    case = "smart"
    case_choices = ["smart", "ignore", "sensitive"]
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


def create_parser():
    """Create the ArgumentParser object.
    """
    # pylint:disable=too-many-statements
    parser = ArgumentParser()

    parser.add_group("Global options")
    parser.add_option("tests", action="arguments", metavar="<test/directory>",
            help="A test for file matching or a the path to a directory to search.")
    if __debug__:
        parser.add_option("--profile", action="store_true", default=False,
                help="Do a profiling run on the given arguments and suppress the output.")
        parser.add_option("--debug", type=type_list, default=["none"], metavar="<categories>",
                help="Show debug messages. Specify either 'all', 'none' or a comma-separated list "\
                     "of <categories>, default is to show 'none'.")
    parser.add_option("--cache", default=Defaults.cache, metavar="<path>",
            help="Location of the metadata cache, the default is ~/.cache/ff.db.")
    parser.add_option("--no-cache", action="store_const", dest="cache", const=None,
            help="Do not use the metadata cache.")
    parser.add_option("--clean-cache", action="store_const", const="clean", dest="action",
            help="Remove stale entries from the metadata cache.")
    parser.add_option("-j", "--jobs", type=type_jobs, default=Defaults.jobs, metavar="<num>",
            help="Set number of processes to use for searching and executing "\
                 "(default: the number of CPU cores).")
    parser.add_option("-D", "--directory", action="append", metavar="<path>", dest="directories",
            default=[], help="Search entries in this path (default is current directory). May be "\
                             "specified multiple times.")

    parser.add_group("Commands")
    parser.add_option("-h", "--help", action="store_optional", const="all", metavar="<plugin>",
            help="Show this help message or the help message for a particular plugin.")
    parser.add_option("--version", action="store_const", const="version", dest="action",
            help="Show program's version number and exit.")
    parser.add_option("--help-full", action="store_const", const="full", dest="action",
            help="Show a full help in man page format.")
    parser.add_option("--help-attributes", action="store_const", const="attributes",
            dest="action",
            help="Show a list of available attributes to use for searching, sorting and output.")
    parser.add_option("--help-plugins", action="store_const", const="plugins", dest="action",
            help="Show a list of available plugins.")
    parser.add_option("--help-types", action="store_const", const="types", dest="action",
            help="Show a list of available types.")

    parser.add_group("Search options")
    parser.add_option("-e", "--exclude", action="append", default=[], metavar="<test>",
            help="Exclude entries that match the given test.")
    parser.add_option("-H", "--hide", action="store_true",  default=False,
            help="Do not show hidden files and directories.")
    parser.add_option("-I", "--ignore", action="store_true", default=False,
            help="Do not show files that are excluded by patterns from .(git|fd|ff)ignore files.")
    parser.add_option("--no-parent-ignore", action="store_true", default=False,
            help="Do not read patterns from ignore files from parent directories.")
    parser.add_option("-d", "--depth", type=type_ranges, metavar="<range>",
            help="Show only files that are located at a certain depth level of the directory "\
                 "tree that is within the given <range>. A <range> is a string of the form "\
                 "'<start>-<stop>'. <start> and <stop> are optional and may be omitted. "\
                 "<range> may also be a single number. It is possible to specify multiple "\
                 "ranges separated by comma.")
    parser.add_option("-c", "--case", choices=Defaults.case_choices, dest="case",
            default=Defaults.case, metavar="<mode>",
            help="How to treat the case of text attributes (smart, ignore or sensitive).")
    parser.add_option("-L", "--follow", action="store_true", dest="follow_symlinks",
            default=Defaults.follow_symlinks, help="Follow symbolic links.")
    parser.add_option("--one-file-system", "--mount", "--xdev", action="store_true",
            default=False,
            help="Do not descend into different file systems.")

    parser.add_group("Output options")
    parser.add_option("-x", "--exec", action="store_remainder", metavar="<cmd>",
            help="Execute a command for each search result.")
    parser.add_option("-X", "--exec-batch", action="store_remainder", metavar="<cmd>",
            help="Execute a command with all search results at once.")
    parser.add_option("-C", "--color", choices=["auto", "never", "always"],
            default="never" if "NO_COLOR" in os.environ else "auto",
            metavar="<when>", help="When to use colors: never, *auto*, always.")
    parser.add_option("-a", "--absolute-path", action="store_true", default=False,
            help="Show absolute instead of relative paths.")
    parser.add_option("-0", "--print0", action="store_const", const="\0", dest="newline",
            default="\n", help="Separate results by the null character.")
    parser.add_option("-v", "--verbose", action="store_const", dest="output", default=["path"],
            const=["mode:h", "links", "user:h", "group:h", "size:5h", "time:h", "path:h"],
            help="Produce output similar to `ls -l`.")
    parser.add_option("-S", "--sort", action="store_optional", type=type_list, const="file.path",
            metavar="<attribute-list>", help="Sort entries by path or any other attribute.")
    parser.add_option("-R", "--reverse", action="store_true", default=False,
            help="Reverse the sort order.")
    parser.add_option("--count", action="store_optional", type=type_list,
            const="file.size:h,file.type", metavar="<attribute-list>",
            help="Count the attributes from <attribute-list> and print statistics, "\
                 "instead of the result, the default is to count the total size and "\
                 "the file types of the entries found. Add --json for JSON output.")
    parser.add_option("-l", "--limit", action="store", type=type_number,
            metavar="<n>", help="Limit output to at most <n> entries.")
    parser.add_option("-1", action="store_const", const=1, dest="limit",
            help="Print only the first entry and exit immediately.")
    parser.add_option("-o", "--output", type=type_list, metavar="<attribute-list>",
            help="Print each entry by using a template of comma-separated attributes. "\
                 "The special value 'file' stands for all file attributes.")
    parser.add_option("--sep", default=" ", metavar="<string>", dest="separator",
            help="Separate each attribute of --output with <string>, default is a single space.")
    parser.add_option("--all", action="store_true", default=False,
            help="Show all entries including the ones with missing attribute values.")
    parser.add_option("--json", action="store_const", const="json", dest="json",
            help="Print attributes as one big json object to stdout.")
    parser.add_option("--jsonl", "--ndjson", action="store_const", const="jsonl", dest="json",
            help="Print attributes as jsonl (one json object per line) to stdout.")
    parser.add_option("--si", action="store_true", default=Defaults.si,
            help="Parse and print file sizes in units of 1K=1000 bytes instead of 1K=1024 bytes.")

    return parser


def collect_arguments():
    """Join arguments for the ArgumentParser from the FF_OPTIONS environment variable with the ones
       from the command line.
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
            # self.args.directories. We allow directory arguments only at the start or the end of
            # the list of tests.
            for tests in (list(self.args.tests), reversed(self.args.tests)):
                for test in tests:
                    if os.sep in test and os.path.isdir(test):
                        self.args.tests.remove(test)
                        directory = os.path.normpath(test)
                        self.args.directories.append(directory)
                    else:
                        break

        # Default to the current directory if no directory arguments are specified or detected.
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
            # Look for an upper limit in the given ranges and exclude everything above it, so we go
            # only as deep into the tree as necessary.
            if not [stop for start, stop in self.args.depth if stop is None]:
                stop = max(stop for start, stop in self.args.depth)
                self.args.exclude.append(f"depth+{stop}")

            # Construct a set of tests for all the given ranges and embed the existing set of tests
            # in it.
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
    """Parse the arguments from the command line, check for conflicts and postprocess them for
       later use.
    """
    parser = create_parser()

    argv = collect_arguments()
    args = parser.parse_args(argv)

    if args.help == "all":
        # Help on plugins is taken care of in libff/find.py.
        parser.print_help()
        raise SystemExit(EX_OK)

    processor = ArgumentsPostProcessor(args)
    warnings = processor.process()

    return args, warnings
