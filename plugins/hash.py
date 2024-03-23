# -----------------------------------------------------------------------
#
# ff - a tool for finding files in the filesystem
# Copyright (C) 2024 Lars Gustäbel <lars@gustaebel.de>
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

import hashlib

from libff.plugin import *


class _Hash(Plugin):

    speed = Speed.SLOW

    use_cache = True

    def can_handle(self, entry):
        return entry.is_file()

    def cache(self, entry):
        try:
            h = hashlib.new(self.name)
            with open(entry.path, "rb") as fobj:
                while buf := fobj.read(8192):
                    h.update(buf)
            return self.name, h.hexdigest()
        except (OSError, EOFError) as exc:
            raise NoData from exc

    def process(self, entry, cached):
        yield cached


for name in hashlib.algorithms_guaranteed:
    vars()[name] = type(name, (_Hash,),
                        {"__doc__": f"The \"{name}\" plugin provides the {name} hashsum of a file.",
                         "name": name,
                         "attributes": [(name, String, f"The {name} hashsum of a file.")]})
del _Hash
