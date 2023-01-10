FROM locustio/locust:2.5.0

USER root

RUN pip3 install python-dotenv

COPY racetrack_client/setup.py racetrack_client/requirements.txt racetrack_client/README.md /src/racetrack_client/
RUN pip install -r /src/racetrack_client/requirements.txt
COPY racetrack_client/racetrack_client/. /src/racetrack_client/racetrack_client/
RUN cd /src/racetrack_client && python setup.py develop

COPY racetrack_commons/setup.py racetrack_commons/requirements.txt /src/racetrack_commons/
RUN pip install -r /src/racetrack_commons/requirements.txt
COPY racetrack_commons/racetrack_commons/. /src/racetrack_commons/racetrack_commons/
RUN cd /src/racetrack_commons && python setup.py develop

COPY tests/stress/locustfile.py /home/locust/
