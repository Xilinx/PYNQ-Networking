#ifndef _XLNX_DMA_H_
#define _XLNX_DMA_H_

#include <linux/dma-mapping.h>
#include <linux/dmaengine.h>
#include <linux/if_ether.h>
#include <linux/interrupt.h>
#include <linux/ioport.h>
#include <linux/slab.h>     /* kmalloc() */
#include <linux/spinlock.h>

#include <asm/io.h>

#include "xlnx_irq.h"

/* AXI-DMA register offsets */
#define AXI_DMA_MM2S_DMACR          0x00        // MM2S DMA control register
#define AXI_DMA_MM2S_DMASR          0x04        // MM2S DMA status register
#define AXI_DMA_S2MM_DMACR          0x30        // S2MM DMA control register
#define AXI_DMA_S2MM_DMASR          0x34        // S2MM DMA status register
/* AXI-DMA simple memory transfer offsets */
#define AXI_DMA_MM2S_SA             0x18        // MM2S DMA source address
#define AXI_DMA_MM2S_LENGTH         0x28        // MM2S DMA transfer length
#define AXI_DMA_S2MM_DA             0x48        // S2MM DMA destination address
#define AXI_DMA_S2MM_LENGTH         0x58        // S2MM DMA transfer length
/* AXI-DMA scatter-gather memory  offsets */
#define AXI_DMA_SG_CTL              0x2C        // Scatter/Gather user and cache
#define AXI_DMA_MM2S_CURRDESC       0x08        // MM2S current descriptor pointer
#define AXI_DMA_MM2S_TAILDESC       0x10        // MM2S tail descriptor pointer
#define AXI_DMA_S2MM_CURRDESC       0x38        // S2MM current descriptor pointer
#define AXI_DMA_S2MM_TAILDESC       0x40        // S2MM tail descriptor pointer
/* AXI-DMA control flags */
#define AXI_DMA_START               0x00000001
#define AXI_DMA_RESET               0x00000004
#define AXI_DMA_KEYHOLE             0x00000008
#define AXI_DMA_CYCLIC_BD           0x00000010
#define AXI_DMA_IOC_IRQ             0x00001000
#define AXI_DMA_DLY_IRQ             0x00002000
#define AXI_DMA_ERR_IRQ             0x00004000
/* AXI-DMA status flag masks */
#define AXI_DMA_HALT                0x00000001
#define AXI_DMA_IDLE                0x00000002
#define AXI_DMA_SG_INCL             0x00000008
#define AXI_DMA_INT_ERR             0x00000010
#define AXI_DMA_SLV_ERR             0x00000020
#define AXI_DMA_DEC_ERR             0x00000040
#define AXI_DMA_SG_INT_ERR          0x00000100
#define AXI_DMA_SG_SLV_ERR          0x00000200
#define AXI_DMA_SG_DEC_ERR          0x00000400
#define AXI_DMA_THRESHOLD           0x00FF0000
#define AXI_DMA_DELAY               0xFF000000
#define AXI_DMA_ERROR               0x00000770  // any error
#define AXI_DMA_INTERRUPT           0x00007000  // any interrupt
/* scatter-gather descriptory control/status flags */
#define SG_BD_LEN_MASK              0x007FFFFF
#define SG_BD_SOP                   0x08000000
#define SG_BD_EOP                   0x04000000
#define SG_BD_SOP_EOP               0x0C000000  // both SOP and EOP
#define SG_BD_INT_ERR               0x10000000
#define SG_BD_SLV_ERR               0x20000000
#define SG_BD_DEC_ERR               0x40000000
#define SG_BD_ERROR                 0x70000000  // any error
#define SG_BD_CMPL                  0x80000000
/* AXI-DMA kernel driver defines */
#define XLNX_DMA_BD_COUNT           128         // NAPI budget is 64
#define XLNX_DMA_MAX_PAGE_SIZE      4096        // PAGESIZE for PYNQ



/** xlnx_dma_device - a container for a single AXI-DMA controller
 */
struct xlnx_dma_device {
    const char                  *name;
    resource_size_t             base_addr;
    resource_size_t             base_len;
    void __iomem                *virt_addr;
};

