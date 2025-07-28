#!/bin/bash

set -e

python3 -m venv ./venv
source ./venv/bin/activate

pip3 install pdm

pdm install

pdm install -G test

cat > ./config.json <<EOL
{
    "access_key": "atestkey",
    "max_concurrent": 2,
    "username": "testuser",
    "log_dir": "./logs",
    "log_level": "debug"
}
EOL
 
minke containers build --images winelyze --images qemu-arm --images qemu-mipsel --images qemu-powerpc

./scripts/unarchive_test_files.sh

pytest -s 