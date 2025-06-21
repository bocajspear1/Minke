FROM debian:bullseye-slim AS basebuild
RUN apt-get -qq update \
&& apt-get -q install --assume-yes debootstrap fakechroot fakeroot
ARG MIRROR=https://archive.debian.org/debian-archive/debian
ARG SUITE=wheezy
RUN mkdir /work
RUN fakeroot fakechroot debootstrap --no-check-gpg --foreign --variant=minbase --arch=powerpc "$SUITE" /work "$MIRROR" 
RUN tar -czf rootfs.tar.gz /work 

FROM alpine:3.21 as qemubuild

RUN apk add -U wget musl-dev gcc g++ samurai make glib-dev glib-static libfdt pixman-dev zlib-dev zlib-static \
    strace python3 patch sudo bash flex bison linux-headers perl libc-dev

# RUN apt-get -qq update \
# && DEBIAN_FRONTEND="noninteractive" apt-get -q install -y wget ninja-build build-essential libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev strace python3-venv

ENV QEMU_VER="9.2.0-rc3"

WORKDIR /opt
RUN wget -q https://download.qemu.org/qemu-${QEMU_VER}.tar.xz 
RUN tar xJf qemu-${QEMU_VER}.tar.xz
COPY ptrace.patch /opt/ptrace.patch
RUN patch -u -b ./qemu-${QEMU_VER}/linux-user/syscall.c -i /opt/ptrace.patch

WORKDIR /opt/qemu-${QEMU_VER}

RUN mkdir /out
RUN ./configure --target-list=ppc-linux-user --static --disable-system --enable-linux-user
RUN make -j 2 && make install

FROM alpine:3.21

RUN mkdir /out
WORKDIR /opt

RUN apk add -U sudo bash strace

COPY --from=basebuild rootfs.tar.gz /opt/rootfs.tar.gz
RUN tar -zxf rootfs.tar.gz && mv work ppc-root && rm rootfs.tar.gz

COPY --from=qemubuild /usr/local/bin/qemu-ppc /usr/local/bin/qemu-ppc
RUN chmod +x /usr/local/bin/qemu-ppc

COPY start.sh /usr/bin/start.sh
RUN chmod +x /usr/bin/start.sh

RUN mkdir /opt/samples

ENTRYPOINT ["/usr/bin/start.sh"]