# Boot Configurations

The folder updates [the corresponding configuration folder on mainline 
PYNQ repository](https://github.com/Xilinx/PYNQ/tree/master/sdbuild/boot_configs/Pynq-Z1-defconfig).

In the `/sdbuild` folder of a PYNQ repository, use the following command to 
build the boot files in Ubuntu:

```shell
make boot_files
```

More information on the building process can be found on 
[the PYNQ repository](https://github.com/Xilinx/PYNQ/tree/master/sdbuild).
