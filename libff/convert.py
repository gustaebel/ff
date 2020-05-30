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
import time
import datetime

UNITS = ("", "K", "M", "G", "T", "P", "E", "Z", "Y")

def format_size(number, base=1024):
    """Convert a number to a string with a human readable file size.
    """
    if number < base:
        return str(number)

    for unit in UNITS:
        if number < base:
            break
        number /= base
        number = round(number, 1)

    if base == 1000:
        unit += "B"

    if number < 10:
        return f"{number:.1f}{unit}"
    else:
        return f"{int(number):d}{unit}"


regex = re.compile(r"(\d+)b?$|(\d+(?:[\.]\d+)?)(" + \
        f"{'|'.join(unit for unit in UNITS if unit)}|" + \
        f"{'|'.join(unit + 'B' for unit in UNITS if unit)}|" + \
        f"{'|'.join(unit + 'iB' for unit in UNITS if unit)}" + \
        ")?$", re.IGNORECASE)

def parse_size(string):
    """Convert a string denoting a file size to an integer.
    """
    string = string.upper()

    match = regex.match(string)
    try:
        number_in_bytes, number, unit = match.groups()
    except AttributeError:
        pass

    if match is None or (number_in_bytes is None and unit is None):
        raise ValueError(f"invalid size {string!r}")

    if number_in_bytes is None:
        prefix = unit[0]
        suffix = unit[1:]

        exp = UNITS.index(prefix)
        base = 1000 if suffix == "B" else 1024
        return int(float(number) * base ** exp)
    else:
        return int(number_in_bytes)


def format_duration(seconds):
    """Format a number of seconds to a human readable duration representation.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds %= 60

    if hours:
        return "%dh%dm%ds" % (hours, minutes, seconds)
    else:
        return "%dm%ds" % (minutes, seconds)


regex_duration = re.compile(r"(\d+)([smhdwMy])?")

def parse_duration(string):
    """Convert a human readable duration from a string to seconds.
    """
    string = string.lower()

    try:
        return int(string) * 60
    except ValueError:
        pass

    duration = 0
    end = 0
    for match in regex_duration.finditer(string):
        if match.start(0) != end:
            raise ValueError(f"unable to parse {string!r}")
        end = match.end(1) + 1

        count, unit = match.groups()
        count = int(count)

        if unit == "s":
            duration += count
        elif unit == "m":
            duration += count * 60
        elif unit == "h":
            duration += count * 3600
        elif unit == "d":
            duration += count * 86400
        elif unit == "w":
            duration += count * 604800 # 7 days
        elif unit == "M":
            duration += count * 2592000 # 30 days
        elif unit == "y":
            duration += count * 31536000 # 365 days

    if end != len(string):
        raise ValueError(f"unable to parse {string!r}")

    return duration


def format_time(seconds):
    """Format a number of seconds from epoch to a date and a time.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(seconds))


time_formats = (
    ("datetime", "%Y-%m-%d %H:%M:%S"),
    ("datetime", "%Y-%m-%d %H:%M"),
    ("datetime", "%Y%m%d%H%M"),
    ("date", "%Y-%m-%d"),
    ("date", "%Y%m%d"),
    ("time", "%H:%M:%S"),
    ("time", "%H:%M"),
    ("time", "%H%M")
)

def parse_time(string):
    """Convert a date and time or a duration to the corresponding number of
       seconds. A simple integer or float is taken as seconds since epoch.
    """
    try:
        return int(float(string))
    except ValueError:
        pass

    if len(string) >= 4:
        for typ, fmt in time_formats:
            try:
                time_obj = datetime.datetime.strptime(string, fmt)
            except ValueError:
                continue
            else:
                if typ == "time":
                    now = datetime.datetime.now()
                    today = datetime.date.today()
                    time_obj = time_obj.replace(year=today.year, month=today.month, day=today.day)
                    if time_obj > now:
                        time_obj -= datetime.timedelta(days=1)
                return int(time_obj.timestamp())

    try:
        return int(time.time() - parse_duration(string))
    except ValueError:
        raise ValueError(f"{string!r} is no valid time")
