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
import functools
import importlib.util

from . import NoData, BaseClass, MissingImport
from .help import FullManPage, TypesManPage, PluginManPage, PluginsManPage, \
    AttributesManPage
from .type import Type
from .cache import NODATA, NOTSET
from .plugin import Speed, Plugin
from .attribute import Attribute
from .exceptions import UsageError, BadPluginError, BadAttributeError


class Registry(BaseClass):
    """Registry class that keeps track of all installed plugins and the attributes they provide.
    """
    # pylint:disable=too-many-public-methods

    PLUGIN_DIR_BUILTIN = os.path.join(os.path.dirname(__file__), "builtin")
    PLUGIN_DIR_CONTRIB = "/usr/lib/ff"
    PLUGIN_DIR_USER = os.path.expanduser("~/.ff")

    registered_types = set()
    registered_plugins = {}

    plugins = {}
    attributes = {}

    def __init__(self, context):
        super().__init__(context)

        self.optimize_for_slow_plugins = False

        with self.context.global_lock:
            if not self.registered_plugins:
                self.load_plugins()

    def iter_plugin_dirs(self):
        """Yield possible plugin directories.
        """
        yield "builtin", self.PLUGIN_DIR_BUILTIN

        # Return different plugin directories depending on whether we are in the git working tree.
        dirname = os.path.dirname(__file__)
        git_dir = os.path.join(dirname, "../.git")
        plugin_dir = os.path.join(dirname, "../plugins")
        if __debug__ and os.path.isdir(git_dir) and os.path.isdir(plugin_dir):
            yield "contrib", os.path.realpath(plugin_dir)
        else:
            yield "contrib", self.PLUGIN_DIR_CONTRIB

        plugin_dirs = os.environ.get("FF_PLUGIN_DIRS")
        if plugin_dirs is not None:
            for directory in plugin_dirs.split(os.pathsep):
                if directory:
                    yield "system", directory

        yield "user", self.PLUGIN_DIR_USER

    def load_plugin(self, name, source, path):
        """Load the plugin code from path into a python module. After that inpect the module
           namespace to find the Type and Plugin classes.
        """
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.inspect_namespace(source, path, module)

    def inspect_namespace(self, source, path, module):
        """Go through the objects in a module namespace and collect Type and Plugin classes.
        """
        # pylint:disable=unidiomatic-typecheck
        for obj in vars(module).values():
            if type(obj) is not type:
                continue

            if issubclass(obj, Type) and obj is not Type:
                self.register_type(obj)

            elif issubclass(obj, Plugin) and obj is not Plugin:
                self.register_plugin(source, path, obj)

    def register_type(self, type_cls):
        """Register Type classes.
        """
        self.registered_types.add(type_cls)

    def register_plugin(self, source, path, plugin_cls):
        """Register and initialize Plugin classes.
        """
        if plugin_cls.name in self.registered_plugins:
            self.logger.warning(f"Skipping already loaded plugin {plugin_cls.name!r} "\
                    f"from {path!r}")
            return

        plugin_cls.initialize(self.logger, source, path)

        self.registered_plugins[plugin_cls.name] = plugin_cls

        for name, type_cls, _ in plugin_cls.attributes:
            if not issubclass(type_cls, tuple(self.registered_types)):
                raise BadPluginError.from_exception(f"plugin {plugin_cls.name!r} attribute "\
                        f"{name!r} uses invalid type {type_cls!r}")

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

                        try:
                            self.load_plugin(direntry.name[:-3], source, direntry.path)
                        except Exception as exc:
                            raise BadPluginError.from_exception(
                                    f"Plugin file {direntry.path!r} failed to load") from exc

            except OSError:
                continue

        # Sort file attributes first.
        for name, plugin_cls in sorted(self.registered_plugins.items(),
                key=lambda t: "" if t[0] == "file" else t[0]):
            for attr, type_cls, _ in sorted(plugin_cls.attributes):
                self.attributes[Attribute(name, attr)] = type_cls

    def init_plugin(self, name):
        """Setup the Plugin class for later use (register it in the cache and call the setup()
           method).
        """
        # pylint:disable=broad-except
        plugin_cls = self.registered_plugins[name]
        try:
            if plugin_cls.use_cache:
                self.cache.register_plugin(plugin_cls)
            self.plugins[name] = plugin_cls()
        except MissingImport as exc:
            raise BadPluginError(f"Plugin {name!r} needs the following module: {exc.module!r}") \
                    from exc
        except Exception as exc:
            raise BadPluginError.from_exception(f"Unable to setup plugin {name!r}") from exc

        if plugin_cls.speed is Speed.SLOW:
            # See FilesystemWalker for an explanation.
            self.optimize_for_slow_plugins = True

    def parse_attribute(self, name):
        """Break down an attribute into plugin name and attribute name. If the attribute is without
           a plugin name guess which one it is.
        """
        try:
            attribute = Attribute(*name.split(".", 1))
        except TypeError as exc:
            plugin_names = self.get_plugin_for_attribute(name)

            # The file plugin always has precedence. This way we avoid
            # essential attributes being overwritten by rogue plugins.
            if "file" in plugin_names:
                attribute = Attribute("file", name, name)

            elif len(plugin_names) == 1:
                # The attribute is provided by exactly one plugin.
                attribute = Attribute(plugin_names.pop(), name, name)

            elif not plugin_names:
                # We could not find the attribute in any of the plugins.
                raise BadAttributeError(f"No plugin found for attribute {name!r}") from exc

            else:
                # There is more than one plugin providing this attribute, we
                # cannot continue.
                raise BadAttributeError(f"Attribute {name!r} is ambiguous (choose between " \
                        f"{', '.join(f'{plugin_name}.{name}' for plugin_name in plugin_names)})") \
                        from exc

        return attribute

    def setup_attribute(self, attribute):
        """Setup an attribute for later use, i.e. setup the plugin that provides it if it has not
           been setup already.
        """
        attribute = self.parse_attribute(attribute)

        if attribute.plugin not in self.registered_plugins:
            raise BadAttributeError(f"No such plugin {attribute.plugin!r}")

        with self.context.global_lock:
            if attribute.plugin not in self.plugins:
                self.init_plugin(attribute.plugin)

        return attribute

    @functools.lru_cache(maxsize=128)
    def get_data(self, entry, plugin):
        """Return all attribute values that are associated with entry.
        """
        plugin = self.plugins[plugin]
        try:
            return self.get_data_from_plugin(entry, plugin)
        except NoData:
            return {}
        except NotImplementedError as exc:
            raise BadPluginError.from_exception(
                    f"Plugin {plugin.name!r} is not completely implemented") from exc
        except Exception as exc:
            raise BadPluginError.from_exception(
                    f"Plugin {plugin.name!r} had an unhandled exception") from exc

    def get_data_from_plugin(self, entry, plugin):
        """Let the plugin process the entry.
        """
        data = {}

        if plugin.can_handle(entry):
            if plugin.use_cache:
                tag = plugin.get_entry_cache_tag(entry)
                cached = self.cache.get(plugin, entry.abspath, tag)
                if cached is NOTSET:
                    # There is no cached result for this entry, so we ask the plugin for the data.
                    # Even if the plugin fails to process this entry, we cache the return value, so
                    # that we know we don't have to try again in the future.
                    if __debug__:
                        self.logger.debug("cache",
                                f"Cache {plugin.name!r} data for {entry.path!r}")

                    try:
                        cached = plugin.cache(entry)
                    except NoData:
                        # Do not bother to call process() below, we could not handle this entry.
                        cached = NODATA

                    self.cache.set(plugin, entry.abspath, tag, cached)

            else:
                cached = None

            if cached is not NODATA:
                data = dict(plugin.process(entry, cached))

        if __debug__:
            for key, value in data.items():
                type_cls = self.get_attribute_type(Attribute(plugin.name, key))
                if not type_cls.check_type(value):
                    raise BadPluginError(
                        f"plugin {plugin.name!r} produced value {key}={value!r} that is "\
                        f"not of type {type_cls.name!r}")

        return data

    def get_attribute(self, entry, attribute):
        """Return the attribute value that is associated with entry.
        """
        if attribute.plugin == "file":
            # Use a shortcut for attributes from the 'file' plugin. Fetch the value directly from
            # the Entry object instead of going through the plugin.
            return entry.get_attribute(attribute.name)

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
        except KeyError as exc:
            raise BadAttributeError(
                    f"{attribute.plugin!r} plugin has no attribute {attribute.name!r}") from exc

    def get_plugin_speed(self, attribute):
        """Return the speed score of the plugin associated with the attribute.
        """
        return self.plugins[attribute.plugin].speed.value

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

    def get_full_manpage(self):
        """Return the full help a.k.a. the manpage.
        """
        return FullManPage()

    def get_plugin_manpage(self, name):
        """Return the help for a specific plugin.
        """
        try:
            plugin = self.registered_plugins[name]
        except KeyError as exc:
            raise UsageError(f"Plugin {name!r} not found") from exc

        return PluginManPage(plugin)

    def get_attributes_manpage(self):
        """Print a table of all available attributes.
        """
        plugins = list(self.registered_plugins.values())
        plugins.sort(key=lambda p: "" if p.name == "file" else p.name)
        return AttributesManPage(plugins)

    def get_plugins_manpage(self):
        """Reutrn the help for all available plugins.
        """
        return PluginsManPage(sorted(self.registered_plugins.values(), key=lambda p: p.name))

    def get_types_manpage(self):
        """Return the help for available types.
        """
        return TypesManPage(sorted(self.registered_types, key=lambda t: t.name))
