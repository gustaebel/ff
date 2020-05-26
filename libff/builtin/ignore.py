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

        self.dirname_cache = {}
        self.ignore_cache = {}

    def can_handle(self, entry):
        return True

    def process(self, entry, cached):
        if entry.dirname not in self.dirname_cache:
            self.dirname_cache[entry.dirname] = GitIgnore.find_ignore_files(entry.dirname)

        ignores = []
        for dirname, name in self.dirname_cache[entry.dirname]:
            if (dirname, name) not in self.ignore_cache:
                self.ignore_cache[(dirname, name)] = GitIgnore(dirname, name)
            ignores.append(self.ignore_cache[(dirname, name)])

        yield "ignored", GitIgnore.match_all(ignores, entry.abspath, entry.name, entry.is_dir())
