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

import setuptools
from Cython import __version__
from Cython.Build import cythonize

from setup import kwargs

if int(__version__.split(".", 1)[0]) < 3:
    raise SystemExit("cython >= 3.0 required")

extra_compile_args = ["-O3", "-DCYTHON_WITHOUT_ASSERTIONS"]

del kwargs["packages"]
kwargs["ext_modules"] = cythonize(["libff/[!_]*.py", "libff/builtin/*.py"], language_level=3)
for ext in kwargs["ext_modules"]:
    ext.extra_compile_args += extra_compile_args

setuptools.setup(**kwargs)
