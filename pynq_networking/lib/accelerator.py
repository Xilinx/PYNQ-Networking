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
from site import getsitepackages
from cffi import FFI
from uuid import getnode
from socket import inet_aton
import logging
logging.getLogger("kamene.runtime").setLevel(logging.ERROR)
from kamene.all import *
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

PYNQ_NETWORKING_PATH = os.path.join(getsitepackages()[0], 'pynq_networking')
MQTTSN_OVERLAY_PATH = os.path.join(PYNQ_NETWORKING_PATH, 'overlays','mqttsn')

BITFILE = os.path.join(MQTTSN_OVERLAY_PATH, 'mqttsn.bit')
SHARED_LIB = os.path.join(MQTTSN_OVERLAY_PATH, 'lib_mqttsn.so')


class Accelerator:
    """Accelerator for constructing MQTTSN packets.

    This accelerator is tied to the hardware block built using SDSoC.
    
    The following is a table of the memory mapped registers:
AXILiteS	
0x00	Control signals
bit 0 - ap_start (Read/Write/COH)
bit 1 - ap_done (Read/COR)
bit 2 - ap_idle (Read)
bit 3 - ap_ready (Read)
bit 7 - auto_restart (Read/Write)
others - reserved
0x04	Global Interrupt Enable Register
bit 0 - Global Interrupt Enable (Read/Write)
others - reserved
0x08	IP Interrupt Enable Register (Read/Write)
bit 0 - Channel 0 (ap_done)
bit 1 - Channel 1 (ap_ready)
others - reserved
0x0c	IP Interrupt Status Register (Read/TOW)
bit 0 - Channel 0 (ap_done)
bit 1 - Channel 1 (ap_ready)
others - reserved
0x10	Data signal of b
bit 0 - b[0] (Read/Write)
others - reserved
0x14	reserved
0x18	Data signal of macAddress_V
bit 31~0 - macAddress_V[31:0] (Read/Write)
0x1c	Data signal of macAddress_V
bit 15~0 - macAddress_V[47:32] (Read/Write)
others - reserved
0x20	reserved
0x24	Data signal of ipAddress_V
bit 31~0 - ipAddress_V[31:0] (Read/Write)
0x28	reserved
0x2c	Data signal of i
bit 31~0 - i[31:0] (Read/Write)
0x30	reserved
0x34	Data signal of destIP_V
bit 31~0 - destIP_V[31:0] (Read/Write)
0x38	reserved
0x3c	Data signal of destPort
bit 31~0 - destPort[31:0] (Read/Write)
0x40	reserved
0x44	Data signal of topicID_V
bit 15~0 - topicID_V[15:0] (Read/Write)
others - reserved
0x48	reserved
0x4c	Data signal of qos
bit 31~0 - qos[31:0] (Read/Write)
0x50	reserved
0x54	Data signal of message
bit 31~0 - message[31:0] (Read/Write)
0x58	reserved
0x5c	Data signal of validMessage
bit 0 - validMessage[0] (Read/Write)
others - reserved
0x60	reserved
0x64	Data signal of network IOP offset
bit 31~0 - network IOP offset[31:0] (Read/Write)
0x68	reserved
0x6c	Data signal of count
bit 31~0 - count[31:0] (Read/Write)
0x70	reserved
0x74	Data signal of size
bit 31~0 - size[31:0] (Read/Write)
0x78	reserved
0x7c	Data signal of reset
bit 0 - reset[0] (Read/Write)
others - reserved
0x80	reserved
0x84	Data signal of p_verbose
bit 0 - p_verbose[0] (Read/Write)
others - reserved
0x88	reserved
0x8c	Data signal of events_completed
bit 31~0 - events_completed[31:0] (Read)
0x90	Control signal of events_completed
bit 0 - events_completed_ap_vld (Read/COR)
others - reserved
0x94	Data signal of publishes_sent
bit 31~0 - publishes_sent[31:0] (Read)
0x98	Control signal of publishes_sent
bit 0 - publishes_sent_ap_vld (Read/COR)
others - reserved
0x9c	Data signal of packets_received
bit 31~0 - packets_received[31:0] (Read)
0xa0	Control signal of packets_received
bit 0 - packets_received_ap_vld (Read/COR)
others - reserved
0xa4	Data signal of packets_sent
bit 31~0 - packets_sent[31:0] (Read)
0xa8	Control signal of packets_sent
bit 0 - packets_sent_ap_vld (Read/COR)
others - reserved
SC = Self Clear, COR = Clear on Read, TOW = Toggle on Write, COH = Clear on Handshake

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
        acc_mmio.write(0x1c, pl_mac >> 32)
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
