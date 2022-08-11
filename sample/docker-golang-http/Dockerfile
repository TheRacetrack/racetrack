FROM golang:1.16-alpine

COPY go.mod main.go /src/
WORKDIR /src/
RUN go mod download && go get ./...
CMD dummy-server

LABEL racetrack-component="fatman"
