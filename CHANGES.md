### Version 608 - (2023-12-30)

- Add --fail option.

### Version 607 - (2023-10-31)

- The -l/--limit option now also takes a <pagesize>,<page> argument.

### Version 606 - (2023-09-18)

- Add pseudofs attribute.

### Version 605 - (2023-09-17)

- Fix: Allow reading xattrs from directories.

### Version 604 - (2023-08-20)

- Add mpath, devname and fstype attributes to the file plugin.

### Version 603 - (2023-08-05)

- Fix dirname for files located directly in the root directory.

### Version 601 - (2021-08-21)

- Fix: Exception when using --color auto|always with unset LS_COLORS.

### Version 600 - (2021-04-09)

- Fix pattern matching in the filesystem root.

### Version 599 - (2021-04-09)

- Allow ignore files in root directory.

### Version 598 - (2021-04-09)

- Fix: Use correct plugin directories when used as a module.

### Version 597 - (2021-04-09)

- Add --ignore-files option.

### Version 596 - (2021-04-07)

- Fix: Month durations did not work.
- Fix a quirk with the cython build.

### Version 595 - (2021-04-04)

- Fix issues with directories containing large numbers of entries.

### Version 594 - (2021-04-04)

- Fix natural (version) sort order.

### Version 593 - (2021-04-04)

- Add natural (version) sort order.
- Fix: Using --exec together with --sort causes hang.

### Version 592 - (2020-10-18)

- Add --halt={never,soon,now} option.
- No longer allow empty -x/--exec and -X/--exec-batch options.
- Show statistics about failed processes for -x/--exec.

### Version 591 - (2020-10-03)

- Properly print usage errors.
- Detect nested directory arguments more accurately.

### Version 590 - (2020-09-13)

- Fix: Don't show a traceback for invalid -l/--limit values.

### Version 589 - (2020-08-07)

- Fix: file.empty attribute failed for inaccessible directories.

### Version 588 - (2020-08-06)

- Allow attribute access to Find() records.
- Warn about using --limit and not using --sort.
- Fix: Subsequent calls to Find() did not produce output.

### Version 587 - (2020-08-03)

- Improve readability of durations.
- Allow escaping { and } in command templates.

### Version 586 - (2020-07-22)

- Remove an optimization that no longer works.

### Version 585 - (2020-07-22)

- Allow slice notation with -l/--limit.
- Fix ignore files from parent directories.
- Do not call subprocesses when there are no results.
- Fix help formatting.

### Version 584 - (2020-07-11)

- Do not use human readable file.size with --count and --json.
- Fix ff.1 manpage.

### Version 583 - (2020-07-01)

- Improve Cython build process.

### Version 582 - (2020-06-29)

- Allow long options with an argument attached.

### Version 581 - (2020-06-28)

- No longer use argparse.

### Version 580 - (2020-06-28)

- Improve glob pattern matching.
- No longer show all debug messages by default.
- Documentation changes.

### Version 579 - (2020-06-28)

- Remove auto-detection of simple patterns.
- Change --directories to --directory with only single arguments.
- Fix: Don't fail if a file is not found or cannot be accessed.
- Fix: Detect empty sub expressions.

### Version 578 - (2020-06-24)

- Do not warn about "Permission denied" errors.

### Version 577 - (2020-06-23)

- Add --ndjson alias for --jsonl.

### Version 576 - (2020-06-21)

- Rename ff.Search to ff.Find.
- Fix placeholders inside arguments. Arguments are now allowed to contain more
  than one placeholder.
- Fix warnings from argument parsing.
- Fix missing attribute errors in -x/--exec.

### Version 575 - (2020-06-20)

- Speed improvements.

### Version 574 - (2020-06-19)

- Fix multiprocessing problems for cython build.

### Version 573 - (2020-06-19)

- Improve building with cython.
- Add compatibility with pypy.

### Version 572 - (2020-06-16)

- Move the main components to a new 'ff' package.

### Version 571 - (2020-06-16)

- Move 'xattrs' attribute to its own plugin.
- Move 'text' attribute to 'grep' plugin.
- Minor documentation changes.

### Version 570 - (2020-06-11)

- Optimize queries by regrouping tests.
- Speed up multiple use of the same plugin.
- git plugin: Increase performance.

### Version 569 - (2020-06-09)

- Add --clean-cache option.
- Minor documentation fixes.

### Version 568 - (2020-06-08)

- git plugin: Add dirty, repo and repo_dir attributes.
- Fix caching of filenames that contain bad characters.
- Improve error handling.

### Version 567 - (2020-06-06)

- Improve the manpage/help system.
- Rename --list-attributes, --list-plugins, --list-types to
  --help-attributes, --help-plugins, --help-types.

### Version 566 - (2020-06-05)

- Show help as manpages.
- Rename fs.fstype attribute to fs.type.
- Remove "fixme" plugin.

### Version 564 - (2020-06-04)

- file plugin: Add file.xattrs attribute.
- py plugin: Fix parsing imports from .py files.

