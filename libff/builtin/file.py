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

from libff.entry import Entry
from libff.plugin import *


class File(Plugin):
    """\
        All essential file attributes.
    """
    # This is basically a dummy plugin for the file namespace. Most attributes
    # are redirected directly to the Entry object in Registry.get_attribute().

    # Since 2.5 pylint warns about properties not having __doc__ attributes...
    # pylint:disable=no-member

    attributes = [
        ("path",    Path,     "The full pathname of the file. It will be relative to the current "\
                              "working directory depending on the <directory> arguments that were "\
                              "given on the command line. This can be changed with the "\
                              "-a/--absolute path option."),
        ("root",    Path,     "The start directory the file was found in."),
        ("relpath", Path,     "The pathname of the file relative to the start directory."),
        ("dir",     Path,     "The dirname portion of the file."),
        ("name",    Path,     "The basename portion of the file"),
        ("ext",     String,   Entry.ext.__doc__),
        ("pathx",   Path,     Entry.pathx.__doc__),
        ("namex",   Path,     Entry.namex.__doc__),
        ("mode",    Mode,     "The mode and permission bits of the file."),
        ("type",    FileType, "The file type: one of 'd'/'directory', 'f'/'file', 'l'/'symlink', "\
                              "'s'/'socket', 'p'/'pipe'/'fifo', 'char', 'block', 'door', 'port', "\
                              "'whiteout' or 'other'."),
        ("device",  Number,   Entry.device.__doc__),
        ("inode",   Number,   Entry.inode.__doc__),
        ("samedev", Boolean,  Entry.samedev.__doc__),
        ("depth",   Number,   Entry.depth.__doc__),
        ("exec",    Boolean,  Entry.exec.__doc__),
        ("size",    Size,     Entry.size.__doc__),
        ("mtime",   Time,     Entry.mtime.__doc__),
        ("ctime",   Time,     Entry.ctime.__doc__),
        ("atime",   Time,     Entry.atime.__doc__),
        ("time",    Time,     Entry.time.__doc__),
        ("perm",    Mode,     Entry.perm.__doc__),
        ("links",   Number,   Entry.links.__doc__),
        ("uid",     Number,   Entry.uid.__doc__),
        ("gid",     Number,   Entry.gid.__doc__),
        ("user",    String,   Entry.user.__doc__),
        ("group",   String,   Entry.group.__doc__),
        ("hide",    Boolean,  "Whether the the name of the file starts with a dot."),
        ("hidden",  Boolean,  Entry.hidden.__doc__),
        ("empty",   Boolean,  Entry.empty.__doc__),
        ("link",    Path,     "The target path of a symbolic link relative to its parent "\
                              "directory. Empty if the file is not a symbolic link."),
        ("target",  Path,     "The full target path of a symbolic link. Empty if the file is not "\
                              "a symbolic link."),
        ("broken",  Boolean,  "Whether the target of a symbolic link points to a file that does "\
                              "not exist."),
        ("text",    Boolean,  Entry.text.__doc__),
        ("mount",   Boolean,  Entry.mount.__doc__)
    ]

    def can_handle(self, entry):
        return True

    def process(self, entry, cached):
        return {}
