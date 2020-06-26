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

import io
import os
import re
import datetime
import subprocess

from . import exceptions
from .convert import time_formats
from .arguments import HelpFormatter, create_parser
from .__version__ import __version__

bd = r"\fB"
it = r"\fI"
rs = r"\fR"
br = ".br"


class ManPageHelpFormatter(HelpFormatter):
    """Produce help output from an argparse.ArgumentParser suitable for the manpage.
    """

    def add_usage(self, usage, actions, groups, prefix=None):
        pass

    def add_text(self, text):
        pass

    def start_section(self, heading):
        super().start_section("    " + heading)

    def _format_action(self, action):
        action_header = self._format_action_invocation(action)
        help_text = self._expand_help(action)
        return f"\n    {action_header}  {help_text}\n\n"


class ManPageUsageFormatter(HelpFormatter):
    """Produce usage output from an argparse.ArgumentParser suitable for the manpage.
    """

    def _format_usage(self, usage, actions, groups, prefix):
        return super()._format_usage(usage, actions, groups, "")


class ManPage:
    """Programmatically create a manpage from text-format parts. The format is similar to that of
       txt2man(1).
    """

    name = "ff"
    title = "ff - Find files in the filesystem"
    section = 1
    description = None

    def __init__(self):
        self.lines = []
        self.render()

    def render(self):
        """Render the manpage.
        """
        self.start()

    def wrap(self, lines):
        """Process a list of lines and wrap paragraphs into single lines.
        """
        current_level = 0
        text = ""
        for line in lines:
            line = line.rstrip()

            level = len(line) - len(line.lstrip())

            if level < current_level or (current_level == 0 and level > 0) or "  " in line.lstrip():
                # Start a new paragraph if the line is empty, its indentation level is smaller than
                # before, if the previous line was a section header line, or the line contains the
                # start of a definition (identified by two consecutive spaces like txt2man(1)'s tag
                # list).
                if text:
                    yield text
                yield ""
                text = line

            else:
                # The line is a continuation line, append it to the current paragraph.
                if not text:
                    text = line
                else:
                    text += " " + line.lstrip()

            if line:
                current_level = level

        if text:
            yield text

    def include(self, name):
        """Replace an include statement.
        """
        if name == "help":
            fobj = io.StringIO()
            parser = create_parser(formatter_class=ManPageHelpFormatter)
            parser.print_help(file=fobj)
            self.parse_lines(fobj.getvalue().splitlines())

        elif name == "usage":
            fobj = io.StringIO()
            parser = create_parser(formatter_class=ManPageUsageFormatter)
            parser.print_usage(file=fobj)
            self.parse_lines(fobj.getvalue().splitlines())

        elif name == "time_patterns":
            lines = []
            for _, fmt in time_formats:
                lines.append("    ``" + re.sub(r"%([YmdHMS])", lambda m: m.group(1)*2, fmt) + "``")
                lines.append("")
            self.parse_lines(lines)

        elif name == "exit_codes":
            lines = []
            for obj in vars(exceptions).values():
                # pylint:disable=unidiomatic-typecheck
                if type(obj) is type and issubclass(obj, exceptions.BaseError) and \
                        obj is not exceptions.BaseError:
                    lines.append(f"    {obj.exitcode}  {obj.__doc__}")
            self.parse_lines(lines)

        else:
            raise ValueError(f"invalid include statement {name!r}")

    def parse_lines(self, lines):
        """Parse a set of lines from a manpage template.
        """
        lines = self.wrap(lines)

        for line in lines:
            line = line.rstrip()

            if line.lstrip().startswith("::"):
                # Evaluate an include marker.
                name = line.lstrip()[2:]
                self.include(name)

            elif re.match(r"^[A-Z ]+$", line):
                # Identify section headers (all caps starting at column 0).
                self.add_section(line)

            elif line.lstrip().startswith("$"):
                # Highlight an example shell command.
                self.lines.append(bd + line + rs)

            elif "  " in line.strip():
                # Format a definition, i.e. a word described with a text.
                key, value = line.strip().split("  ", 1)
                self.add_definition(key)
                self.add(value)
                self.lines.append(".PP")

            else:
                self.add(line)

    def process(self, string):
        """Process a string containing one of more lines and produce roff(7) output.
        """
        # Turn paragraphs into one long line each.
        string = "\n\n".join(" ".join(s.split()) for s in string.split("\n\n"))

        def replace(match):
            if match.group(1):
                # Make single-quoted strings italic. It should match "'s'" but not "file's".
                return f"'{it}{match.group(1)}{rs}'"
            elif match.group(2):
                # Make double backtick-quoted strings italic.
                return f"{it}{match.group(2)}{rs}"
            elif match.group(3):
                # Make backtick-quoted strings bold.
                return f"{bd}{match.group(3)}{rs}"
            elif match.group(4):
                # Highlight references to other manpages.
                return f"{bd}{match.group(4)}{rs}{match.group(5)}"
            else:
                # Highlight short and long options.
                return f"{bd}{match.group(6)}{rs}"

        string = re.sub(r"'(?!s\s)([^']+)'|"\
                        r"``([^`]+)``|"\
                        r"`([^`]+)`|"\
                        r"([a-z_-]+)(\(\d\))|"\
                        r"(?<![a-zA-Z])(\-[a-zA-Z]|\-\-[a-zA-Z-]+)", replace, string)

        # Escape dashes.
        return string.replace("-", "\\-")

    def add(self, line=""):
        """Add a line to the internal buffer.
        """
        self.lines.append(self.process(line))

    def add_header(self, name, section, title):
        """Add a manpage header.
        """
        self.lines.append(f".TH {name} {str(section)} \"{datetime.date.today()}\" "\
                    f"\"Version {__version__}\" \"{title}\"")
        self.lines.append(".nh") # turn off hyphenation

    def add_section(self, name):
        """Add a section.
        """
        self.lines.append(f".SH {name.upper()}")

    def add_subsection(self, name):
        """Add a subsection.
        """
        self.lines.append(f".SS {name}")

    def add_definition(self, name):
        """Add a definition.
        """
        self.lines.append(f".IP \"{bd}{name}{rs}\" 4")

    def start(self):
        """Initialize the manpage.
        """
        self.add_header(self.name, self.section, self.title)
        if self.description:
            self.add_section("Description")
            self.add(self.description)
            self.add()

    def render_attributes(self, plugin):
        """Render a list of attributes of a plugin.
        """
        for attr, type_cls, help_text in plugin.attributes:
            if plugin.name == "file":
                attribute = f"[file.]{attr}"
            else:
                attribute = f"{plugin.name}.{attr}"

            self.add_definition(attribute)
            self.add(f"Type: {type_cls.name}  ( {' '.join(type_cls.operators)} )")
            self.add(br)
            self.add(help_text)
            self.add()

        self.add()

    def render_plugin_detail(self, plugin, full=False):
        """Render the details of a specific plugin with or without author information.
        """
        names = ("name", "source", "path", "use_cache")
        if full:
            names += ("author", "email", "url")

        for name in names:
            if name == "use_cache":
                self.add(f"Uses cache: {'Yes' if plugin.use_cache else 'No'}")
            else:
                self.add(f"{name.capitalize()}: {getattr(plugin, name)}")
            self.add(br)

    def print(self):
        """Print the raw manpage to stdout.
        """
        print("\n".join(self.lines))

    def show(self):
        """Show the manpage using man(1) reading from stdin.
        """
        try:
            subprocess.run(["man", "-l", "-"], input="\n".join(self.lines), text=True, check=True)
        except FileNotFoundError:
            raise SystemExit("unable to call man(1), is it installed?")
        except subprocess.CalledProcessError:
            raise SystemExit("calling man(1) failed")


