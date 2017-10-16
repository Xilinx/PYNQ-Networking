#ifndef _XLNX_IRQ_H_
#define _XLNX_IRQ_H_

#include <linux/platform_device.h>
#include <linux/irq.h>
#include <linux/of.h>
#include <linux/of_irq.h>

static const struct of_device_id gic_match[] = {
        { .compatible = "arm,cortex-a9-gic", },
        { .compatible = "arm,cortex-a15-gic", },
        { },
};
static struct device_node *gic_node = NULL;

static unsigned xlate_irq(unsigned int hwirq)
{
    struct of_phandle_args irq_data;
    unsigned int irq;

    if (!gic_node)
        gic_node = of_find_matching_node(NULL, gic_match);

    if (WARN_ON(!gic_node))
        return hwirq;

    irq_data.np = gic_node;
    irq_data.args_count = 3;
    irq_data.args[0] = 0;
    irq_data.args[1] = hwirq - 32; /* GIC SPI offset */
    irq_data.args[2] = IRQ_TYPE_LEVEL_HIGH;

    irq = irq_create_of_mapping(&irq_data);
    if (WARN_ON(!irq))
        irq = hwirq;

    pr_info("%s: hwirq %d, irq %d\n", __func__, hwirq, irq);
    return irq;
}


#endif  /* _XLNX_IRQ_H_ */
