#   Copyright (c) 2017, Xilinx, Inc.
#   All rights reserved.
# 
#   Redistribution and use in source and binary forms, with or without 
#   modification, are permitted provided that the following conditions are met:
#
#   1.  Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#
#   2.  Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the 
#       documentation and/or other materials provided with the distribution.
#
#   3.  Neither the name of the copyright holder nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#   OR BUSINESS INTERRUPTION). HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
#   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
#   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from setuptools import setup, find_packages
import shutil
import subprocess
import sys
import os
from datetime import datetime

__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "yunq@xilinx.com"


GIT_DIR = os.path.dirname(os.path.realpath(__file__))

# Update boot partition
def update_boot():
    boot_mount = '/mnt/boot'
    if not os.path.exists('/mnt/boot'):
        subprocess.check_call(['mkdir', boot_mount])
        try:
            subprocess.check_call(['mount', '/dev/mmcblk0p1', boot_mount])
        finally:
            subprocess.check_call(['umount', '/dev/mmcblk0p1'])

    backup_folder = boot_mount + '/BOOT_PARTITION_{}'.format(
        datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
    subprocess.check_call(['mkdir', backup_folder])
    boot_file = ['BOOT.bin', 'devicetree.dtb', 'uEnv.txt', 'uImage']
    for file in boot_file:
        if os.path.isfile(boot_mount + '/' + file):
            shutil.copy2(boot_mount + '/' + file,
                         backup_folder + '/')
    for file in boot_file:
        shutil.copy2(GIT_DIR + '/boot_files/' + file,
                     boot_mount + '/')
    print("Update boot files done ...")


# Install packages
def install_packages():
    subprocess.check_call(['apt-get', '--yes', '--force-yes', 'install',
                           'tcpdump', 'iptables', 'ebtables', 'bridge-utils'])
    subprocess.check_call(['pip3.6', 'install',
                           'scapy-python3', 'wurlitzer',
                           'pytest-runner', 'paho-mqtt'])
    print("Installing packages done ...")


# Update interfaces
def update_interfaces():
    eth0_file = '/etc/network/interfaces.d/eth0'
    backup_file = eth0_file + '_{}'.format(
        datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
    shutil.copy2(eth0_file, backup_file)
    shutil.copy2(GIT_DIR + '/interfaces.d/eth0', eth0_file)
    print("Update interface files done ...")


# Build submodules
def build_submodules():
    subprocess.check_call(['git', 'submodule', 'init'])
    subprocess.check_call(['git', 'submodule', 'update'])
    print("Update submodules done ...")


# Run makefiles
def run_make(src_path, output_lib):
    status = subprocess.check_call(["make", "-C", GIT_DIR + '/' + src_path])
    if status is not 0:
        print("Error while running make for", output_lib, "Exiting..")
        sys.exit(1)
    print("Running make for " + output_lib + " done ...")


# Notebook delivery
def fill_notebooks():
    src_nb = GIT_DIR + '/notebooks'
    dst_nb_dir = '/home/xilinx/jupyter_notebooks/networking'
    shutil.copytree(src_nb, dst_nb_dir)

    for folder in ['/kernel_module', '/broker_client']:
        shutil.copytree(GIT_DIR + folder, dst_nb_dir + folder)
    print("Filling notebooks done ...")


# Move overlay
def fill_overlay():
    src_overlay = GIT_DIR + '/overlays/mqttsn'
    dst_overlay_dir = '/home/xilinx/pynq/overlays/'
    subprocess.check_call(['cp', '-rf', src_overlay, dst_overlay_dir])
    print("Filling overlays done ...")


if len(sys.argv) > 1 and sys.argv[1] == 'install':
    update_boot()
    install_packages()
    update_interfaces()
    build_submodules()
    run_make("rsmb/rsmb/src/", "broker_mqtts")
    fill_notebooks()
    fill_overlay()


setup(name='pynq_networking',
      version='2.0',
      description='PYNQ networking package',
      author='Xilinx networking group',
      author_email='stephenn@xilinx.com',
      url='https://github.com/Xilinx/PYNQ-Networking',
      packages=find_packages(),
      download_url='https://github.com/Xilinx/PYNQ-Networking',
      package_data={
          '': ['tests/*', '*.ipynb', '*.bin', 
               '*.ko', '*.so', '*.bit', '*.tcl'],
      }
      )
