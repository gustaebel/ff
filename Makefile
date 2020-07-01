check: isort lint test

isort:
	python -m ff -HI ext=py -X isort --length-sort --multi-line 2 --diff --check-only

lint:
	python -m ff ext=so libff/ -x rm
	pylint --rcfile config/pylintrc -j0 ff libff plugins

test:
	python tests/runtests.py

test-v:
	python tests/runtests.py -v

inplace:
	python setup-cython.py build_ext -j8 --inplace

clean:
	rm -rf build dist
	rm -rf *.egg-info
	rm -rf __pycache__
	python -m ff ext=so or ext=c libff/ -x rm

create-pypi-pkgs:
	python setup.py sdist
	python setup.py bdist_wheel

upload: create-pypi-pkgs
	twine upload -r find-ff dist/*

create-arch-pkg:
	cd ~/box/packages/ff && arch-pkg publish

publish: upload create-arch-pkg

man/ff.1: ff/*.py libff/*.py libff/builtin/*.py libff/manpage.template
	mkdir -p man
	python -c "from ff import Find; Find().registry.get_full_manpage().print()" > $@

man/ff.7: ff/*.py libff/*.py libff/builtin/*.py plugins/*.py
	mkdir -p man
	python -c "from ff import Find; Find().registry.get_attributes_manpage().print()" > $@

manpages: man/ff.1 man/ff.7
