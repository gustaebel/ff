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

import textwrap
import itertools

from . import OUTPUT_WIDTH


class Table(list):
    """A simple class for tabular output.
    """

    def __init__(self, column_names, padding="   ", indent="    ", wrap_last_column=False):
        super().__init__()
        self.column_names = column_names
        self.padding = padding
        self.indent = indent
        self.wrap_last_column = wrap_last_column

        self.column_widths = []
        for name in column_names:
            self.column_widths.append(len(name))

    def calculate_last_column_length(self):
        """Calculate the length of the last column if it supposed to be
           wrapped.
        """
        width = OUTPUT_WIDTH
        width -= len(self.indent)
        width -= self.calculate_padding()
        width -= sum(self.column_widths[:-1])
        return max(25, width)

    def calculate_padding(self):
        """Calculate the total length of the padding between the columns.
        """
        return len(self.padding) * (len(self.column_widths) - 1)

    def add(self, row):
        """Add a new row of values.
        """
        if self.wrap_last_column:
            row = row[:-1] + [" ".join(row[-1].strip().split())]

        for i, value in enumerate(row):
            self.column_widths[i] = max(len(value), self.column_widths[i])

        self.append(row)

    def format(self, row):
        """Format a row and generate a list of lines for output. Optionally,
           wrap the last column.
        """
        if self.wrap_last_column:
            for new_row in itertools.zip_longest(
                    *([value] for value in row[:-1]),
                    textwrap.wrap(row[-1], width=self.calculate_last_column_length()),
                    fillvalue=""):
                yield new_row
        else:
            yield row

    def print_row(self, row):
        """Format a row and print it to standard output.
        """
        for new_row in self.format(row):
            print(self.indent, end="")
            for value, width in zip(new_row[:-1], self.column_widths[:-1]):
                print(value.ljust(width), end=self.padding)
            print(new_row[-1])

    def print_separator(self):
        """Print the separator between header and values.
        """
        width = min(OUTPUT_WIDTH - len(self.indent),
                sum(self.column_widths) + self.calculate_padding())
        print(self.indent + "-" * width)

    def print(self):
        """Print the table to standard output.
        """
        self.print_row(self.column_names)
        self.print_separator()
        for row in self:
            self.print_row(row)
