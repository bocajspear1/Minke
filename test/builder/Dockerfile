FROM ubuntu:20.04 as builder

RUN apt-get -qq update \
&& DEBIAN_FRONTEND="noninteractive" apt-get -q install -y make gcc-mingw-w64 gcc gcc-9-multilib gcc-arm-linux-gnueabi gcc-aarch64-linux-gnu gcc-mips-linux-gnu gcc-mipsel-linux-gnu gcc-mips64-linux-gnuabi64

WORKDIR /opt

RUN apt-get -qq update \
&& DEBIAN_FRONTEND="noninteractive" apt-get -q install -y  wget
RUN wget https://go.dev/dl/go1.18.linux-amd64.tar.gz
RUN rm -rf /usr/local/go && tar -C /usr/local -xzf go1.18.linux-amd64.tar.gz

ENV PATH=$PATH:/usr/local/go/bin

COPY Makefile .
COPY test.c .
COPY test.go .
COPY test-win.c .
COPY test-win.go .
COPY test-dll.c .

RUN mkdir /tmp/out && make

FROM scratch as artifact
COPY --from=builder /tmp/out /out