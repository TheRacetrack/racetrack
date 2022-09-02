FROM python:3.8-slim-buster

# install Docker CLI
RUN apt-get update -y && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg &&\
    echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&\
    apt-get update -y && apt-get install -y docker-ce-cli

RUN mkdir -p -m 777 /var/log/racetrack/image-builder/build-logs /src/workspaces /src/.plugins /.docker

WORKDIR /src/
COPY .dockerignore /src/
COPY wrappers/docker/. /src/wrappers/docker/

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
COPY image_builder/setup.py image_builder/requirements.txt /src/image_builder/
RUN pip install -r /src/racetrack_client/requirements.txt \
  -r /src/racetrack_commons/requirements.txt \
  -r /src/image_builder/requirements.txt

COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
COPY image_builder/image_builder/. /src/image_builder/image_builder/
RUN cd /src/racetrack_client && python setup.py develop &&\
  cd /src/racetrack_commons && python setup.py develop &&\
  cd /src/image_builder && python setup.py develop

CMD python -u -m image_builder serve

EXPOSE 7001
ARG GIT_VERSION
ARG DOCKER_TAG
ENV GIT_VERSION ${GIT_VERSION}
ENV DOCKER_TAG ${DOCKER_TAG}
LABEL racetrack-component="image-builder" git-version="${GIT_VERSION}"
