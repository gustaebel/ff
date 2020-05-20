## ff

### About

`ff` is a tool for searching the filesystem. It was inspired by
[fd](https://github.com/sharkdp/fd).

**`ff` is in the early stages of development, expect things to break and syntax
to change.**

### Summary

`ff` lets you search the filesystem using a sequence of expressions. Its scope
is similar to `find(1)` and `fd(1)` but it tries to be more accessible and
easier to use than `find` and and more versatile and powerful than `fd`.
It is inspired by and borrows many ways of doing things from `fd`. It is
written in [Python](https://www.python.org/).

It features parallel processing, many different ways of output, sorting, an
extensible plugin framework and many more things.

Examples are [here](https://github.com/gustaebel/ff/blob/master/EXAMPLES.md).


### Installation

To build and install `ff` simply type:

```sh
$ python setup.py install
```

This installs the python sources, the `ff` script, the man page and a set of
plugins.

To build a slightly faster version of `ff` you can use
[cython](https://cython.org/):

```sh
$ CYTHONIZE=yes python setup.py install
```


### Developing plugins and debug mode

There is a template for new plugins to start from (`plugin_template.py`) with
exhaustive instructions and comments, so you can develop plugins for your own
needs.

Useful in that regard is `ff`'s debug mode. It can be activated by starting
`ff` as a script using the `python` executable:

```sh
$ python /usr/bin/ff --debug info,cache ...
```

Debug mode produces lots of messages which can be limited to certain categories
using the `--debug category1,category2,...` option. On top of that, debug mode
activates many internal checks using `assert()`. Therefore, it is advisable to
use debug mode during plugin development.
