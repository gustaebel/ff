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

import re
import collections

from . import Attribute
from .type import Count
from .exceptions import UsageError

Field = collections.namedtuple("Field", "attribute type width modifier")


class Fields(list):
    """A class that stores a list of attributes as fields.
    """

    regex = re.compile(r"^((?:[a-zA-Z][a-zA-Z0-9_]+\.)?[a-zA-Z][a-zA-Z0-9_]+?)"\
            r"(?::(-?\d+)?(h|o|x|n)?)?$")

    def __init__(self, context, argument):
        super().__init__()

        self.context = context
        self.args = self.context.args
        self.registry = self.context.registry

        self.store(argument)

    def make_field(self, string):
        """Create a Field from an attribute string.
        """
        match = self.regex.match(string.strip())
        if match is None:
            raise UsageError(f"Invalid attribute {string!r}")
        name, width, modifier = match.groups()
        attribute = self.registry.setup_attribute(name)
        type_cls = self.registry.get_attribute_type(attribute)
        return Field(attribute, type_cls, width, modifier)

    def store(self, argument):
        """Convert argument to a list of Field objects and store them.
        """
        raise NotImplementedError


class OutputFields(Fields):
    """Store a list of fields that help with formatting output.
    """

    def store(self, argument):
        for string in argument:
            self.append(self.make_field(string))

    def to_dict(self, entry):
        """Create a dictionary from the list of fields.
        """
        record = {}
        for field in self:
            try:
                value, type_cls = \
                        self.context.registry.get_attribute_and_type(entry, field.attribute)
            except KeyError:
                value = None
            else:
                if field.modifier == "h":
                    value = type_cls.output(self.args, field.modifier, value)

            record[str(field.attribute)] = value

        return record


class CountFields(OutputFields):
    """Store a list of fields that help with formatting statistics output.
    """

    def store(self, argument):
        super().store(argument)

        for field in self:
            if field.type.count is Count.UNCOUNTABLE:
                raise UsageError(f"Attribute {field.attribute} is not suited for --count!")


class SortFields(OutputFields):
    """Store a list of fields that help with sorting Entry objects.
    """

    def render(self, entry):
        """Create a sort key from an Entry object.
        """
        output = []
        for field in self:
            try:
                value = self.registry.get_attribute(entry, field.attribute)
            except KeyError:
                output.append(field.type.sort_none)
            else:
                value = field.type.sort_key(value)
                output.append(value)
        return tuple(output)


class ExecFields(Fields):
    """Store a list of fields that help with calling subprocesses.
    """

    def store(self, argument):
        for string in argument:
            if string == "{}":
                field = self.make_field("file.path")
            elif string == "{/}":
                field = self.make_field("file.name")
            elif string == "{//}":
                field = self.make_field("file.dir")
            elif string == "{.}":
                field = self.make_field("file.pathx")
            elif string == "{/.}":
                field = self.make_field("file.namex")
            elif string == "{..}":
                field = self.make_field("file.ext")
            elif string.startswith("{") and string.endswith("}"):
                field = self.make_field(string[1:-1])
            else:
                field = string

            self.append(field)

        # Append path if there is no placeholder in the argument list.
        if not any(isinstance(field, Field) for field in self):
            attribute = Attribute("file", "path")
            type_cls = self.registry.get_attribute_type(attribute)
            self.append(Field(attribute, type_cls, None, None))

    def render(self, entry):
        """Create a list of arguments from an Entry object for calling a
           subprocess.
        """
        return self.render_fields(self, [entry], ignore_missing=False)

    def render_fields(self, fields, entries, ignore_missing=True):
        """Return a list of arguments with all placeholders replaced.
        """
        output = []
        for field in fields:
            if isinstance(field, Field):
                for entry in entries:
                    try:
                        value = self.registry.get_attribute(entry, field.attribute)
                    except KeyError:
                        if self.args.all or field.modifier == "n":
                            output.append("")
                        elif not ignore_missing:
                            raise
                    else:
                        output.append(field.type.output(self.args, field.modifier, value))
            else:
                # Fields that do not contain a placeholder will be left
                # unchanged.
                output.append(field)
        return output


class ExecBatchFields(ExecFields):
    """Store a list of fields that help with calling one subprocess with
       arguments from multiple Entry objects.
    """

    # pylint:disable=arguments-differ
    def render(self, entries):
        """Create a list of arguments from multiple Entry objects for calling a
           subprocess.
        """
        return [self[0]] + self.render_fields(self[1:], entries, ignore_missing=True)
