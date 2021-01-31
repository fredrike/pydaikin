ifndef version
	version = patch
endif

.PHONY: default format white black lint test check clean pypireg pypi release

default: check

format: white
	isort setup.py bin/pydaikin pydaikin/*.py

white: black

black:
	black . pydaikin

lint: requirements.txt setup.py
	flake8
	pylint pydaikin

check: format lint

clean:
	rm -f *.pyc
	rm -rf .tox
	rm -rf *.egg-info
	rm -rf __pycache__
	rm -f pip-selfcheck.json
	rm -rf pytype_output

pypireg:
	python setup.py register -r pypi

pypi:
	rm -f dist/*.tar.gz
	python3 setup.py sdist
	twine upload dist/*.tar.gz

release:
	git diff-index --quiet HEAD -- && make check && bumpversion $(version) && git push --tags && git push && make pypi
