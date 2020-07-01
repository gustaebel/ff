#!/usr/bin/python3
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
import sys
import glob
from distutils.sysconfig import get_python_lib

import setuptools

from libff.__version__ import __version__

with open("README.md") as fobj:
    long_description = fobj.read()

kwargs = {
    "name":         "find-ff",
    "version":      str(__version__),
    "author":       "Lars Gustäbel",
    "author_email": "lars@gustaebel.de",
    "url":          "https://github.com/gustaebel/ff/",
    "description":  "A tool for finding files in the filesystem",
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
    "license":      "GPLv3+",
    "classifiers":  ["Development Status :: 3 - Alpha",
                     "Environment :: Console",
                     "Intended Audience :: Developers",
                     "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
                     "Operating System :: POSIX",
                     "Operating System :: POSIX :: Linux",
                     "Topic :: System :: Filesystems",
                     "Topic :: Utilities",
                     "Programming Language :: Python :: 3"],
    "python_requires": ">=3.6",
    "install_requires": ["pymediainfo", "file-magic"],

    "packages":     ["ff", "libff", "libff.builtin"],
    "scripts":      ["bin/ff"],
    "data_files":   [("/usr/share/man/man1", ["man/ff.1"]),
                     ("/usr/share/man/man7", ["man/ff.7"]),
                     ("/usr/lib/ff", glob.glob("plugins/*.py")),
                     ("/usr/share/ff", ["plugin_template.py"]),
                     (os.path.join(get_python_lib(), "libff"), ["libff/manpage.template"])]
}

setuptools.setup(**kwargs)
