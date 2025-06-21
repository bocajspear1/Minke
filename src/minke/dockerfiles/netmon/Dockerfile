FROM alpine:3.20

RUN apk add -U tcpdump libcap-setcap iproute2 sudo iptables

RUN adduser -D -H netmon && mkdir /opt/out && chown netmon:netmon /opt/out

RUN addgroup -g 1001 pcap && addgroup netmon pcap \
&& chown 0:1001 /usr/bin/tcpdump \
&& chmod 750 /usr/bin/tcpdump \
&& setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump

COPY run.sh /run.sh

RUN chmod +x /run.sh

# USER netmon

ENTRYPOINT [ "/run.sh" ]

