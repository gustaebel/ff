## ff

### About

`ff` is a tool for finding files in the filesystem.

**NOTE: ff is in the early stages of development, expect things to break and
syntax to change.**

### Summary

`ff` is a tool for finding files in the filesystem that all share a set of
common features. Its scope is similar to `find(1)` and `fd(1)` but it aims at
being more accessible and easier to use than `find` and more versatile and
powerful than `fd`. It is written in [Python >= 3.6](https://www.python.org/).

### Features

* Search by file attributes.
* Search in a wide variety of file metadata.
* Simple yet powerful expression syntax.
* Flexible output options.
* Flexible sort options.
* Extendable by user plugins.
* Parallel search and processing.
* Usable in scripts with a Python API.

### Examples

Store all files from the current directory that are tracked by `git(1)` in a
`tar(1)` archive:

```sh
$ ff type=f git.tracked=yes --sort --exec-batch tar cvzf git-tracked.tar.gz
```

Find files in the directory `Videos/` that end with `.mkv` or `.mp4` and are
between 720 and 1080 pixels high:

```sh
$ ff Videos/ {{ ext=mkv or ext=mp4 }} and {{ height+=720 and height-=1080 }}
```

More examples are [here](https://github.com/gustaebel/ff/blob/master/EXAMPLES.md).

### Installation

To build and install `ff` simply type:

```sh
$ python setup.py install
```

or

```sh
$ pip install find-ff
```

Building with [Cython](https://cython.org/) is also supported. Cython >= 3.0 is
required. Depending on the set of arguments this may offer a significant
speed-up.

```sh
$ python setup-cython.py install
```

### Python API

You can use `ff`'s query capabilities in your own scripts:

```python
from ff import Find

for entry in Find("type=f git.tracked=yes", directories=["/home/user/project"], sort=["path"]):
    print(entry["relpath"])
```

### Developing plugins and debug mode

There is a template for new plugins to start from (`plugin_template.py`) with
exhaustive instructions and comments, so you can develop plugins for your own
needs.

Useful in that regard is `ff`'s debug mode. It can be activated by executing
the `ff` module.

```sh
$ python -m ff --debug info,cache ...
```

Debug mode produces lots of messages which can be limited to certain categories
using the `--debug category1,category2,...` option. On top of that, debug mode
activates many internal checks using `assert()`. Therefore, it is advisable to
use debug mode during plugin development.
