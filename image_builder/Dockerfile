FROM python:3.11-slim-bullseye AS base

# install Docker CLI
RUN apt-get update -y && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    dnsutils \
    vim
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg &&\
    echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&\
    apt-get update -y && apt-get install -y docker-ce-cli &&\
    rm -rf /var/lib/apt/lists/*
# apt cache is cleaned automatically, see /etc/apt/apt.conf.d/docker-clean

RUN useradd -u 100000 -m racetrack &&\
  mkdir -p -m 777 \
    /home/racetrack/.docker \
    /home/racetrack/.local/lib/python3.10/site-packages \
    /var/log/racetrack/image-builder/build-logs \
    /src/workspaces

WORKDIR /src/
COPY .dockerignore /src/

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
COPY image_builder/setup.py image_builder/requirements.txt /src/image_builder/
RUN pip install -r /src/racetrack_client/requirements.txt \
  -r /src/racetrack_commons/requirements.txt \
  -r /src/image_builder/requirements.txt

COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
COPY image_builder/image_builder/. /src/image_builder/image_builder/
RUN cd /src/racetrack_client && pip install -e . &&\
  cd /src/racetrack_commons && pip install -e . &&\
  cd /src/image_builder && pip install -e .

EXPOSE 7001
STOPSIGNAL SIGTERM
ARG GIT_VERSION
ARG DOCKER_TAG
ENV GIT_VERSION ${GIT_VERSION}
ENV DOCKER_TAG ${DOCKER_TAG}
LABEL racetrack-component="image-builder" git-version="${GIT_VERSION}"

FROM base AS debug

RUN pip install debugpy
CMD ["python", "-u", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "image_builder", "serve"]

FROM base

CMD ["python", "-u", "-m", "image_builder", "serve"]