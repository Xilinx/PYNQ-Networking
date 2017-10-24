#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>

#include <linux/etherdevice.h>

#include "module_param_hex.h"
#include "pynqenet.h"

MODULE_LICENSE("GPL");
MODULE_VERSION(DRV_VERSION);

/**
 * pynqenet_tx_th - top half of the TX IRQ handler
 *
 * here we schedule a bottom-half tasket to free the TX resources
 **/
static irqreturn_t pynqenet_tx_th(int irq, void *data)
{
    struct pynqenet_adapter *adapter = data;
    u32 status;

    status = xlnx_dma_status(adapter->tx_chan);
    if (unlikely(!xlnx_dma_chan_irc(status))) {
        return IRQ_NONE;    /* not our interrupt */
    }

    /* FIXME: check for errors */
    /* FIXME: schedule tasklet to cleanup resources? */

    xlnx_dma_irq_ack(adapter->tx_chan);
    return IRQ_HANDLED;
}

/**
 * pynqenet_rx_th - top half of the RX IRQ handler
 *  @irq: interrupt number
 *  @data: pointer to network adapter
 **/
static irqreturn_t pynqenet_rx_th(int irq, void *data)
{
    struct pynqenet_adapter *adapter = data;
    u32 status;

    status = xlnx_dma_status(adapter->rx_chan);
    if (unlikely(!xlnx_dma_chan_irc(status))) {
        return IRQ_NONE;    /* not our interrupt */
    }

    /* FIXME: check for error status */

    /* disable interrupts & schedule napi_poll() */
    xlnx_dma_irq_stop(adapter->rx_chan);
    xlnx_dma_irq_ack(adapter->rx_chan);
    napi_schedule(&adapter->napi);
    return IRQ_HANDLED;
}

static void pynqenet_rx_recv(struct net_device *dev, void *buf, int len)
{
    // struct pynqenet_adapter *adapter = netdev_priv(dev);
    struct sk_buff *skb;
    int err;

    skb = netdev_alloc_skb(dev, len + 2);
    if (unlikely(!skb)) {
        if (printk_ratelimit())
            netdev_notice(dev, "packet dropped ratelimit()\n");
        dev->stats.rx_dropped++;
        return;
    }

    skb_reserve(skb, 2);
    memcpy(skb_put(skb, len), buf, len);

    // /* TODO: here for debugging */
    // printk(KERN_DEBUG "pynqenet: rx_packet\n");
    // packet_hexdump(buf, len);

    /* NOTE: forward directly to some other adapter interface */
    /*  skb->dev = adapter->fwd_dev;
     *  skb->priority = 0;
     *  if (likely(dev_queue_xmit(skb) == NET_XMIT_SUCCESS)) {
     */
    /* NOTE: pass along to the linux kernel */
    skb->protocol = eth_type_trans(skb, dev);
    if (likely(netif_receive_skb(skb) == NET_RX_SUCCESS)) {
        dev->stats.rx_packets++;
        dev->stats.rx_bytes += len;
    } else {
        printk(KERN_NOTICE "slurper: drop packet netif_receive_skb(): %d\n", err);
        dev->stats.rx_dropped++;
    }
}

/**
 * pynqenet_rx_clean - send received data up the network stack
 *
 * Result # of packets handled
 *
 * clean bd resources after use
 */
static int pynqenet_rx_clean(struct pynqenet_adapter *adapter, int budget)
{
    struct net_device *ndev = adapter->ndev;
    struct xlnx_dma_chan *chan = adapter->rx_chan;
    struct xlnx_dma_bd *bd;

    int i, length, work_done;
    dma_addr_t tailptr;

    /* get the first packet */
    work_done = 0;
    i = chan->bd_curr;
    bd = chan->bd_pool[i];

    /* work until done, or until the budget is spent */
    while (work_done < budget && xlnx_dma_bd_valid(bd)) {
        work_done++;

        length = xlnx_dma_bd_len(bd);
        pynqenet_rx_recv(ndev, chan->bd_kaddr[i], length);
        xlnx_dma_scrub_bd(bd, XLNX_DMA_MAX_PAGE_SIZE | SG_BD_SOP_EOP);

        i = xlnx_dma_bd_next(chan, i);
        bd = chan->bd_pool[i];
        chan->bd_tail = xlnx_dma_bd_next(chan, chan->bd_tail);
    }

    /* update DMA controller */
    chan->bd_curr = i;
    tailptr = xlnx_dma_bd_addr(chan, chan->bd_tail);
    xlnx_dma_taildesc(chan, tailptr);

    return work_done;
}

