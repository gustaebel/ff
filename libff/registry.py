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

import os
import binascii
import textwrap
import importlib.util

from . import NOTSET, EX_USAGE, EX_BAD_PLUGIN, EX_BAD_ATTRIBUTE, NoData, \
    Attribute, BaseClass
from .type import Type
from .table import Table
from .plugin import Plugin


class Registry(BaseClass):
    """Registry class that keeps track of all installed plugins and the
       attributes they provide.
    """

    PLUGIN_DIR_BUILTIN = os.path.join(os.path.dirname(__file__), "builtin")
    PLUGIN_DIR_CONTRIB = "/usr/lib/ff"
    PLUGIN_DIR_USER = os.path.expanduser("~/.ff")

    registered_types = set()
    registered_plugins = {}

    def __init__(self, context):
        super().__init__(context)

        self.plugins = {}
        self.attributes = {}

        self.optimize_for_caching_plugins = False

        self.load_plugins()

    def iter_plugin_dirs(self):
        """Yield possible plugin directories.
        """
        yield "builtin", self.PLUGIN_DIR_BUILTIN
        if __debug__:
            yield "contrib", os.path.join(os.path.dirname(__file__), "../plugins")
        else:
            yield "contrib", self.PLUGIN_DIR_CONTRIB
        plugin_dirs = os.environ.get("FF_PLUGIN_DIRS")
        if plugin_dirs is not None:
            for directory in plugin_dirs.split(os.pathsep):
                if directory:
                    yield "system", directory
        yield "user", self.PLUGIN_DIR_USER

    def load_plugin(self, module_name, module_source, module_path):
        """Load the plugin code from path into a python module. After that
           inpect the module namespace to find the Type and Plugin classes.
        """
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.inspect_namespace(module_source, module_path, module)

    def inspect_namespace(self, module_source, module_path, module):
        """Go through the objects in a module namespace and collect Type and
           Plugin classes.
        """
        # pylint:disable=unidiomatic-typecheck
        for obj in vars(module).values():
            if type(obj) is not type:
                continue

            if issubclass(obj, Type) and obj is not Type:
                self.register_type(obj)

            elif issubclass(obj, Plugin) and obj is not Plugin:
                self.register_plugin(module_source, module_path, obj)

    def register_type(self, type_cls):
        """Register Type classes.
        """
        self.registered_types.add(type_cls)

    def register_plugin(self, module_source, module_path, plugin_cls):
        """Register and initialize Plugin classes.
        """
        if plugin_cls.name in self.registered_plugins:
            self.context.warning(f"Skipping already loaded plugin {plugin_cls.name!r} "\
                    f"from {module_path!r}")
            return

        # Create a checksum of the plugin module file as a tag for the cache
        # database.
        with open(module_path, "rb") as fobj:
            module_tag = binascii.crc32(fobj.read())

        plugin_cls.initialize(module_source, module_path, module_tag)

        self.registered_plugins[plugin_cls.name] = plugin_cls

        for name, type_cls, _ in plugin_cls.attributes:
            if not issubclass(type_cls, tuple(self.registered_types)):
                self.context.exception(f"plugin {plugin_cls.name!r} attribute {name!r} uses "\
                        f"invalid type {type_cls!r}", EX_BAD_PLUGIN)

    def load_plugins(self):
        """Load all available plugins from the designated plugin directories.
        """
        for source, directory in self.iter_plugin_dirs():
            try:
                with os.scandir(directory) as direntries:
                    for direntry in direntries:
                        if not direntry.is_file() or not direntry.name.endswith(".py") or \
                                direntry.name.startswith("_"):
                            continue

                        # pylint:disable=broad-except
                        try:
                            self.load_plugin(direntry.name[:-3], source, direntry.path)
                        except Exception:
                            self.context.exception(f"Plugin file {direntry.path!r} failed to load",
                                    EX_BAD_PLUGIN)

            except OSError:
                continue

        # Sort file attributes first.
        for name, plugin_cls in sorted(self.registered_plugins.items(),
                key=lambda t: "" if t[0] == "file" else t[0]):
            for attr, type_cls, _ in sorted(plugin_cls.attributes):
                self.attributes[Attribute(name, attr)] = type_cls

    def init_plugin(self, name):
        """Setup the Plugin class for later use (register it in the cache and
           call the setup() method).
        """
        # pylint:disable=broad-except
        plugin_cls = self.registered_plugins[name]
        try:
            if plugin_cls.use_cache:
                self.cache.register_plugin(plugin_cls)
            self.plugins[name] = plugin_cls()
        except ImportError as exc:
            self.context.error(f"Unable to setup plugin {name!r}: {exc}", EX_BAD_PLUGIN)
        except Exception:
            self.context.exception(f"Unable to setup plugin {name!r}", EX_BAD_PLUGIN)

        if plugin_cls.use_cache:
            # See FilesystemWalker for an explanation.
            self.optimize_for_caching_plugins = True

    def parse_attribute(self, name):
        """Break down an attribute into plugin name and attribute name. If the
           attribute is without a plugin name guess which one it is.
        """
        try:
            attribute = Attribute(*name.split(".", 1))
        except TypeError:
            plugin_names = self.get_plugin_for_attribute(name)

            # The file plugin always has precedence. This way we avoid
            # essential attributes being overwritten by rogue plugins.
            if "file" in plugin_names:
                attribute = Attribute("file", name)

            elif len(plugin_names) == 1:
                # The attribute is provided by exactly one plugin.
                attribute = Attribute(plugin_names.pop(), name)

            elif not plugin_names:
                # We could not find the attribute in any of the plugins.
                self.context.error(f"No plugin found for attribute {name!r}", EX_BAD_ATTRIBUTE)

            else:
                # There is more than one plugin providing this attribute, we
                # cannot continue.
                self.context.error(f"Attribute {name!r} is ambiguous (choose between " \
                        f"{', '.join(f'{plugin_name}.{name}' for plugin_name in plugin_names)})",
                        EX_BAD_ATTRIBUTE)

        return attribute

    def setup_attribute(self, attribute):
        """Setup an attribute for later use, i.e. setup the plugin that
           provides it if it has not been setup already.
        """
        attribute = self.parse_attribute(attribute)

        if attribute.plugin not in self.registered_plugins:
            self.context.error(f"No such plugin {attribute.plugin!r}", EX_BAD_ATTRIBUTE)

        if attribute.plugin not in self.plugins:
            self.init_plugin(attribute.plugin)

        return attribute

    def get_data(self, entry, plugin):
        """Return all attribute values that are associated with entry.
        """
        # pylint:disable=broad-except
        plugin = self.plugins[plugin]
        try:
            return self.get_data_from_plugin(entry, plugin)
        except NoData:
            return {}
        except NotImplementedError:
            self.context.exception(f"Plugin {plugin.name!r} is not completely implemented",
                    EX_BAD_PLUGIN)
        except Exception:
            self.context.exception(f"Plugin {plugin.name!r} had an unhandled exception",
                    EX_BAD_PLUGIN)

    def get_data_from_plugin(self, entry, plugin):
        """Let the plugin process the entry.
        """
        if plugin.can_handle(entry):
            if plugin.use_cache:
                data = self.cache.get(plugin, entry.abspath, entry.time)
                if data is NOTSET:
                    if __debug__:
                        self.context.debug("cache",
                                f"Cache {plugin.name!r} data for {entry.path!r}")
                    # There is no cached result for this entry, so we ask
                    # the plugin for the data. If the plugin fails to
                    # process this entry, we cache an empty data dict, so
                    # that we know we don't have to try again in the
                    # future.
                    data = dict(plugin.process(entry))
                    self.cache.set(plugin, entry.abspath, entry.time, data)
            else:
                data = dict(plugin.process(entry))
        else:
            data = {}

        if __debug__:
            for key, value in data.items():
                type_cls = self.get_attribute_type(Attribute(plugin.name, key))
                if not type_cls.check_type(value):
                    self.context.error(
                        f"plugin {plugin.name!r} produced value {key}={value!r} that is "\
                        f"not of type {type_cls.name!r}", EX_BAD_PLUGIN)

        return data

    def get_attribute(self, entry, attribute):
        """Return the attribute value that is associated with entry.
        """
        if attribute.plugin == "file":
            # Use a shortcut for attributes from the 'file' plugin. Fetch the
            # value directly from the Entry object instead of going through the
            # plugin.
            try:
                return entry.get_attribute(attribute.name)
            except KeyError:
                # Not all attributes are provided by the Entry object, e.g.
                # 'class'.
                pass

        data = self.get_data(entry, attribute.plugin)
        return data[attribute.name]

    def get_attribute_and_type(self, entry, attribute):
        """Return the attribute value and its type.
        """
        return self.get_attribute(entry, attribute), self.attributes[attribute]

    def get_attribute_type(self, attribute):
        """Return the Type associated with the attribute.
        """
        try:
            return self.attributes[attribute]
        except KeyError:
            self.context.error(f"{attribute.plugin!r} plugin has no attribute {attribute.name!r}",
                    EX_BAD_ATTRIBUTE)

    def get_file_attributes(self):
        """Get all attributes associated with the 'file' plugin.
        """
        for attribute in self.attributes:
            if attribute.plugin == "file":
                yield attribute.name

    def get_plugin_for_attribute(self, name):
        """Return a set of possible plugin names for an attribute name.
        """
        return set(attribute.plugin for attribute in self.attributes if attribute.name == name)

    def print_help(self, name):
        """Print the help for a specific plugin.
        """
        try:
            plugin = self.registered_plugins[name]
        except KeyError:
            self.context.error(f"Plugin {name!r} not found", EX_USAGE)

        print(f"Plugin: {name}")
        print()
        if plugin.__doc__:
            print(textwrap.dedent(plugin.__doc__))
        self.print_attributes(name, with_help=True)

    def print_attributes(self, name=None, with_operators=False, with_help=False):
        """Print a table of all available attributes.
        """
        if name is None:
            plugins = list(self.registered_plugins.values())
        else:
            plugins = [self.registered_plugins[name]]

        plugins.sort(key=lambda p: "" if p.name == "file" else p.name)

        header = ["Name", "Type"]
        if with_operators:
            header.append("Operators")
        if with_help:
            header.append("Help")

        table = Table(header, wrap_last_column=with_help)
        for plugin in plugins:
            for attr, type_cls, _help in plugin.attributes:
                row = [f"{plugin.name}.{attr}", type_cls.name]
                if with_operators:
                    row.append("  ".join(type_cls.operators))
                if with_help:
                    row.append(_help)
                table.add(row)
        table.print()

    def print_plugins(self):
        """Print a table of available plugins.
        """
        table = Table(("Name", "Source", "Path"))
        for name, plugin in sorted(self.registered_plugins.items()):
            table.add((name, plugin.module_source, plugin.module_path))
        table.print()

    def print_types(self):
        """Print a table of available types.
        """
        table = Table(("Name", "Operators", "Count", "Help"), wrap_last_column=True)
        for type_cls in sorted(self.registered_types, key=lambda t: t.name):
            table.add([type_cls.name, "  ".join(type_cls.operators), type_cls.count.name.lower(),
                type_cls.__doc__])
        table.print()
