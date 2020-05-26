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

from . import NoData
from .type import *

__all__ = ["NoData", "Type", "String", "Number", "FileType", "Mode",
        "Size", "Time", "Duration", "Boolean", "ListOfStrings", "Plugin"]


class Plugin:
    """Base class for all plugins.
    """

    use_cache = False
    attributes = {}

    def __init_subclass__(cls):
        super().__init_subclass__()

        cls.name = cls.__name__.lower()

    @classmethod
    def initialize(cls, module_source, module_path, module_tag):
        """Initialize the Plugin class with basic information.
        """
        cls.module_source = module_source
        cls.module_path = module_path
        cls.module_tag = module_tag
        cls.sql_table_name = f"plugin_{cls.name}_{cls.module_tag}"

    def __init__(self):
        self.setup()

    def setup(self):
        """Setup the Plugin class. This is called once for every plugin, but
           only if it will be actually used. This is mainly supposed to be used
           for importing third-party modules that may or may not be installed
           on the system.
        """

    def can_handle(self, entry):
        """Return True if this plugin can handle this particular Entry object.
           This is supposed to reduce calls to process() and minimize the
           number of needlessly cached entries.
        """
        raise NotImplementedError

    def cache_tag(self, entry):
        """Return a value for the Entry object that if it changes causes the
           cached value to be invalidated. The default uses the modification
           time of the file. The returned value may have any type.
        """
        return entry.time

    def cache(self, entry):
        """Extract and prepare data from the Entry object and cache it. It is
           then passed on to the process() method. cache() is only called if
           use_cache is True. The data returned may have any type. Raise a
           NoData exception if the required data cannot be extracted. It will
           be the same as if None was returned.
        """
        # pylint:disable=unused-argument
        return None

    def process(self, entry, cached):
        """Generate key-value pairs or return a dict with the values that were
           "extracted" from the entry. The set of keys must match the
           ones from the attributes dict, but it is not necessary that all the
           keys actually have values. Raise a NoData exception or return an
           empty sequence if the plugin cannot extract the required attributes
           properly. The cached argument is only present when use_cache is True
           and contains the cached data that was prepared in the cache() method.
        """
        raise NotImplementedError
