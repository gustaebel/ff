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

from libff.plugin import *

pymediainfo = None


class Medium(Plugin):
    """Plugin that gives access to media related information like image format,
       running time, mp3 tags, etc. Requires the 'pymediainfo' module.
    """

    use_cache = True

    attributes = [
        ("duration", Duration, "The duration of a medium (audio, video) in seconds."),
        ("artist", String, "The artist audio tag of the file."),
        ("album", String, "The album audio tag of the file."),
        ("title", String, "The title audio tag of the file."),
        ("genre", String, "The genre audio tag of the file."),
        ("date", String, "The date audio tag of the file."),
        ("format", String, "The format of an image ('png', 'jpeg', etc.) in case the file is an "\
                           "image."),
        ("width", Number, "The width of a visual medium (image, video) in pixel."),
        ("height", Number, "The height of a visual medium (image, video) in pixel.")
    ]

    @classmethod
    def setup(cls):
        # pylint:disable=global-statement,import-outside-toplevel
        global pymediainfo
        import pymediainfo as module
        pymediainfo = module

    def prepare_tracks(self, entry):
        """Prepare a more accessible structure of tracks from a media file.
        """
        try:
            tracks = {}
            for track in pymediainfo.MediaInfo.parse(entry.path,
                    encoding_errors="backslashreplace").tracks:
                track_type = track.track_type.lower()
                if track_type in ("audio", "video", "image") and track_type not in tracks:
                    tracks[track_type] = track
                elif track_type == "general":
                    tracks.setdefault(track_type, []).append(track)
            return tracks

        except (OSError, RuntimeError):
            raise NoData

    def can_handle(self, entry):
        return entry.mime.split("/", 1)[0] in set(["image", "audio", "video"])

    def process(self, entry):
        tracks = self.prepare_tracks(entry)

        audio_track = tracks.get("audio")
        video_track = tracks.get("video")
        image_track = tracks.get("image")

        # Extract available audio tags.
        for track in tracks.get("general", []):
            for key, attr in (("artist", "performer"), ("album", "album"), ("title", "title"),
                    ("genre", "genre"), ("date", "recorded_date")):
                value = getattr(track, attr, "")
                if value:
                    yield key, value

        # Extract the width and height of a video or an image. If there are
        # both video and image streams give precedence to video.
        if video_track is not None:
            if video_track.height is not None and video_track.width is not None:
                yield "width", video_track.width
                yield "height", video_track.height

        elif image_track is not None:
            if image_track.format is not None:
                yield "format", image_track.format.lower()
            if image_track.height is not None and image_track.width is not None:
                yield "width", image_track.width
                yield "height", image_track.height

        # Extract the duration of an audio or video stream.
        for track in (video_track, audio_track):
            if track is None:
                continue

            duration = track.duration
            if duration is not None:
                if isinstance(duration, str):
                    duration = float(duration)
                yield "duration", int(duration / 1000)
