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


import subprocess
import os
import socket
import struct
import ipaddress
from uuid import getnode
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
from .mqtt import *
from .mqttsn_sw import *


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "yunq@xilinx.com"


def get_ip_string():
    """Get the string representation of the IP address.

    Returns
    -------
    str
        The IP address representation in str format.

    """
    ipaddr_slist = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
    ip_str = str(ipaddr_slist.stdout.decode('utf-8').split(" ")[0])
    return ip_str


def ip_str_to_int(ip_str):
    """Convert IP string to integer value. 

    Parameters
    ----------
    ip_str : str
        The IP string, for example, '192.168.1.104'.

    """
    return int(ipaddress.ip_address(ip_str))


def int_2_ip_str(ip_int):
    """Convert IP integer value to a readable string. 

    Parameters
    ----------
    ip_int : str
        The IP integer representation.

    """
    return socket.inet_ntoa(struct.pack("!I", ip_int))


def get_mac_string():
    """Get the string representation of the MAC address.

    Returns
    -------
    str
        The MAC address representation in str format.

    """
    mac_int = getnode()
    mac_str = ':'.join(("%012x" % mac_int)[i:i + 2] for i in range(0, 12, 2))
    return mac_str


def mac_str_to_int(mac_str):
    """Convert MAC string to integer value. 

    Parameters
    ----------
    mac_str : str
        The MAC string, for example, '8a:70:bd:29:2b:40'.

    """
    return int(mac_str.replace(':', ''), 16)


def get_pid(process_name):
    return int(subprocess.check_output(["pidof", process_name]))


class Broker(object):
    """Broker class sets up the broker server for MQTT client to talk to.

    Ideally, there should be only 1 broker set up for each board.
    
    """
    def __init__(self, ip_address=None, mqtt_port=1883, mqttsn_port=1884,
                 max_connections=100):
        """MQTT broker initialization. 

        Parameters
        ----------
        ip_address : int
            The IP address of the broker, defaulted to `None` to use host IP.
        mqtt_port : int
            MQTT port number.
        mqttsn_port: int
            MQTT-SN port number.
        max_connections : int
            Max number of connections allowed on each port.

        """
        self.ip_address = get_ip_string() \
            if ip_address is None else ip_address
        self.mqtt_port = mqtt_port
        self.mqttsn_port = mqttsn_port
        self.max_connections = max_connections
        self.log = 'broker.log'

        with open("broker.cfg", 'w') as file:
            file.write("trace_output on\n")
            file.write("listener " + str(self.mqtt_port) + "\n")
            file.write("    max_connections " +
                       str(self.max_connections) + "\n")
            file.write("listener " + str(self.mqttsn_port) + " " +
                       self.ip_address + " mqtts\n")
            file.write("    max_connections " +
                       str(self.max_connections) + "\n")

    def open(self):
        """Open the server for client to connect.

        This method will open the server. It first check whether there is 
        any running broker already. Then it binds the port number to packets.

        """
        self.close()
        os.system("nohup /opt/python3.6/lib/python3.6/site-packages/"
                  "pynq_networking/rsmb/rsmb/src/broker_mqtts >" +
                  self.log + "&")

        for t in MQTT_PACKET_TYPES:
            bind_layers(MQTT, t, {'type': t.type})

        bind_layers(TCP, MQTT_Stream, {'dport': self.mqtt_port})
        bind_layers(TCP, MQTT_Stream, {'sport': self.mqtt_port})

        for t in MQTTSN_PACKET_TYPES:
            bind_layers(MQTTSN, t, {'type': t.type})

        bind_layers(UDP, MQTTSN, {'dport': self.mqttsn_port})
        bind_layers(UDP, MQTTSN, {'sport': self.mqttsn_port})

    def close(self):
        """Close the server.

        It will kill the broker running in the background.

        """
        try:
            process_id = get_pid("broker_mqtts")
        except subprocess.CalledProcessError:
            pass
        else:
            os.system("kill -9 {}".format(process_id))
        if os.path.isfile(self.log):
            os.system("rm -rf " + self.log)
