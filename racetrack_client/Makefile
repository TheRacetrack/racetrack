.PHONY: setup test

setup:
		pip install -r requirements.txt
		python setup.py develop

test:
		cd tests && python -m pytest -vv --tb=short -ra $(test)

deploy-sample:
		racetrack deploy ../sample/python-class/ http://localhost:7202

deploy-sample-dashboard:
		racetrack deploy ../sample/python-ui-flask/ http://localhost:7202

release-clean:
		rm -rf build/
		rm -rf dist/
		rm -rf ./*.egg-info

release-test-pypi: release-clean
		python setup.py sdist bdist_wheel
		python -m twine upload --repository testpypi dist/*

release-pypi: release-clean
		python setup.py sdist bdist_wheel
		python -m twine upload dist/*