/** struct xlnx_dma_bd - a contianer for the AXI-DMA scatter gather block
 *      descriptor.
 *  NOTES: for 32-bit operation the MSB fields should always be 0
 */
struct xlnx_dma_bd {
    u32                         next_desc;
    u32                         next_desc_msb;
    u32                         buf_addr;
    u32                         buf_addr_msb;
    u32                         empty[2];
    u32                         control;
    u32                         status;
    u32                         user_app[5];
} __aligned(64);

/** xlnx_dma_chan -  a container for a single AXI-DMA channel used to
 *      hold state of MM2S or S2MM channel.
 */
struct xlnx_dma_chan {
    const char                  *name;
    struct device               *dev;
    spinlock_t                  lock;
    enum dma_transfer_direction direction;
    void __iomem                *virt_addr;
    struct tasklet_struct       tasklet;

    int                         bd_size;
    int                         bd_curr;
    int                         bd_tail;
    struct xlnx_dma_bd*         bd_pool[XLNX_DMA_BD_COUNT];
    phys_addr_t*                bd_kaddr[XLNX_DMA_BD_COUNT];
    dma_addr_t                  bd_base_addr;
};

struct xlnx_dma_chan_config {
    const char                  *name;
    enum dma_transfer_direction direction;
    struct xlnx_dma_device      *parent;

    int                         irq;
    irq_handler_t               irq_handler;
    void                        *irq_data;
};


void xlnx_dma_scrub_bd(struct xlnx_dma_bd *desc, u32 control)
{
    desc->control       = control;
    desc->status        = 0x0;
    desc->user_app[0]   = 0x0;
    desc->user_app[1]   = 0x0;
    desc->user_app[2]   = 0x0;
    desc->user_app[3]   = 0x0;
    desc->user_app[4]   = 0x0;
}

/** initialization and cleanup functions */
int xlnx_dma_device_init(struct xlnx_dma_device *dev, const char *name,
        resource_size_t start, resource_size_t n)
{
    dev->name = name;
    dev->base_addr = start;
    dev->base_len = n;

    /* setup iomem mapping */
    if (!request_mem_region(start, n, name)) {
        return -ENODEV;
    }

    dev->virt_addr = ioremap(start, n);
    return 0;
}

void xlnx_dma_device_cleanup(struct xlnx_dma_device *dev)
{
    iounmap(dev->virt_addr);
    release_mem_region(dev->base_addr, dev->base_len);
}

int xlnx_dma_chan_bd_init(struct xlnx_dma_chan *chan)
{
    int err, i;
    u32 bd_control;
    void __iomem* ptr;

    /* allocate BD space */
    chan->dev = NULL;
    ptr = dma_zalloc_coherent(chan->dev,
            sizeof(struct xlnx_dma_bd) * XLNX_DMA_BD_COUNT,
            &(chan->bd_base_addr),
            GFP_KERNEL);
    if (!ptr) {
        printk(KERN_ERR "xlnx_dma: could not allocate bd ring\n");
        return -ENOMEM;
    }

    chan->bd_size = XLNX_DMA_BD_COUNT;
    for (i = 0; i < XLNX_DMA_BD_COUNT; ++i) {
        chan->bd_pool[i] = (struct xlnx_dma_bd *)
            (ptr + (sizeof(struct xlnx_dma_bd) * i));
        chan->bd_pool[i]->next_desc = chan->bd_base_addr +
            (sizeof(struct xlnx_dma_bd) * ((i+1) % XLNX_DMA_BD_COUNT));
    }

    /* allocate DMA space for packets */
    if (chan->direction == DMA_DEV_TO_MEM) {
        bd_control = XLNX_DMA_MAX_PAGE_SIZE | SG_BD_SOP_EOP;
        chan->bd_curr = 0;
        chan->bd_tail = chan->bd_size - 2;
    } else {
        bd_control = 0x00000000 | SG_BD_SOP_EOP;
        chan->bd_curr = 0;
        chan->bd_tail = 0;
    }

    for (i = 0; i < XLNX_DMA_BD_COUNT; ++i) {
        chan->bd_kaddr[i] = dma_zalloc_coherent(chan->dev,
                XLNX_DMA_MAX_PAGE_SIZE,
                &(chan->bd_pool[i]->buf_addr),
                GFP_KERNEL);
        if (!chan->bd_kaddr[i]) {
            err = -ENOMEM;
            goto cleanup_bd_alloc;
        }
        xlnx_dma_scrub_bd(chan->bd_pool[i], bd_control);
    }

    return 0;

cleanup_bd_alloc:
    i--;
    while (i >= 0) {
        dma_free_coherent(chan->dev,
                XLNX_DMA_MAX_PAGE_SIZE,
                chan->bd_kaddr[i],
                chan->bd_pool[i]->buf_addr);
    }
    dma_free_coherent(chan->dev,
            sizeof(struct xlnx_dma_bd) * XLNX_DMA_BD_COUNT,
            chan->bd_pool[0],
            chan->bd_base_addr);
    return err;
}

