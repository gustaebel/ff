## Examples

```sh
# Find all files that were changed within the last one and a half hours.

$ ff type=f time+=1h30m
```

```sh
# Find all files whose modification time is newer than that of `foo`.

$ ff type=f mtime+={}foo
```

```sh
# Find all files with the extension '.mp4' that are bigger than 100 megabytes.

$ ff ext=mp4 size+=100M
```

```sh
# List all files ordered by their size and print a JSON object for each one
# containing their path name and their size.

$ ff type=f -S size -o path,size --jsonl
```

```sh
# Find video files that are at least 1080 pixels high and order them
# according to running time.

$ ff class=video height+=1080 -S duration
```

```sh
# Find files in the directory `Videos/` that end with `.mkv` or `.mp4` and are
# at between 720 and 1080 pixels high.

$ ff Videos/ {{ ext=mkv or ext=mp4 }} and {{ height+=720 and height-=1080 }}

This is equivalent:

$ ff Videos/ \( 'ext = mkv' or 'ext = mp4' \) and \( 'height >= 720' and 'height <= 1080' \)
```

```sh
# Store all files from the current directory that are tracked by `git(1)` in a
# `tar(1)` archive.

$ ff type=f git.tracked=yes -S -X tar cvzf git-tracked.tar.gz
```

