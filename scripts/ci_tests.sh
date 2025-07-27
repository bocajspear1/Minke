#!/bin/bash

set -e

python3 -m venv ./venv
source ./venv/bin/activate

pip3 install pdm

pdm install

pdm install -G test
 
minke containers build --images winelyze --images qemu-arm --images qemu-mipsel --images qemu-powerpc

./scripts/unarchive_test_files.sh

pytest -s 