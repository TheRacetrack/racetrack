.PHONY: setup run test

setup:
	pip install -r requirements.txt

run:
	EXTERNAL_PUB_URL="http://localhost:7205/pub" \
	EXTERNAL_LIFECYCLE_URL="http://localhost:7202/lifecycle" \
	LIFECYCLE_URL="http://localhost:7202/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	SITE_NAME=dev \
	python -u main.py

# Run dashboard on localhost, connected to other services running on docker
run-local-rt-docker:
	EXTERNAL_PUB_URL="http://localhost:7105/pub" \
	EXTERNAL_LIFECYCLE_URL="http://localhost:7102/lifecycle" \
	LIFECYCLE_URL="http://localhost:7102/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	SITE_NAME=dev \
	python -u main.py

test:
	pytest -vv --tb=short -ra $(test)
