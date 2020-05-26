check: lint test

lint:
	pylint --rcfile aux/pylintrc -j0 ff libff plugins

test:
	python tests/runtests.py

test-v:
	python tests/runtests.py -v

clean:
	ff -I ext=egg-info -X rm -rf
	rm -rf build dist
	rm -rf *.egg-info

man:
	$(MAKE) -C doc
