FROM golang:1.19-alpine

COPY go.mod main.go /src/
WORKDIR /src/
RUN go mod download && go get ./...
CMD dummy-server

LABEL racetrack-component="job"
