FROM golang:1.22-alpine
ENV CGO_ENABLED=0
ENV GOOS=linux
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN go build /app/

FROM alpine:3.14.0
WORKDIR /
COPY --from=0 /app/pub .
CMD ["/pub"]

ARG GIT_VERSION
ENV GIT_VERSION ${GIT_VERSION}
EXPOSE 7005
LABEL racetrack-component="pub" git-version="${GIT_VERSION}"
