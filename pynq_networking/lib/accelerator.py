#   Copyright (c) 2017, Xilinx, Inc.
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#
#   1.  Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#   3.  Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#   OR BUSINESS INTERRUPTION). HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
import subprocess
import struct
from cffi import FFI
from uuid import getnode
from socket import inet_aton
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
from wurlitzer import sys_pipes
from pynq import PL, MMIO
from .broker import ip_str_to_int, mac_str_to_int


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "yunq@xilinx.com"


CFFI_INTERFACE = """
void init_ethernet_raw(const char *interface, uint16_t myPort);
float read_sensor(volatile char * sensor);
void Top(int size, int count,
         unsigned long long macAddress,
         unsigned int ipAddress,
         unsigned int destIP,
         int destPort,
         unsigned short topicID,
         int qos,
         bool verbose,         
         volatile char * networkIOP,
         volatile char * sensor);
void sds_mmap(int phys, int length, void *virtual);
void *sds_alloc(size_t size);
"""
BITFILE = '/opt/python3.6/lib/python3.6/site-packages/pynq_networking/' \
          'overlays/mqttsn/mqttsn.bit'
SHARED_LIB = '/opt/python3.6/lib/python3.6/site-packages/pynq_networking' \
             '/overlays/mqttsn/lib_mqttsn.so'


