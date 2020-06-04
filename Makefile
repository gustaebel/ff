check: isort lint test

isort:
	ff -HI name=ff or ext=py -X isort --length-sort --multi-line 2 --diff --check-only

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

create-pypi-pkg:
	python setup.py sdist bdist_wheel
	twine upload -r find-ff dist/*

create-arch-pkg:
	cd ~/box/packages/ff && arch-pkg publish

publish: create-pypi-pkg create-arch-pkg

man:
	$(MAKE) -C doc
