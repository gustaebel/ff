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
import re
import itertools
import collections

from .type import Count
from .exceptions import UsageError

Field = collections.namedtuple("Field", "attribute type width modifier")


class AttributeDict(dict):
    """Allow attribute access to a dictionary. Dot field separators are replaced with underscores.
    """

    def __init__(self, fields):
        super().__init__()
        self._fields = {field.replace(".", "_"): field for field in fields}

    def __getattr__(self, name):
        if name not in self._fields:
            raise KeyError(name)
        else:
            return self[self._fields[name]]


class Fields(list):
    """A class that stores a list of attributes as fields.
    """

    regex = re.compile(r"^((?:[a-zA-Z][a-zA-Z0-9_]+\.)?[a-zA-Z][a-zA-Z0-9_]+?)"\
            r"(?::(-?\d+)?(h|o|x|n|v)?)?$")

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

    def __init__(self, context, argument):
        super().__init__(context, argument)

        self.fields = [str(field.attribute) for field in self]

    def store(self, argument):
        for string in argument:
            self.append(self.make_field(string))

    def to_dict(self, entry):
        """Create a dictionary from the list of fields.
        """
        record = AttributeDict(self.fields)
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

    regex_digits = re.compile(r"(\d+)")

    def prepare_component(self, component):
        """Prepare a path component to act as a part of a sort key.
        """
        # Strip away all file extensions that don't contain digits.
        extensions = []
        while component:
            comp, ext = os.path.splitext(component)
            ext = ext.lstrip(os.extsep)
            if not ext or ext[0].isdigit():
                break
            component = comp
            extensions.insert(0, ext)

        # Split the component into string and number parts. Make sure the list starts with a
        # string.
        parts = self.regex_digits.split(component)
        if parts[0].isdigit():
            parts.insert(0, "")

        # Yield a list of tokens with all numbers converted to ints.
        yield [int(p) if p.isdigit() else p for p in parts]

        # Yield extensions separately.
        if extensions:
            yield extensions

    def prepare_sort_key(self, value):
        """Prepare a sort key from a path for natural/version sorting.
        """
        # Split a full path in its components and prepare each component separately. This should
        # produce output similar to natsort.os_sort_key().
        cmp_key = []
        for component in os.path.normpath(value).split(os.sep):
            cmp_key += list(self.prepare_component(component))
        return cmp_key

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
                if field.modifier == "v":
                    value = self.prepare_sort_key(value)
                output.append(value)
        return tuple(output)


class ExecFields(Fields):
    """Store a list of fields that help with calling subprocesses.
    """

    regex_placeholder = re.compile(r"({{|}}|{[^}]*})")

    def replace(self, part):
        """Replace a placeholder with a Field.
        """
        if part == "{{":
            field = "{"
        elif part == "}}":
            field = "}"
        elif part == "{}":
            field = self.make_field("file.path")
        elif part == "{/}":
            field = self.make_field("file.name")
        elif part == "{//}":
            field = self.make_field("file.dir")
        elif part == "{.}":
            field = self.make_field("file.pathx")
        elif part == "{/.}":
            field = self.make_field("file.namex")
        elif part == "{..}":
            field = self.make_field("file.ext")
        elif part.startswith("{") and part.endswith("}"):
            field = self.make_field(part[1:-1])
        else:
            field = part
        return field

    def store(self, argument):
        # This list of arguments:
        #
        #    ["convert", "{}", "new-{.}.jpg"]
        #
        # will be translated to:
        #
        #    [["convert"], [Field("file.path")], ["new-", Field("file.pathx"), ".jpg"]]
        #
        for string in argument:
            self.append([self.replace(part)
                for part in self.regex_placeholder.split(string)
                if part])

        # Append a path field if there was no placeholder found in the argument list.
        if not any(isinstance(field, Field) for field in itertools.chain(*self[1:])):
            self.append([self.make_field("file.path")])

    def render_field(self, entry, field):
        """Return a rendered Field value for the Entry object.
        """
        if isinstance(field, Field):
            try:
                value = self.registry.get_attribute(entry, field.attribute)
            except KeyError:
                if self.args.all or field.modifier == "n":
                    return ""
                else:
                    raise
            else:
                return field.type.output(self.args, field.modifier, value)
        else:
            # Fields that do not contain a placeholder will be left unchanged.
            return field

    def render_fields(self, fields, entries, batch):
        """Return a list of arguments with all placeholders replaced.
        """
        output = []
        for subfields in fields:
            # Each element of the list of 'fields' is a alternating sequence of strings and Field
            # objects that act as placeholders, see the comment in store().
            # If in batch mode each Entry from the 'entries' list will produce a new argument in
            # the output argument list, i.e. ["echo", "{/}"] with ["foo", "bar", "baz"] as entries
            # will produce ["echo", "foo", "bar", "baz"].
            # When not in batch mode the same will produce: ["echo", "foo"], ["echo", "bar"],
            # ["echo", "baz"].
            if any(isinstance(a, Field) for a in subfields):
                for entry in entries:
                    # Build one argument for each Entry at a time.
                    try:
                        argument = []
                        for field in subfields:
                            argument.append(self.render_field(entry, field))
                        output.append("".join(argument))

                    except KeyError:
                        # One of the attributes produced no value. If in batch mode, we ignore this
                        # and simply add no new argument. If not in batch mode we want this problem
                        # to be propagated to the caller, so that there is no --exec call.
                        if not batch:
                            raise

            else:
                output.append("".join(subfields))

        return output

    def render(self, entry):
        """Create a list of arguments from an Entry object for calling a subprocess.
        """
        return self.render_fields(self, [entry], False)


class ExecBatchFields(ExecFields):
    """Store a list of fields that help with calling one subprocess with arguments from multiple
       Entry objects.
    """

    def store(self, argument):
        super().store(argument)

        if any(isinstance(field, Field) for field in self[0]):
            raise UsageError("The first part of the command must not contain placeholders!")

    # pylint:disable=arguments-renamed
    def render(self, entries):
        """Create a list of arguments from multiple Entry objects for calling a subprocess.
        """
        return ["".join(self[0])] + self.render_fields(self[1:], entries, True)
