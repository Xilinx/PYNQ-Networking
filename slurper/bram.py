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


from math import log
from pynq import MMIO
from pynq import PL


__author__ = "Stephen Neuendorffer, Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "stephenn@xilinx.com"


class BRAM(object):
    """A simple Python wrapper for an AXI BRAM Controller.

    In this class, data length is measured in 32-bit words.

    Attributes
    ----------
    base_addr : int
        MMIO base address.
    length : int
        MMIO length.

    """
    _mmio = None

    def __init__(self, network_iop="networkIOP/axi_bram_ctrl_0"):
        """Initialize BRAM interface.

        Parameters
        ----------
        network_iop : str
            Name of the network IOP in the IP dictionary.

        """
        if BRAM._mmio is None:
            ip_base_addr = PL.ip_dict[network_iop]['phys_addr']
            ip_addr_range = PL.ip_dict[network_iop]['addr_range']
            BRAM._mmio = MMIO(ip_base_addr, ip_addr_range)
        self.base_addr = BRAM._mmio.base_addr
        self.length = BRAM._mmio.length

    def __len__(self):
        """Length of the MMIO.
        
        Returns
        -------
        int
            Length of the MMIO in 32-bit words.

        """
        return self._mmio.length >> 2

    def read32(self, addr):
        """Read the values from MMIO.
        
        Parameters
        ----------
        addr : int
            The word address to read.

        Returns
        -------
        int
            The 32-bit word read from the given address.

        """
        return self._mmio.read(addr << 2)

    def write32(self, addr, val):
        """Read the values from MMIO.

        Parameters
        ----------
        addr : int
            The word address to write.
        val : int
            The 32-bit word to write into the given address.

        """
        self._mmio.write(addr << 2, val)

    def flush32(self, val=0x00):
        """Clear all the values in the MMIO range.

        Parameters
        ----------
        val : int
            Initialization values for all the word addresses, default to 0.

        """
        for i in range(len(self)):
            self.write32(i, val)
