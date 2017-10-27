## Make sure to source the correct settings file before running this
## e.g. source /proj/gsd/vivado/Vivado/2017.2/settings64.csh
## kernel configuration file can be found as kernel.config in boot_config folder

obj-m += pynqenet.o

all: git_clone kernel_module

git_clone:
	git clone https://github.com/Xilinx/linux-xlnx.git linux-xlnx
	cd linux-xlnx && git reset --hard 5d029fdc257cf88e65500db348eda23040af332b && cd ..

kernel_module:
	make -C $(PWD)/linux-xlnx/ M=$(PWD) modules
	cp -rf $(PWD)/pynqenet.ko $(PWD)/../

clean:
	make -C linux-xlnx/ M=$(PWD) clean
