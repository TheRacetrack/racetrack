# Bake custom CA certificates into the image intended for private use
FROM ghcr.io/theracetrack/racetrack/lifecycle:latest
COPY ca-certificates/* /usr/local/share/ca-certificates/
RUN update-ca-certificates
