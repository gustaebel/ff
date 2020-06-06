check: isort lint test

isort:
	ff -HI name=ff or ext=py -X isort --length-sort --multi-line 2 --diff --check-only

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

man/ff.1: libff/*.py libff/builtin/*.py
	mkdir -p man
	python -c "from libff.search import Search; Search().registry.get_full_help().print()" > man/ff.1

man/ff-attributes.7: libff/*.py libff/builtin/*.py
	mkdir -p man
	python -c "from libff.search import Search; Search().registry.get_attributes_help().print()" > man/ff-attributes.7

manpages: man/ff.1 man/ff-attributes.7
