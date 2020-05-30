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

import time
import pickle
import string
import sqlite3

from . import BaseClass


class NOTSET:
    """Return value of the cache if there is no cached value.
    """

class NODATA:
    """Cached value for when there was no value that could have been cached.
    """


class NullCache(BaseClass):
    """A cache that stores nothing and also acts as a base class.
    """

    def close(self):
        """Close the cache.
        """

    def register_plugin(self, plugin_cls):
        """Register a Plugin class in the cache.
        """

    def get(self, plugin, path, tag):
        """Get the object for a specific Plugin class, path with a specific
           modification time from the cache. Return NOTSET if nothing is found.
        """
        # pylint:disable=unused-argument
        return NOTSET

    def set(self, plugin, path, tag, obj):
        """Add an object to the cache for a specific Plugin class, path and
           modification time.
        """


class Cache(NullCache):
    """A cache that stores pickled Python objects in an sqlite3 database.
    """

    registered = {}

    commit_every_seconds = 30
    commit_every_count = 500

    def __init__(self, context):
        super().__init__(context)

        self.conn = sqlite3.connect(self.context.args.cache, timeout=30)

        self.num_cached_rows = 0
        self.last_commit = time.time()
        self.cached_rows = {}

        self.hits = 0
        self.misses = 0

    def close(self):
        """Commit remaining cached rows and close the database connection.
        """
        if self.num_cached_rows > 0:
            if __debug__:
                self.logger.debug("cache", f"closing cache with {self.num_cached_rows} "\
                        "pending entries")
            self.commit()

        self.conn.close()

        with self.context.cache_hits.get_lock():
            self.context.cache_hits.value += self.hits
        with self.context.cache_misses.get_lock():
            self.context.cache_misses.value += self.misses

    def register_plugin(self, plugin_cls):
        """Register Plugin objects.
        """
        assert plugin_cls.name not in self.registered
        self.init_table(plugin_cls)
        self.registered[plugin_cls.name] = plugin_cls

    def init_table(self, plugin_cls):
        """Check if there is already a table for this plugin in the database.
           Also drop tables from older versions of this plugin.
        """
        # Ask the database if a table exists for this plugin.
        curs = self.conn.execute(
                "select name from sqlite_master where type = 'table' and name like ?",
                (plugin_cls.sql_table_name.rstrip(string.digits) + "%",))

        # Create a table if there is none for this plugin.
        tables = set(row[0] for row in curs)
        if plugin_cls.sql_table_name not in tables:
            for statement in self.get_sql_create_table(plugin_cls):
                self.conn.execute(statement)
            self.conn.commit()
        else:
            tables.remove(plugin_cls.sql_table_name)

        for table in tables:
            if __debug__:
                self.logger.debug("cache", f"Removing old cache table {table!r}")
            self.conn.execute(f"drop table {table}")

    def get_sql_create_table(self, plugin_cls):
        """Return the statements needed to create a table for a specific Plugin
           class.
        """
        table_name = plugin_cls.sql_table_name
        yield f"create table {table_name} "\
                "(path text not null primary key, tag blob not null, data blob not null)"
        yield f"create index {table_name}_idx on {table_name} (path, tag)"

    def get(self, plugin, path, tag):
        """Return a row of cached values.
        """
        tag = pickle.dumps(tag, pickle.HIGHEST_PROTOCOL)

        for row in self.conn.execute(
                f"select data from {plugin.sql_table_name} where path = ? and tag = ?",
                (path, tag)):
            self.hits += 1
            return pickle.loads(row[0])

        self.misses += 1
        return super().get(plugin, path, tag)

    def set(self, plugin, path, tag, obj):
        """Write data to the cache.
        """
        tag = pickle.dumps(tag, pickle.HIGHEST_PROTOCOL)
        data = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)

        self.cached_rows.setdefault(plugin, []).append((path, tag, data))
        self.num_cached_rows += 1

        if time.time() >= self.last_commit + self.commit_every_seconds or \
                self.num_cached_rows == self.commit_every_count:
            if __debug__:
                self.logger.debug("cache", f"commit cache with {self.num_cached_rows} entries "\
                        f"after {time.time() - self.last_commit:.1f} seconds")
            self.commit()

    def commit(self):
        """We commit cached data in chunks, so that parallel processes will
           block each other less often.
        """
        for plugin, rows in self.cached_rows.items():
            while True:
                try:
                    self.conn.executemany(
                            f"insert or replace into {plugin.sql_table_name} values (?, ?, ?)",
                            rows)
                    self.conn.commit()
                except sqlite3.OperationalError as exc:
                    if "database is locked" in str(exc):
                        self.logger.warning("Database is locked, retrying ...")
                        time.sleep(0.5)
                    else:
                        raise
                else:
                    break

        self.num_cached_rows = 0
        self.cached_rows = {}
        self.last_commit = time.time()
