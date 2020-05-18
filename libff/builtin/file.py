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

from libff.entry import Entry
from libff.plugin import *


class File(Plugin):
    """\
        All essential file attributes.
    """
    # This is basically a dummy plugin for the file namespace. Most attributes
    # are redirected directly to the Entry object in Registry.get_attribute().

    attributes = [
        ("path",    String,   "The full pathname of the file. It will be relative to the current "\
                              "working directory depending on the <directory> arguments that were "\
                              "given on the command line. This can be changed with the "\
                              "-a/--absolute path option."),
        ("root",    String,   "The start directory the file was found in."),
        ("relpath", String,   "The pathname of the file relative to the start directory."),
        ("dir",     String,   "The dirname portion of the file."),
        ("name",    String,   "The basename portion of the file"),
        ("ext",     String,   Entry.ext.__doc__),
        ("pathx",   String,   Entry.pathx.__doc__),
        ("namex",   String,   Entry.namex.__doc__),
        ("device",  Number,   Entry.device.__doc__),
        ("inode",   Number,   Entry.inode.__doc__),
        ("samedev", Boolean,  Entry.samedev.__doc__),
        ("depth",   Number,   Entry.depth.__doc__),
        ("type",    FileType, Entry.type.__doc__),
        ("exec",    Boolean,  Entry.exec.__doc__),
        ("size",    Size,     Entry.size.__doc__),
        ("mtime",   Time,     Entry.mtime.__doc__),
        ("ctime",   Time,     Entry.ctime.__doc__),
        ("atime",   Time,     Entry.atime.__doc__),
        ("time",    Time,     Entry.time.__doc__),
        ("mode",    Mode,     Entry.mode.__doc__),
        ("perm",    Mode,     Entry.perm.__doc__),
        ("links",   Number,   Entry.links.__doc__),
        ("uid",     Number,   Entry.uid.__doc__),
        ("gid",     Number,   Entry.gid.__doc__),
        ("user",    String,   Entry.user.__doc__),
        ("group",   String,   Entry.group.__doc__),
        ("hide",    Boolean,  "Whether the the name of the file starts with a dot."),
        ("hidden",  Boolean,  Entry.hidden.__doc__),
        ("empty",   Boolean,  Entry.empty.__doc__),
        ("link",    String,   "The target path of a symbolic link relative to its parent "\
                              "directory. Empty if the file is not a symbolic link."),
        ("target",  String,   "The full target path of a symbolic link. Empty if the file is not "\
                              "a symbolic link."),
        ("broken",  Boolean,  "Whether the target of a symbolic link points to a file that does "\
                              "not exist."),
        ("mime",    String,   Entry.mime.__doc__),
        ("class",   String,   Entry.class_.__doc__),
        ("text",    Boolean,  Entry.text.__doc__)
    ]

    def can_handle(self, entry):
        return True

    def process(self, entry):
        return {}
