.PHONY: setup test run

setup:
	pip install -r requirements.txt
	python setup.py develop

test:
	cd tests && python -m coverage run --source=fatman_wrapper -m pytest -vv --tb=short -ra $(test) &&\
	python -m coverage report --show-missing --skip-empty --skip-covered

# Run local server wrapping sample model (outside docker)
run:
	CONFIG_FILE=tests/sample/config.yaml FATMAN_NAME=adder FATMAN_VERSION=0.0.1 \
	fatman_wrapper run tests/sample/adder_model.py

run-waiter:
	CONFIG_FILE=tests/sample/config.yaml FATMAN_NAME=waiter FATMAN_VERSION=0.0.1 \
	fatman_wrapper run tests/sample/waiter_model.py
