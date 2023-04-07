front-setup:
	. ~/.nvm/nvm.sh &&\
	nvm install v16.20.0 &&\
	nvm use v16.20.0 &&\
	npm install

npm-run: 
	. ./nvm-activate.sh &&\
	npm run dev

npm-build:
	. ./nvm-activate.sh &&\
	npm run build

build-in-docker:
	DOCKER_BUILDKIT=1 docker build -t frontend-builder:latest -f build.Dockerfile .

build-in-docker-replace: build-in-docker
	set -e ;\
	rm -rf ../static/react ;\
	ID=$$(docker create frontend-builder:latest) ;\
	echo $$ID ;\
	docker cp "$$ID:/build/build" ../static/react/ ;\
	docker rm -v $$ID ;\
