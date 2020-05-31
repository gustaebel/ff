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
import queue
import shutil
import threading
import traceback
import collections
import multiprocessing

from .__version__ import __version__

__copyright__= f"""ff {__version__}
Copyright (C) 2020 Lars Gustäbel <https://github.com/gustaebel/ff>
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.

This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law."""


TIMEOUT = 0.01
MAX_CPU = multiprocessing.cpu_count()


class NoData(Exception):
    """Exception for when a plugin cannot process an entry.
    """

class MissingImport(Exception):
    """Exception for when a plugin cannot import a third party module.
    """
    def __init__(self, module):
        self.module = module
        super().__init__(module)


OUTPUT_WIDTH = shutil.get_terminal_size((100, 100))[0] - 2


Directory = collections.namedtuple("Directory", "start relpath ignore_paths")
Entries = collections.namedtuple("Entries", "parent entries")

class _Attribute(collections.namedtuple("Attribute", "plugin name alias")):
    """An Attribute namedtuple that contains the plugin name and the attribute
       name.
    """

    def __str__(self):
        return self.alias

    def fullname(self):
        """Return the full canonical name of the attribute.
        """
        return f"{self.plugin}.{self.name}"

    def __eq__(self, other):
        return self[:2] == other[:2]

    def __hash__(self):
        return hash(self[:2])

def Attribute(plugin, name, alias=None):
    """Factory function to create Attribute objects.
    """
    # pylint:disable=invalid-name
    if alias is None:
        alias = f"{plugin}.{name}"
    return _Attribute(plugin, name, alias)


class BaseClass:
    """This class can be used as the base for each class that depends on
       Context and access to args, registry, etc. It offers shortcuts to the
       each of these components as self.component instead of
       self.context.component without using properties. Not exactly a matter of
       life and death but nice nevertheless.
    """

    component_names = set(["args", "registry", "excluder", "matcher", "walker"])

    def __init__(self, context):
        self.context = context

    def __getattr__(self, name):
        try:
            attr = getattr(self.context, name)
        except AttributeError:
            raise AttributeError(f"{self.__class__.__name__} object has no attribute {name!r}")

        if name in self.component_names:
            setattr(self, name, attr)
        return attr


def join(part1, part2):
    """A simpler version of os.path.join() with a limited scope that is
       significantly faster.
    """
    if part1:
        return part1 + os.sep + part2
    else:
        return part2
