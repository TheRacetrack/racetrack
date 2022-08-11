FROM python:3.8-slim-buster

RUN pip install flask
COPY main.py /src/
WORKDIR /src/
CMD python -u main.py

LABEL racetrack-component="fatman"
