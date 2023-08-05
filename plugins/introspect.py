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
import ast

from libff.plugin import *


class Elf(Plugin):
    """The "elf" plugin provides information extracted from ELF executable files. It requires the
       'pyelftools' module.
    """

    use_cache = True

    attributes = [
        ("sonames", ListOfStrings, "The names of all shared objects that are linked in this "\
                                   "executable file.")
    ]

    def setup(self):
        # pylint:disable=global-statement,import-outside-toplevel,global-variable-not-assigned
        global ELFFile, DynamicSection, ELFError
        try:
            from elftools.elf.dynamic import DynamicSection
            from elftools.elf.elffile import ELFFile
            from elftools.common.exceptions import ELFError
        except ImportError as exc:
            raise MissingImport("pyelftools") from exc

    def extract_sonames(self, path):
        """Yield the names of the shared objects required by an ELF executable.
        """
        # pylint:disable=undefined-variable
        try:
            with open(path, "rb") as fobj:
                elffile = ELFFile(fobj)
                for section in elffile.iter_sections():
                    if not isinstance(section, DynamicSection):
                        continue

                    for tag in section.iter_tags():
                        if tag.entry.d_tag == "DT_NEEDED":
                            yield tag.needed
        except (OSError, ELFError) as exc:
            raise NoData from exc

    def can_handle(self, entry):
        if entry.is_file():
            try:
                with open(entry.path, "rb") as fobj:
                    return fobj.read(4) == b"\x7fELF"
            except OSError:
                pass
        return False

    def cache(self, entry):
        return sorted(self.extract_sonames(entry.path))

    def process(self, entry, cached):
        yield "sonames", cached


class Shebang(Plugin):
    """The "shebang" plugin extracts the shebang line from a script, i.e. the first line of the
       file if it starts with '#!'.
    """

    attributes = [
        ("shebang", String, "The contents of the shebang line (#!).")
    ]

    @staticmethod
    def extract_shebang(path):
        """Extract the shebang line.
        """
        try:
            with open(path, "rb") as lines:
                for line in lines:
                    if line.startswith(b"#!"):
                        return line[2:].decode("ascii").rstrip()
        except (OSError, UnicodeDecodeError):
            pass

        return None

    def can_handle(self, entry):
        return entry.is_file()

    def process(self, entry, cached):
        shebang = self.extract_shebang(entry.path)
        if shebang is not None:
            yield "shebang", shebang


class Py(Plugin):
    """The "py" plugin provides information about Python scripts.
    """

    attributes = [
        ("imports", ListOfStrings, "A list of module and package names that are imported "\
                                   "in a Python file.")
    ]

    def parse_imports(self, entry):
        """Extract the names of modules and packages that a Python script imports.
        """
        # pylint:disable=unspecified-encoding
        with open(entry.path) as fobj:
            data = fobj.read()

        for node in ast.walk(ast.parse(data)):
            if isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    if node.level > 0:
                        parts = [node.module]
                        dirname = entry.dir
                        for _ in range(node.level):
                            dirname, basename = os.path.split(dirname)
                            parts.insert(0, basename)
                        yield ".".join(parts)
                    else:
                        yield node.module

            elif isinstance(node, ast.Import):
                yield node.names[0].name

    def can_handle(self, entry):
        if entry.ext.lower() == "py":
            return True
        shebang = Shebang.extract_shebang(entry.path)
        return shebang is not None and "python" in shebang

    def process(self, entry, cached):
        try:
            yield "imports", sorted(self.parse_imports(entry))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            raise NoData from exc
