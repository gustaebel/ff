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

import tarfile

from libff.plugin import *


class Tar(Plugin):
    """Extract information from tar archives.
    """

    use_cache = True
    attributes = [
        ("members", ListOfStrings, "The list of file names that are stored in a .tar archive.")
    ]

    extensions = (
            ".tar",
            ".tar.gz", ".taz", ".tgz", ".tpz",
            ".tar.bz2", ".tb2", ".tbz", ".tbz2", ".tz2",
            ".tar.lz", ".tar.lzma", ".tlz",
            ".tar.xz", ".txz")

    def can_handle(self, entry):
        return entry.name.endswith(self.extensions)

    def cache(self, entry):
        try:
            with tarfile.open(entry.path) as tar:
                return set(name for name in tar.getnames())
        except (OSError, EOFError):
            raise NoData

    def process(self, entry, cached):
        yield "members", cached
