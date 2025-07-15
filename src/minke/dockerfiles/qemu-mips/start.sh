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
adduser ${NAME} -h /home/${NAME} -D
chown -R ${NAME}:${NAME} /home/${NAME}

sudo -u ${NAME} /bin/bash -c "cp ${DIR}/* /home/${NAME}/"
chown -R ${NAME}:${NAME} /home/${NAME}
chmod 777 /home/${NAME}/${SAM}

sleep 4
echo "Starting sample"
# sudo -u ${NAME} /bin/bash -c "cd /home/${NAME}; strace -f -s 1024 -x -v -tt -o /tmp/${OUT} qemu-mips -L /opt/mips-root /home/${NAME}/${SAM}"
sudo -u ${NAME} /bin/bash -c "cd /home/${NAME}; strace -f -s 1024 -xx -v -tt -o /tmp/${OUT} qemu-mips -L /opt/mips-root /home/${NAME}/${SAM} ${ARGS}"