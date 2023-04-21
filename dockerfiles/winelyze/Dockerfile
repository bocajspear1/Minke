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

RUN wget -nv -O- https://dl.winehq.org/wine-builds/winehq.key | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add - \
    && echo "deb https://dl.winehq.org/wine-builds/ubuntu/ $(grep VERSION_CODENAME= /etc/os-release | cut -d= -f2) main" >> /etc/apt/sources.list \
    && dpkg --add-architecture i386

ARG WINE_BRANCH="stable=8.0.0.0~focal-1"
RUN apt-get update \
    && apt-cache search winehq-stable \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --install-recommends winehq-${WINE_BRANCH} \
    && rm -rf /var/lib/apt/lists/*

# Configure locale for unicode
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends x11-apps coreutils

ARG GECKO_VER="2.47.3"
RUN mkdir -p /usr/share/wine/gecko
RUN wget -nv -O /usr/share/wine/gecko/wine-gecko-${GECKO_VER}-x86.msi http://dl.winehq.org/wine/wine-gecko/${GECKO_VER}/wine-gecko-${GECKO_VER}-x86.msi
RUN wget -nv -O /usr/share/wine/gecko/wine-gecko-${GECKO_VER}-x86_64.msi http://dl.winehq.org/wine/wine-gecko/${GECKO_VER}/wine-gecko-${GECKO_VER}-x86_64.msi
ARG MONO_VER="7.4.0"
RUN mkdir -p /usr/share/wine/mono
RUN wget -nv -O /usr/share/wine/mono/wine-mono-${MONO_VER}-x86.msi http://dl.winehq.org/wine/wine-mono/${MONO_VER}/wine-mono-${MONO_VER}-x86.msi

COPY start.sh /usr/bin/start.sh
COPY screenshot.sh /usr/bin/screenshot.sh
COPY quiet.reg /tmp/quiet.reg

ARG USERNAME="default"
RUN mkdir -p /home/${USERNAME} && ls -la /home
RUN useradd ${USERNAME} -d /home/${USERNAME}
RUN chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}
RUN bash -c 'nohup /usr/bin/Xvfb :0 -screen 0 1024x768x8 &' && sudo --user ${USERNAME} bash -c 'DISPLAY=:0.0 wine hostname' && pkill Xvfb
RUN if [ -f "/tmp/.X0-lock" ]; then rm /tmp/.X0-lock; fi
RUN chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.wine/
ENTRYPOINT ["/usr/bin/start.sh"]