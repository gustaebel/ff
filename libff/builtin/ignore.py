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
    ]

    def __init__(self):
        super().__init__()

        self.ignore_cache = {}

    def can_handle(self, entry):
        return True

    def get_ignores(self, dirname):
        """Return the list of GitIgnore objects that apply to this particular
           directory.
        """
        if dirname not in self.ignore_cache:
            ignores = None
            for name in GitIgnore.IGNORE_NAMES:
                path = os.path.join(dirname, name)

                if ignores is None:
                    if dirname == os.sep:
                        ignores = []
                    else:
                        ignores = self.get_ignores(os.path.dirname(dirname)).copy()

                if os.path.exists(path):
                    ignores.append(GitIgnore(dirname, name))

            self.ignore_cache[dirname] = ignores if ignores is not None else []

        return self.ignore_cache[dirname]

    def process(self, entry, cached):
        ignores = self.get_ignores(entry.dirname)
        return {"ignored": GitIgnore.match_all(ignores, entry.abspath, entry.name, entry.is_dir())}
