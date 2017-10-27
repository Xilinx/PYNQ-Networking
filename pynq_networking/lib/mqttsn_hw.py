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


import struct
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
from .pynqsocket import L2PynqSocket
from .broker import ip_str_to_int, mac_str_to_int, int_2_ip_str
from .mqttsn_sw import *
from .accelerator import Accelerator


__author__ = "Stephen Neuendorffer"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "stephenn@xilinx.com"


LOCAL_IP_STR = '192.168.1.104'
LOCAL_MAC_STR = '8a:70:bd:29:2b:40'
conf.L2PynqSocket = L2PynqSocket


def mqttsn_valid_ack(ack, t):
    """ Check the valid acknowledgment.

    Return True if ack is a valid acknowledgment packet of type t.
    In addition, handle ARP request packets by sending an ARP reply.

    """
    if ARP in ack:
        arp = ack[ARP]
        if arp.pdst == LOCAL_IP_STR:
            arpreply = Ether(dst=ack.src, src=LOCAL_MAC_STR) / \
                       ARP(op='is-at', psrc=LOCAL_IP_STR, hwsrc=LOCAL_MAC_STR,
                           pdst=arp.psrc, hwdst=arp.hwdst)
            conf.L2PynqSocket().send(arpreply)
    if IP not in ack:
        return False
    if IP in ack and isinstance(ack[IP].payload, ICMP):
        print("Error response:")
        ack[IP].payload.show()
        return False
    if MQTTSN in ack:
        print("MQTTSN:", ack.summary())
        # FIXME: model this in the same way as scapy in the packet description
        if isinstance(ack[MQTTSN].payload, t):
            return True
        else:
            print("Unexpected response should have been " + str(t) + ":")
            ack.payload.show()
            return False
    return False


class MQTT_Client_PL:
    """MQTT client class with PL acceleration.

    This class is similar to the class `MQTT_client` except that it uses
    the PL acceleration to construct the packets.

    """
    def __init__(self, server_ip, server_port, client_name, verbose=0):
        """MQTT client class with PL acceleration.

        Create a new client object representing a connection to an 
        MQTTSN server.

        Parameters
        ----------
        server_ip : int/str
            The IP of the server.
        server_port : int
            An integer represeting the port of the server (usually 1884).
        client_name : str
            The name of the client.
        verbose : int
            If non-zero, get verbose debugging feedback about the connection.

        """
        if type(server_ip) is int:
            self.server_ip_int = server_ip
            self.server_ip_str = int_2_ip_str(server_ip)
        else:
            self.server_ip_str = server_ip
            self.server_ip_int = ip_str_to_int(server_ip)
        self.server_port = server_port
        self.client = client_name
        self.verbose = verbose
        self.local_ip_str = LOCAL_IP_STR
        self.local_ip_int = ip_str_to_int(self.local_ip_str)
        self.local_mac_str = LOCAL_MAC_STR
        self.local_mac_int = mac_str_to_int(self.local_mac_str)
        self.frame = None

        self.socket = conf.L2PynqSocket()
        self.accel = Accelerator()

    def __enter__(self):
        self.connect()
        # Fixme: on failure throw exception
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def connect(self):
        """Connect to the server.

        This blocks until an acknowledgement is received.

        """
        frame = Ether(src=self.local_mac_str, dst='FF:FF:FF:FF:FF:FF')/\
                IP(src=self.local_ip_str, dst=self.server_ip_str)/\
                UDP(sport=50000, dport=self.server_port)/\
                MQTTSN()/MQTTSN_CONNECT(client=self.client)
        _ = self.socket.srp1(frame, mqttsn_valid_ack, MQTTSN_CONNACK)
        return True

    def disconnect(self):
        """Disconnect from the server. 

        It is empty for now, and needs to be fixed. 

        """
        # Fixme: need to implement this
        pass

    def register(self, topic):
        """Register the given topic with the server.

        This blocks until an acknowledgement is received.
        Return the topicID that should be used to publish on the given topic.

        """
        frame = Ether(src=self.local_mac_str, dst='FF:FF:FF:FF:FF:FF')/\
                IP(src=self.local_ip_str, dst=self.server_ip_str)/\
                UDP(sport=50000, dport=self.server_port)/\
                MQTTSN()/MQTTSN_REGISTER(topic=topic)
        regack_frame = self.socket.srp1(frame, mqttsn_valid_ack, MQTTSN_REGACK)
        return regack_frame[MQTTSN_REGACK].topicID

    def publish_sw(self, topic_id, message, qos=1):
        """Publish the given message on the topic.
         
        The topic is associated with the given topicID to the server.
        This blocks until an acknowledgement is received. This method
        is based on the software packet constructor.

        Returns
        -------
        Bool
            True if the publish succeeds.

        """
        self.frame = bytes(
            Ether(src=self.local_mac_str, dst='FF:FF:FF:FF:FF:FF')/
            IP(src=self.local_ip_str, dst=self.server_ip_str)/
            UDP(sport=50000, dport=self.server_port)/
            MQTTSN()/MQTTSN_PUBLISH(qos=qos,
                                    topicID=topic_id, message=message))
        if qos == 0:
            self.socket.send(self.frame)
        else:
            _ = self.socket.srp1(self.frame, mqttsn_valid_ack, MQTTSN_PUBACK)
        return True

    def publish_hw(self, network_iop, sensor_iop, topic_id, qos, range_arg):
        """Publish the sensor values using PL acceleration. 

        This call leverages the `publish_mmio()` method from the 
        `Accelerator()` class.
        This method is based on the hardware packet constructor.

        Returns
        -------
        Bool
            True if the publish succeeds.

        """
        self.accel.publish_mmio(100, len(range_arg),
                                self.local_mac_int, self.local_ip_int,
                                self.server_ip_int, self.server_port,
                                topic_id, qos, self.verbose,
                                network_iop, sensor_iop)
        return True
