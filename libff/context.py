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

import threading
import subprocess
import multiprocessing
import multiprocessing.sharedctypes

from . import TIMEOUT
from .exceptions import EX_SUBPROCESS


class Context:
    """The Context class contains a global state and is globally accessible so that all components
       find all other components.
    """
    # pylint:disable=too-many-instance-attributes

    warnings_emitted = set()

    def __init__(self):
        # These are added later.
        self.args = None
        self.logger = None
        self.cache = None
        self.registry = None
        self.matcher = None
        self.excluder = None
        self.walker = None
        self.processing = None

        self.global_lock = None
        self.stop_queue = None
        self.barrier = None
        self.exitcode_object = None
        self.process_succeeded = None
        self.process_failed = None

        self.cache_hits = None
        self.cache_misses = None

    def setup(self):
        """Set up multiprocessing and inter-process communication.
        """
        self.global_lock = multiprocessing.Lock()

        # We use a Queue object to emulate a stop event, because multiprocessing.Event did not work
        # the way I expected it.
        self.stop_queue = multiprocessing.Queue(self.args.jobs)

        # Create a Barrier with the number of processes plus one for the main process.
        if __debug__ and self.args.profile:
            num_jobs = 1
        else:
            num_jobs = self.args.jobs + 1
        self.barrier = multiprocessing.Barrier(num_jobs)

        # The exitcode object provides a way for --exec and --exec-batch processes to feed back
        # errors to the main process.
        self.exitcode_object = multiprocessing.sharedctypes.RawValue("i", 0)
        self.process_succeeded = multiprocessing.Value("L")
        self.process_failed = multiprocessing.Value("L")

        # Provide a shared counter for cache hits and misses.
        self.cache_hits = multiprocessing.Value("L")
        self.cache_misses = multiprocessing.Value("L")

    def close(self):
        """Close the Context and clean up.
        """
        self.stop_queue.close()

    def set_exitcode(self, exitcode):
        """Set the shared resource 'exitcode' to the value that will be used as the main exit code.
        """
        self.exitcode_object.value = exitcode

    @property
    def exitcode(self):
        """The exitcode to use as the main exit code.
        """
        return self.exitcode_object.value

    def barrier_wait(self, timeout=TIMEOUT):
        """Wait for all processes to reach the Barrier. If all processes do that means that there
           is no more input and processing is finished.
        """
        try:
            self.barrier.wait(timeout)
        except threading.BrokenBarrierError:
            self.barrier.reset()
            return self.is_stopping()
        else:
            return True

    def idle_processes(self):
        """Return the number of idle processes, i.e. processes that are waiting for the barrier
           because there is nothing in the queue.
        """
        return self.barrier.n_waiting

    def is_stopping(self):
        """Return True all Processes are supposed to stop.
        """
        return self.stop_queue.qsize() > 0

    def stop(self):
        """Stop all processes immediately.
        """
        if not self.is_stopping():
            self.stop_queue.put(None)

    def run_exec_process(self, args):
        """Run a subprocess with the arguments from --exec. If the process fails, terminate the
           main loop and all other running subprocesses depending on the value of the --halt
           option.
        """
        exitcode = 1

        try:
            # pylint:disable=consider-using-with
            process = subprocess.Popen(args)

            if self.args.halt in ("never", "soon"):
                # Let this process finish regardless of the state of the main loop.
                exitcode = process.wait()

            elif self.args.halt == "now":
                # If the main loop is stopped, stop this process as well.
                while not self.is_stopping():
                    try:
                        exitcode = process.wait(0.1)
                        break
                    except subprocess.TimeoutExpired:
                        continue

                else:
                    process.terminate()

        except OSError as exc:
            self.logger.error(exc, None)

        if exitcode != 0:
            self.set_exitcode(EX_SUBPROCESS)
            with self.process_failed.get_lock():
                self.process_failed.value += 1

            # Stop the main loop (and all running subprocesses).
            if self.args.halt in ("soon", "now"):
                self.stop()

        else:
            with self.process_succeeded.get_lock():
                self.process_succeeded.value += 1
