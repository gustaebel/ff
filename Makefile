lint:
	pylint --rcfile aux/pylintrc -j0 ff libff plugins

test:
	python tests/runtests.py

test-v:
	python tests/runtests.py -v

check: lint test

man:
	$(MAKE) -C doc
