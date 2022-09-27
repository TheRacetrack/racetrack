FROM python:3.9-slim-bullseye

WORKDIR /src/fatman

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
COPY wrappers/python_wrapper/setup.py wrappers/python_wrapper/requirements.txt /src/python_wrapper/
RUN pip install -r /src/racetrack_client/requirements.txt \
  -r /src/racetrack_commons/requirements.txt \
  -r /src/python_wrapper/requirements.txt

COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
COPY wrappers/python_wrapper/fatman_wrapper/. /src/python_wrapper/fatman_wrapper/
RUN cd /src/racetrack_client && python setup.py develop &&\
  cd /src/racetrack_commons && python setup.py develop &&\
  cd /src/python_wrapper && python setup.py develop

ENV PYTHONPATH "/src/fatman/"
LABEL racetrack-component="fatman"
