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
import queue
import textwrap
import threading
import traceback
import multiprocessing
import multiprocessing.sharedctypes

from . import TIMEOUT, OUTPUT_WIDTH


class Context:
    """The Context class contains a global state and is globally accessible so that
       all components find all other components.
    """
    # pylint:disable=too-many-instance-attributes

    warnings_emitted = set()

    def __init__(self):
        # These are added later.
        self.args = None
        self.cache = None
        self.registry = None
        self.matcher = None
        self.excluder = None
        self.walker = None
        self.processing = None

        self.stop_queue = None
        self.barrier = None
        self.exitcode_object = None

        self.cache_hits = None
        self.cache_misses = None

    def setup(self):
        """Set up multiprocessing and inter-process communication.
        """
        # We use a Queue object to emulate a stop event, because
        # multiprocessing.Event did not work the way I expected it.
        self.stop_queue = multiprocessing.Queue(self.args.jobs)

        # Create a Barrier with the number of processes plus one for the main
        # process.
        if __debug__ and self.args.profile:
            num_jobs = 1
        else:
            num_jobs = self.args.jobs + 1
        self.barrier = multiprocessing.Barrier(num_jobs)

        # The exitcode object provides a way for --exec and --exec-batch
        # processes to feed back errors to the main process.
        self.exitcode_object = multiprocessing.sharedctypes.RawValue("i", 0)

        # Provide a shared counter for cache hits and misses.
        self.cache_hits = multiprocessing.Value("L")
        self.cache_misses = multiprocessing.Value("L")

    def close(self):
        """Close the Context and clean up.
        """
        self.stop_queue.close()

    def set_exitcode(self, exitcode):
        """Set the shared resource 'exitcode' to the value that will
           be used as the main exit code.
        """
        self.exitcode_object.value = exitcode

    @property
    def exitcode(self):
        """The exitcode to use as the main exit code.
        """
        return self.exitcode_object.value

    def barrier_wait(self, timeout=TIMEOUT):
        """Wait for all processes to reach the Barrier. If all processes do
           that means that there is no more input and processing is finished.
        """
        # Use a Barrier object to determine if all processes are currently
        # waiting for input, which means the operation is finished.
        try:
            self.barrier.wait(timeout)
        except threading.BrokenBarrierError:
            if self.is_stopping():
                # Stop immediately without waiting for all processes to finish.
                return True
            else:
                self.barrier.reset()
                return False
        else:
            return True

    def idle_processes(self):
        """Return the number of idle processes, i.e. processes that are waiting
           for the barrier because there is nothing in the queue.
        """
        return self.barrier.n_waiting

    def is_stopping(self):
        """Return True all Processes are supposed to stop.
        """
        try:
            self.stop_queue.get_nowait()
        except queue.Empty:
            return False
        else:
            return True

    def stop(self):
        """Stop all processes immediately.
        """
        for _ in range(self.args.jobs):
            self.stop_queue.put(None)

    def wrap(self, category, message):
        """Format and wrap the text of a message for output.
        """
        return textwrap.fill(category + ": " + str(message), width=OUTPUT_WIDTH,
                subsequent_indent=" " * (len(category) + 2))

    def warning(self, message, tag=None):
        """Print a warning to standard error output. If tag is not None hide
           the warning if there has already been another warning with that tag.
        """
        if tag is not None:
            if tag in self.warnings_emitted:
                return
            else:
                self.warnings_emitted.add(tag)

        print(self.wrap("WARNING", message), file=sys.stderr)

    def error(self, message, exitcode):
        """Print an error message to standard error output and exit.
        """
        print(self.wrap("ERROR", message), file=sys.stderr)
        if exitcode is not None:
            raise SystemExit(exitcode)

    def info(self, message):
        """Print an info message to standard error output.
        """
        print(self.wrap("INFO", message), file=sys.stderr)

    if __debug__:
        def debug(self, category, message):
            """Print a debug message to standard error output if --debug is
               switched on.
            """
            if self.args.debug is None or category in self.args.debug:
                print(f"DEBUG:{category}: {message}", file=sys.stderr)

        def debug_proc(self, index, message):
            """Print a debug message to standard error output if --debug-processes
               is switched on.
            """
            self.debug("mp", f"#{index:02d} {message}")

    def exception(self, message, exitcode=None):
        """Print an error message and a traceback to standard error output and
           exit.
        """
        print(self.wrap("INTERNAL", message + ":"), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if exitcode is not None:
            raise SystemExit(exitcode)
