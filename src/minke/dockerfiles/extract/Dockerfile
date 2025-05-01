FROM alpine:3.15

RUN apk add -U p7zip

COPY run.sh /opt/run.sh

RUN chmod +x /opt/run.sh

ENTRYPOINT ["/opt/run.sh"]