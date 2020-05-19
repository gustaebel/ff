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

from libff.plugin import *


class Grep(Plugin):
    """Plugin that gives access to the lines of a text file.
    """

    use_cache = False
    attributes = [
        ("lines", ListOfStrings, "The lines of the file.")
    ]

    def can_handle(self, entry):
        return entry.text

    def process(self, entry):
        with open(entry.path) as lines:
            yield "lines", list(lines)