void xlnx_dma_chan_bd_cleanup(struct xlnx_dma_chan *chan)
{
    int i;
    for (i = 0; i < XLNX_DMA_BD_COUNT; ++i) {
        dma_free_coherent(chan->dev,
                XLNX_DMA_MAX_PAGE_SIZE,
                chan->bd_kaddr[i],
                chan->bd_pool[i]->buf_addr);
    }
    dma_free_coherent(chan->dev,
            sizeof(struct xlnx_dma_bd) * XLNX_DMA_BD_COUNT,
            chan->bd_pool[0],
            chan->bd_base_addr);
}

int xlnx_dma_chan_init(struct xlnx_dma_chan *chan,
        struct xlnx_dma_chan_config *config)
{
    int err;

    /* a dma controller should have been intialized before a channel */
    if (!config->parent) {
        return -EINVAL;
    }

    /* allocate kernel memory for the channel */
    chan->name = config->name;
    chan->virt_addr = config->parent->virt_addr;
    chan->direction = config->direction;

    /* initalize the interrupt & handlers */
    if (config->irq <= 0) {
        return -EINVAL;
    }
    config->irq = xlate_irq(config->irq);
    if (config->irq <= 0) {
        return -ENODEV;
    }
    err = request_irq(config->irq, config->irq_handler, 0, config->name, config->irq_data);
    if (err < 0) {
        irq_dispose_mapping(config->irq);
        return err;
    }
    spin_lock_init(&(chan->lock));

    /* allocate and initialize the scatter-gather BDs */
    err = xlnx_dma_chan_bd_init(chan);
    if (err < 0) {
        goto cleanup_chan_irq;
    }

    return 0;

cleanup_chan_irq:
    free_irq(config->irq, chan);
    irq_dispose_mapping(config->irq);
    return err;
}

void xlnx_dma_chan_cleanup(struct xlnx_dma_chan *chan,
        struct xlnx_dma_chan_config *config)
{
    xlnx_dma_chan_bd_cleanup(chan);
    free_irq(config->irq, chan);
    irq_dispose_mapping(config->irq);
}




