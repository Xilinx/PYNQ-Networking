## Make sure to source the correct settings file before running this
## e.g. source /proj/gsd/vivado/Vivado/2017.2/settings64.csh
## kernel configuration file can be found as kernel.config in boot_config folder

PYNQ_TAG := image_v2.1
RELEASE := Pynq-Z1-Xenial
ARCH := arm
CROSS_COMPILE := arm-linux-gnueabihf-

obj-m += pynqenet.o

all: git_clone kernel_module

git_clone:
	/usr/bin/git clone https://github.com/Xilinx/PYNQ.git .pynq_git
	cd .pynq_git/sdbuild && \
	/usr/bin/git checkout -b $(PYNQ_TAG) origin/$(PYNQ_TAG) && \
	make boot_files RELEASE=$(RELEASE) && \
	cd ../..

kernel_module:
	ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) \
	make -C $(PWD)/.pynq_git/sdbuild/.build/linux/ M=$(PWD) modules
	cp -rf $(PWD)/pynqenet.ko $(PWD)/../

clean:
	make -C $(PWD)/.pynq_git/sdbuild/.build/linux/ M=$(PWD) clean
