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
import queue
import signal
import subprocess
import multiprocessing

from . import TIMEOUT, Entries, BaseClass, Directory, join
from .entry import Entry
from .ignore import GitIgnore
from .exceptions import EX_SUBPROCESS


class FilesystemWalker(BaseClass):
    """Walk through the directories of a filesystem using multiple processes,
       collect information about the entries that were found and process them
       accordingly.
    """

    def __init__(self, context):
        super().__init__(context)

        self.processes = []
        self.queue = multiprocessing.Queue()

    def close(self):
        """Close the FilesystemWalker and clean up.
        """
        for process in self.processes:
            process.join()

        self.queue.close()

    def put(self, chunk):
        """Put a chunk of objects in the queue for processing by the
           FilesystemWalker. Either these objects are Directory objects for
           searching or lists of arguments from an ImmediateExecProcessing
           processor to run as subprocesses in the context of the
           FilesystemWalker.
        """
        self.queue.put(chunk)

    def start_processes(self):
        """Start a pool of processes that walk through the filesystem.
        """
        # We set the processes daemon=True because this seems to make them more
        # reactive on KeyboardInterrupt.
        for index in range(self.args.jobs):
            process = multiprocessing.Process(target=self.loop, args=(index,))
            process.daemon = True
            process.start()
            self.processes.append(process)

    def loop(self, index):
        """Get arguments from the queue and process them until searching has
           finished.
        """
        # pylint:disable=too-many-branches,attribute-defined-outside-init
        if __debug__:
            self.index = index

        if not (__debug__ and self.args.profile):
            # When profiling, loop() runs in the main thread, so we have to
            # allow KeyboardInterrupt.
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            while not self.context.is_stopping():
                try:
                    objs = self.queue.get(timeout=TIMEOUT)
                except queue.Empty:
                    if self.context.barrier_wait():
                        break
                    else:
                        continue

                if isinstance(objs, Entries):
                    if __debug__:
                        self.logger.debug_proc(self.index,
                                f"got Entries object with {len(objs.entries)} entries "\
                                f"from {objs.parent.start.root}")

                    self.process_entries(*objs)

                elif isinstance(objs[0], Directory):
                    if __debug__:
                        self.logger.debug_proc(self.index, f"got {len(objs)} Directory entries")

                    for obj in objs:
                        self.process_directory(obj)

                else:
                    if __debug__:
                        self.logger.debug_proc(self.index, f"got {len(objs)} process arguments")

                    for obj in objs:
                        self.process_arguments(obj)

        except Exception:
            # Terminate all processes if an unexpected error occurs.
            self.context.stop()
            raise

        self.cache.close()

    def scan_directory(self, parent):
        """Scan the directory `parent` and produce a list of entries and the
           names of .*ignore files that were found.
        """
        entries = []
        ignore_paths = parent.ignore_paths.copy()

        try:
            with os.scandir(join(parent.start.root, parent.relpath)) as direntries:
                for direntry in direntries:
                    try:
                        status = direntry.stat(follow_symlinks=self.args.follow_symlinks)
                        entry = Entry(parent.start, join(parent.relpath, direntry.name),
                                status, ignore_paths)

                    except FileNotFoundError:
                        # Do not warn about files that have vanished.
                        pass
                    except OSError as exc:
                        self.logger.warning(exc)
                        continue

                    entries.append(entry)

                    if entry.name in GitIgnore.IGNORE_NAMES:
                        if __debug__:
                            self.logger.debug("walk", f"Found ignore file {entry.name!r} "\
                                    f"in {entry.dirname!r}")
                        # Please note that we take advantage of the side-effect,
                        # that we can still update the same ignore_paths list we
                        # already passed to a number of Entry objects earlier.
                        ignore_paths.append(entry.abspath)

        except FileNotFoundError:
            # Do not warn about directories that have vanished.
            pass
        except PermissionError:
            # Do not warn about directories that we are not allowed to enter.
            pass
        except OSError as exc:
            self.logger.warning(exc)

        return entries

    def process_directory(self, parent):
        """Scan the directory `parent` for entries, collect .*ignore files, and
           process the entries or distribute them to other FilesystemWalkers
           for processing.
        """
        entries = self.scan_directory(parent)
        if entries:
            self.process_entries(parent, entries)

    def process_entries(self, parent, entries):
        """Go through the list of entries and see which ones we have to ignore,
           and exclude, which ones match and will be taken to further
           processing and which directory entries to descend into.
        """
        search = []
        process = []

        try:
            while entries:
                entry = entries.pop(0)
                is_dir = entry.is_dir()

                if self.excluder.test(entry):
                    continue

                elif self.matcher.test(entry):
                    process.append(entry)

                if is_dir:
                    search.append(Directory(parent.start, entry.relpath, entry.ignore_paths))

                # If there are plugins in action that use the cache, that means
                # that processing entries may take more time than usual (except
                # when they are already cached). Here we share the load of this
                # process with another process that is currently idle.
                if self.registry.optimize_for_caching_plugins and \
                        self.context.idle_processes() / self.args.jobs > 0.25 and \
                        len(entries) > 10:
                    split = len(entries) // 2 + 1
                    self.queue.put(Entries(parent, entries[split:]))
                    entries = entries[:split]

        except OSError as exc:
            self.logger.warning(exc)

        if search:
            # Calculate a reasonable size for a chunk of Entry objects based on
            # the number of parallel jobs, use at least 10 and at most 100
            # entries to avoid unnecessary overhead.
            chunk_size = min(100, max(10, int(len(search) / self.args.jobs) + 1))

            for i in range(0, len(search), chunk_size):
                self.queue.put(search[i:i + chunk_size])

        if process:
            self.processing.process(process)

    def process_arguments(self, arguments):
        """Call a subprocess with a list of arguments and wait for its
           completion.
        """
        try:
            process = subprocess.run(arguments, check=False)
            if process.returncode != 0:
                self.context.set_exitcode(EX_SUBPROCESS)
        except OSError as exc:
            # Show an error, but don't kill this FilesystemWalker process.
            self.context.error(exc, None)
