RELEASE := ff $(shell cd ..; python -c 'from libff import __version__; print(__version__)')

.PHONY: man clean

all: man

man: ff.1

ff.1: ff.1.man ../libff/__init__.py ../libff/arguments.py ../libff/builtin/*.py render_help.py
	PYTHONPATH=.. python -O render_help.py ff.1.man ff.1.tmp
	txt2man -s $(subst .,,$(suffix $(suffix $@))) -t $(basename $(basename $<)) -r "$(RELEASE)" ff.1.tmp > ff.1
	rm ff.1.tmp

clean:
	rm *.1
