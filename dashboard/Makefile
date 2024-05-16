.PHONY: setup run test

setup:
	pip install -r requirements.txt
	pip install -e .

run:
	LIFECYCLE_URL="http://127.0.0.1:7202/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	SITE_NAME=dev \
	python -u dashboard/main.py

# Run dashboard on localhost, connected to other services running on docker
run-local-rt-docker:
	LIFECYCLE_URL="http://127.0.0.1:7102/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	SITE_NAME=dev \
	python -u dashboard/main.py

run-frontend:
	(cd dashboard-front && make run)

test:
	pytest -vv --tb=short -ra $(test)
