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


""" Scapy dissector definitions for MQTT packets.

    We have a stream of MQTT packets encapsulated in TCP packets.  This allows 
    the MQTT_Stream class to work right.
    see: http://stackoverflow.com/questions/8073508/scapy-adding-new-protocol-\
    with-complex-field-groupings

"""


class MQTTBasePacket(Packet):
    def extract_padding(self, s):
        return '', s


class MQTT_CONNECT(MQTTBasePacket):
    type = 0x01
    name = "CONNECT"
    fields_desc = [
        FieldLenField("protocolNameLength", 4, fmt="H",
                      length_of="protocolName"),
        StrLenField("protocolName", "MQTT",
                    length_from=lambda pkt:pkt.protocolNameLength),
        ByteField("protocol", 4),
        BitField("userName", 1, 1),
        BitField("password", 1, 1),
        BitField("willRetain", 0, 1),
        BitField("willQoS", 1, 2),
        BitField("willFlag", 1, 1),
        BitField("cleanSession", 1, 1),
        BitField("reserved", 0, 1),
        ShortField("keepAlive", 10),
        FieldLenField("clientIDLength", None, fmt="H",
                      length_of="clientID"),
        StrLenField("clientID", "value",
                    length_from=lambda pkt:pkt.clientIDLength)
    ]


class MQTT_CONNACK(MQTTBasePacket):
    type = 0x02
    name = "CONNACK"
    fields_desc = [BitField("sessionPresent", 0, 1),
                   BitField("reserved", 0, 7),
                   ByteField("returnCode", 0)]


class MQTT_PUBLISH(MQTTBasePacket):
    type = 0x03
    name = "PUBLISH"
    fields_desc = [
        FieldLenField("topicLength", None, fmt="H", length_of="topic"),
        StrLenField("topic", "value",
                    length_from=lambda pkt:pkt.topicLength),
        ConditionalField(ShortField("messageID", 0),
                         lambda pkt:pkt.underlayer.qos > 0),
        StrLenField("message", None,
                    length_from=lambda pkt:pkt.underlayer.len -
                                           pkt.topicLength - 4)]


class MQTT_PUBACK(MQTTBasePacket):
    type = 0x04
    name = "PUBACK"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_PUBREC(MQTTBasePacket):
    type = 0x05
    name = "PUBREC"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_PUBREL(MQTTBasePacket):
    type = 0x06
    name = "PUBREL"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_PUBCOMP(MQTTBasePacket):
    type = 0x07
    name = "PUBCOMP"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_SUBSCRIBE(MQTTBasePacket):
    type = 0x08
    name = "SUBSCRIBE"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_SUBSCRIBE_TOPIC(MQTTBasePacket):
    name = "SUBSCRIBE_TOPIC"
    fields_desc = [
        FieldLenField("topicLength", None, fmt="H", length_of="topic"),
        StrLenField("topic", "value", length_from=lambda pkt:pkt.topicLength),
        BitField("QoS", 0, 2)
    ]


class MQTT_SUBACK(MQTTBasePacket):
    type = 0x09
    name = "SUBACK"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_SUBACK_TOPIC(MQTTBasePacket):
    name = "SUBACK_TOPIC"
    fields_desc = [ByteField("returnCode", 0)]


class MQTT_UNSUBSCRIBE(MQTTBasePacket):
    type = 0x0A
    name = "UNSUBSCRIBE"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_UNSUBSCRIBE_TOPIC(MQTTBasePacket):
    name = "UNSUBSCRIBE_TOPIC"
    fields_desc = [
        FieldLenField("topicLength", None, fmt="H", length_of="topic"),
        StrLenField("topic", "value", length_from="topicLength"),
    ]


class MQTT_UNSUBACK(MQTTBasePacket):
    type = 0x0B
    name = "UNSUBACK"
    fields_desc = [ShortField("messageID", 0)]


class MQTT_PINGREQ(MQTTBasePacket):
    type = 0x0C
    name = "PINGREQ"
    fields_desc = []


class MQTT_PINGRESP(MQTTBasePacket):
    type = 0x0D
    name = "PINGRESP"
    fields_desc = []


class MQTT_DISCONNECT(MQTTBasePacket):
    type = 0x0E
    name = "DISCONNECT"
    fields_desc = []


MQTT_PACKET_TYPES = [
    MQTT_CONNECT,
    MQTT_CONNACK,
    MQTT_PUBLISH,
    MQTT_PUBACK,
    MQTT_PUBREC,
    MQTT_PUBREL,
    MQTT_PUBCOMP,
    MQTT_SUBSCRIBE,
    MQTT_SUBACK,
    MQTT_UNSUBSCRIBE,
    MQTT_UNSUBACK,
    MQTT_PINGREQ,
    MQTT_PINGRESP,
    MQTT_DISCONNECT]


class MQTTLenField(ShortField):
    """ MQTT length field.

    It uses a variable-length encoding.

    """
    def i2len(self, pkt, x):
        """Convert internal value to a length usable by a FieldLenField. """
        m = self.i2m(pkt, x)
        if m < 128:
            return 1
        elif m < 16384:
            return 2
        elif m < 2097152:
            return 3
        else:
            return 4

    def i2m(self, pkt, x):
        l = x
        if x is None:
            l = len(pkt.payload)
        return l

    def addfield(self, pkt, s, val):
        """Add an internal value  to a string. """
        v = self.i2m(pkt, val)
        while v > 0:
            byte = v % 128
            v = v // 128
            if v > 0:
                byte = byte + 128
            s = s + struct.pack("B", byte)
        return s

    def getfield(self, pkt, s):
        """Extract an internal value from a string. """
        multiplier = 1
        value = 0
        done = False
        s2 = s
        while not done:
            byte = struct.unpack("B", s2[:1])[0]
            s2 = s2[1:]
            value = value + (byte & 127) * multiplier
            multiplier = multiplier * 128
            if multiplier > 128*128*128:
                done = True
            else:
                done = byte < 128
        return s2, value


class MQTTTypeField(BitEnumField):
    def __init__(self, name, default):
        BitEnumField.__init__(self, name, default, 4,
                              {x.type: x.name for x in MQTT_PACKET_TYPES})

    def randval(self):
        return RandChoice(*[x.type for x in MQTT_PACKET_TYPES])


class MQTT(Packet):
    name = "MQTT"
    fields_desc = [
        MQTTTypeField("type", MQTT_CONNECT.type),
        BitField("dup", 0, 1),
        BitField("qos", 0, 2),
        BitField("retain", 0, 1),
        MQTTLenField("len", None)
    ]

    def answers(self, other):
        """Returns true if self is an answer from other. 

        Assume that any MQTT packet is an answer for any other.
        This is slightly inaccurate because only some packets
        are actually responses, but it's good enough for now.

        """
        if other.__class__ == self.__class__:
            return 1
        return 0


class MQTT_Stream(Packet):
    """MQTT stream class.
    
    This is a simple packet that represents the sequence of MQTT packets
    in a TCP stream.  It's very possible that multiple MQTT packets are
    assembled into the same TCP packet.  This is a bit of a hack to
    avoid doing full TCP stream reconstruction.

    """
    fields_desc=[PacketListField("packets", None, MQTT)]
