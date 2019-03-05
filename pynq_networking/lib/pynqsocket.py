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


import logging
logging.getLogger("kamene.runtime").setLevel(logging.ERROR)
from kamene.all import *
from .slurper import PacketSlurper


__author__ = "Stephen Neuendorffer, Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "stephenn@xilinx.com"


class L2PynqSocket(SuperSocket):
    """A kamene-like socket object that reads and writes packets.
    
    The packets will be accessed using the PYNQ NetworkIOP interface;
    i.e., read/write packets at layer 2 using PYNQ bypass.

    """
    _slurper = PacketSlurper()

    def __init__(self, iface=None, type=ETH_P_ALL, filter=None, nofilter=0):
        if iface is None:
            self.iface = conf.iface
        self.LL = Ether
        self.slurper = L2PynqSocket._slurper

    def flush(self):
        """Flush any packets buffered up in the interface.

        Packets are buffered up in the interface.  Since packets can 
        potentially come in faster than being read, this causes a problem 
        since the buffer of packets often starts close to full and can drop 
        newer packets while keeping older stale packets around. This method 
        enables an application to flush stale packets from the buffer before 
        starting a packet exchange to avoid losing packets of interest.

        """
        i = 0
        while self.has_packet():
            i = i + 1
            self.recv()
        print(i, "packets flushed")

    def has_packet(self):
        """Return true if the interface has a packet to read. """
        return self.slurper.has_packet()

    def srp1(self, outframe, valid_ack, ptype):
        """Send the given outframe and wait for response.
        
        This method waits for a valid acknowledgment of the given ptype as 
        determined by the valid_ack function.
        valid_ack must model (frame, ptype) -> bool.
        This function blocks until a valid acknowledgment is received.

        """
        self.send(outframe)
        frame = None
        while not frame:
            if self.has_packet():
                frame = self.recv()
                if not valid_ack(frame, ptype):
                    frame = None
        return frame

    def recv(self, x=MTU):
        """Receive a frame.

        This function blocks until a frame is received.

        """
        pkt = self.slurper.recv()
        try:
            q = self.LL(pkt)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            q = conf.raw_layer(pkt)
        q.time = time.time()
        return q

    def send(self, x):
        """Send a frame.

        This function blocks until the frame has been sent.

        """
        if hasattr(x, "sent_time"):
            x.sent_time = time.time()
        return self.slurper.send(bytes(x))
