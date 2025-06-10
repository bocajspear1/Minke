#!/bin/bash

# Remove env variables that might be an indicator
DIR=${TMPDIR}
unset TMPDIR
SAM=${SAMPLENAME}
unset SAMPLENAME
NAME=${USER}
unset USER
SCR=${SCREENSHOT}
unset SCREENSHOT
OUT=${LOG}
unset LOG


# Ensure we can resolve ourselves
HOSTNAME=$(hostname)
echo "127.0.0.1 ${HOSTNAME}" >> /etc/hosts

nohup /usr/bin/Xvfb :0 -screen 0 1024x768x8 &

ps aux

echo "Doing a regedit"
chmod 777 /tmp/quiet.reg
sudo --user ${NAME} /bin/bash -c "DISPLAY=:0.0 wine regedit /tmp/quiet.reg"
rm /tmp/quiet.reg

echo "Running as ${NAME}"
echo "Running screenshot script"
sudo --user ${NAME} /bin/bash -c "nohup /usr/bin/screenshot.sh ${SCR} &"
echo "Copying in sample"
sudo --user ${NAME} /bin/bash -c "cp ${DIR}/* /home/${NAME}/.wine/drive_c/users/${NAME}/"
ls -la /home/${NAME}/.wine/drive_c/users/
# chown -R ${NAME}:${NAME} /home/${NAME}/.wine/drive_c/

sleep 4
echo "Starting sample"
sudo --user ${NAME} /bin/bash -c "cd /home/${NAME}/.wine/drive_c/users/${NAME}/; DISPLAY=:0.0 WINEDEBUG='+loaddll,+relay,+pid' wineconsole C:\\\\users\\\\${NAME}\\\\${SAM} 2> /tmp/${OUT}"