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
    # Cython < 3.0 has problems with __init_subclass__().
    raise SystemExit("cython >= 3.0 required")

def extension(name, sources):
    return setuptools.Extension(name, sources,
            extra_compile_args=["-DCYTHON_WITHOUT_ASSERTIONS"])

kwargs["packages"] = ["ff"]
kwargs["ext_modules"] = cythonize([
        extension("libff.*", ["libff/[!_]*.py"]),
        extension("libff.builtin.*", ["libff/builtin/*.py"])],
        language_level=3)

setuptools.setup(**kwargs)
