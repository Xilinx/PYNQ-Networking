/*****************************************************************************
 *
 *     Author: Xilinx, Inc.
 *
 *     XILINX IS PROVIDING THIS DESIGN, CODE, OR INFORMATION "AS IS"
 *     AS A COURTESY TO YOU, SOLELY FOR USE IN DEVELOPING PROGRAMS AND
 *     SOLUTIONS FOR XILINX DEVICES.  BY PROVIDING THIS DESIGN, CODE,
 *     OR INFORMATION AS ONE POSSIBLE IMPLEMENTATION OF THIS FEATURE,
 *     APPLICATION OR STANDARD, XILINX IS MAKING NO REPRESENTATION
 *     THAT THIS IMPLEMENTATION IS FREE FROM ANY CLAIMS OF INFRINGEMENT,
 *     AND YOU ARE RESPONSIBLE FOR OBTAINING ANY RIGHTS YOU MAY REQUIRE
 *     FOR YOUR IMPLEMENTATION.  XILINX EXPRESSLY DISCLAIMS ANY
 *     WARRANTY WHATSOEVER WITH RESPECT TO THE ADEQUACY OF THE
 *     IMPLEMENTATION, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OR
 *     REPRESENTATIONS THAT THIS IMPLEMENTATION IS FREE FROM CLAIMS OF
 *     INFRINGEMENT, IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 *     FOR A PARTICULAR PURPOSE.
 *
 *     Xilinx products are not intended for use in life support appliances,
 *     devices, or systems. Use in such applications is expressly prohibited.
 *
 *     (c) Copyright 2008 Xilinx Inc.
 *     All rights reserved.
 *
 *****************************************************************************/

/*
 * This file contains a simple non-synthesizeable simulation testbench.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>
//#include "system.h"
//#include "packet_sim.h"
//#include "seewave_compat.h"
//#include "locallink.h"
#include "ap_axi_sdata.h"
#include "ap_int.h"
#include "hls_stream.h"
//#include "pcap_support.h"
#include "stdint.h"
#include <assert.h>


void packetSlurper(hls::stream<ap_axiu<32,1,1,1> > &in,  hls::stream<ap_axiu<32,1,1,1> > &inControl,
                   hls::stream<ap_axiu<32,1,1,1> > &out, hls::stream<ap_axiu<32,1,1,1> > &outControl,
                   ap_uint<32> data[1024]);

int main(int argc, char *argv[]) {
    hls::stream<ap_axiu<32,1,1,1> > in("in");
    hls::stream<ap_axiu<32,1,1,1> > inStatus("inStatus");
    hls::stream<ap_axiu<32,1,1,1> > out("out0");
    hls::stream<ap_axiu<32,1,1,1> > outStatus("out0Status");
    ap_uint<32> data[1024];
    data[0x190] = 0;
    data[0x390] = 0;
    int retval = 0;

    // Send several packets
    for(int size = 64; size < 72; size++) {
        std::cout << "Sending " << size << " Bytes\n";
 
        // packetSlurper(in, inStatus, out, outStatus, data);
        // assert(data[0x190] == 0);
        // assert(data[0x390] == 0);

        for(int i = 0; i < 24; i++) {
            data[i] = i;
        }
        for(int i = 0; i < 6; i++) {
            data[0x180+i] = i;
        }
        data[0x194] = size;
        data[0x190] = 1;
        data[0x390] = 0;
        packetSlurper(in, inStatus, out, outStatus, data);

        ap_axiu<32,1,1,1> tmp;
        int i = 0;
        while(!out.empty()) {
            tmp = out.read();
            std::cout << i << " " << tmp.data << " " << tmp.keep << " " << tmp.strb << "\n";
            in.write(tmp);
            i++;
        }
        std::cout << "Got " << i << " Data Beats\n";
        assert(data[0x190] == 0);
        assert(data[0x390] == 0);
        assert(tmp.last == 1);

        for(int i = 0; i < 6; i++) {
            tmp = outStatus.read();
            std::cout << i << " " << tmp.data << " " << tmp.keep << " " << tmp.strb << "\n";
            inStatus.write(tmp);
        }
        assert(tmp.last == 1);

        // Receive the packet;
        packetSlurper(in, inStatus, out, outStatus, data);
        std::cout << "Received " << data[0x394] << " Bytes\n";
        assert(data[0x394] == size);
        assert(data[0x190] == 0);
        assert(data[0x390] == 1);
        data[0x390] = 0;

        packetSlurper(in, inStatus, out, outStatus, data);
        assert(data[0x190] == 0);
        assert(data[0x390] == 0);
    }
    return retval;
}
