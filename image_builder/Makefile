.PHONY: setup build-sample run test

setup:
		pip install -r requirements.txt
		pip install -e .

test:
		cd tests && python -m pytest -vv --tb=short -ra $(test)

build-sample:
		cd ../sample/python-class && image_builder build

run:
		 CONFIG_FILE=tests/sample/local.yaml image_builder serve
