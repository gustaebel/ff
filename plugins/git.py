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

import subprocess

from libff.plugin import *


class Git(Plugin):
    """Extract information from files that are inside a git(1) repository.
    """

    use_cache = True
    attributes = [
        ("tracked", Boolean, "Whether the file is tracked by a git repository.")
    ]

    def check_tracked(self, entry):
        """Return True if the Entry object is under version control.
        """
        return subprocess.run(["git", "ls-files", "--error-unmatch", entry.basename],
                cwd=entry.dirname, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def can_handle(self, entry):
        return entry.is_file() or entry.is_symlink()

    def cache(self, entry):
        try:
            return self.check_tracked(entry)
        except OSError:
            raise NoData

    def process(self, entry, cached):
        yield "tracked", cached
