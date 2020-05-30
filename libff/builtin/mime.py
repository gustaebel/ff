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

from libff.plugin import *


class Mime(Plugin):
    """Plugin that guesses the mime type and encoding using libmagic. Requires
       the 'file-magic' module.
    """

    use_cache = True

    attributes = [
        ("mime", String, "The full mime type of the file."),
        ("type", String, "The content type of the file, i.e. the first part of the mime type."),
        ("subtype", String, "The sub type of the file, i.e. the second part of the mime type."),
        ("encoding", String, "The encoding of the file."),
        ("name", String, "The full text description of the type of the file."),
    ]

    @classmethod
    def setup(cls):
        # pylint:disable=global-statement,import-outside-toplevel
        global magic
        try:
            import magic
        except ImportError:
            raise MissingImport("file-magic")

    def can_handle(self, entry):
        return entry.is_file()

    def cache(self, entry):
        # pylint:disable=undefined-variable
        try:
            detected = magic.detect_from_filename(entry.path)
            return detected.mime_type, detected.encoding, detected.name
        except (OSError, ValueError):
            raise NoData

    def process(self, entry, cached):
        mime, encoding, name = cached
        mime_parts = mime.split("/", 1)
        yield "mime", mime
        yield "type", mime_parts[0]
        yield "subtype", mime_parts[1]
        yield "encoding", encoding
        yield "name", name