/**
 * pynqenet_napi_poll - NAPI RX polling callback
 *
 * return the amount of work that has been done. if the budget is not
 * fully consumed then exit polling mode.
 *
 * FIXME: we could also take this time to cleanup the tx resources
 **/
static int pynqenet_napi_poll(struct napi_struct *napi, int budget)
{
    struct pynqenet_adapter *adapter = container_of(napi,
            struct pynqenet_adapter, napi);
    int work_done = 0;

    work_done = pynqenet_rx_clean(adapter, budget);
    if (work_done < budget) {
        napi_complete(napi);
        xlnx_dma_irq_en(adapter->rx_chan);
    }

    return work_done;
}

static struct xlnx_dma_chan_config pynqenet_mm2s_config __read_mostly = {
    .name           = "pynqenet_mm2s",
    .direction      = DMA_MEM_TO_DEV,
    .irq            = PYNQ_SG_MM2S_IRQ,
    .irq_handler    = pynqenet_tx_th,
};
static struct xlnx_dma_chan_config pynqenet_s2mm_config __read_mostly = {
    .name           = "pynqenet_s2mm",
    .direction      = DMA_DEV_TO_MEM,
    .irq            = PYNQ_SG_S2MM_IRQ,
    .irq_handler    = pynqenet_rx_th,
};

/**
 * pynqenet_open - called when a network interface is brought up
 *
 * Returns 0 on success, netagive value on failure
 *
 * when the interface is brought up we need to allocate the resources: RX/TX
 * ring buffers, interrupt handlers, NAPI needs to be enabled.
 **/
static int pynqenet_open(struct net_device *dev)
{
    struct pynqenet_adapter *adapter = netdev_priv(dev);
    int err;
    u32 status;

    netdev_info(dev, "pynqenet_open\n");
    napi_enable(&adapter->napi);

    err = -ENOMEM;
    pynqenet_mm2s_config.parent = adapter->dma_dev;
    pynqenet_mm2s_config.irq_data = adapter;
    err = xlnx_dma_chan_init(adapter->tx_chan, &pynqenet_mm2s_config);
    if (err < 0) {
        netdev_err(dev, "could not initalize TX channel\n");
        goto err_tx_chan_alloc;
    }

    pynqenet_s2mm_config.parent = adapter->dma_dev;
    pynqenet_s2mm_config.irq_data = adapter;
    err = xlnx_dma_chan_init(adapter->rx_chan, &pynqenet_s2mm_config);
    if (err < 0) {
        netdev_err(dev, "could not initalize RX channel\n");
        goto err_rx_chan_alloc;
    }

    // /* get access to foward interface */
    // err = -ENODEV;
    // adapter->fwd_dev = dev_get_by_name(&init_net, "eth0");
    // if (adapter->fwd_dev == NULL) {
    //     netdev_err(dev, "FWD DEV(%s) could not be found\n", "eth0");
    //     goto err_fwd_dev;
    // }
    // netdev_info(dev, "fwd iface:%s MAC:%pM\n", "eth0", adapter->fwd_dev->dev_addr);

    /* reset the DMA */
    err = -EINVAL;
    xlnx_dma_reset(adapter->tx_chan);
    xlnx_dma_reset(adapter->rx_chan); /* may not be needed */
    /* set the delay/threshold values & enable the DMA with interrupts */
    xlnx_dma_delay_and_threshold(adapter->rx_chan,
            64, (NAPI_POLL_WEIGHT >> 1));
    xlnx_dma_chan_start_with_irq(adapter->tx_chan);
    xlnx_dma_chan_start_with_irq(adapter->rx_chan);
    /* FIXME: debug code */
    xlnx_dma_pprint(adapter->dma_dev);

    status = xlnx_dma_control(adapter->tx_chan);
    if (!xlnx_dma_chan_running(status) || !xlnx_dma_chan_ioc_enable(status)) {
        netdev_err(dev, "TX channel issue: %08x\n", status);
        goto err_chan_status;
    }
    status = xlnx_dma_control(adapter->rx_chan);
    if (!xlnx_dma_chan_running(status) || !xlnx_dma_chan_ioc_enable(status)) {
        netdev_err(dev, "RX channel issue: %08x\n", status);
        goto err_chan_status;
    }

    netif_start_queue(dev);
    return 0;

err_chan_status:
//     dev_put(adapter->fwd_dev);
// err_fwd_dev:
    xlnx_dma_chan_cleanup(adapter->rx_chan, &pynqenet_s2mm_config);
err_rx_chan_alloc:
    xlnx_dma_chan_cleanup(adapter->tx_chan, &pynqenet_mm2s_config);
err_tx_chan_alloc:
    napi_disable(&adapter->napi);
    return err;
}

