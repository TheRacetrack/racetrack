.PHONY: setup build-sample run test

setup:
		pip install -r requirements.txt
		python setup.py develop

test:
		cd tests && python -m coverage run --source=image_builder -m pytest -vv --tb=short -ra $(test) &&\
		python -m coverage report --show-missing --skip-empty --skip-covered

build-sample:
		cd ../sample/python-class && image_builder build

run:
		 CONFIG_FILE=tests/sample/local.yaml image_builder serve
