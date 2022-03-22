#!/bin/bash

# Remove env variables that might be an indicator
DIR=${TMPDIR}
unset TMPDIR
SAM=${SAMPLENAME}
unset SAMPLENAME
NAME=${USER}
unset USER
OUT=${LOG}
unset LOG

# Ensure we can resolve ourselves
HOSTNAME=$(hostname)
echo "127.0.0.1 ${HOSTNAME}" >> /etc/hosts

mkdir -p /home/${NAME}
useradd ${NAME} -d /home/${NAME}
chown -R ${NAME}:${NAME} /home/${NAME}

cp /tmp/${DIR}/${SAM} /tmp/${SAM}
chmod 777 /tmp/${SAM}

sudo -u ${NAME} /bin/bash -c "cp /tmp/${SAM} /home/${NAME}/${SAM}"
chown -R ${NAME}:${NAME} /home/${NAME}

sleep 5
echo "Starting sample"
sudo -u ${NAME} /bin/bash -c "cd /home/${NAME}; strace -f -s 1024 -x -v -tt -o /tmp/${OUT} qemu-mipsel -L /opt/mipsel-root /home/${NAME}/${SAM}"