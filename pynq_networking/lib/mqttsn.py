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


__author__ = "Stephen Neuendorffer"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "stephenn@xilinx.com"


""" Scapy dissector definitions for MQTT-SN packets."""


def MQTTSN_FLAGS():
    return [
        BitField("dup", 0, 1),
        BitField("qos", 0, 2),
        BitField("retain", 0, 1),
        BitField("will", 0, 1),
        BitField("clean", 1, 1),
        BitField("topicIDtype", 0, 2)]


class MQTTSN_ADVERTISE(Packet):
    type = 0x00
    name = "ADVERTISE"
    fields_desc = [ByteField("gatewayID", None),
                   ShortField("duration", 30)]


class MQTTSN_SEARCHGW(Packet):
    type = 0x01
    name = "SEARCHGW"
    fields_desc = [ByteField("radius", 1)]


class MQTTSN_GWINFO(Packet):
    type = 0x02
    name = "GWINFO"
    fields_desc = [ByteField("gatewayID", None),
                   StrField("gatewayAdd", None)]


class MQTTSN_CONNECT(Packet):
    type = 0x04
    name = "CONNECT"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([
                  ByteField("protocol", 1),
                  ShortField("duration", 30),
                  StrField("client", "client")])


class MQTTSN_CONNACK(Packet):
    type = 0x05
    name = "CONNACK"
    fields_desc = [ByteField("returnCode", 0)]


class MQTTSN_WILLTOPICREQ(Packet):
    type = 0x06
    name = "WILLTOPICREQ"
    fields_desc = []


class MQTTSN_WILLTOPIC(Packet):
    type = 0x07
    name = "WILLTOPIC"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([StrField("topic", None)])


class MQTTSN_WILLMSGREQ(Packet):
    type = 0x08
    name = "WILLMSGREQ"
    fields_desc = []


class MQTTSN_WILLMSG(Packet):
    type = 0x09
    name = "WILLMSG"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([StrField("message", None)])


class MQTTSN_REGISTER(Packet):
    type = 0x0A
    name = "REGISTER"
    fields_desc = [
        ShortField("topicID", None),
        ShortField("messageID", None),
        StrField("topic", None)
    ]


class MQTTSN_REGACK(Packet):
    type = 0x0B
    name = "REGACK"
    fields_desc = [
                  ShortField("topicID", None),
                  ShortField("messageID", None),
                  ByteField("returnCode", 0) 
    ]


class MQTTSN_PUBLISH(Packet):
    type = 0x0C
    name = "PUBLISH"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([
                  ShortField("topicID", None),
                  ShortField("messageID", 0),
                  StrField("message", None)
    ])


class MQTTSN_PUBACK(Packet):
    type = 0x0D
    name = "PUBACK"
    fields_desc = [ShortField("topicID", None),
                   ShortField("messageID", 0),
                   ByteField("returnCode", 0)]


class MQTTSN_PUBCOMP(Packet):
    type = 0x0E
    name = "PUBCOMP"
    fields_desc = [ShortField("messageID", 0)]


class MQTTSN_PUBREC(Packet):
    type = 0x0F
    name = "PUBREC"
    fields_desc = [ShortField("messageID", 0)]


class MQTTSN_PUBREL(Packet):
    type = 0x10
    name = "PUBREL"
    fields_desc = [ShortField("messageID", 0)]


class MQTTSN_SUBSCRIBE(Packet):
    type = 0x12
    name = "SUBSCRIBE"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([
                  ShortField("messageID", None),
                  StrField("topic", None)
    ])


class MQTTSN_SUBACK(Packet):
    type = 0x13
    name = "SUBACK"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([
                  ShortField("topicID", None),
                  ShortField("messageID", None),
                  ByteField("returnCode", 0) 
    ])


class MQTTSN_UNSUBSCRIBE(Packet):
    type = 0x14
    name = "UNSUBSCRIBE"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([
                  ShortField("messageID", None),
                  StrField("topic", None)
                  
    ])


class MQTTSN_UNSUBACK(Packet):
    type = 0x15
    name = "UNSUBACK"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([
                  ShortField("topicID", None),
                  ShortField("messageID", None),
                  ByteField("returnCode", 0) 
    ])


