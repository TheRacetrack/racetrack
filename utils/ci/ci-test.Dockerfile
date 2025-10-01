FROM ubuntu:focal

RUN apt-get update -y && apt-get install -y \
    python3.8 python3.8-dev python3.8-venv \
    make wget git gcc

# install Go
ENV GOPATH /root/go
ENV GO_VERSION 1.19
ENV GO_ARCH amd64
ENV PATH /usr/local/go/bin:$PATH
ENV PATH $GOPATH/bin:$PATH
ENV GOPROXY=https://proxy.golang.org
RUN wget -q https://storage.googleapis.com/golang/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz \
 && tar -C /usr/local/ -xf /go${GO_VERSION}.linux-${GO_ARCH}.tar.gz \
 && rm /go${GO_VERSION}.linux-${GO_ARCH}.tar.gz \
 && mkdir -p ${GOPATH}/src \
 && mkdir -p ${GOPATH}/bin
