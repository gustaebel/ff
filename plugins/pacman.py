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
import subprocess

from libff.plugin import *


class Pacman(Plugin):
    """Extract information from Archlinux package files.
    """

    attributes = [
        ("installed", Boolean, "Whether the file belongs to an Arch Linux system package "\
                               "installed by the package manager pacman."),
        ("pkgname", String, "Name of package the file belongs to.")
    ]

    def setup(self):
        self.pkglist = {}
        self.filelist = set()
        for line in subprocess.Popen(["pacman", "-Ql"], stdout=subprocess.PIPE, text=True).stdout:
            line = line.strip()
            pkgname, path = line.split(None, 1)
            path = path.rstrip(os.sep)
            self.filelist.add(path)
            self.pkglist.setdefault(pkgname, set()).add(path)

    def can_handle(self, entry):
        return True

    def process(self, entry, cached):
        if entry.path in self.filelist:
            yield "installed", True
            for pkgname, filelist in self.pkglist.items():
                if entry.path in filelist:
                    yield "pkgname", pkgname
        else:
            yield "installed", False
