# Put this file in ~/.ff and rename it.

from libff.plugin import *

# IMPORTANT: Do not import third-party modules here, that may not
# be installed on the system, do this in Plugin.setup().


class Name(Plugin):
    # Give the Plugin a descriptive name that does not yet exist.

    # If the code in the process() method takes a lot of time to produce the
    # results, and under the condition that the result would not change between
    # different calls to process(), you can turn on caching here. A once cached
    # result is discarded as soon as the associated entry's modification time
    # changes or the code of this module is altered.
    use_cache = False

    # Here you tell ff(1) which attributes your plugin will provide.
    # `attributes` is a list of 3-element-tuples: (name, type, description).
    # `type` must be a subclass of Type. A Type's job is for example to
    # describe which operators the value supports, and to format the value
    # for output or to a human readable form. You can create your own Types if
    # needed, see libff/type.py for details.
    #
    # Available Types are:
    #
    #    String             a generic string
    #    ListOfStrings      a list of strings
    #    Number             a number greater or equal to 0
    #    Size               a size in bytes
    #    Time               a point in time in seconds
    #    Duration           a duration in seconds
    #    Boolean            a true or false value
    #
    attributes = [
        ("name", String, "The name of the file."),
        ("size", Size, "The size of the file.")
    ]

    @classmethod
    def setup(cls):
        # Optional.
        #
        # This classmethod is called once before the Plugin is about to be
        # used. It is supposed to be used for setup code, mainly for importing
        # modules that may or may not be installed.
        #
        #   @classmethod
        #   def setup(cls):
        #       global module
        #       import module

    def can_handle(self, entry):
        # Required.
        #
        # Return True if this plugin can handle this type of file. There are
        # many ways possible for you to do this: based on an attribute of the
        # Entry object (e.g. file type, extension, mime type etc.) or by
        # reading a magic number from the file.
        # This check is supposed to reduce the number the process() method is
        # called. If use_cache is active, each result from process() will be
        # cached, even if it is empty, so a properly implemented can_handle()
        # method will also reduce the load on the cache and the number of
        # needlessly cached entries.
        return entry.is_file()

    def process(self, entry):
        # Required.
        #
        # Extract information from the entry to produce values for the
        # attributes described above, e.g. by examining the contents of the
        # file. `entry` is a an Entry object from libff/entry.py, see there
        # for attributes and properties.
        # On success, either return a dictionary with the values or yield
        # key-value pairs. On failure, i.e. if the file information cannot be
        # extracted, raise a NoData exception or return an empty dictionary.
        yield "name", entry.name
        yield "size", entry.size
