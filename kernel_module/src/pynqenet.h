#ifndef _PYNQENET_H_
#define _PYNQENET_H_

#include <linux/netdevice.h>

#include "xlnx_dma.h"

#define DRV_NAME                "pynqenet"
#define DRV_VERSION             "1.0-NAPI"

/* default hw values */
#define PYNQ_SG_DMA_BASE        0x80400000
#define PYNQ_SG_DMA_LEN         0x00010000
#define PYNQ_SG_MM2S_IRQ        62
#define PYNQ_SG_S2MM_IRQ        63

struct pynqenet_device {
    struct net_device *ndev;
    unsigned dma_base;
    unsigned dma_len;
    unsigned dma_mm2s_irq;
    unsigned dma_s2mm_irq;
};

struct pynqenet_adapter {
    struct pynqenet_device *pdev;
    struct net_device *ndev;
    struct xlnx_dma_device *dma_dev;
    //spinlock_t stats_lock;

    /* TX */
    struct xlnx_dma_chan *tx_chan;

    /* RX */
    struct xlnx_dma_chan *rx_chan;
    struct napi_struct napi;
};

void packet_hexdump(void *buf, int len)
{
    int i;
    u8 *encap = (u8 *)buf;
    printk(KERN_DEBUG "packet (%d bytes)\n", len);
    for (i = 0; i < len; ++i) {
        if ((i%16) == 0)
            printk(KERN_DEBUG "\t%02x", encap[i]);
        else if ((i%8) == 0)
            printk(KERN_CONT "   %02x", encap[i]);
        else
            printk(KERN_CONT " %02x", encap[i]);
    }
    printk(KERN_CONT "\n");
}

#endif  /* _PYNQENET_H_ */
