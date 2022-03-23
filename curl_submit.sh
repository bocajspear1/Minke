#!/bin/sh
curl -XPOST -k -F sample=@${1} https://localhost:5051/api/v1/samples/submit