class FullManPage(ManPage):
    """Create the ff(1) manpage.
    """

    def render(self):
        super().render()

        with open(os.path.join(os.path.dirname(__file__), "manpage.template")) as lines:
            self.parse_lines(lines)


class AttributesManPage(ManPage):
    """Create the ff(7) manpage.
    """

    title = "ff Plugin Attributes Reference"
    section = 7
    description = """
        This is a list of all the attributes that are available. Attributes are provided by
        plugins. For more details on a specific plugin use 'ff --help <plugin>'. Please note that
        if you got this help text by using 'man 7 ff', the information you get is limited to the
        builtin plugins. Use 'ff --help-attributes' to get the full attribute list from all plugins
        that are available right now.
    """

    def __init__(self, plugins):
        self.plugins = plugins
        super().__init__()

    def render_plugin(self, plugin):
        """Render a plugin section.
        """
        self.add_section(f"{plugin.name} Plugin")
        self.add()
        self.add(plugin.__doc__)
        self.add()
        self.render_attributes(plugin)

    def render(self):
        super().render()

        for plugin in self.plugins:
            self.render_plugin(plugin)

        self.add_section("See Also")
        self.add("ff(1)")


class PluginManPage(ManPage):
    """Create a plugin manpage/helptext.
    """

    def __init__(self, plugin):
        self.plugin = plugin

        self.name = f"ff-{plugin.name}"
        self.title = f"{plugin.name} Plugin Reference"
        self.description = plugin.__doc__

        super().__init__()

    def render_plugin(self, plugin):
        """Render a plugin section.
        """
        self.add_section("Attributes")
        self.add()
        self.render_attributes(plugin)

    def render(self):
        super().render()

        self.render_plugin(self.plugin)
        self.add_section("Details")
        self.render_plugin_detail(self.plugin, full=True)

        self.add_section("See Also")
        self.add("ff(1), ff(7)")


class TypesManPage(ManPage):
    """Create manpage/helptext about types.
    """

    name = "ff-types"
    title = "ff Types Reference"
    section = 7
    description = """
        This is a list of all the types that are available. Furthermore, there is information about
        which test operators are supported by each type and if and how attributes of certain types
        will be counted ('ff --count').
    """

    def __init__(self, types):
        self.types = types
        super().__init__()

    def render_type(self, type_cls):
        """Render a type section.
        """
        self.add_section(f"{type_cls.name} Type")
        self.add(f"Name:  {type_cls.name}")
        self.add(br)
        self.add(f"Operators:  {' '.join(type_cls.operators)}")
        self.add(br)
        self.add(f"Count: {type_cls.count.name.lower()}")
        self.add()
        self.add(type_cls.__doc__)
        self.add()

    def render(self):
        super().render()

        for type_cls in self.types:
            self.render_type(type_cls)

        self.add_section("See Also")
        self.add("ff(1), ff(7)")


class PluginsManPage(ManPage):
    """Create manpage/helptext about all available plugins.
    """

    name = "ff-plugins"
    title = "ff Plugins Reference"
    section = 7
    description = """
        This is a list of all the plugins that are currently available. For more details on a
        specific plugin use 'ff --help <plugin>'.
    """

    def __init__(self, plugins):
        self.plugins = plugins
        super().__init__()

    def render_plugin(self, plugin):
        """Render a plugin section.
        """
        self.add_section(f"{plugin.name} Plugin")
        self.render_plugin_detail(plugin)
        self.add()
        self.add(plugin.__doc__)

    def render(self):
        super().render()

        for plugin in self.plugins:
            self.render_plugin(plugin)

        self.add_section("See Also")
        self.add("ff(1), ff(7)")
