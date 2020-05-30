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

from libff.ignore import GitIgnore
from libff.plugin import *


class Ignore(Plugin):
    """Plugin that shows whether files match patterns from .(git|fd|ff)ignore
       files.
    """

    attributes = [
        ("ignored", Boolean, "Whether the file matches patterns in a .(git|fd|ff)ignore file."),
        ("path", String, "The path to the ignore file that contained the matching pattern."),
    ]

    def __init__(self):
        super().__init__()

        self.ignore_cache = {}
        self.ignores_cache = {}

    def can_handle(self, entry):
        return True

    def get_ignores(self, paths):
        """Return a list of GitIgnore objects that apply to this particular
           directory.
        """
        paths = tuple(paths)

        # Construct a chain of GitIgnore objects one for each ignore file found
        # from the parent directories on down to the current directory.
        if paths not in self.ignores_cache:
            ignores = []
            for path in paths:
                # Reuse GitIgnore objects that have already been instantiated.
                try:
                    ignore = self.ignore_cache[path]
                except KeyError:
                    try:
                        ignore = GitIgnore(*os.path.split(path))
                    except OSError as exc:
                        self.logger.warning(exc, tag=f"ignore-{path}")
                        continue

                    self.ignore_cache[path] = ignore

                ignores.append(ignore)

            self.ignores_cache[paths] = ignores

        return self.ignores_cache[paths]

    def is_ignored(self, entry):
        """Return True if the Entry object matches a pattern in one of the
           ignore files that apply.
        """
        if entry.ignore_paths:
            ignores = self.get_ignores(entry.ignore_paths)
            return GitIgnore.match(ignores, entry.abspath, entry.name, entry.is_dir())
        else:
            return False, None

    def process(self, entry, cached):
        ignored, path = self.is_ignored(entry)
        return {"ignored": ignored, "path": path if path is not None else ""}
