#!/bin/sh
cd builder
DOCKER_BUILDKIT=1 docker build --target artifact --output type=local,dest=. .
cd ..