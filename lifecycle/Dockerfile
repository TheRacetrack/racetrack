FROM python:3.10-slim-bullseye

# install Docker CLI
RUN apt-get update -y && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    postgresql-client \
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
    /home/racetrack/.local/lib/python3.10/site-packages

# install kubectl
RUN curl -L "https://dl.k8s.io/release/v1.26.2/bin/linux/amd64/kubectl" \
    -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

WORKDIR /src/lifecycle

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
COPY lifecycle/setup.py lifecycle/requirements.txt postgres/wait-for-postgres.sh postgres/wait-for-migration.sh /src/lifecycle/
RUN pip install -r /src/racetrack_client/requirements.txt \
  -r /src/racetrack_commons/requirements.txt \
  -r /src/lifecycle/requirements.txt

COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
COPY lifecycle/lifecycle/. /src/lifecycle/lifecycle/
RUN cd /src/racetrack_client && python setup.py develop &&\
  cd /src/racetrack_commons && python setup.py develop &&\
  cd /src/lifecycle && python setup.py develop

RUN chmod 777 -R /src/lifecycle/lifecycle/django

ENV DJANGO_SETTINGS_MODULE "lifecycle.django.app.settings"
CMD ["python", "-u", "-m", "lifecycle", "serve"]

EXPOSE 7002
STOPSIGNAL SIGTERM
ARG GIT_VERSION
ARG DOCKER_TAG
ENV GIT_VERSION ${GIT_VERSION}
ENV DOCKER_TAG ${DOCKER_TAG}
LABEL racetrack-component="lifecycle" git-version="${GIT_VERSION}"
