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
from site import getsitepackages

__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "yunq@xilinx.com"

KERNEL_MODULE_PATH = os.path.join(getsitepackages()[0], 'pynq_networking',
                                  'kernel_module')

class LinkManager:
    """Wrapper class for bring up or down the kernel modules.
    
    After the kernel module is started, the interface called `pynq0` will be 
    setup.

    """
    def __init__(self, kernel_interface_name='pynq0'):
        """Initialize internal variables.

        Parameters
        ----------
        kernel_interface_name : str
            The name of the interface for the kernel module.

        """
        self.kernel_interface_name = kernel_interface_name
        if os.system('chmod 777 ' + KERNEL_MODULE_PATH + "/*.sh"):
            raise OSError("Cannot chmod for link scripts.")

    def if_up(self, interface_name, interface_ip_str):
        """Bring up an arbitrary interface using ifconfig.

        This is not required when bringing up the kernel module.

        """
        if os.system("ifconfig " + interface_name + " " + interface_ip_str):
            raise OSError("Cannot bring up {}.".format(interface_name))

    def if_down(self, interface_name):
        """Put down an existing interface using ifconfig.

        This is not required when putting down the kernel module.

        """
        if os.system("ifconfig " + interface_name + " down"):
            raise OSError("Cannot put down {}.".format(interface_name))

    def kernel_up(self):
        """Bring up the interface after running `link_up.sh`.
        
        Must make sure the desired interface has not been up before running
        this method.

        """
        self.kernel_down()
        _ = os.system(KERNEL_MODULE_PATH + "/link_up.sh")

        interface_list = os.listdir('/sys/class/net/')
        if 'pynq0' not in interface_list:
            raise ValueError("Interface {} not set up properly.".format(
                self.kernel_interface_name))

    def kernel_down(self):
        """Put down the interface after running `link_down.sh`.

        Must make sure the desired interface has not been down before running
        this method.

        """
        interface_list = os.listdir('/sys/class/net/')
        if 'pynq0' in interface_list:
            _ = os.system(KERNEL_MODULE_PATH + "/link_down.sh 2>/dev/null")

        interface_list = os.listdir('/sys/class/net/')
        if 'pynq0' in interface_list:
            raise ValueError("Interface {} not put down properly.".format(
                self.kernel_interface_name))
