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
import sys
import pstats
import cProfile

from . import BaseClass, __copyright__
from .walk import Directory, FilesystemWalker
from .cache import Cache, NullCache
from .entry import StartDirectory
from .field import ExecFields, SortFields, CountFields, OutputFields, \
    ExecBatchFields
from .filter import Matcher, Excluder
from .ignore import GitIgnore
from .logger import Logger
from .parser import ParserError
from .context import Context
from .registry import Registry
from .exceptions import EX_OK, EX_PROCESS, EX_SUBPROCESS, BaseError, \
    UsageError, ProcessError, SubprocessError
from .processing import ImmediateExecProcessing, CollectiveExecProcessing, \
    ImmediateConsoleProcessing, CollectiveConsoleProcessing

try:
    import cython
except ImportError:
    pass

class _Base(BaseClass):

    def __init__(self):
        super().__init__(Context())

    def setup_processing(self):
        """Set up the required Processing object.
        """
        raise NotImplementedError

    def setup_context(self, args, warnings):
        """Initialize the central Context object which will be passed to all components.
        """
        self.context.args = args
        self.context.setup()

        self.context.logger = Logger()
        if __debug__:
            self.context.logger.set_debug(args.debug)

        for warning in warnings:
            self.logger.warning(warning)

    def setup_components(self):
        """Set up all remaining components like the registry, the cache and so on.
        """
        # pylint:disable=too-many-branches

        args = self.context.args

        # Setup the sqlite3 metadata cache.
        if args.cache is None:
            CacheClass = NullCache
        else:
            CacheClass = Cache

        # Once we're on Python >=3.8 we can use context.cache = (cache := CacheClass(context)).
        cache = CacheClass(self.context)
        self.context.cache = cache

        # Register all types and metadata plugins.
        registry = Registry(self.context)
        self.context.registry = registry

        # Replace the special value "file" in -o/--output by a list of all file
        # attributes.
        if "file" in args.output:
            pos = args.output.index("file")
            args.output.pop(pos)
            args.output = args.output[:pos] + [a + ":n" for a in registry.get_file_attributes()] + \
                    args.output[pos:]

        # Turn all options that take fields as arguments in to Fields objects.
        args.output = OutputFields(self.context, args.output)
        if args.sort is not None:
            args.sort = SortFields(self.context, args.sort)
        if args.count is not None:
            args.count = CountFields(self.context, args.count)
        if args.exec is not None:
            args.exec = ExecFields(self.context, args.exec)
        if args.exec_batch is not None:
            args.exec_batch = ExecBatchFields(self.context, args.exec_batch)

        if args.action is not None:
            if args.action == "version":
                print(__copyright__)

            elif args.action == "clean":
                self.context.cache.clean()

            else:
                manpage = getattr(registry, f"get_{args.action}_manpage")()
                manpage.show()

            raise SystemExit(EX_OK)

        elif args.help is not None:
            registry.get_plugin_manpage(args.help).show()
            raise SystemExit(EX_OK)

        try:
            # Setup the matcher from the command line arguments.
            matcher = Matcher(self.context, args.tests)
            self.context.matcher = matcher
        except ParserError as exc:
            raise UsageError(f"unable to parse tests: {exc}")

        # Setup the excluder from the command line arguments.
        excluder = Excluder(self.context, args.exclude)
        self.context.excluder = excluder

    def setup_walker(self):
        """Set up the filesystem walker processes.
        """
        walker = FilesystemWalker(self.context)
        self.context.walker = walker

        if __debug__:
            self.logger.debug("info", "Directories to search:")

        # Preload the in-queue with the path arguments.
        for path in self.context.args.directories:
            if self.context.args.absolute_path:
                path = os.path.abspath(path)

            if self.context.args.no_parent_ignore:
                # Don't use ignore files from parent directories.
                ignores = []
            else:
                # Find ignore files in parent directories.
                if self.context.args.ignore:
                    ignores = GitIgnore.from_parent_directories(os.path.dirname(path))
                else:
                    ignores = []

            if __debug__:
                self.logger.debug("info",
                        f"  {path if path != '.' else os.path.abspath(path)}")
                for ignore in ignores:
                    self.logger.debug("info",
                            f"    found ignorefile in parent: {ignore}")

            walker.put([Directory(StartDirectory(self.context.args, path), "", ignores)])

    def show_debug_info(self):
        """Show general debug information and the tests to be performed.
        """
        self.logger.debug("info", f"Executable: {sys.argv[0]}.")

        try:
            if cython.compiled:
                self.logger.debug("info", "This is a cythonized build.")
        except NameError:
            pass

        self.logger.debug("info", f"Using {self.context.processing.__class__.__name__}.")

        if not self.context.excluder.is_empty():
            self.logger.debug("info", "Exclude Sequence:")
            for line in self.context.excluder.parser.format():
                self.logger.debug("info", "  " + line)

        if not self.context.matcher.is_empty():
            self.logger.debug("info", "Test Sequence:")
            for line in self.context.matcher.parser.format():
                self.logger.debug("info", "  " + line)


