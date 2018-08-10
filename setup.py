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
from distutils.dir_util import copy_tree, remove_tree
from distutils.file_util import copy_file
import subprocess
import sys
import os
import glob
from datetime import datetime


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "yunq@xilinx.com"


GIT_DIR = os.path.dirname(os.path.realpath(__file__))


# Board specific package delivery setup
def exclude_from_files(exclude, path):
    return [file for file in os.listdir(path)
            if os.path.isfile(os.path.join(path, file))
            and file != exclude]


def find_overlays(path):
    return [f for f in os.listdir(path)
            if os.path.isdir(os.path.join(path, f))
            and len(glob.glob(os.path.join(path, f, "*.bit"))) > 0]


def collect_pynq_overlays():
    overlay_files = []
    overlay_dirs = find_overlays(board_folder)
    for ol in overlay_dirs:
        copy_tree(os.path.join(board_folder, ol),
                  os.path.join("pynq_networking/overlays", ol))
        newdir = os.path.join("pynq_networking/overlays", ol)
        files = exclude_from_files('makefile', newdir)
        overlay_files.extend(
                [os.path.join("..", newdir, f) for f in files])
    return overlay_files


pynq_package_files = []
if 'BOARD' not in os.environ:
    print("Please set the BOARD environment variable "
          "to get any BOARD specific overlays (e.g. Pynq-Z1).")
    board = None
    board_folder = None
else:
    board = os.environ['BOARD']
    board_folder = 'boards/{}'.format(board)
    pynq_package_files.extend(collect_pynq_overlays())


# Update interfaces
def update_interfaces():
    eth0_file = '/etc/network/interfaces.d/eth0'
    backup_file = '/etc/network/interfaces.d/.{}'.format(
        datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
    copy_file(eth0_file, backup_file)
    copy_file(GIT_DIR + '/interfaces.d/eth0', eth0_file)
    print("Update interface files done ...")


# Build submodules
def build_submodules():
    subprocess.check_call(['git', 'submodule', 'init'])
    subprocess.check_call(['git', 'submodule', 'update'])
    copy_tree(GIT_DIR + '/mqtt-sn-tools',
              GIT_DIR + '/pynq_networking/mqtt-sn-tools')
    copy_tree(GIT_DIR + '/rsmb',
              GIT_DIR + '/pynq_networking/rsmb')
    print("Update submodules done ...")


# Notebook delivery
def fill_notebooks():
    src_nb = os.path.join(GIT_DIR, '/notebooks')
    dst_nb_dir = '/home/xilinx/jupyter_notebooks/networking'
    if os.path.exists(dst_nb_dir):
        remove_tree(dst_nb_dir)
    copy_tree(src_nb, dst_nb_dir)

    print("Filling notebooks done ...")


# Run makefiles
def run_make(src_path, output_lib):
    status = subprocess.check_call(["make", "-C", GIT_DIR + '/' + src_path])
    if status is not 0:
        print("Error while running make for", output_lib, "Exiting..")
        sys.exit(1)

    print("Running make for " + output_lib + " done ...")


# Bring br0 up online
def if_up_br0():
    subprocess.check_call(['ifup', 'br0'])
    subprocess.check_call(['service', 'networking', 'restart'])

    print("Bringing up br0 done ...")


if len(sys.argv) > 1 and sys.argv[1] == 'install':
    update_interfaces()
    build_submodules()
    fill_notebooks()
    run_make("pynq_networking/rsmb/rsmb/src/", "broker_mqtts")
    if_up_br0()


def package_files(directory):
    paths = []
    for (path, directories, file_names) in os.walk(directory):
        for file_name in file_names:
            paths.append(os.path.join('..', path, file_name))
    return paths


pynq_package_files.extend(package_files('pynq_networking'))
setup(name='pynq_networking',
      version='2.3',
      description='PYNQ networking package',
      author='Xilinx networking group',
      author_email='stephenn@xilinx.com',
      url='https://github.com/Xilinx/PYNQ-Networking',
      packages=find_packages(),
      download_url='https://github.com/Xilinx/PYNQ-Networking',
      package_data={
          '': pynq_package_files,
      },
      install_requires=[
          'scapy-python3',
          'wurlitzer',
          'pytest-runner',
          'paho-mqtt',
          'netifaces',
          'pynq>=2.3'
      ]
      )
