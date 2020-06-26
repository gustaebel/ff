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
import subprocess

from libff.plugin import *


class Filelist(set):
    """The list of filenames that are tracked inside a git repository.
    """

    def __init__(self, dirname):
        super().__init__()

        proc = subprocess.run(["git", "-C", dirname, "ls-files"], capture_output=True, text=True,
                check=False)
        for filename in proc.stdout.splitlines():
            self.add(os.path.join(dirname, filename))


class Status(set):
    """The list of filenames that are tracked inside a git repository and have been changed.
    """

    def __init__(self, dirname):
        super().__init__()

        proc = subprocess.run(["git", "-C", dirname, "status", "--porcelain"], capture_output=True,
                text=True, check=False)
        for line in proc.stdout.splitlines():
            status, filename = line.split(None, 1)
            if status == "??":
                continue
            self.add(os.path.join(dirname, filename))


class Git(Plugin):
    """The "git" plugin provides information about files that are inside a git(1) repository. It
       requires the 'git' executable.
    """

    speed = Speed.SLOW

    attributes = [
        ("tracked", Boolean, "True if the file is tracked by a git repository."),
        ("dirty", Boolean, "True if the file is tracked and has changed or if a directory "\
                "contains a changed file."),
        ("repo_dir", String, "The base directory of the git repository the file or "\
                "directory is in."),
        ("repo", Boolean, "True if the directory contains a git repository.")
    ]

    def __init__(self):
        super().__init__()

        self._cache = {}

    def can_handle(self, entry):
        return True

    def find_repo(self, dirname):
        """Find a .git directory in the current or upper directories and return a list of changed
           files and a list of tracked files.
        """
        if dirname not in self._cache:
            path = os.path.join(dirname, ".git")
            if os.path.isdir(path):
                self._cache[dirname] = dirname, Filelist(dirname), Status(dirname)
            else:
                if dirname == os.sep:
                    self._cache[dirname] = None, None, None
                else:
                    self._cache[dirname] = self.find_repo(os.path.dirname(dirname))

        return self._cache[dirname]

    def process(self, entry, cached):
        dirname = entry.abspath if entry.is_dir() else \
                os.path.dirname(entry.abspath)

        repo_dir, filelist, status = self.find_repo(dirname)

        if repo_dir is None:
            raise NoData

        else:
            data = {"repo_dir": repo_dir, "repo": repo_dir == entry.abspath}

            # Iterate the list of tracked files and the list of changed files and test whether the
            # entry is in one of them. In case of directories it is checked whether it contains a
            # file that is in one of these lists.
            for key, paths in ("tracked", filelist), ("dirty", status):
                if entry.is_dir():
                    abspath = entry.abspath + os.sep
                    data[key] = any(p.startswith(abspath) for p in paths)
                else:
                    data[key] = entry.abspath in paths

            return data