static int pynqenet_stop(struct net_device *dev)
{
    struct pynqenet_adapter *adapter = netdev_priv(dev);

    printk(KERN_DEBUG "pynqenet_stop\n");
    // dev_put(adapter->fwd_dev);
    xlnx_dma_chan_cleanup(adapter->rx_chan, &pynqenet_s2mm_config);
    xlnx_dma_chan_cleanup(adapter->tx_chan, &pynqenet_mm2s_config);
    napi_disable(&adapter->napi);
    netif_stop_queue(dev);
    return 0;
}

static netdev_tx_t pynqenet_xmit(struct sk_buff *skb, struct net_device *dev)
{
    struct pynqenet_adapter *adapter = netdev_priv(dev);

    int err, len;
    char *data, shortpkt[ETH_ZLEN];

    /* enforce minimum ethernet frame size */
    len = skb->len;
    data = skb->data;
    if (len < ETH_ZLEN) {
        memset(shortpkt, 0, ETH_ZLEN);
        memcpy(shortpkt, skb->data, skb->len);
        len = ETH_ZLEN;
        data = shortpkt;
    }

    // printk(KERN_DEBUG "pynqenet: tx_packet\n");
    // packet_hexdump(data, len);

    /* send the packet to the PL */
    err = xlnx_dma_chan_send_packet(adapter->tx_chan, data, len);
    if (err < 0) {
        netdev_info(dev, "TX to DMA failed: %d\n", err);
        dev->stats.tx_dropped++;
    } else {
        dev->stats.tx_bytes += skb->len;
        dev->stats.tx_packets += 1;
    }

    /* free the skb */
    skb_tx_timestamp(skb);
    dev_kfree_skb_any(skb);
    return NETDEV_TX_OK;
}


static void set_multicast_list(struct net_device *dev)
{
    /* just fake multicast ability? */
    /* dummy.c and veth.c do it so ... monkey see monkey do */
}

static const struct net_device_ops pynqenet_netdev_ops = {
    .ndo_open                   = pynqenet_open,
    .ndo_stop                   = pynqenet_stop,
    .ndo_start_xmit             = pynqenet_xmit,
    .ndo_set_rx_mode            = set_multicast_list,
    .ndo_validate_addr          = eth_validate_addr,
    .ndo_set_mac_address        = eth_mac_addr,
};

/**
 * FIXME: the ethtool operations could be more robust
 **/
static void pynqenet_get_drvinfo(struct net_device *dev,
        struct ethtool_drvinfo *info)
{
    strlcpy(info->driver, DRV_NAME, sizeof(info->driver));
    strlcpy(info->version, DRV_VERSION, sizeof(info->version));
}
static const struct ethtool_ops pynqenet_ethtool_ops = {
    .get_drvinfo                = pynqenet_get_drvinfo,
    .get_link                   = ethtool_op_get_link,
};

static void pynqenet_ether_setup(struct net_device *dev)
{
    ether_setup(dev);
    dev->ethtool_ops = &pynqenet_ethtool_ops;
    dev->netdev_ops = &pynqenet_netdev_ops;

    dev->flags      |= IFF_NOARP;
    dev->flags      &= ~IFF_MULTICAST;

    dev->priv_flags |= IFF_LIVE_ADDR_CHANGE;

    dev->features   |= NETIF_F_SG;
    // dev->features |= NETIF_F_SG | NETIF_F_FRAGLIST
    //     | NETIF_F_TSO
    //     | NETIF_F_HW_CSUM
    //     | NETIF_F_HIGHDMA
    //     | NETIF_F_LLTX;

    /* assign a random MAC address */
    eth_hw_addr_random(dev);
}

/**
 * pynqenet_probe - device initialization routine
 * @pdev: PYNQ device description
 *
 * Returns 0 on success, negative on failure
 *
 * this routine is a place holder, in case we want to migrate the code
 * to the device tree. It initalizes the network device, and the
 * AXI-DMA controller.
 **/
