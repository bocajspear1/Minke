#!/bin/sh

docker kill $(docker ps -q)
docker container prune