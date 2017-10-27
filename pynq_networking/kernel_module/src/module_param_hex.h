#ifndef _MODULE_PARAM_HEX_H_
#define _MODULE_PARAM_HEX_H_

#include <linux/moduleparam.h>

int param_set_hex32(const char *val, const struct kernel_param *kp)
{
    return kstrtoul(val, 16, (unsigned long *)kp->arg);
}

int param_get_hex32(char *buf, const struct kernel_param *kp)
{
    return scnprintf(buf, PAGE_SIZE, "%x", *((unsigned *)kp->arg));
}

const struct kernel_param_ops param_ops_hex32 = {
    .set = param_set_hex32,
    .get = param_get_hex32
};
#define param_check_hex32(name, p) param_check_uint(name, p)
 
#endif /* _MODULE_PARAM_HEX_H_ */
