# Put this file in ~/.ff and rename it.

from libff.plugin import *

# IMPORTANT: Do not import third-party modules here, that may not
# be installed on the system, do this in Plugin.setup().


class Name(Plugin):
    # Give the Plugin a descriptive name that does not yet exist.

    # If use_cache is True it is possible to cache data for each entry that is
    # time-consuming to prepare. The cache() method will be called, its return
    # value will be cached and then passed to process(). Cached values are
    # discarded as soon as the associated entry's modification time changes or
    # the code of this module is altered.
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
        ("foo", String, "The name of the file."),
        ("bar", Size, "The size of the file.")
    ]

    @classmethod
    def get_plugin_cache_tag(cls, path):
        # Optional. Is only used if use_cache = True. Rarely used.
        #
        # Return a "tag" that should stay the same as long as the format of the
        # plugin's cached data stays the same. Otherwise, all cached values for
        # this plugin are discarded and recached.
        # The default scheme returns a checksum of the plugins source code, so
        # the cache is invalidated automatically everytime the plugin code is
        # changed.
        # If you need more control over the cache you can implement your own
        # scheme, e.g. return a number that you increment manually everytime
        # you change the data format.

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
        # This check is supposed to reduce the number that the cache() and
        # process() methods will be called and will also reduce the load on the
        # cache and the number of needlessly cached entries.
        #
        #   def can_handle(self, entry):
        #       return entry.is_file()

    def get_entry_cache_tag(self, entry):
        # Optional. Is only called if use_cache = True. Rarely used.
        #
        # Return a "tag" that indicates the validity of the cached value for
        # this entry. Once it changes the cached value will be discarded and
        # recached. The default method returns the file's modification time
        # which is what you want in most cases.

    def cache(self, entry):
        # Optional. Is only called if use_cache = True.
        #
        # Extract and prepare information from the entry and put it in the
        # cache. After the value has been cached this method will not be called
        # again unless the result of cache_tag(entry) changes. The return value
        # of cache() will be cached and then passed to the process() method. It
        # may have any type. If the file information cannot be extracted, raise
        # a NoData exception.

    def process(self, entry, cached):
        # Required.
        #
        # Extract information from the entry to produce values for the
        # attributes described above. `entry` is a an Entry object from
        # libff/entry.py, see there for attributes and properties. If use_cache
        # is True, `cached` is the cached return value from the cache() method
        # or None if there was a NoData exception raised.
        # On success, either return a dictionary with the values or yield
        # key-value pairs. On failure, i.e. if the file is invalid or the
        # required information cannot be extracted, raise a NoData exception or
        # return an empty dictionary.
        yield "foo", entry.name
        yield "bar", entry.size
