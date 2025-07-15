#!/bin/sh

FILE=$1
ARGS=$2

if [ ! -z "$ARGS" ]; then
    curl -XPOST -k -F sample=@${1} -F arguments="$ARGS" http://localhost:8000/api/v1/samples/submit
else
    curl -XPOST -k -F sample=@${1} http://localhost:8000/api/v1/samples/submit
fi


echo ""