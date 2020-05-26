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
import textwrap

from . import OUTPUT_WIDTH


class Logger:
    """Class that centralizes logging.
    """

    warnings_emitted = set()

    def __init__(self):
        self.debug_categories = None

    def set_debug(self, debug_categories):
        """Set the list of debug categories to display.
        """
        self.debug_categories = debug_categories

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
            if self.debug_categories is None or category in self.debug_categories:
                print(f"DEBUG:{category}: {message}", file=sys.stderr)

        def debug_proc(self, index, message):
            """Print a debug message to standard error output if --debug-processes
               is switched on.
            """
            self.debug("mp", f"#{index:02d} {message}")

    def exception(self, message, traceback, exitcode=None):
        """Print an error message and a traceback to standard error output and
           exit.
        """
        print(self.wrap("INTERNAL", message + ":"), file=sys.stderr)
        sys.stderr.write(traceback)
        if exitcode is not None:
            raise SystemExit(exitcode)
