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

import collections


class _Attribute(collections.namedtuple("Attribute", "plugin name")):
    """An Attribute namedtuple that contains the plugin name and the attribute name.
    """

    def __new__(cls, plugin:str, name:str, fullname:str, alias:str):
        self = super().__new__(cls, plugin, name)
        self.fullname:str = fullname
        self.alias:str = alias if alias is not None else fullname
        return self

    def __str__(self):
        # pylint:disable=no-member
        return self.alias

def Attribute(plugin:str, name:str, alias:str=None) -> _Attribute:
    """Factory function to create Attribute objects.
    """
    # pylint:disable=invalid-name
    return _Attribute(plugin, name, f"{plugin}.{name}", alias)
