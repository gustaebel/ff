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
import unittest
import subprocess

from libff.find import Find
from libff.ignore import Glob
from libff.exceptions import ExpressionError

tests_directory = os.path.dirname(os.path.abspath(sys.argv[0]))


class ShellTest(unittest.TestCase):

    @classmethod
    def add_test(cls, test, test_number, workdir, command, output, keep_order):
        def shell(self):
            env = os.environ.copy()
            env["PATH"] = tests_directory + os.pathsep + env["PATH"]

            try:
                stdout = subprocess.check_output(command, shell=True, env=env,
                        cwd=workdir, universal_newlines=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as exc:
                stdout = exc.output

            if keep_order:
                self.assertEqual(stdout, output)
            else:
                self.assertEqual(set(output.splitlines()), set(stdout.splitlines()))

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


class APITest(unittest.TestCase):

    tests_dir = os.path.dirname(sys.argv[0])

    def setUp(self):
        self.startdir = os.getcwd()
        os.chdir(os.path.join(self.tests_dir, "test-01/workdir"))

    def tearDown(self):
        os.chdir(self.startdir)

    def _test(self, values, output=["path"], keep_order=False, **kwargs):
        expected_rows = []
        for i in range(0, len(values), len(output)):
            expected_rows.append({k: v for k, v in zip(output, values[i:i+len(output)])})

        rows = []
        for row in Find(output=output, **kwargs):
            rows.append({k: v for k, v in row.items() if k in output})

        expected_rows = [tuple(row.items()) for row in expected_rows]
        rows = [tuple(row.items()) for row in rows]

        if not keep_order:
            expected_rows = set(expected_rows)
            rows = set(rows)

        self.assertEqual(expected_rows, rows)

    def test_basic_01(self):
        self._test(["foo", "BAR", "baz", "dir", "dir/dir", "dir/dir/empty", "dir/empty_dir"],
                   hide=True)

    def test_basic_02(self):
        self._test(["foo", "BAR", "baz", "dir", "dir/dir", "dir/dir/empty", "dir/empty_dir",
                       ".hidden"])

    def test_basic_03(self):
        self._test(["dir", "dir/dir", "dir/empty_dir"],
                   query="type=d",
                   hide=True)

    def test_basic_04(self):
        self._test(["foo", "baz", "dir/dir/empty"],
                   query="type=f",
                   hide=True)

    def test_basic_05(self):
        self._test(["foo", "baz", "dir/dir/empty", ".hidden"],
                   query="type=f")

    def test_basic_06(self):
        self._test(["BAR"],
                   query="type=l")

    def test_basic_07(self):
        self._test(["foo", "BAR"],
                   query="type=l",
                   output=["link", "name"])

    def test_basic_08(self):
        self._test(["foo", "BAR", None, "baz", None, "dir", None, "dir/dir", None, "dir/dir/empty",
                    None, "dir/empty_dir", None, "foo", None, ".hidden"],
                   output=["link", "path"])

    def test_basic_09(self):
        self._test(["BAR", "baz"],
                   query="name%ba?")

    def test_basic_10(self):
        self._test(["dir/empty_dir", "dir/dir/empty"],
                   query="empty=yes",
                   hide=True)

    def test_basic_11(self):
        self._test(["dir/empty_dir", "dir/dir/empty", "BAR"],
                   query="empty=yes OR type=l",
                   hide=True)

    def test_basic_12(self):
        self._test(["foo", "BAR", "baz", "dir", "dir/dir"],
                   query="empty=no")

    def test_basic_13(self):
        self._test(["foo", "BAR", "baz", "dir"],
                   query="depth=0",
                   hide=True)

    def test_basic_14(self):
        self._test(["BAR", "dir", "dir/dir", "dir/empty_dir", "dir/dir/empty"],
                   query="size=0",
                   hide=True)

    def test_basic_15(self):
        self._test(["foo", "baz"],
                   query="size+0",
                   hide=True)

    def test_basic_16(self):
        self._test(["baz"],
                   query="size+=10",
                   hide=True)

    def test_basic_17(self):
        self._test([0o777, 0, "BAR", 0o644, 4, "foo", 0o644, 10, "baz"],
                   query="not type=d depth=0",
                   hide=True,
                   output=["perm", "size", "name"])

    def test_basic_18(self):
        self._test(["BAR", "baz", "dir", "dir/dir", "dir/dir/empty", "dir/empty_dir", "foo"],
                   hide=True, sort=["path"], keep_order=True)

    def test_basic_19(self):
        self._test(["BAR", "baz", "dir", "dir/dir", "dir/dir/empty", "dir/empty_dir", "foo",
                       ".hidden"],
                   hide=False, sort=["path"], keep_order=True)

    def test_basic_20(self):
        self._test(["dir/dir/empty", "foo", "baz"],
                   query="type=f",
                   hide=True, sort=["size"], keep_order=True)

    def test_basic_21(self):
        self._test(["foo", "baz"],
                   query="type=f {{ name=baz or name=foo }}",
                   hide=True)

    def test_basic_22(self):
        self._test(["foo", "baz"],
                   query=["type=f", "{{", "name=baz", "or", "name=foo", "}}"],
                   hide=True)

    def test_case_01(self):
        self._test(["BAR", "baz"], query=["name%ba?"])

    def test_case_02(self):
        self._test(["BAR"], query=["name%BA?"])

    def test_case_03(self):
        self._test(["BAR", "baz"], query=["name%BA?"], case="ignore")

    def test_case_04(self):
        self._test(["BAR"], query=["name%BA?"], case="sensitive")

    def test_case_05(self):
        self._test(["BAR"], query=["name%BA?"], case="sensitive")

    def test_case_06(self):
        self._test([], query=["name%bA?"], case="sensitive")

    def test_case_error(self):
        self.assertRaises(ValueError, Find, case="foo")

    def test_strict(self):
        self.assertRaises(ExpressionError, Find, query="ba?")

    def test_keys(self):
        find = Find()
        count = 0
        for row in find:
            self.assertEqual(set(row.keys()), set(find.registry.get_file_attributes()))
            count += 1
        self.assertEqual(count, 8)


if __name__ == "__main__":
    for path in glob.glob(os.path.join(tests_directory, "test-??/tests")):
        test = os.path.basename(os.path.dirname(path))

        test_number = 1
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
