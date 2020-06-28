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

import shlex
import argparse

from .main import _Base
from .arguments import Defaults, ArgumentsPostProcessor
from .processing import ImmediateGenerator, CollectiveGenerator


class FindNamespace(argparse.Namespace):
    """An argparser.Namespace that contains the minimum number of arguments for setting up the
       Python API.
    """
    # pylint:disable=too-many-instance-attributes

    debug = ["none"]
    profile = None
    json = None

    depth = None

    # Options that have no relevance for the Python API but will be referenced somewhere in the
    # code. Would be nice to remove these one day.
    count = None
    exec = None
    exec_batch = None
    action = None
    help = None

    no_parent_ignore = False


class Find(_Base):
    """Query the filesystem and yield the resulting entries.
    """
    # pylint:disable=too-many-arguments,too-many-locals,dangerous-default-value,invalid-name

    def __init__(self, query=None, directories=["."], exclude=[], output=["file"],
            sort=[], reverse=False,
            hide=False, ignore=False, one_file_system=False,
            case=Defaults.case,
            si=Defaults.si,
            follow_symlinks=Defaults.follow_symlinks,
            absolute_path=False, jobs=Defaults.jobs, cache=Defaults.cache):
        super().__init__()

        if case not in Defaults.case_choices:
            raise ValueError(f"case argument must be one of {', '.join(Defaults.case_choices)}")

        if query is None:
            tests = []
        elif isinstance(query, str):
            tests = shlex.split(query)
        else:
            tests = query

        args = FindNamespace()
        args.tests = tests
        args.directories = directories.copy()
        args.exclude = exclude.copy()
        args.output = output
        args.sort = sort
        args.reverse = reverse
        args.hide = hide
        args.ignore = ignore
        args.one_file_system = one_file_system
        args.case = case
        args.si = si
        args.follow_symlinks = follow_symlinks
        args.absolute_path = absolute_path
        args.jobs = jobs
        args.cache = cache

        processor = ArgumentsPostProcessor(args)
        processor.process()

        self.setup_context(args, [])
        self.setup_components()
        self.setup_processing()
        if __debug__:
            self.show_tests()
        self.setup_walker()

    def setup_processing(self):
        if self.context.args.sort:
            self.context.processing = CollectiveGenerator(self.context)
        else:
            self.context.processing = ImmediateGenerator(self.context)

    def __iter__(self):
        # Start processing.
        try:
            self.context.walker.start_processes()

            # Collect Entry objects from the Walker.
            self.context.processing.loop()

            # Finalize and put out the result if --sort or --exec-batch is involved.
            self.context.processing.finalize()

            yield from self.context.processing

        except KeyboardInterrupt:
            # Stop all processes immediately.
            self.context.stop()
            raise

        self.context.close()
        self.context.walker.close()
        self.context.processing.close()
