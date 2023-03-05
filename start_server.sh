#!/bin/sh
. ./venv/bin/activate

if [ ! -f key.pem ]; then
    echo "Generating self-signed key"
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
fi

./venv/bin/gunicorn minke.server:app --certfile=cert.pem --keyfile=key.pem --bind 0.0.0.0:5051 --access-logfile ./server.log