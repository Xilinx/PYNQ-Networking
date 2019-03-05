PROJECT :=
DIR := ${CURDIR}
RECIPE := ${DIR}/petalinux_project/project-spec/meta-user/recipes-modules/pynqenet

all: check module

check:
	@if [ -z "${PROJECT}" ]; then \
		echo "Please specify a valid petalinux project path."; \
		echo "    e.g. make PROJECT=<petalinux_project_path>"; \
		exit 1; \
	fi

module:
	cd ${PROJECT} &&\
	petalinux-create --force -t modules -n pynqenet --enable &&\
	cp -rf ${RECIPE} project-spec/meta-user/recipes-modules/pynqenet &&\
	petalinux-build -c kernel &&\
	petalinux-build -c pynqenet -x do_install &&\
	cp -f build/tmp/work/plnx_zynq7-xilinx-linux-gnueabi/pynqenet/1.0-r0/pynqenet.ko ${DIR}

