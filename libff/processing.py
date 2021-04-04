#!/usr/bin/python3
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

import sys
import json
import time
import queue
import threading
import subprocess
import collections
import multiprocessing

from . import TIMEOUT, BaseClass
from .type import Count
from .console import Console, JsonConsole, NullConsole, ColorConsole, \
    JsonlConsole
from .exceptions import EX_PROCESS, EX_SUBPROCESS, SubprocessError


class Parallel(BaseClass):
    """Implement a pool of threads each running a subprocess. Normally -x/--exec commands are
       issued directly in FilesystemWalker, but when entries are collated first (e.g. by --sort) we
       use this pool afterwards to call -x/--exec commands in parallel.
    """

    def __init__(self, context):
        super().__init__(context)

        self.queue = queue.Queue()

        self.threads = []
        for _ in range(self.args.jobs):
            thread = threading.Thread(target=self.thread)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for thread in self.threads:
            self.queue.put(None)
        for thread in self.threads:
            thread.join()

    def thread(self):
        """Loop over a queue and execute subprocesses.
        """
        while not self.context.is_stopping():
            try:
                args = self.queue.get(timeout=TIMEOUT)
            except queue.Empty:
                continue

            if args is None:
                break

            self.context.run_exec_process(args)

    def add_job(self, entry):
        """Add a subprocess to the queue for an Entry object.
        """
        try:
            self.queue.put(self.args.exec.render(entry))
        except KeyError:
            pass


class BaseProcessing(BaseClass):
    """Base class for processing Entry objects.
    """

    def __init__(self, context):
        super().__init__(context)

        self.next_processes_check = time.time() + 10

    def check_for_failed_processes(self):
        """Check regularly if all processes are still active and allow an ordered shutdown even if
           processes terminated abnormally. In this case, abnormal shutdown means that a process
           crashed in a way that it could not do the usual cleanup procedure (print a traceback,
           send stop signal to all other processes, set the exitcode). This may happen if one the
           process is terminated by a signal e.g. a segmentation fault.
        """

        if time.time() >= self.next_processes_check:
            for index, process in enumerate(self.walker.processes):
                if not process.is_alive():
                    self.logger.warning(f"process #{index} terminated abnormally")
                    self.context.set_exitcode(EX_PROCESS)
                    self.context.stop()
                    return True

            self.next_processes_check = time.time() + 10

        return False

    def processing_done(self, timeout=TIMEOUT):
        """Check if processing is done (because all processes wait on the barrier) or one or more
           processes failed unexpectedly.
        """
        return self.context.barrier_wait(timeout) or self.check_for_failed_processes()

    def process(self, entries):
        """Process a chunk of Entry objects.
        """
        raise NotImplementedError

    def loop(self):
        """Wait for the Walker processes to finish (while possibly collecting entries).
        """

    def finalize(self):
        """Process the collected list of Entry objects (in case this is a Processing class that
           collects entries first).
        """

    def close(self):
        """Allow doing some clean up.
        """


class ImmediateBaseProcessing(BaseProcessing):
    """Base class for Processing classes that will process entries without collecting them first.
    """
    # pylint:disable=abstract-method

    def loop(self):
        while not self.processing_done(1):
            pass


class BaseConsoleProcessing(ImmediateBaseProcessing):
    """Processing base class for console output.
    """

    def __init__(self, context):
        super().__init__(context)

        if self.args.count is not None:
            console_cls = NullConsole

        elif self.args.json == "json":
            console_cls = JsonConsole

        elif self.args.json == "jsonl":
            console_cls = JsonlConsole

        elif sys.stdout.isatty() if self.args.color == "auto" else self.args.color == "always":
            console_cls = ColorConsole

        else:
            console_cls = Console

        self.console = console_cls(self.context)

    def process(self, entries):
        for entry in entries:
            self.console.process(entry)

    def close(self):
        super().close()

        self.console.close()


class ImmediateExecProcessing(ImmediateBaseProcessing):
    """Processing class for direct execution of --exec jobs.

       Ensure an even distribution of jobs to processes, therefore put only one Call in the queue
       at a time.
    """

    def process(self, entries):
        for entry in entries:
            try:
                self.walker.put([self.args.exec.render(entry)])
            except KeyError:
                pass


class ImmediateConsoleProcessing(BaseConsoleProcessing):
    """Processing class for direct output to the console.
    """


