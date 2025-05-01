#!/bin/sh
curl -XPOST -k -F sample=@${1} http://localhost:8000/api/v1/samples/submit