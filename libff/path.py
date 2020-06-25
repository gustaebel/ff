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
from typing import Tuple

separator:str = os.sep


def splitext(path:str) -> Tuple[str, str]:
    """A simpler and faster version of os.path.splitext().
    """
    sep:int = path.rfind(separator)
    dot:int = path.rfind(".")
    if dot > sep:
        idx:int = sep + 1
        while idx < dot:
            if path[idx:idx+1] != ".":
                return path[:dot], path[dot:]
            idx += 1

    return path, path[:0]

def split(path:str) -> Tuple[str, str]:
    """A simpler and faster version of os.path.split().
    """
    sep:int = path.rfind(separator)
    if sep < 0:
        return "", path
    else:
        return path[:sep], path[sep + 1:]

def join(part1:str, part2:str) -> str:
    """A simpler and faster version of os.path.join().
    """
    if part1:
        if part2:
            if part1 == separator:
                return part1 + part2
            else:
                return part1 + separator + part2
        else:
            return part1
    else:
        return part2
