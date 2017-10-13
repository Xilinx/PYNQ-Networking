# PYNQ-Networking
PYNQ networking overlay enables networking capabilities from PL on the board.
Traditionally, the PS on ZYNQ board connects to the Ethernet port, while this 
overlay also bridges the PL on ZYNQ to the Ethernet port. MQTT-SN is 
implemented on this overlay, leveraging the `scapy` python library.

![](./block_diagram.jpg)

## Boot Files
This overlay requires the boot files to be upgraded to Xilinx 2017.2 tool 
suite. For example, the device tree must have the following patch:

```
/ {
	chosen {
		bootargs = "console=ttyPS0,115200 root=/dev/mmcblk0p2 rw earlyprintk rootfstype=ext4 rootwait devtmpfs.mount=1 uio_pdrv_genirq.of_id=\"generic-uio\"";
		linux,stdout-path = "/amba@0/serial@E0001000";
	};

	amba {

		fabric@40000000 {
			compatible = "generic-uio";
			reg = <0x40000000 0x10000>;
			interrupt-parent = <&intc>;
			interrupts = <0x0 0x1d 0x4>;
		};

		ethernet@e000b000 {
			phy-handle = <&ethernet_phy>;
                        ethernet_phy: ethernet-phy@1{
				reg = <1>;
			};
		};

		slcr@f8000000 {
			clkc@100 {
				fclk-enable = <0xf>;
			};
		};
	};


	xlnk {
		compatible = "xlnx,xlnk-1.0";
		clock-names = "xclk0", "xclk1", "xclk2", "xclk3";
		clocks = <&clkc 0xf &clkc 0x10 &clkc 0x11 &clkc 0x12>;
	};
	usb_phy0: phy0 {
		compatible = "ulpi-phy";
		#phy-cells = <0>;
		reg = <0xe0002000 0x1000>;
		view-port = <0x170>;
		drv-vbus;
	};
   
};

&usb0 {
	usb-phy = <&usb_phy0>;
};
```
The ethernet entry must have bridging enabled as above.

Files in the boot partition compatible to 2017.2 tool suite are in 
`/boot_files`. Users can replace the files in the boot partition of a PYNQ
image.

*Note: make a backup of the old files if necessary before replacing files!*

The source files to generate those boot files, are in 
`/Pynq-Z1-defconfig`; 
this folder has several patches for the folder of the same name in `/sdbuild`
of the mainline PYNQ repository. For example, `kernel.config` file enables the 
IP bridging functionality.

## Installing Packages
There are several packages to be installed:

```shell
apt-get install tcpdump iptables ebtables bridge-utils
pip3.6 install scapy-python3 wurlitzer pytest-runner paho-mqtt
```

## Modifying `eth0` Port
Users have to modify the `eth0` port on Linux (`/etc/network/interfaces.d/eth0`).

*Note: again, make a backup of the old files if necessary.*

The modified file looks like this:
```shell
auto eth0
auto br0
iface br0 inet dhcp
bridge_ports eth0
```

## Others
To be added.