void xlnx_dma_pprint(struct xlnx_dma_device *dev)
{
    printk(KERN_INFO "\tMM2S_DMACR   : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_MM2S_DMACR));
    printk(KERN_INFO "\tMM2S_DMASR   : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_MM2S_DMASR));
    printk(KERN_INFO "\tMM2S_CURDESC : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_MM2S_CURRDESC));
    printk(KERN_INFO "\tMM2S_TAILDESC: 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_MM2S_TAILDESC));
    //printk(KERN_INFO "\tSG_CTL       : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_SG_CTL));
    printk(KERN_INFO "\tS2MM_DMACR   : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_S2MM_DMACR));
    printk(KERN_INFO "\tS2MM_DMASR   : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_S2MM_DMASR));
    printk(KERN_INFO "\tS2MM_CURDESC : 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_S2MM_CURRDESC));
    printk(KERN_INFO "\tS2MM_TAILDESC: 0x%08x\n", ioread32(dev->virt_addr + AXI_DMA_S2MM_TAILDESC));
}

void xlnx_dma_chan_pprint(struct xlnx_dma_chan *chan)
{
    printk(KERN_INFO "\tbd_size     : %d\n", chan->bd_size);
    printk(KERN_INFO "\tbd_curr     : %d\n", chan->bd_curr);
    printk(KERN_INFO "\tbd_tail     : %d\n", chan->bd_tail);
}

void xlnx_dma_bd_pprint(struct xlnx_dma_bd *desc)
{
    printk(KERN_INFO "\tnext_desc   : 0x%08x\n", desc->next_desc);
    printk(KERN_INFO "\tbuf_addr    : 0x%08x\n", desc->buf_addr);
    printk(KERN_INFO "\tcontrol     : 0x%08x\n", desc->control);
    printk(KERN_INFO "\tstatus      : 0x%08x\n", desc->status);
    printk(KERN_INFO "\tuser_app    : 0x%08x\n", desc->user_app[0]);
    printk(KERN_INFO "\t            : 0x%08x\n", desc->user_app[1]);
    printk(KERN_INFO "\t            : 0x%08x\n", desc->user_app[2]);
    printk(KERN_INFO "\t            : 0x%08x\n", desc->user_app[3]);
    printk(KERN_INFO "\t            : 0x%08x\n", desc->user_app[4]);
}



#define DMA_RD(addr, offset)            ioread32(addr + offset)
#define DMA_WR(addr, offset, value)     iowrite32(value, addr + offset)

/* allow user to get info about the DMA channel */
__always_inline u32 xlnx_dma_control(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    return DMA_RD(chan->virt_addr, offset);
}
__always_inline u32 xlnx_dma_status(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMASR : AXI_DMA_S2MM_DMASR;
    return DMA_RD(chan->virt_addr, offset);
}

/* allow user to start/stop/reset/init the DMA channels */
__always_inline void xlnx_dma_start(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    DMA_WR(chan->virt_addr, offset, DMA_RD(chan->virt_addr, offset) | AXI_DMA_START);
}
__always_inline void xlnx_dma_stop(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    DMA_WR(chan->virt_addr, offset, DMA_RD(chan->virt_addr, offset) & ~AXI_DMA_START);
}
__always_inline void xlnx_dma_reset(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    DMA_WR(chan->virt_addr, offset, DMA_RD(chan->virt_addr, offset) | AXI_DMA_RESET);
}
__always_inline void xlnx_dma_irq_en(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    u32 value = DMA_RD(chan->virt_addr, offset) | AXI_DMA_IOC_IRQ | AXI_DMA_DLY_IRQ;
    DMA_WR(chan->virt_addr, offset, value);
}
__always_inline void xlnx_dma_irq_stop(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    u32 value = DMA_RD(chan->virt_addr, offset) & ~(AXI_DMA_IOC_IRQ | AXI_DMA_DLY_IRQ);
    DMA_WR(chan->virt_addr, offset, value);
}

/* allow user to interract with the DMA channels at runtime */
__always_inline void xlnx_dma_delay_and_threshold(struct xlnx_dma_chan *chan,
        u8 delay, u8 threshold) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMACR : AXI_DMA_S2MM_DMACR;
    u32 mask = AXI_DMA_DELAY | AXI_DMA_THRESHOLD;
    u32 new_val = (((u32)delay << 24) + ((u32)threshold << 16)) & mask;
    u32 old_val = DMA_RD(chan->virt_addr, offset) & (~mask);
    DMA_WR(chan->virt_addr, offset, old_val | new_val);
}
__always_inline void xlnx_dma_currdesc(struct xlnx_dma_chan *chan, u32 val) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_CURRDESC : AXI_DMA_S2MM_CURRDESC;
    DMA_WR(chan->virt_addr, offset, val);
}
__always_inline void xlnx_dma_taildesc(struct xlnx_dma_chan *chan, u32 val) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_TAILDESC : AXI_DMA_S2MM_TAILDESC;
    DMA_WR(chan->virt_addr, offset, val);
}
__always_inline void xlnx_dma_irq_ack(struct xlnx_dma_chan *chan) {
    u32 offset = (chan->direction == DMA_MEM_TO_DEV)?  AXI_DMA_MM2S_DMASR : AXI_DMA_S2MM_DMASR;
    u32 value = DMA_RD(chan->virt_addr, offset) & (AXI_DMA_IOC_IRQ | AXI_DMA_DLY_IRQ);
    DMA_WR(chan->virt_addr, offset, value);
}

#undef DMA_RD
#undef DMA_WR

__always_inline bool xlnx_dma_chan_running(u32 control)
{ return control & AXI_DMA_START; }

__always_inline bool xlnx_dma_chan_ioc_enable(u32 control)
{ return control & AXI_DMA_IOC_IRQ; }

__always_inline bool xlnx_dma_chan_halted(u32 status)
{ return status & AXI_DMA_HALT; }

__always_inline bool xlnx_dma_chan_idle(u32 status)
{ return status & AXI_DMA_IDLE; }

__always_inline bool xlnx_dma_chan_sg(u32 status)
{ return status & AXI_DMA_SG_INCL; }

__always_inline bool xlnx_dma_chan_irc(u32 status)
{ return status & AXI_DMA_INTERRUPT; }

__always_inline bool xlnx_dma_chan_error(u32 status)
{ return status & AXI_DMA_ERROR; }


__always_inline int xlnx_dma_bd_next(struct xlnx_dma_chan *chan, int index)
{ return (index + 1) % chan->bd_size; }

__always_inline dma_addr_t xlnx_dma_bd_addr(struct xlnx_dma_chan *chan,
        size_t index)
{ return chan->bd_base_addr + (sizeof(struct xlnx_dma_bd) * index); }

__always_inline bool xlnx_dma_bd_err(struct xlnx_dma_bd *bd)
{ return bd->status & SG_BD_ERROR; }

__always_inline bool xlnx_dma_bd_valid(struct xlnx_dma_bd *bd)
{ return bd->status & SG_BD_SOP_EOP; }

__always_inline u32 xlnx_dma_bd_len(struct xlnx_dma_bd *bd)
{ return bd->status & SG_BD_LEN_MASK; }


int xlnx_dma_chan_start_with_irq(struct xlnx_dma_chan *chan)
{
    dma_addr_t currptr;
    dma_addr_t tailptr;

    currptr = xlnx_dma_bd_addr(chan, chan->bd_curr);
    xlnx_dma_currdesc(chan, currptr);
    xlnx_dma_start(chan);
    xlnx_dma_irq_en(chan);
    if (chan->direction == DMA_DEV_TO_MEM) {
        tailptr = xlnx_dma_bd_addr(chan, chan->bd_tail);
        xlnx_dma_taildesc(chan, tailptr);
    }
    return 0;
}

int xlnx_dma_chan_send_packet(struct xlnx_dma_chan *chan, void *buf, size_t len)
{
    struct xlnx_dma_bd *bd;
    int indx, next;
    dma_addr_t indxptr;
    unsigned long flags;

    /* make sure the channel is for sending too the DMA */
    if (chan->direction != DMA_MEM_TO_DEV) {
        return -EINVAL;
    }

    /* FIXME: cleanup current block descriptors now */
    spin_lock_irqsave(&(chan->lock), flags);
    indx = chan->bd_curr;
    next = xlnx_dma_bd_next(chan, indx);
    while ((chan->bd_pool[indx]->status & SG_BD_CMPL) && (next != chan->bd_tail)) {
        indx = next;
        next = xlnx_dma_bd_next(chan, indx);
        // printk(KERN_INFO "xlnx_dma: curr descriptor done: %d\n", indx);
    }
    chan->bd_curr = indx;
    spin_unlock_irqrestore(&(chan->lock), flags);
    /* FIXME: end */

    /* make sure the data can fit within an ethernet frame */
    if (len > ETH_FRAME_LEN) {
        return -ENOMEM;
    }
    /* make sure we have enough buffer space to send the packet */
    spin_lock_irqsave(&(chan->lock), flags);
    indx = chan->bd_tail;
    next = xlnx_dma_bd_next(chan, indx);
    if (next == chan->bd_curr) {
        // printk(KERN_INFO "xlnx_dma: drop packet because buffer is full\n");
        spin_unlock_irqrestore(&(chan->lock), flags);
        return -ENOMEM;
    }

    bd = chan->bd_pool[indx];
    xlnx_dma_scrub_bd(bd, len | SG_BD_SOP_EOP);
    memcpy(chan->bd_kaddr[indx], buf, len);

    indxptr = xlnx_dma_bd_addr(chan, indx);
    xlnx_dma_taildesc(chan, indxptr);
    chan->bd_tail = next;
    spin_unlock_irqrestore(&(chan->lock), flags);

    return len;
}


#endif  /* _XLNX_DMA_H_ */
