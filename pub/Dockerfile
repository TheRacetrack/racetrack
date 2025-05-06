FROM golang:1.22-alpine AS build

ENV CGO_ENABLED=0
ENV GOOS=linux
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN go build /app/

FROM build AS debug-build

RUN go install -ldflags "-w -extldflags '-static'" github.com/go-delve/delve/cmd/dlv@v1.24.2
RUN go build -gcflags 'all=-N -l' /app/

FROM alpine:3.14.0 AS debug

WORKDIR /app
COPY --from=debug-build /app .
COPY --from=debug-build /go/bin/dlv /usr/bin/

ARG GIT_VERSION
ENV GIT_VERSION=${GIT_VERSION}
EXPOSE 7005
LABEL racetrack-component="pub" git-version="${GIT_VERSION}"

CMD ["dlv", "exec", "pub", "--headless=true", "--api-version=2", "--listen=:12345", "--accept-multiclient", "--continue"]

FROM alpine:3.14.0

WORKDIR /
COPY --from=build /app/pub .

ARG GIT_VERSION
ENV GIT_VERSION=${GIT_VERSION}
EXPOSE 7005
LABEL racetrack-component="pub" git-version="${GIT_VERSION}"

CMD ["/pub"]