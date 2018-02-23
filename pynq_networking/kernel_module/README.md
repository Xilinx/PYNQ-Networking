# Kernel Modules

The kernel driver will be inserted during run-time. This folder contains
the pre-compiled object file along with its source codes.

The `pynqenet.ko` file must be compiled with the Linux source codes; this 
is not recommended for the users. However, users can directly use the 
pre-compiled object file.

In any case the kernel object file has to be compiled, users can run `make` 
inside `/src` folder. This will pull in the PYNQ repository and rebuilt the 
boot files. The kernel module will be rebuilt after that.