class MQTTSN_PINGREQ(Packet):
    type = 0x16
    name = "PINGREQ"
    fields_desc = [StrField("client", "client")]


class MQTTSN_PINGRESP(Packet):
    type = 0x17
    name = "PINGRESP"
    fields_desc = []


class MQTTSN_DISCONNECT(Packet):
    type = 0x18
    name = "DISCONNECT"
    fields_desc = [ShortField("duration", 30)]


class MQTTSN_WILLTOPICUPD(Packet):
    type = 0x1A
    name = "WILLTOPICUPD"
    fields_desc = MQTTSN_FLAGS()
    fields_desc.extend([StrField("topic", None)])


class MQTTSN_WILLTOPICRESP(Packet):
    type = 0x1B
    name = "WILLTOPICRESP"
    fields_desc = [ByteField("returnCode", 0)]


class MQTTSN_WILLMSGUPD(Packet):
    type = 0x1C
    name = "WILLMSGUPD"
    fields_desc = [StrField("message", None)]


class MQTTSN_WILLMSGRESP(Packet):
    type = 0x1D
    name = "WILLMSGRESP"
    fields_desc = [ByteField("returnCode", 0)]


MQTTSN_PACKET_TYPES = [MQTTSN_ADVERTISE,
                       MQTTSN_SEARCHGW,
                       MQTTSN_GWINFO,
                       MQTTSN_CONNECT,
                       MQTTSN_CONNACK,
                       MQTTSN_WILLTOPICREQ,
                       MQTTSN_WILLTOPIC,
                       MQTTSN_WILLMSGREQ,
                       MQTTSN_WILLMSG,
                       MQTTSN_REGISTER,
                       MQTTSN_REGACK,
                       MQTTSN_PUBLISH,
                       MQTTSN_PUBACK,
                       MQTTSN_PUBCOMP,
                       MQTTSN_PUBREC,
                       MQTTSN_PUBREL,
                       MQTTSN_SUBSCRIBE,
                       MQTTSN_SUBACK,
                       MQTTSN_UNSUBSCRIBE,
                       MQTTSN_UNSUBACK,
                       MQTTSN_PINGREQ,
                       MQTTSN_PINGRESP,
                       MQTTSN_DISCONNECT,
                       MQTTSN_WILLTOPICUPD,
                       MQTTSN_WILLTOPICRESP,
                       MQTTSN_WILLMSGUPD,
                       MQTTSN_WILLMSGRESP]


class MQTTSN_LenField(ShortField):
    """An MQTTSN Length field.
    
    It uses a variable-length encoding. Short lengths are one byte, longer 
    lengths are 3 bytes. This works because the minimum length is 2, including 
    the type field and the length field itself.

    """
    def i2len(self, pkt, x):
        """Convert internal value to a length usable by a FieldLenField"""
        m = self.i2m(pkt, x)
        if m <= 256:
            return 1
        else:
            return 3

    def i2m(self, pkt, x):
        l = x
        if x is None:
            l = len(pkt.payload) + 2
        return l

    def addfield(self, pkt, s, val):
        """Add an internal value  to a string"""
        v = self.i2m(pkt,val)
        if v <= 256:
            return s+struct.pack("B", v)
        else:
            return "\x01" + struct.pack("H", v)

    def getfield(self, pkt, s):
        """Extract an internal value from a string"""
        i = struct.unpack("B", s[:1])[0]
        s2 = s[1:]
        if i == 1:
                i = struct.unpack("H", s2[:2])[0]
                s2 = s2[2:]
        return s2, i
   

class MQTTSN_TypeField(ByteEnumField):
    def __init__(self, name, default):
        ByteEnumField.__init__(self, name, default,
                               {x.type: x.name for x in MQTTSN_PACKET_TYPES})

    def randval(self):
        return RandChoice(*[x.type for x in MQTTSN_PACKET_TYPES])


class MQTTSN(Packet):
    name = "MQTTSN"
    fields_desc = [MQTTSN_LenField("len", None),
                   MQTTSN_TypeField("type", 4)]

    def answers(self, other):
        """Returns true if self is an answer from other. 

        Assume that any MQTT packet is an answer for any other.
        This is slightly inaccurate because only some packets
        are actually responses, but it's good enough for now.

        """
        if other.__class__ == self.__class__:
            return 1
        return 0


