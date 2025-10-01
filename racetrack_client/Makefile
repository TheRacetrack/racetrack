.PHONY: setup test build

setup:
		pip install -r requirements.txt
		pip install -e .

test:
		cd tests && python -m pytest -vv --tb=short -ra $(test)

release-clean:
		rm -rf build/
		rm -rf dist/
		rm -rf ./*.egg-info

build:
		python setup.py sdist bdist_wheel

release-test-pypi: release-clean build
		python -m twine upload --repository testpypi dist/*

release-pypi: release-clean build
		python -m twine upload -u __token__ dist/*
