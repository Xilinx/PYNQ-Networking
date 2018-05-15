#include "ap_axi_sdata.h"
#include "hls_stream.h"
#include "hls/utils/x_hls_utils.h"
#include "assert.h"

#define MTU 1500

template<int N>
ap_uint<BitWidth<N>::Value> keptbytes(ap_uint<N> keep) {
    for(int i = 1; i < N; i++) {
        if(keep[i] && !keep[i-1]) {
            std::cout << "Sparse keep not allowed: " << std::hex << keep << "\n."; assert(false);
        }
    }
    return ap_uint<N+1>(~keep).reverse().countLeadingZeros();
}
// 0 -> 0b1111
// 1 -> 0b0001
// 2 -> 0b0011
// 3 -> 0b0111
template<int N>
void init_generatekeep_ROM(ap_uint<N> table[64]) {
#pragma HLS inline self off
    for(int i = 0; i < N; i++) {
        table[i] = (i == 0) ? -1 : (1<<i)-1;
    }
}
template<int N>
ap_uint<N> generatekeep(ap_uint<BitWidth<N>::Value> remainder) {
#pragma HLS inline
    ap_uint<N> table[64]; // FIXME: workaround for HLS bug.
    init_generatekeep_ROM(table);
    return table[remainder];
}
template<>
inline ap_uint<4> generatekeep<4>(ap_uint<BitWidth<4>::Value> remainder) {
#pragma HLS inline
    const ap_uint<4> table[64] = {0xF, 0x1, 0x3, 0x7}; // FIXME: workaround for HLS bug.
    return table[remainder];
}
template<>
inline ap_uint<8> generatekeep<8>(ap_uint<BitWidth<8>::Value> remainder) {
#pragma HLS inline
    const ap_uint<8> table[64] = {0xFF, 0x1, 0x3, 0x7, 0xF, 0x1F, 0x3F, 0x7F}; // FIXME: workaround for HLS bug.
    return table[remainder];
}
template<>
inline ap_uint<16> generatekeep<16>(ap_uint<BitWidth<16>::Value> remainder) {
#pragma HLS inline
    const ap_uint<16> table[64] = {0xFFFF, 0x1, 0x3, 0x7, 0xF, 0x1F, 0x3F, 0x7F,
                                   0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF, 0x1FFF, 0x3FFF, 0x7FFF}; // FIXME: workaround for HLS bug.
    return table[remainder];
}

// data layout:
// data[0..0x180]: packet data to stream 'output'
// data[0x180..0x185]: control words for stream 'output'
// data[0x190]: mailbox. when written as non-zero, triggers the transfer of a packet.  Written as zero to signal the completion of transfer.
// data[0x194]: packet size (in bytes) to transfer
// data[0x200..0x380]: packet data from stream 'input'
// data[0x380..0x385]: control words from stream 'input'
// data[0x390]: mailbox. written as non-zero, to signal the presence of a packet.  when written as non-zero, triggers capture of the next packet.
// data[0x394]: packet size (in bytes)

void packetSlurper(hls::stream<ap_axiu<32,1,1,1> > &in,  hls::stream<ap_axiu<32,1,1,1> > &inControl,
                   hls::stream<ap_axiu<32,1,1,1> > &out, hls::stream<ap_axiu<32,1,1,1> > &outControl,
                   ap_uint<32> data[1024]) {
#pragma HLS INTERFACE ap_ctrl_none port=return
#pragma HLS INTERFACE axis port=in
#pragma HLS INTERFACE axis port=inControl
#pragma HLS INTERFACE axis port=out
#pragma HLS INTERFACE axis port=outControl
#pragma HLS INTERFACE bram port=data 
#pragma HLS resource variable=data core=RAM_1P_BRAM

//  unsigned txC[6] = {0xA0000000, 2, 0, 0, 0, 0};
	if(!in.empty() && !inControl.empty() && data[0x390] == 0) {
		//send control first
		bool finished = false;
        int inControlCount = 0;
		while(!finished) {
#pragma HLS PIPELINE
			ap_axiu<32,1,1,1> tmp;
			inControl.read(tmp);
            data[0x380+inControlCount] = tmp.data;
            if(inControlCount < 7) inControlCount++;
            if(tmp.last)
				finished = true;
		}

		//then send the data
		bool done = false;
        int inCount = 0;
		while(!done) {
#pragma HLS PIPELINE
			ap_axiu<32,1,1,1> tmp;
			in.read(tmp);
            if(inCount < MTU+1) {
                data[0x200+inCount/4] = tmp.data;
                inCount += keptbytes(tmp.keep);
            }
            if(tmp.last)
				done = true;
		}
        std::cout << inControlCount << " " << inCount << "\n";
        //if(inControlCount > 6 || inCount > MTU) {
        data[0x394] = inCount; // What about last strobe?
        data[0x390] = 1;
        //        }
    }

	if(!out.full() && data[0x190] == 1) {
		//send control first
		ap_axiu<32,1,1,1> tmp;
		for(int i = 0; i < 6; i++) {
#pragma HLS PIPELINE II=1
			tmp.data = data[0x180+i];
			tmp.dest = 0;
			tmp.id = 0;
			tmp.keep = 0xF;
			tmp.last = (i == 5);
			tmp.strb = 0xF;
			tmp.user = 0;
			outControl.write(tmp);
		}

		//write the data
        int outCount = data[0x194];
        assert(outCount <= MTU);
        int lastdb = (outCount+3)/4;
        for(int i = 0; i < lastdb; i++) {
#pragma HLS PIPELINE
			ap_axiu<32,1,1,1> tmp;
            tmp.data = data[0x0+i];
			tmp.dest = 0;
			tmp.id = 0;
            tmp.last = (i == lastdb-1);
            int remainder = outCount % 4;
            ap_uint<4> lastkeep = generatekeep<4>(remainder);
			tmp.keep = tmp.last ? lastkeep: ap_uint<4>(0xF);
            tmp.strb = tmp.last ? lastkeep: ap_uint<4>(0xF);
            std::cout << "out: " << outCount << " " << tmp.keep << "\n";
            out.write(tmp);
		}
        data[0x190] = 0;
	}
}
