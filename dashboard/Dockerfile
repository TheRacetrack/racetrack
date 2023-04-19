FROM node:16.20 AS frontend-builder

WORKDIR /build
COPY dashboard/dashboard-front/index.html \
  dashboard/dashboard-front/env.d.ts \
  dashboard/dashboard-front/package.json \
  dashboard/dashboard-front/package-lock.json \
  dashboard/dashboard-front/tsconfig.json \
  dashboard/dashboard-front/tsconfig.node.json \
  dashboard/dashboard-front/vite.config.js \
  /build/
RUN npm install

COPY dashboard/dashboard-front/public /build/public
COPY dashboard/dashboard-front/src /build/src

RUN npm install && npm run build


FROM python:3.9-slim-bullseye

WORKDIR /src/dashboard

RUN apt-get update -y && apt-get install -y \
  curl dnsutils vim &&\
  rm -rf /var/lib/apt/lists/*
# apt cache is cleaned automatically, see /etc/apt/apt.conf.d/docker-clean

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
COPY dashboard/setup.py dashboard/requirements.txt /src/dashboard/
RUN pip install -r /src/racetrack_client/requirements.txt \
  -r /src/racetrack_commons/requirements.txt \
  -r /src/dashboard/requirements.txt

COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
RUN cd /src/racetrack_client && python setup.py develop &&\
  cd /src/racetrack_commons && python setup.py develop &&\
  cd /src/dashboard && python setup.py develop

COPY dashboard/dashboard/. /src/dashboard/dashboard/

COPY docs/. /src/docs/

COPY --from=frontend-builder /build/dist /src/dashboard/static/

CMD python -u dashboard/main.py

EXPOSE 7003
STOPSIGNAL SIGINT
ARG GIT_VERSION
ARG DOCKER_TAG
ENV GIT_VERSION ${GIT_VERSION}
ENV DOCKER_TAG ${DOCKER_TAG}
LABEL racetrack-component="dashboard" git-version="${GIT_VERSION}"