static int pynqenet_probe(struct pynqenet_device *pdev)
{
    struct net_device *ndev;
    struct pynqenet_adapter *adapter;
    struct xlnx_dma_device *dma_dev;
    struct xlnx_dma_chan *tx_chan;
    struct xlnx_dma_chan *rx_chan;

    int err;

    /* alloc_etherdev()
     *  allocates an ethernet device with the kernel using functions
     *  from /net/ethernet/eth.c
     *      name    : "eth%d"
     *      setup   : ether_setup
     * alloc_netdev()
     *  allows us to specify custom name and setup routines.
     */
    err = -ENOMEM;
    // ndev = alloc_etherdev(sizeof(struct pynqenet_adapter));
    ndev = alloc_netdev(sizeof(struct pynqenet_adapter),
            "pynq%d", NET_NAME_UNKNOWN, pynqenet_ether_setup);
    if (!ndev) {
        printk(KERN_ERR "pynqenet: could not allocate network device\n");
        return err;
    }

    dma_dev = (struct xlnx_dma_device *)kmalloc(
            sizeof(struct xlnx_dma_device), GFP_KERNEL);
    if (!dma_dev) {
        printk(KERN_ERR "pynqenet: could not allocate DMA controller\n");
        goto err_dma_alloc;
    }
    tx_chan = (struct xlnx_dma_chan *)kmalloc(
            sizeof(struct xlnx_dma_chan), GFP_KERNEL);
    if (!tx_chan) {
        printk(KERN_ERR "pynqenet: could not allocate TX (MM2S) channel");
        kfree(dma_dev);
        goto err_dma_alloc;
    }
    rx_chan = (struct xlnx_dma_chan *)kmalloc(
            sizeof(struct xlnx_dma_chan), GFP_KERNEL);
    if (!rx_chan) {
        printk(KERN_ERR "pynqenet: could not allocate RX (S2MM) channel");
        kfree(tx_chan);
        kfree(dma_dev);
        goto err_dma_alloc;
    }

    pdev->ndev = ndev;

    adapter = netdev_priv(ndev);
    adapter->pdev = pdev;
    adapter->ndev = ndev;
    adapter->dma_dev = dma_dev;
    adapter->tx_chan = tx_chan;
    adapter->rx_chan = rx_chan;

    /* bring up the dma controller */
    err = xlnx_dma_device_init(dma_dev, DRV_NAME,
            pdev->dma_base, pdev->dma_len);
    if (err < 0) {
        printk(KERN_ERR "pynqenet: could not initalize DMA controller\n");
        goto err_dma_init;
    }
    /* FIXME: check the the device is actually there? */

    /* register network device */
    netif_napi_add(ndev, &adapter->napi, pynqenet_napi_poll, NAPI_POLL_WEIGHT);
    err = register_netdev(ndev);
    if (err)
        goto err_netdev_register;

    return 0;

err_netdev_register:
    netif_napi_del(&adapter->napi);
    xlnx_dma_device_cleanup(dma_dev);
err_dma_init:
    kfree(dma_dev);
    kfree(tx_chan);
    kfree(rx_chan);
err_dma_alloc:
    free_netdev(ndev);

    return err;
}

static void pynqenet_remove(struct pynqenet_device *pdev)
{
    struct net_device *ndev = pdev->ndev;
    struct pynqenet_adapter *adapter = netdev_priv(ndev);

    unregister_netdev(ndev);
    netif_napi_del(&adapter->napi);

    xlnx_dma_device_cleanup(adapter->dma_dev);
    kfree(adapter->tx_chan);
    kfree(adapter->rx_chan);
    kfree(adapter->dma_dev);

    free_netdev(ndev);
}

/**
 * ideally this module would be registered with the device tree, but that is
 * not currently the case. so we use module parameters for portability.
 **/
static unsigned pynq_dma_base = PYNQ_SG_DMA_BASE;
module_param(pynq_dma_base, hex32, S_IRUGO);
// MODULE_PARAM_DESC(pynq_dma_base, "base AXI address for the SG DMA Controller");

static unsigned pynq_dma_len = PYNQ_SG_DMA_LEN;
module_param(pynq_dma_len, hex32, S_IRUGO);
// MODULE_PARAM_DESC(pynq_dma_len, "AXI region size for the SG DMA Controller");

static struct pynqenet_device pynq_dev;
static int __exit pynqenet_init(void)
{
    pynq_dev.dma_base = pynq_dma_base;
    pynq_dev.dma_len = pynq_dma_len;
    pynq_dev.dma_mm2s_irq = PYNQ_SG_MM2S_IRQ;
    pynq_dev.dma_s2mm_irq = PYNQ_SG_MM2S_IRQ;
    return pynqenet_probe(&pynq_dev);
}

static void __exit pynqenet_exit(void)
{
    printk(KERN_DEBUG "pynqenet exit\n");
    pynqenet_remove(&pynq_dev);
}

module_init(pynqenet_init);
module_exit(pynqenet_exit);
