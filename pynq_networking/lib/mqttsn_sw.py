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
from kamene.all import *
from .mqttsn import *


__author__ = "Stephen Neuendorffer"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "stephenn@xilinx.com"


""" Scapy implementation of the MQTTSN protocol """


def valid_ack(ack, t):
    if isinstance(ack[IP].payload, ICMP):
        print("Error response:")
        ack[IP].payload.show()
        return False
    if not isinstance(ack[MQTTSN].payload, t):
        print("Unexpected response should have been " + str(t) + ":")
        ack.payload.show()
        return False
    return True


class MQTT_Client:
    def __init__(self, serverIP, serverPort, name, verbose=0):
        self.serverIP = serverIP
        self.serverPort = serverPort
        self.client = name
        self.verbose = verbose

    def __enter__(self):
        try:
            self.connect()
        except Exception:
            raise Exception
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def connect(self):
        """Establish the connection. 

        Return the valid acknowledgement.

        """
        connack = sr1(IP(dst=self.serverIP) /
                      UDP(sport=50000, dport=self.serverPort) /
                      MQTTSN() / MQTTSN_CONNECT(client=self.client),
                      verbose=self.verbose)
        return valid_ack(connack, MQTTSN_CONNACK)

    def disconnect(self):
        """Destroy the connection.
        
        The rsmb tends to respond without the disconnect payload.

        """
        _ = send(IP(dst=self.serverIP) /
                 UDP(sport=50000, dport=self.serverPort) /
                 MQTTSN() / MQTTSN_DISCONNECT(),
                 verbose=self.verbose)

    def register(self, topic):
        """Register the given topic.  

        Return the associated topicID.

        """
        regack = sr1(IP(dst=self.serverIP) /
                     UDP(sport=50000, dport=self.serverPort) /
                     MQTTSN() / MQTTSN_REGISTER(topic=topic),
                     verbose=self.verbose)
        if not valid_ack(regack, MQTTSN_REGACK):
            raise RuntimeError("register() not acknowledged.")
        return regack[MQTTSN_REGACK].topicID

    def publish(self, topicID, message, qos=1):
        """Publish on the given topicID with the given message.
         
        With qos=1, it will guarantee the delivery. 
        Return bool indicating success.

        """
        frame = IP(dst=self.serverIP) / \
            UDP(sport=50000, dport=self.serverPort) / \
            MQTTSN() / MQTTSN_PUBLISH(qos=qos,
                                      topicID=topicID, message=message)
        if qos == 0:
            send(frame, verbose=self.verbose)
        if qos == 1:
            puback_frame = sr1(frame, verbose=self.verbose)
            if not valid_ack(puback_frame, MQTTSN_PUBACK):
                return False
        return True