class CollectiveMixin(BaseProcessing):
    """Processing mixin class that collects all entries first and then does the processing
       afterwards.
    """

    def __init__(self, context):
        super().__init__(context)

        self.out_queue = multiprocessing.Queue()
        self.entries = []
        self.count = collections.Counter()

    def process(self, entries):
        self.out_queue.put(entries)

    def entries_range(self):
        """Limit the list of entries according to the -l/--limit option.
        """
        if self.args.limit is None:
            return self.entries
        else:
            start, stop = self.args.limit
            return self.entries[start:stop]

    def loop(self):
        while True:
            try:
                entries = self.out_queue.get(timeout=TIMEOUT)
            except queue.Empty:
                if self.processing_done():
                    break
                else:
                    continue

            if self.args.count is not None:
                self.collect_count(entries)

            self.entries += entries

    def finalize(self):
        if self.args.sort is not None:
            self.entries.sort(key=self.args.sort.render, reverse=self.args.reverse)

    def close(self):
        super().close()

        self.out_queue.close()

        if self.args.count is not None:
            self.print_count()

    def collect_count(self, entries):
        """Collect value count.
        """
        for entry in entries:
            # Count the total number of entries found.
            self.count["_total"] += 1

            for field in self.args.count:
                try:
                    value = self.registry.get_attribute(entry, field.attribute)
                except KeyError:
                    continue

                if field.type.count is Count.TOTAL:
                    # Create a total of all the values.
                    self.count[field] += value

                elif field.type.count is Count.COUNT:
                    # Count each value individually.
                    self.count.setdefault(field, collections.Counter())[value] += 1

    def prepare_count(self):
        """Prepare the collected value count for printing.
        """
        # First prepare a plain dictionary structure suited for JSON output.
        count = {}
        for field, value in self.count.items():
            if isinstance(field, str):
                # E.g. "_total".
                count[field] = value

            else:
                name = str(field.attribute)

                if isinstance(value, dict):
                    # This is a dictionary with a by-value count.
                    count[name] = {}
                    for key, val in value.items():
                        # Format the key which is the counted value in this case, JSON objects
                        # allow only string keys anyway.
                        key = field.type.output(self.args, field.modifier, key)
                        count[name][key] = val

                else:
                    if field.modifier is not None:
                        # Format the value only in case there is a modifier, so that numbers won't
                        # turn out as strings.
                        value = field.type.output(self.args, field.modifier, value)
                    count[name] = value

        return count

    def print_count(self):
        """Print collected value count.
        """
        count = self.prepare_count()

        # Print the count to stdout.
        if self.args.json is not None:
            json.dump(count, sys.stdout, sort_keys=True)
            print()

        else:
            for key, value in sorted(count.items()):
                if isinstance(value, dict):
                    for k, v in sorted(value.items(),
                            key=lambda t: int(t[0]) if t[0].isdigit() else t[0]):
                        print(f"{key}[{k}]={v}")
                else:
                    print(f"{key}={value}")


class CollectiveConsoleProcessing(CollectiveMixin, BaseConsoleProcessing):
    """Processing class for collection and ordering of entries with output to the console
       afterwards.
    """

    def finalize(self):
        super().finalize()

        for entry in self.entries_range():
            self.console.process(entry)


class CollectiveExecProcessing(CollectiveMixin, BaseProcessing):
    """Processing class for collective execution of --exec and --exec-batch jobs.
    """

    def finalize(self):
        super().finalize()

        entries = self.entries_range()

        if not entries:
            return

        if self.args.exec is not None:
            with Parallel(self.context) as parallel:
                for entry in entries:
                    parallel.add_job(entry)

        elif self.args.exec_batch is not None:
            args = self.args.exec_batch.render(entries)

            try:
                process = subprocess.run(args, check=False)
                if process.returncode != 0:
                    self.context.set_exitcode(EX_SUBPROCESS)
            except OSError as exc:
                raise SubprocessError(str(exc)) from exc

        else:
            raise AssertionError("wrong usage of CollectiveExecProcessing class")


class ImmediateGenerator(ImmediateBaseProcessing):
    """Processing class that allows immediate iteration over the results.
    """

    def __init__(self, context):
        super().__init__(context)

        self.out_queue = multiprocessing.Queue()

    def loop(self):
        pass

    def finalize(self):
        pass

    def process(self, entries):
        self.out_queue.put(entries)

    def __iter__(self):
        while True:
            try:
                for entry in self.out_queue.get(timeout=TIMEOUT):
                    yield self.args.output.to_dict(entry)
            except queue.Empty:
                if self.processing_done():
                    break
                else:
                    continue


class CollectiveGenerator(ImmediateGenerator):
    """Processing class that allows iteration over the results after they have been postprocessed.
    """

    def __init__(self, context):
        super().__init__(context)

        self.entries = []

    def loop(self):
        while True:
            try:
                entries = self.out_queue.get(timeout=TIMEOUT)
            except queue.Empty:
                if self.processing_done():
                    break
                else:
                    continue

            self.entries += entries

    def finalize(self):
        super().finalize()

        self.entries.sort(key=self.args.sort.render, reverse=self.args.reverse)

    def __iter__(self):
        yield from (self.args.output.to_dict(entry) for entry in self.entries)
