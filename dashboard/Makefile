.PHONY: setup run test

setup:
	pip install -r requirements.txt
	python setup.py develop

run:
	LIFECYCLE_URL="http://localhost:7202/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	SITE_NAME=dev \
	python -u dashboard/main.py

# Run dashboard on localhost, connected to other services running on docker
run-local-rt-docker:
	LIFECYCLE_URL="http://localhost:7102/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	SITE_NAME=dev \
	python -u dashboard/main.py

run-frontend:
	(cd dashboard-front && make npm-run)

test:
	pytest -vv --tb=short -ra $(test)
