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
import pstats
import cProfile

from libff import EX_OK, EX_USAGE, EX_PROCESS, EX_SUBPROCESS, Directory
from libff.walk import FilesystemWalker
from libff.cache import Cache, NullCache
from libff.entry import StartDirectory
from libff.field import ExecFields, SortFields, CountFields, OutputFields, \
    ExecBatchFields
from libff.filter import Matcher, Excluder
from libff.ignore import GitIgnore
from libff.parser import ParserError
from libff.context import Context
from libff.registry import Registry
from libff.arguments import parse_arguments
from libff.processing import ImmediateExecProcessing, \
    CollectiveExecProcessing, ImmediateConsoleProcessing, \
    CollectiveConsoleProcessing

if __name__ == "__main__":
    # Set up the Context object that is passed to all components.
    context = Context()

    # Parse command-line arguments.
    # Once we're on Python >=3.8 we can use context.args = (args := parse_arguments(context)).
    args = parse_arguments(context)
    context.args = args
    context.setup()

    # Setup the sqlite3 metadata cache.
    if args.cache is None:
        CacheClass = NullCache
    else:
        CacheClass = Cache
    cache = CacheClass(context)
    context.cache = cache

    # Register all types and metadata plugins.
    registry = Registry(context)
    context.registry = registry

    # Replace the special value "file" in -o/--output by a list of all file
    # attributes.
    if "file" in args.output:
        pos = args.output.index("file")
        args.output.pop(pos)
        args.output = args.output[:pos] + list(registry.get_file_attributes()) + args.output[pos:]

    # Turn all options that take fields as arguments in to Fields objects.
    args.output = OutputFields(context, args.output)
    if args.sort is not None:
        args.sort = SortFields(context, args.sort)
    if args.count is not None:
        args.count = CountFields(context, args.count)
    if args.exec is not None:
        args.exec = ExecFields(context, args.exec)
    if args.exec_batch is not None:
        args.exec_batch = ExecBatchFields(context, args.exec_batch)

    if args.list_attributes:
        registry.print_attributes(with_operators=True)
        raise SystemExit(EX_OK)

    elif args.list_plugins:
        registry.print_plugins()
        raise SystemExit(EX_OK)

    elif args.list_types:
        registry.print_types()
        raise SystemExit(EX_OK)

    elif args.help is not None:
        registry.print_help(args.help)
        raise SystemExit(EX_OK)

    try:
        # Setup the matcher from the command line arguments.
        matcher = Matcher(context, args.expressions)
        context.matcher = matcher
    except ParserError as exc:
        context.error(f"unable to parse expressions: {exc}", EX_USAGE)

    # Setup the excluder from the command line arguments.
    excluder = Excluder(context, args.exclude)
    context.excluder = excluder

    # Set up processing. There are two modes of operation: Either collect all
    # results and process them in their entirety, or process results
    # immediately as they come in.
    if args.sort or args.count or args.limit or args.exec_batch or args.json == "json":
        if args.exec or args.exec_batch:
            processing = CollectiveExecProcessing(context)
            context.processing = processing
        else:
            processing = CollectiveConsoleProcessing(context)
            context.processing = processing
    elif args.exec:
        processing = ImmediateExecProcessing(context)
        context.processing = processing
    else:
        processing = ImmediateConsoleProcessing(context)
        context.processing = processing

    # Set up the filesystem walker.
    walker = FilesystemWalker(context)
    context.walker = walker

    if __debug__:
        context.debug("info", f"Using {context.processing.__class__.__name__}.")

        # Show some debug output.
        context.debug("info", "Directories to search:")
        for directory in args.directories:
            context.debug("info",
                    f"    {directory if directory != '.' else os.path.abspath(directory)}")

        if not excluder.is_empty():
            context.debug("info", "Exclude Sequence:")
            for line in excluder.parser.format():
                context.debug("info", "  " + line)

        if not matcher.is_empty():
            context.debug("info", "Test Sequence:")
            for line in matcher.parser.format():
                context.debug("info", "  " + line)

    # Preload the in-queue with the path arguments.
    for path in args.directories:
        if args.absolute_path:
            path = os.path.abspath(path)

        if __debug__ and args.ignore_parent_ignorefiles:
            # Don't use ignore files from parent directories.
            ignores = []
        else:
            # Find ignore files in parent directories.
            if args.ignored:
                ignores = GitIgnore.from_directory(context, path)
            else:
                ignores = []

        walker.put([Directory(StartDirectory(args, path), "", ignores)])

    # Start processing.
    try:
        if __debug__ and args.profile:
            # Start profiling. No multiprocessing is involved, Walker.loop() is
            # run in the main thread.
            profiler = cProfile.Profile()
            profiler.enable()
            walker.loop(0)
        else:
            walker.start_processes()

        # Collect Entry objects from the Walker.
        processing.loop()

        # Finalize and put out the result if --sort or --exec-batch is
        # involved.
        processing.finalize()

        if __debug__ and args.profile:
            # Stop profiling and print the statistics.
            profiler.disable()
            stats = pstats.Stats(profiler, stream=sys.stderr)
            stats.sort_stats("cumulative")
            stats.print_stats(.1)

    except KeyboardInterrupt:
        # Stop all processes immediately.
        context.stop()
        if __debug__:
            raise
        else:
            raise SystemExit("keyboard interrupt")

    except BrokenPipeError:
        context.stop()

    context.close()
    walker.close()
    processing.close()

    if __debug__:
        hits = context.cache_hits.value
        misses = context.cache_misses.value
        if hits or misses:
            context.debug("cache", f"Cache stats: {hits} hits, {misses} misses")
        else:
            context.debug("cache", "Cache was not used")

    if context.exitcode == EX_SUBPROCESS:
        context.error("One or more --exec/--exec-batch commands had errors", EX_SUBPROCESS)
    elif context.exitcode == EX_PROCESS:
        context.error("One or more ff processes had unrecoverable errors! "\
                "Result is probably incomplete!", EX_PROCESS)
