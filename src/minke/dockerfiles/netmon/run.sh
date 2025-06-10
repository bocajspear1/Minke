#!/bin/sh

ip route add default via $GATEWAY
sudo -u netmon tcpdump -U -i eth0 -s 65535 -w /opt/out/traffic.pcap
