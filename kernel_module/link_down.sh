#!/bin/bash

IFACE="pynq0"

sudo ip link set dev ${IFACE} down
sudo rmmod pynqenet
