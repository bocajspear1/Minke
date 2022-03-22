FROM ubuntu:20.04

RUN apt-get -qq update \
&& DEBIAN_FRONTEND="noninteractive" apt-get -q install -y wget

WORKDIR /opt
RUN wget https://github.com/horsicq/DIE-engine/releases/download/3.04/die_3.04_Ubuntu_20.04_amd64.deb

RUN dpkg -i /opt/die_*.deb || true

RUN DEBIAN_FRONTEND="noninteractive" apt-get -q install -y -f

COPY run.sh /opt/run.sh

RUN chmod +x /opt/run.sh

ENTRYPOINT ["/opt/run.sh"]