class Accelerator:
    """Accelerator for constructing MQTTSN packets.

    This accelerator is tied to the hardware block built using SDSoC.

    Attributes
    ----------
    interface_string : str
        The FFI interface description of the overlay 
        (containing c-like prototypes)
    ffi : FFI
        The FFI object used by the overlay.
    dll_name : str
        This overlay assumes the dll filename is derived from bitfile name.

    """
    def __init__(self):
        if PL.bitfile_name != BITFILE:
            raise ValueError("mqttsn_publish.bit must be loaded.")

        self.interface_string = CFFI_INTERFACE
        self.ffi = FFI()
        self.dll_name = SHARED_LIB
        self.dll = None
        self.sensor_ptr = None

        self.ffi.cdef(self.interface_string)
        with sys_pipes():
            self.dll = self.ffi.dlopen(self.dll_name)

    def read_sensor(self, sensor_iop):
        """Read the value of a temperature sensor. """
        if self.sensor_ptr is None:
            self.sensor_ptr = self.map(sensor_iop.mmio)
        return self.dll.read_sensor(self.sensor_ptr)

    def init_ethernet_raw(self, interface, port=1884):
        """Initialize the Ethernet raw interface. """
        with sys_pipes():
            self.dll.init_ethernet_raw(interface.encode('utf-8'), port)

    def map(self, mmio):
        """Map the given mmio interface in a way that SDSoC can use."""
        virtaddr = self.ffi.from_buffer(mmio.mem)
        self.dll.sds_mmap(mmio.base_addr + mmio.virt_offset, mmio.length,
                          virtaddr)
        return virtaddr

    def publish_cffi(self, size, count, pl_mac_address, pl_ip_address,
                     server_ip_address, server_port_number,
                     topic_id, qos, verbose, net_iop, sensor_iop):
        """Publish data from the given temperature sensor to an MQTTSN server.

        This method will use the CFFI to control the accelerator.

        Parameters
        ----------
        size : int
            The size of frames to generate.
        count : int
            The number of publish events to complete.
        pl_mac_address : int/str
            The MAC Address of the PL accelerator (not the host MAC address).
        pl_ip_address : int/str
            The IP Address of the PL accelerator (not the host IP address).
        server_ip_address : int/str
            The IP Address of the MQTTSN server.
        server_port_number : int
            The port number of the MQTTSN server.
        topic_id : int
            The topic ID to publish on.
        qos : int
            The MQTTSN qos to use (0 means response is not required).
        verbose : int
            A non-zero value will get verbose debugging information.
        net_iop : NetworkIOP
            The network IOP object.
        sensor_iop : Pmod_TMP2
            The temperature sensor object.

        """
        pl_ip = pl_ip_address if type(pl_ip_address) is int \
            else ip_str_to_int(pl_ip_address)
        pl_mac = pl_mac_address if type(pl_mac_address) is int \
            else mac_str_to_int(pl_mac_address)
        server_ip = server_ip_address if type(server_ip_address) is int \
            else ip_str_to_int(server_ip_address)

        mac_address_arg = self.ffi.cast("unsigned long long", pl_mac)
        ip_address_arg = self.ffi.cast("unsigned int", pl_ip)
        server_ip_arg = self.ffi.cast("unsigned int", server_ip)
        with sys_pipes():
            net_iop_ptr = self.map(net_iop.mmio)
            sensor_iop_ptr = self.map(sensor_iop.mmio)
            ol.dll.Top(size, count, mac_address_arg, ip_address_arg,
                       server_ip_arg, server_port_number,
                       topic_id, qos, verbose,
                       net_iop_ptr, sensor_iop_ptr)

    def publish_mmio(self, size, count, pl_mac_address, pl_ip_address,
                     server_ip_address, server_port_number,
                     topic_id, qos, verbose, net_iop, sensor_iop):
        """Publish data from the given temperature sensor to an MQTTSN server.

        This method will use the MMIO to control the accelerator.

        Parameters
        ----------
        size : int
            The size of frames to generate.
        count : int
            The number of publish events to complete.
        pl_mac_address : int/str
            The MAC Address of the PL accelerator (not the host MAC address).
        pl_ip_address : int/str
            The IP Address of the PL accelerator (not the host IP address).
        server_ip_address : int/str
            The IP Address of the MQTTSN server.
        server_port_number : int
            The port number of the MQTTSN server.
        topic_id : int
            The topic ID to publish on.
        qos : int
            The MQTTSN qos to use (0 means response is not required).
        verbose : int
            A non-zero value will get verbose debugging information.
        net_iop : NetworkIOP
            The network IOP object.
        sensor_iop : Pmod_TMP2
            The temperature sensor object.

        """
        pl_ip = pl_ip_address if type(pl_ip_address) is int \
            else ip_str_to_int(pl_ip_address)
        pl_mac = pl_mac_address if type(pl_mac_address) is int \
            else mac_str_to_int(pl_mac_address)
        server_ip = server_ip_address if type(server_ip_address) is int \
            else ip_str_to_int(server_ip_address)

        _ = self.map(net_iop.mmio)
        net_iop_phys = net_iop.mmio.base_addr + net_iop.mmio.virt_offset
        _ = self.map(sensor_iop.mmio)

        acc_mmio = MMIO(0x83c00000, 0x10000)
        acc_mmio.write(0x10, 1)
        acc_mmio.write(0x18, pl_mac & 0xFFFFFFFF)
        acc_mmio.write(0x1c, pl_mac >> 32 + 1)
        acc_mmio.write(0x24, pl_ip)
        acc_mmio.write(0x2c, 1)
        acc_mmio.write(0x34, server_ip)
        acc_mmio.write(0x3c, server_port_number)
        acc_mmio.write(0x44, topic_id)
        acc_mmio.write(0x4c, qos)
        acc_mmio.write(0x54, 0x0)
        acc_mmio.write(0x5c, 1)
        acc_mmio.write(0x64, net_iop_phys)
        acc_mmio.write(0x6c, count)
        acc_mmio.write(0x74, size)
        acc_mmio.write(0x7c, 1)
        acc_mmio.write(0x84, verbose)  # verbose

        # execute the accelerator once to reset things
        acc_mmio.write(0x0, 1)
        status = acc_mmio.read(0x0)
        while status & 0x2 == 0:
            status = acc_mmio.read(0x0)

        # deassert reset
        acc_mmio.write(0x7c, 0)  # reset

        # wait for the events to complete
        events_completed = 0
        i = 0
        while events_completed < count:
            status = acc_mmio.read(0x0)
            while status & 0x4 == 0:
                status = acc_mmio.read(0x0)
            # set our inputs and start
            acc_mmio.write(0x2c, i)
            # valid message
            acc_mmio.write(0x5c, i % 2)
            # start
            acc_mmio.write(0x0, 1)
            i = i + 1
            events_completed = acc_mmio.read(0x8c)
            if i % 1000 == 0:
                print("status", status)
                print("events_completed:", events_completed)
                print("PublishesSent:", acc_mmio.read(0x94))

        print("calls", i)
        print("events_completed:", events_completed)
        print("PublishesSent:", acc_mmio.read(0x94))
        print("PacketsReceived:", acc_mmio.read(0x9c))
        print("PacketsSent:", acc_mmio.read(0xa4))
