#!/bin/bash

for bridge in $(sudo ovs-vsctl list bridge | grep name | cut -d":"  -f2 | sed 's/^[ ]+//'); do
    echo "Removing bridge $bridge"
    sudo ovs-vsctl del-br $bridge
done