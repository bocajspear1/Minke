FROM ubuntu:20.04

# Install prerequisites
RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        cabextract \
        git \
        gnupg \
        gosu \
        gpg-agent \
        locales \
        p7zip \
        pulseaudio \
        pulseaudio-utils \
        sudo \
        tzdata \
        unzip \
        wget \
        winbind \
        xvfb \
        zenity \
    && rm -rf /var/lib/apt/lists/*

# Install wine
ARG WINE_BRANCH="stable"
RUN wget -nv -O- https://dl.winehq.org/wine-builds/winehq.key | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add - \
    && echo "deb https://dl.winehq.org/wine-builds/ubuntu/ $(grep VERSION_CODENAME= /etc/os-release | cut -d= -f2) main" >> /etc/apt/sources.list \
    && dpkg --add-architecture i386 \
    && apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --install-recommends winehq-${WINE_BRANCH} \
    && rm -rf /var/lib/apt/lists/*

# Configure locale for unicode
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends x11-apps coreutils

ARG GECKO_VER="2.47.2"
RUN mkdir -p /usr/share/wine/gecko
RUN wget -nv -O /usr/share/wine/gecko/wine-gecko-${GECKO_VER}-x86.msi http://dl.winehq.org/wine/wine-gecko/${GECKO_VER}/wine-gecko-${GECKO_VER}-x86.msi
RUN wget -nv -O /usr/share/wine/gecko/wine-gecko-${GECKO_VER}-x86_64.msi http://dl.winehq.org/wine/wine-gecko/${GECKO_VER}/wine-gecko-${GECKO_VER}-x86_64.msi
ARG MONO_VER="7.0.0"
RUN mkdir -p /usr/share/wine/mono
RUN wget -nv -O /usr/share/wine/mono/wine-mono-${MONO_VER}-x86.msi http://dl.winehq.org/wine/wine-mono/${MONO_VER}/wine-mono-${MONO_VER}-x86.msi

COPY start.sh /usr/bin/start.sh
COPY screenshot.sh /usr/bin/screenshot.sh
COPY quiet.reg /tmp/quiet.reg
ENTRYPOINT ["/usr/bin/start.sh"]