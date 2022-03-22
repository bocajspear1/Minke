FROM debian:bullseye-slim AS builder
RUN apt-get -qq update \
&& apt-get -q install --assume-yes debootstrap fakechroot fakeroot
ARG MIRROR=http://deb.debian.org/debian
ARG SUITE=stretch
RUN mkdir /work
RUN fakeroot fakechroot debootstrap --foreign --variant=minbase --arch=mipsel "$SUITE" /work "$MIRROR"
RUN tar -czf rootfs.tar.gz /work 

FROM ubuntu:20.04

RUN apt-get -qq update \
&& DEBIAN_FRONTEND="noninteractive" apt-get -q install -y wget ninja-build build-essential libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev strace

ENV QEMU_VER="6.2.0"

WORKDIR /opt
RUN wget -q https://download.qemu.org/qemu-${QEMU_VER}.tar.xz 
RUN tar xJf qemu-${QEMU_VER}.tar.xz
COPY ptrace.patch /opt/ptrace.patch
RUN patch -u -b ./qemu-${QEMU_VER}/linux-user/syscall.c -i /opt/ptrace.patch

WORKDIR /opt/qemu-${QEMU_VER}

RUN ./configure --help 
RUN ./configure --target-list=mipsel-linux-user --static --disable-system --enable-linux-user 
RUN make -j 2 && make install

WORKDIR /opt

COPY --from=builder rootfs.tar.gz /opt/rootfs.tar.gz
RUN tar -zxf rootfs.tar.gz && mv work mipsel-root

RUN apt-get -qq update \
&& DEBIAN_FRONTEND="noninteractive" apt-get -q install -y sudo


COPY start.sh /usr/bin/start.sh
RUN chmod +x /usr/bin/start.sh

ENTRYPOINT ["/usr/bin/start.sh"]