class Main(_Base):
    """The main entry point for the ff(1) script.
    """

    def __init__(self, args, warnings):
        super().__init__()

        self.setup_context(args, warnings)

        try:
            self.setup_components()
            self.setup_processing()
            if __debug__:
                self.show_debug_info()
            self.setup_walker()

        except BaseError as exc:
            self.handle_exception(exc)

    def loop(self):
        """Do all the processing and exit.
        """
        try:
            self.walk()
        except BaseError as exc:
            self.handle_exception(exc)

    def handle_exception(self, exc):
        """Print a BaseError exception using the correct formatting and exit.
        """
        if exc.traceback is not None:
            self.logger.exception(exc.message, exc.traceback, exc.exitcode)
        else:
            self.logger.error(exc.message, exc.exitcode)

    def setup_processing(self):
        args = self.context.args

        # Set up processing. There are two modes of operation: Either collect all results and
        # process them in their entirety, or process results immediately as they come in.
        if args.sort or args.count or args.limit or args.exec_batch or args.json == "json":
            if args.exec or args.exec_batch:
                self.context.processing = CollectiveExecProcessing(self.context)
            else:
                self.context.processing = CollectiveConsoleProcessing(self.context)
        elif args.exec:
            self.context.processing = ImmediateExecProcessing(self.context)
        else:
            self.context.processing = ImmediateConsoleProcessing(self.context)

    def walk(self):
        """Walk through the filesystem and process the results.
        """
        try:
            if __debug__ and self.context.args.profile:
                # Start profiling. No multiprocessing is involved, Walker.loop() is run in the main
                # thread.
                profiler = cProfile.Profile()
                profiler.enable()
                self.context.walker.loop(0)
            else:
                self.context.walker.start_processes()

            # Collect Entry objects from the Walker.
            self.context.processing.loop()

            # Finalize and put out the result if --sort or --exec-batch is involved.
            self.context.processing.finalize()

            if __debug__ and self.context.args.profile:
                # Stop profiling and print the statistics.
                profiler.disable()
                stats = pstats.Stats(profiler, stream=sys.stderr)
                stats.sort_stats("cumulative")
                stats.print_stats(.1)

        except KeyboardInterrupt:
            # Stop all processes immediately.
            self.context.stop()
            if __debug__:
                raise
            else:
                raise SystemExit("keyboard interrupt")

        except BrokenPipeError:
            self.context.stop()

        self.context.close()
        self.context.walker.close()
        self.context.processing.close()

        if __debug__:
            hits = self.context.cache_hits.value
            misses = self.context.cache_misses.value
            if hits or misses:
                self.logger.debug("cache", f"Cache stats: {hits} hits, {misses} misses")
            else:
                self.logger.debug("cache", "Cache was not used")

        if self.context.exitcode == EX_SUBPROCESS:
            raise SubprocessError("One or more --exec/--exec-batch commands had errors")
        elif self.context.exitcode == EX_PROCESS:
            raise ProcessError("One or more ff processes had unrecoverable errors! "\
                    "Result is probably incomplete!")
