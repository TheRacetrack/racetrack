FROM python:3.9-slim-bullseye

RUN pip install flask
COPY main.py /src/
WORKDIR /src/
CMD python -u main.py

LABEL racetrack-component="job"
