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


from queue import Queue
from .bram import BRAM


def fmt_packet(data):
    ary = bytearray(data)
    size = len(ary)
    result = []
    pos = 0
    while pos < size:
        read = min(size - pos, 32)
        line = []
        for i in range(0, read):
            line.append("{:02x}".format(ary[pos+i]))
            if i % 4 == 3:
                line.append(' ')
        result.append("".join(line))
        pos += read
    return '\n'.join(result)


class PacketSlurper(BRAM):
    """Wrapper class around a BRAM Controller.

    This wrapper can interface with Steve's HLS PacketSlurper.

    """
    def __init__(self):
        super().__init__()
        # transmit offsets
        self.TX_DATA_OFFSET = 0x000
        self.TX_CTRL_OFFSET = 0x180
        self.TX_EN_OFFSET = 0x190
        self.TX_LEN_OFFSET = 0x194
        # receive offsets
        self.RX_DATA_OFFSET = 0x200
        self.RX_CTRL_OFFSET = 0x380
        self.RX_EN_OFFSET = 0x390
        self.RX_LEN_OFFSET = 0x394

        # remove some indirection
        self.array = self._mmio.array
        self.mem = self._mmio.mem

        # start polling to receive packets
        self._rx_packet = None
        self._queue = Queue(maxsize=4)

    def _poll_rx_thread(self):
        while True:
            if self.has_packet():
                to_read = super().read32(self.RX_LEN_OFFSET)
                i = 0
                pkt = b""
                while to_read:
                    data = super().read32(self.RX_DATA_OFFSET+i)
                    read = min(to_read, 4)
                    pkt = pkt + data.to_bytes(4, byteorder='little')
                    to_read = to_read - read
                    i = i + 1
                if not self._queue.full():
                    self._queue.put(pkt)
                super().write32(self.RX_EN_OFFSET, 0x00)

    def has_packet(self):
        t = super().read32(self.RX_EN_OFFSET)
        return t == 1

    def recvt(self):
        result = self._queue.get()
        return result

    def recv(self):
            if self.has_packet():
                to_read = super().read32(self.RX_LEN_OFFSET)
                i = 0
                pkt = b""
                while to_read:
                    data = super().read32(self.RX_DATA_OFFSET+i)
                    read = min(to_read, 4)
                    pkt = pkt + data.to_bytes(4, byteorder='little')
                    to_read = to_read - read
                    i = i + 1
                super().write32(self.RX_EN_OFFSET, 0x00)
                return pkt
            return None

    def _setup_eth_tx_packet(self, buff, leng):
        # mmio requires 4-byte aligned read/writes
        padding = leng % 4
        if padding:
            payload = buff + (b'\00' * (4-padding))
        else:
            payload = buff

        super().write32(self.TX_CTRL_OFFSET, 0xa0000000)
        super().write32(self.TX_CTRL_OFFSET+1, 0x02)
        super().write32(self.TX_DATA_OFFSET, payload)
        super().write32(self.TX_LEN_OFFSET, leng)

    def _issue_eth_tx_packet(self):
        super().write32(self.TX_EN_OFFSET, 0x01)

    def send(self, packet):
        mem = self.mem
        array = self.array
        mem.seek(0x0)
        mem.write(packet)
        array[0x194] = len(packet)
        array[0x190] = 0x01

    def flush(self):
        super().flush32(0x00)
