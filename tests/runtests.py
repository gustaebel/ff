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

import os
import sys
import glob
import unittest
import subprocess

from libff.ignore import Glob

test_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
source_directory = os.path.dirname(test_directory)


class ShellTest(unittest.TestCase):

    @classmethod
    def add_test(cls, test, test_number, workdir, command, output, keep_order):
        def shell(self):
            env = os.environ.copy()
            env["PATH"] = source_directory + os.pathsep + env["PATH"]

            try:
                stdout = subprocess.check_output(command, shell=True, env=env,
                        cwd=workdir, universal_newlines=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as exc:
                stdout = exc.output

            if keep_order:
                self.assertEqual(stdout, output)
            else:
                self.assertEqual(set(stdout.splitlines()), set(output.splitlines()))

        setattr(cls, f"test_[{test}-{test_number:02d}/{command}]", shell)


class GlobTest(unittest.TestCase):

    def _test(self, pattern, path, match=True, is_dir=False):
        pattern = Glob(pattern)
        pattern_match = pattern.match(path, is_dir=is_dir)
        if not pattern.include:
            pattern_match = not pattern_match
        self.assertIs(pattern_match, match)

    def test_glob_1(self):
        self._test("*.py", "a.py")
        self._test("*.py", "a/b.py")
        self._test("!*.py", "a/b.py", False)

        self._test("a/", "a", is_dir=True)
        self._test("a/", "a", False, is_dir=False)

    def test_glob_2(self):
        self._test("frotz/", "doc/frotz", is_dir=True)
        self._test("frotz/", "a/doc/frotz", is_dir=True)
        self._test("/frotz/", "frotz", is_dir=True)
        self._test("/frotz/", "doc/frotz", False, is_dir=True)
        self._test("doc/frotz/", "doc/frotz", is_dir=True)
        self._test("doc/frotz/", "a/doc/frotz", False, is_dir=True)
        self._test("/doc/frotz/", "doc/frotz", is_dir=True)
        self._test("/doc/frotz/", "a/doc/frotz", False, is_dir=True)
        self._test("!/doc/frotz/", "doc/frotz", False, is_dir=True)

    def test_glob_3(self):
        self._test("*", "a")
        self._test("*", "a/b")
        self._test("a/*", "a/b")
        self._test("*/b", "a/b")
        self._test("a/*/c", "a/b/c")
        self._test("a/*/c", "a/c", False)

    def test_glob_4(self):
        self._test("?", "a")
        self._test("a/?", "a/b")
        self._test("?/b", "a/b")
        self._test("a?b", "a/b", False)
        self._test("a?c", "abc")
        self._test("a?c", "ac", False)

    def test_glob_5(self):
        self._test("[a-b]", "a")
        self._test("[a-b]", "b")
        self._test("[a-b]", "c", False)
        self._test("[!a-b]", "a", False)
        self._test("[!a-b]", "b", False)
        self._test("[!a-b]", "c")

    def test_glob_6(self):
        self._test("**/foo", "foo")
        self._test("**/foo", "bar/foo")
        self._test("**/foo", "foo/bar", False)
        self._test("**/foo/bar", "foo/bar")
        self._test("**/foo/bar", "baz/foo/bar")
        self._test("**/foo/bar", "foo/baz/bar", False)

    def test_glob_7(self):
        self._test("foo/*", "foo/bar")
        self._test("foo/*", "foo/bar/baz", False)
        self._test("foo/**", "foo")
        self._test("foo/**", "foo/bar")
        self._test("foo/**", "foo/bar/baz")
        self._test("/foo/**", "foo/bar/baz")
        self._test("/foo/**", "bar/foo", False)
        self._test("/foo/**", "bar/foo/baz", False)

    def test_glob_8(self):
        self._test("a/**/b", "a/b")
        self._test("a/**/b", "a/x/b")
        self._test("a/**/b", "a/x/y/b")


if __name__ == "__main__":
    for path in glob.glob(os.path.join(test_directory, "test-??/tests")):
        test = os.path.basename(os.path.dirname(path))

        test_number = 0
        with open(path) as lines:
            workdir = os.path.join(os.path.dirname(path), "workdir")

            lines = list(lines)

            # Parse a test file. The command is on the first line, the
            # required output follows. Tests are separated by one or more empty
            # lines. Directive lines start with a # and stay valid for all
            # tests that follow.
            keep_order = False
            while lines:
                while lines:
                    line = lines[0].strip()
                    if not line or line.startswith("#"):
                        line = line.strip("# ")
                        if line == "keep_order":
                            keep_order = True
                        elif line == "no_order":
                            keep_order = False
                        lines.pop(0)
                    else:
                        break
                else:
                    break

                command = lines.pop(0).strip()
                output = []
                while lines:
                    line = lines.pop(0)
                    if not line.strip():
                        break
                    output.append(line)

                ShellTest.add_test(test, test_number, workdir, command, "".join(output), keep_order)
                test_number += 1

    unittest.main()
