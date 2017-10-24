#!/bin/bash

CURR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
IFACE="pynq0"

sudo insmod ${CURR_DIR}/src/pynqenet.ko pynq_dma_base=40400000
sudo ip link set dev ${IFACE} up
sudo ip link set dev ${IFACE} master br0
