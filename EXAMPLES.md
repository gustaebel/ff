## Examples

### File plugin

Find all files that were changed within the last one and a half hours:

```sh
$ ff type=f time+=1h30m
```

Find all files whose modification time is newer than that of `foo`:

```sh
$ ff type=f mtime+={}foo
```

Find all files with the extension '.mp4' that are bigger than 100 megabytes:

```sh
$ ff ext=mp4 size+=100M
```

Find all text files.

```sh
$ ff text=yes
```

Find all text files that contain the substring `'foo'`.

```sh
$ ff lines:foo
```

List all files ordered by their size and print a JSON object for each one
containing their path name and their size:

```sh
$ ff type=f --sort size --output path,size --jsonl
```

List all files that have multiple hard links to their inode.

```sh
$ ff type=f links+1
```

### Media plugin

Find video files that are at least 1080 pixels high and order them
according to running time:

```sh
$ ff mtype=video height+=1080 --sort duration
```

Find files in the directory `Videos/` that end with `.mkv` or `.mp4` and are
between 720 and 1080 pixels high:

```sh
$ ff Videos/ {{ ext=mkv or ext=mp4 }} and {{ height+=720 and height-=1080 }}
```

This is equivalent:

```sh
$ ff Videos/ \( 'ext = mkv' or 'ext = mp4' \) and \( 'height >= 720' and 'height <= 1080' \)
```

### Git plugin

Store all files from the current directory that are tracked by `git(1)` in a
`tar(1)` archive:

```sh
$ ff type=f git.tracked=yes --sort --exec-batch tar cvzf git-tracked.tar.gz
```

### Introspection plugin

Find all python scripts in the Python-3.8.3 directory that import the _shutil_
module:

```sh
$ ff imports=shutil Python-3.8.3/
```

Find all python scripts that still use Python 2:

```sh
$ ff shebang:python2
```

Find all text files that contain a `FIXME` tag:

```sh
$ ff fixme=yes
```

Find all executables in `/usr/bin` that require the `libz.so.1` shared library:

```sh
$ ff sonames=libz.so.1 /usr/bin
```

### Filesystem

Print all files in the root filesystem but don't descend into remote filesystems:

```sh
$ ff / --exclude remote=yes
```

Find all mountpoints and print which filesystem they contain.

```sh
$ ff / type=d mount=yes --output fstype,path
```

### Tar archives

Find all tar archives that contain a file called `setup.py`.

```sh
$ ff members:setup.py
```
