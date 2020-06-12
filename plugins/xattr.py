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
import sys

from libff.plugin import *


class Xattr(Plugin):
    """The "xattr" plugin provides access to a file's extended attributes.
    """

    attributes = [
        ("xattrs",  ListOfStrings, "A list of key=value pairs from the file's extended attributes.")
    ]

    def can_handle(self, entry):
        return entry.is_file()

    def process(self, entry, cached):
        xattrs = []
        try:
            for key in os.listxattr(entry.path):
                value = os.getxattr(entry.path, key)
                try:
                    value = os.fsdecode(value)
                except UnicodeDecodeError:
                    value = value.decode(sys.getfilesystemencoding(), "backslashreplace")
                xattrs.append(f"{key}={value}")
        except OSError:
            pass

        yield "xattrs", xattrs
