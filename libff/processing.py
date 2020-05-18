#!/usr/bin/python3
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

import sys
import time
import queue
import threading
import subprocess
import multiprocessing

from . import TIMEOUT, EX_PROCESS, EX_SUBPROCESS, BaseClass
from .console import Console, JsonConsole, ColorConsole, JsonlConsole


class Parallel(BaseClass):
    """Implement a pool of threads each running a subprocess.
    """

    def __init__(self, context):
        super().__init__(context)

        self.stop_event = threading.Event()
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
        self.queue.put(None)
        for thread in self.threads:
            thread.join()

    def thread(self):
        """Loop over a queue and execute subprocesses.
        """
        while not self.stop_event.is_set():
            try:
                args = self.queue.get(timeout=TIMEOUT)
            except queue.Empty:
                continue

            if args is None:
                self.stop_event.set()
                break

            try:
                process = subprocess.run(args, check=False)
                if process.returncode != 0:
                    self.context.set_exitcode(EX_SUBPROCESS)
            except OSError as exc:
                self.context.error(exc, EX_SUBPROCESS)

    def add_job(self, entry):
        """Add a subprocess to the queue for an Entry object.
        """
        self.queue.put(self.args.exec.render(entry))


class BaseProcessing(BaseClass):
    """Base class for processing Entry objects.
    """

    def __init__(self, context):
        super().__init__(context)

        self.next_processes_check = time.time() + 10

    def check_for_failed_processes(self):
        """Check regularly if all processes are still active and allow an
           ordered shutdown even if processes terminated abnormally.
        """

        if time.time() >= self.next_processes_check:
            for index, process in enumerate(self.walker.processes):
                if not process.is_alive():
                    self.context.warning(f"process #{index} terminated abnormally")
                    self.context.set_exitcode(EX_PROCESS)
                    self.context.stop()
                    return True

            self.next_processes_check = time.time() + 10

        return False

    def process(self, entries):
        """Process a chunk of Entry objects.
        """
        raise NotImplementedError

    def loop(self):
        """Wait for the Walker processes to finish (while possibly collecting
           entries).
        """

    def finalize(self):
        """Process the collected list of Entry objects (in case this is a
           Processing class that collects entries first).
        """

    def close(self):
        """Allow doing some clean up.
        """


class ImmediateBaseProcessing(BaseProcessing):
    """Base class for Processing classes that will process entries
       without collecting them first.
    """
    # pylint:disable=abstract-method

    def loop(self):
        while not self.context.barrier_wait(1):
            if self.check_for_failed_processes():
                break

    def finalize(self):
        # If we don't actively wait here for the processes to terminate,
        # results will be lost. That is because when the main process exits,
        # all subprocesses terminate as well because they are daemon=True.
        self.walker.wait_processes()


class BaseConsoleProcessing(ImmediateBaseProcessing):
    """Processing base class for console output.
    """

    def __init__(self, context):
        super().__init__(context)

        if self.args.json == "json":
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


class ImmediateExecProcessing(ImmediateBaseProcessing):
    """Processing class for direct execution of --exec jobs.

       Ensure an even distribution of jobs to processes, therefore
       put only one Call in the queue at a time.
    """

    def process(self, entries):
        for entry in entries:
            self.walker.put([self.args.exec.render(entry)])


class ImmediateConsoleProcessing(BaseConsoleProcessing):
    """Processing class for direct output to the console.
    """


class CollectiveMixin(BaseProcessing):
    """Processing mixin class that collects all entries first and
       then does the processing afterwards.
    """

    def __init__(self, context):
        super().__init__(context)

        self.out_queue = multiprocessing.Queue()
        self.entries = []

    def process(self, entries):
        self.out_queue.put(entries)

    def loop(self):
        while True:
            try:
                self.entries += self.out_queue.get(timeout=TIMEOUT)
            except queue.Empty:
                if self.context.barrier_wait():
                    break
                else:
                    if self.check_for_failed_processes():
                        break

            # Exit prematurely if there are already enough entries to satisfy
            # the limit, unless sorting is enabled in which case we want to
            # collect all entries first, sort them and then print the first N
            # entries.
            if self.args.sort is None and self.args.limit is not None and \
                    len(self.entries) >= self.args.limit:
                self.context.stop()
                break

    def finalize(self):
        if self.args.sort is not None:
            self.entries.sort(key=self.args.sort.render, reverse=self.args.reverse)

    def close(self):
        self.out_queue.close()


class CollectiveConsoleProcessing(CollectiveMixin, BaseConsoleProcessing):
    """Processing class for collection and ordering of entries with output to
       the console afterwards.
    """

    def finalize(self):
        super().finalize()

        # If a limit is set, print only the first N entries.
        for entry in self.entries[:self.args.limit]:
            self.console.process(entry)


class CollectiveExecProcessing(CollectiveMixin, BaseProcessing):
    """Processing class for collective execution of --exec and --exec-batch
       jobs.
    """

    def finalize(self):
        super().finalize()

        if self.args.exec is not None:
            with Parallel(self.context) as parallel:
                for entry in self.entries[:self.args.limit]:
                    parallel.add_job(entry)

        elif self.args.exec_batch is not None:
            args = self.args.exec_batch.render(self.entries[:self.args.limit])

            try:
                process = subprocess.run(args, check=False)
                if process.returncode != 0:
                    self.context.set_exitcode(EX_SUBPROCESS)
            except OSError as exc:
                self.context.error(exc, EX_SUBPROCESS)

        else:
            raise AssertionError("wrong usage of CollectiveExecProcessing class")
