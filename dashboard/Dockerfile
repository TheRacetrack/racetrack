FROM python:3.9-slim-bullseye

WORKDIR /src/dashboard

RUN apt-get update -y && apt-get install -y postgresql-client

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
COPY dashboard/requirements.txt /src/dashboard/
RUN pip install -r /src/racetrack_client/requirements.txt \
  -r /src/racetrack_commons/requirements.txt \
  -r /src/dashboard/requirements.txt

COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
RUN cd /src/racetrack_client && python setup.py develop &&\
  cd /src/racetrack_commons && python setup.py develop

COPY dashboard/manage.py dashboard/main.py postgres/wait-for-postgres.sh /src/dashboard/
COPY dashboard/app/. /src/dashboard/app/
COPY dashboard/dashboard/. /src/dashboard/dashboard/

COPY docs/. /src/docs/

ENV DJANGO_DEBUG False
ENV DJANGO_SETTINGS_MODULE "app.settings"
CMD python -u main.py

EXPOSE 7003
STOPSIGNAL SIGINT
ARG GIT_VERSION
ARG DOCKER_TAG
ENV GIT_VERSION ${GIT_VERSION}
ENV DOCKER_TAG ${DOCKER_TAG}
LABEL racetrack-component="dashboard" git-version="${GIT_VERSION}"
