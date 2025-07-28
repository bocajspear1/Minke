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

cat > ./docker.json <<EOL
{
  "userns-remap": "default",
  "iptables": false
}
EOL

sudo cp ./docker.json /etc/docker/daemon.json

sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

sudo systemctl restart docker
 
minke containers build --images winelyze --images qemu-arm --images qemu-mipsel --images qemu-powerpc

git clone https://github.com/bocajspear1/ports4u.git
cd ports4u
make build
cd ..

./scripts/unarchive_test_files.sh

mkdir ./logs

pytest -s 