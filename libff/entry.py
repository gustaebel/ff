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
import grp
import pwd
import stat

from . import join
from .type import Mode


class EntryAttributeError(AttributeError):
    """A subclass of AttributeError that provides the missing attribute name.
    """

    def __init__(self, name):
        self.name = name
        super().__init__(name)


class StartDirectory:
    """A basic version of an Entry that is used for start directories and is
       passed to Entry objects as the reference point for relpath, depth and
       samedev.
    """

    def __init__(self, args, root):
        self.root = root
        self.absroot = os.path.abspath(root)
        self.status = os.stat(self.root, follow_symlinks=args.follow_symlinks)
        self.device = self.status.st_dev


# pylint:disable=too-many-instance-attributes,too-many-public-methods
class Entry:
    """Provide access to all of a file's information. The attributes and
       properties have to adhere to the attributes dict of the File plugin,
       because it just redirects requests right to the Entry object.
    """

    _pwd_cache = {}
    _grp_cache = {}

    @classmethod
    def as_reference(cls, args, path):
        """Create an Entry from scratch, e.g when a file is given as reference.
           The resulting Entry object has emulated values for depth and samedev.
        """
        # This is a bit kludgy, but here we try to attribute a reference file
        # to a search directory from the command line, in order to emulate
        # attributes like depth and samedev. If the reference file is outside
        # of the search area we use default values.
        abspath = os.path.abspath(path)
        for directory in args.directories:
            # Go through the list of search directories and pick the first one
            # that matches the reference file.
            dirname = os.path.abspath(directory) + os.sep
            if abspath.startswith(dirname):
                relpath = abspath[len(dirname):]
                break
        else:
            directory, relpath = os.path.split(path)

        start_directory = StartDirectory(args, directory)
        status = os.stat(path, follow_symlinks=args.follow_symlinks)

        return cls(start_directory, relpath, status)

    def __init__(self, start_directory, relpath, status, ignore_paths=None):
        # pylint:disable=too-many-branches

        self.start_directory = start_directory
        self.relpath = relpath
        self.status = status
        self.ignore_paths = ignore_paths

        self.root = self.start_directory.root
        self.path = join(self.root, self.relpath) if self.root != "." else self.relpath
        self.abspath = join(self.start_directory.absroot, self.relpath)

        self.dir, self.name = os.path.split(self.path)

        # Collect information early to avoid having OSErrors later on.
        if stat.S_ISLNK(self.status.st_mode):
            self.link = os.readlink(self.path)
            self.target = os.path.realpath(join(self.dir, self.link))
            self.broken = not os.path.exists(self.target)
        else:
            # Don't set link and target so that KeyError is raised in
            # get_attribute().
            self.broken = False

        self.hide = self.name[0] == "."

        self.mode = self.status.st_mode

        if stat.S_ISDIR(self.mode):
            self.type = "directory"
        elif stat.S_ISREG(self.mode):
            self.type = "file"
        elif stat.S_ISLNK(self.mode):
            self.type = "symlink"
        elif stat.S_ISSOCK(self.mode):
            self.type = "socket"
        elif stat.S_ISFIFO(self.mode):
            self.type = "fifo"
        elif stat.S_ISCHR(self.mode):
            self.type = "char"
        elif stat.S_ISBLK(self.mode):
            self.type = "block"
        elif stat.S_ISDOOR(self.mode):
            self.type = "door"
        elif stat.S_ISPORT(self.mode):
            self.type = "port"
        elif stat.S_ISWHT(self.mode):
            self.type = "whiteout"
        else:
            self.type = "other"

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.path!r}>"

    #
    # Public properties.
    #
    @property
    def ext(self):
        """The file extension without the leading dot or the empty string if
           the file has no extension.
        """
        return os.path.splitext(self.path)[1][1:]

    @property
    def device(self):
        """The number of the device the file is located.
        """
        return self.status.st_dev

    @property
    def inode(self):
        """The number of the inode of the file.
        """
        return self.status.st_ino

    @property
    def samedev(self):
        """Whether the file is on the same device as the start directory.
        """
        return self.device == self.start_directory.device

    @property
    def depth(self):
        """The depth of the file relative to the start directory.
        """
        return self.relpath.count(os.sep)

    @property
    def exec(self):
        """Whether the file is executable or not.
        """
        return self.is_executable()

    @property
    def size(self):
        """The size of the file in bytes. All types except 'file' have a size
           of 0.
        """
        if stat.S_ISREG(self.status.st_mode):
            return self.status.st_size
        else:
            return 0

    @property
    def time(self):
        """An alias for 'mtime'.
        """
        return self.mtime

    @property
    def mtime(self):
        """The modification time of the file in seconds since epoch.
        """
        return int(self.status.st_mtime)

    @property
    def ctime(self):
        """The inode change time of the file in seconds since epoch.
        """
        return int(self.status.st_ctime)

    @property
    def atime(self):
        """The access time of the file in seconds since epoch.
        """
        return int(self.status.st_atime)

    @property
    def perm(self):
        """The permission bits of the file without the file type bits.
        """
        return self.status.st_mode & Mode.MODE_ALL

    @property
    def links(self):
        """The number of links to the inode.
        """
        return self.status.st_nlink

    @property
    def uid(self):
        """The user id of the owner of the file.
        """
        return self.status.st_uid

    @property
    def gid(self):
        """The group id of the owner of the file.
        """
        return self.status.st_gid

    @property
    def user(self):
        """The user name of the owner of the file.
        """
        try:
            return self._pwd_cache[self.status.st_uid]
        except KeyError:
            uid = self.status.st_uid
            try:
                self._pwd_cache[uid] = pwd.getpwuid(uid)[0]
            except KeyError:
                self._pwd_cache[uid] = ""
            return self._pwd_cache[uid]

    @property
    def group(self):
        """The group name of the owner of the file.
        """
        try:
            return self._grp_cache[self.status.st_gid]
        except KeyError:
            gid = self.status.st_gid
            try:
                self._grp_cache[gid] = grp.getgrgid(gid)[0]
            except KeyError:
                self._grp_cache[gid] = ""
            return self._grp_cache[gid]

    @property
    def hidden(self):
        """Whether the file is "hidden" or not, i.e. if one of the path
           components contains a leading dot.
        """
        return any(part.startswith(".") for part in self.path.split(os.sep))

    @property
    def empty(self):
        """Whether the file or directory is empty or not.
        """
        if stat.S_ISDIR(self.status.st_mode):
            # The far better solution would be to set some kind of "empty"
            # attribute in FilesystemWalker, so that we don't have to call
            # os.scandir() two times for every directory. But the way
            # FilesystemWalker is designed makes this impossible: the directory
            # has already been yielded before we find out if it is empty or
            # not.
            with os.scandir(self.path) as entries:
                for _ in entries:
                    return False
                return True
        elif stat.S_ISREG(self.status.st_mode):
            return self.size == 0
        else:
            return False

    @property
    def pathx(self):
        """The file path without the extension.
        """
        return os.path.splitext(self.path)[0]

    @property
    def namex(self):
        """The file basename without the extension.
        """
        return os.path.basename(self.pathx)

    @property
    def text(self):
        """Whether the file contains text or binary data.
        """
        if not self.is_file():
            return False

        try:
            with open(self.path) as fobj:
                try:
                    fobj.readline()
                except UnicodeDecodeError:
                    return False
                else:
                    return True
        except OSError:
            return False

    @property
    def mount(self):
        """Whether the entry is a mountpoint.
        """
        if not self.is_dir():
            return False

        parent = os.path.realpath(join(self.path, ".."))

        if parent == self.path:
            return True

        try:
            status = os.lstat(parent)
        except OSError:
            return False

        return self.status.st_dev != status.st_dev

    #
    # Private properties.
    #
    @property
    def dirname(self):
        """The dirname for the path.
        """
        return os.path.abspath(self.dir)

    @property
    def basename(self):
        """The basename for the path.
        """
        return self.name

    def is_dir(self):
        """Return True if the Entry is a directory.
        """
        return self.type == "directory"

    def is_file(self):
        """Return True if the Entry is a regular file.
        """
        return self.type == "file"

    def is_symlink(self):
        """Return True if the Entry is a symbolic link.
        """
        return self.type == "symlink"

    def is_socket(self):
        """Return True if the Entry is a socket.
        """
        return self.type == "socket"

    def is_fifo(self):
        """Return True if the Entry is a fifo i.e. named pipe.
        """
        return self.type == "fifo"

    def is_executable(self):
        """Return True if the Entry is executable.
        """
        if self.is_dir() or self.is_symlink():
            return False
        return ((self.perm & stat.S_IXUSR) | (self.perm & stat.S_IXGRP) |
                (self.perm & stat.S_IXOTH)) > 0

    def __getattr__(self, name):
        raise EntryAttributeError(name)

    def get_attribute(self, name):
        """Return attribute `name` from this Entry object and raise KeyError if
           the attribute is not defined.
        """
        try:
            return getattr(self, name)
        except EntryAttributeError as exc:
            # We have to check if the AttributeError that was raised
            # was actually about attribute.name, so we don't hide
            # programming errors inside the Entry object.
            if exc.name != name:
                raise AttributeError(exc.name)

            raise KeyError(name)
