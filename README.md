## ff

### About

`ff` is a tool for searching the filesystem. It was originally inspired by
[fd](https://github.com/sharkdp/fd).

**NOTE: ff is in the early stages of development, expect things to break and
syntax to change.**

### Summary

`ff` is a tool for searching the filesystem. Its scope is similar to `find(1)`
and `fd(1)` but it tries to be more accessible and easier to use than `find`
and and more versatile and powerful than `fd`. It is inspired by and borrows
many ways of doing things from `fd`. It is written in
[Python >= 3.6](https://www.python.org/).

### Features

* Search by file attributes and file metadata(!).
* Simple yet powerful expression syntax.
* Flexible output options.
* Flexible sort options.
* Extendable by user plugins.
* Parallel search and processing.

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

This installs the python sources, the `ff` script, the man page and a set of
plugins.

### Developing plugins and debug mode

There is a template for new plugins to start from (`plugin_template.py`) with
exhaustive instructions and comments, so you can develop plugins for your own
needs.

Useful in that regard is `ff`'s debug mode. It can be activated by executing
the `libff` module.

```sh
$ python -m libff --debug info,cache ...
```

Debug mode produces lots of messages which can be limited to certain categories
using the `--debug category1,category2,...` option. On top of that, debug mode
activates many internal checks using `assert()`. Therefore, it is advisable to
use debug mode during plugin development.
