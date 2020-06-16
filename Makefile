check: isort lint test

isort:
	ff -HI ext=py -X isort --length-sort --multi-line 2 --diff --check-only

lint:
	pylint --rcfile config/pylintrc -j0 ff libff plugins

test:
	python tests/runtests.py

test-v:
	python tests/runtests.py -v

clean:
	ff -I ext=egg-info -X rm -rf
	rm -rf build dist
	rm -rf *.egg-info

create-pypi-pkg:
	python setup.py sdist bdist_wheel
	twine upload -r find-ff dist/*

create-arch-pkg:
	cd ~/box/packages/ff && arch-pkg publish

publish: create-pypi-pkg create-arch-pkg

man/ff.1: ff/*.py libff/*.py libff/builtin/*.py libff/manpage.template
	mkdir -p man
	python -c "from ff import Search; Search().registry.get_full_manpage().print()" > $@

man/ff.7: ff/*.py libff/*.py libff/builtin/*.py plugins/*.py
	mkdir -p man
	python -c "from ff import Search; Search().registry.get_attributes_manpage().print()" > $@

manpages: man/ff.1 man/ff.7
