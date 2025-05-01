#!/bin/bash

PATH=$1

/usr/bin/mkdir /tmp/${PATH}
while :; do
    timestamp=$(/usr/bin/date +%s);
    DISPLAY=:0.0 /usr/bin/xwd -root -silent -out /tmp/${PATH}/${timestamp}.xscr;
    /usr/bin/sleep 2
done;