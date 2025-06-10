FROM alpine:3.15

RUN apk add -U p7zip

COPY run.sh /opt/run.sh

RUN chmod +x /opt/run.sh

RUN mkdir /opt/samples

ENTRYPOINT ["/opt/run.sh"]