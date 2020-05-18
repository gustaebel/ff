# -----------------------------------------------------------------------
#
# ff - a simple, powerful and user-friendly alternative to 'find'.
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
import re
import sys

from libff.builtin import file, media
from libff.convert import time_formats
from libff.arguments import HelpFormatter, create_parser


class ManPageHelpFormatter(HelpFormatter):
    """Produce help output suitable for inclusion in the manpage.
    """

    def add_usage(self, *args):
        pass

    def add_text(self, *args):
        pass

    def start_section(self, heading):
        super().start_section("  " + heading)

    def _format_action(self, action):
        action_header = self._format_action_invocation(action)
        help_text = self._expand_help(action)

        parts = []
        parts.append(f"  {action_header}  \n")
        parts.append(f"      {help_text}\n")
        parts.append("\n")
        return self._join_parts(parts)


class ManPageUsageFormatter(HelpFormatter):

    def _format_usage(self, usage, actions, groups, prefix):
        return super()._format_usage(usage, actions, groups, "")



def include_help():
    fobj = io.StringIO()
    parser = create_parser(formatter_class=ManPageHelpFormatter)
    parser.print_help(file=fobj)
    return fobj.getvalue().splitlines()


def include_usage():
    fobj = io.StringIO()
    parser = create_parser(formatter_class=ManPageUsageFormatter)
    parser.print_usage(file=fobj)
    return fobj.getvalue().splitlines()


def include_plugin_help(name):
    for module in file, media:
        try:
            plugin = getattr(module, name.capitalize())
        except AttributeError:
            continue

    lines = []
    for attr, type, help in plugin.attributes:
        if name == "file":
            attribute = f"[file.]{attr}"
        else:
            attribute = f"{name}.{attr}"

        lines.append(f"  {attribute} :: {type.name}  ")
        lines.append(f"      {help.strip()}")
        lines.append("")

    return lines


path_in, path_out = sys.argv[1:]

with open(path_out, "w") as fobj:
    with open(path_in) as lines:
        for line in lines:
            line = line.rstrip()
            if line.startswith("__include_") and line.endswith("__"):
                name = line[10:-2]
                if name == "help":
                    for line in include_help():
                        print(line, file=fobj)
                elif name == "usage":
                    for line in include_usage():
                        print(line, file=fobj)
                elif name == "time_patterns":
                    for typ, fmt in time_formats:
                        def repl(m):
                            return m.group(1)*2
                        print("  - " + re.sub(r"%([YmdHMS])", repl, fmt) + "  ", file=fobj)
                else:
                    for line in include_plugin_help(name):
                        print(line, file=fobj)
            else:
                print(line, file=fobj)
