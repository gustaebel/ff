# -----------------------------------------------------------------------
#
# ff - a tool to search the filesystem
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
import sys
import shlex
import argparse

# These imports must be absolute because of __main__.
from libff import EX_OK, MAX_CPU, EX_USAGE, __version__, __copyright__


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
            usage="%(prog)s [<options>] [<expression/directory> ... | [-D] <directory> ...]")

    group = parser.add_argument_group("Global options")

    if __debug__:
        group.add_argument("--profile", action="store_true", default=False,
                help="Do a profiling run on the given arguments and suppress the output.")
        group.add_argument("--debug", type=type_list, default=None,
                help="Show only debug messages of certain categories, default is to show all.")
        group.add_argument("--ignore-parent-ignorefiles", action="store_true", default=False,
                help="Do not read ignore files from parent directories.")
    group.add_argument("--cache", default=os.path.expanduser("~/.cache/ff.db"),
            help="Location of the metadata cache (default: %(default)s).")
    group.add_argument("--no-cache", action="store_const", dest="cache", const=None,
            help="Do not use the metadata cache.")
    group.add_argument("-j", "--jobs", type=type_jobs, default=MAX_CPU, metavar="<num>",
            help="Set number of processes to use for searching and executing "\
                 "(default: the number of CPU cores).")
    group.add_argument("expressions", nargs="*", metavar="<expression/directory>",
            help="An expression for matching files or a directory to search.")
    group.add_argument("-D", "--directories", nargs="+", default=[], metavar="<path>",
            help="Search entries in these paths (default is current directory).")

    group = parser.add_argument_group("Commands")
    group.add_argument("-h", "--help", nargs="?", const="all", metavar="<plugin>",
            help="Show this help message or the help message for a particular plugin.")
    group.add_argument("--version", action="store_true", default=False,
            help="Show program's version number and exit.")
    group.add_argument("--list-attributes", action="store_true", default=False,
            help="Show a list of available attributes to use for searching, sorting and output.")
    group.add_argument("--list-plugins", action="store_true", default=False,
            help="Show the list of available plugins.")
    group.add_argument("--list-types", action="store_true", default=False,
            help="Show the list of available types.")

    group = parser.add_argument_group("Search options")
    group.add_argument("-H", "--hidden", action="store_false", dest="hide", default=True,
            help="Show hidden files and directories.")
    group.add_argument("-I", "--ignored", action="store_false", dest="ignored", default=True,
            help="Show files that are normally excluded by patterns from .(git|fd|ff)ignore files.")
    group.add_argument("-e", "--exclude", action="append", default=[], metavar="<expression>",
            help="Exclude entries that match the given expression.")
    group.add_argument("-g", "--glob", action="store_const", const="%", dest="default_operator",
            default="~", help="Treat the pattern as a literal string.")
    group.add_argument("-r", "--regex", action="store_const", const="~", dest="default_operator",
            help="Perform a regular-expression based search (default).")
    group.add_argument("-F", "--fixed-strings", action="store_const", const=":",
            dest="default_operator", help="Treat the pattern as a literal string.")
    group.add_argument("-c", "--case", choices=["smart", "ignore", "sensitive"], dest="case_mode",
            default="smart", metavar="<mode>",
            help="How to treat the case of text attributes (smart, ignore or sensitive).")
    group.add_argument("-a", "--absolute-path", action="store_true", default=False,
            help="Show absolute instead of relative paths.")
    group.add_argument("-L", "--follow", action="store_true", dest="follow_symlinks", default=False,
            help="Follow symbolic links.")
    group.add_argument("-p", "--full-path", action="store_const", const="path",
            dest="default_attribute", default="name",
            help="Search full path (default: file-/dirname only).")
    group.add_argument("--one-file-system", "--mount", "--xdev", action="store_true", default=False,
            help="Do not descend into different file systems.")

    group = parser.add_argument_group("Output options")
    group.add_argument("-x", "--exec", nargs=argparse.REMAINDER, metavar="<cmd>",
            help="Execute a command for each search result.")
    group.add_argument("-X", "--exec-batch", nargs=argparse.REMAINDER, metavar="<cmd>",
            help="Execute a command with all search results at once.")
    group.add_argument("-C", "--color", choices=["auto", "never", "always"],
            default="never" if "NO_COLOR" in os.environ else "auto",
            metavar="<when>", help="When to use colors: never, *auto*, always.")
    group.add_argument("-0", "--print0", action="store_const", const="\0", dest="newline",
            default="\n", help="Separate results by the null character.")
    group.add_argument("-v", "--verbose", action="store_const", dest="output", default=["path"],
            const=["mode:h", "links", "user:h", "group:h", "size:5h", "time:h", "path:h"],
            help="Produce output similar to `ls -l`.")
    group.add_argument("-S", "--sort", nargs="?", type=type_list, const="file.path", default=None,
            metavar="<attribute-list>", help="Sort entries by path or any other attribute.")
    group.add_argument("-R", "--reverse", action="store_true", default=False,
            help="Reverse the sort order.")
    group.add_argument("-l", "--limit", action="store", type=type_number, default=None, metavar="N",
            help="Limit output to at most N entries.")
    group.add_argument("-1", action="store_const", const=1, dest="limit",
            help="Print only the first entry and exit immediately.")
    group.add_argument("-o", "--output", type=type_list, metavar="<attribute-list>",
            help="Print each entry by using a template of comma-separated attributes. "\
                 "The special value 'file' stands for all file attributes.")
    group.add_argument("--sep", default=" ", metavar="<string>", dest="separator",
            help="Separate each attribute of --output with <string>, default is a single space.")
    group.add_argument("--json", action="store_const", const="json", dest="json", default=None,
            help="Print attributes as one big json object to stdout.")
    group.add_argument("--jsonl", action="store_const", const="jsonl", dest="json",
            help="Print attributes as jsonl (one json object per line) to stdout.")
    group.add_argument("--si", action="store_true", default=False,
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


def print_help(parser, args):
    """Print help and version information.
    """
    if args.help == "all":
        # Help on plugins is taken care of in the main script.
        parser.print_help()
        raise SystemExit(EX_OK)

    elif args.version:
        print(__copyright__)
        raise SystemExit(EX_OK)


def check_arguments_sanity(context, args):
    """Check some of the arguments for semantic conflicts with other arguments.
    """
    if args.sort and args.exec and args.jobs != 1:
        context.warning("Using both --sort and --exec makes no sense unless you set --jobs=1!")

    if __debug__:
        if args.profile and (args.exec or args.exec_batch):
            context.error("You cannot use --exec or --exec-batch together with --profile",
                    EX_USAGE)

    if args.output != ["path"] and (args.exec or args.exec_batch):
        context.warning("--output has no effect with --exec and --exec-batch")


def postprocess_directories(context, args):
    """Arrange directory arguments and check them for validity.
    """
    if not args.directories:
        # Check which arguments are existing directories and append them to
        # args.directories. We allow directory arguments only at the start or
        # the end of the list of expressions.
        for expressions in (list(args.expressions), reversed(args.expressions)):
            for expression in expressions:
                if os.sep in expression and os.path.isdir(expression):
                    args.expressions.remove(expression)
                    directory = os.path.normpath(expression)
                    args.directories.append(directory)
                else:
                    break

    # Default to the current directory if no directory arguments are specified
    # or detected.
    if not args.directories:
        args.directories = ["."]

    # Check if directory arguments are sub-directories of one another.
    for directory in sorted(args.directories, reverse=True):
        for subdir in args.directories:
            if subdir == directory:
                continue
            if os.path.commonpath([directory, subdir]) == subdir:
                context.error(f"{directory!r} is a sub-directory of {subdir!r}", EX_USAGE)


def postprocess_arguments(args):
    """Check existing arguments and arrange them in specific ways.
    """
    if args.json:
        args.color = "never"
        args.absolute_path = True

    if args.hide:
        args.exclude.append("hide=yes")

    if args.one_file_system:
        args.exclude.append("samedev=no")


def parse_arguments(context):
    """Parse the arguments from the command line, check for conflicts and
       postprocess them for later use.
    """
    parser = create_parser()

    argv = collect_arguments()
    args = parser.parse_args(argv)

    print_help(parser, args)

    check_arguments_sanity(context, args)

    postprocess_directories(context, args)

    postprocess_arguments(args)

    return args
