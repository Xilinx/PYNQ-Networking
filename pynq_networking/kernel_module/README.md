# Kernel Modules

The kernel driver will be inserted during run-time. This folder contains
the pre-compiled object file along with its source codes.

The `pynqenet.ko` file must be compiled with the Petalinux source codes; this
requires the users to have the Petalinux project for the PYNQ image. To
get the Petalinux project, users have to follow the SD build flow in the 
original PYNQ repository.

## Rebuilding the Kernel Module
We provide a makefile to build the `pynqenet.ko` file. For example,

```shell
make PROJECT=<pynq_repo>/sdbuild/build/Pynq-Z1/petalinux_project
```

Notice that the above path will usually be available after you have at least
built the boot files for the corresponding board once.

## Compatibility

Currently only zynq-7000 devices are supported.
