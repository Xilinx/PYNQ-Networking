############################################################
## This file is generated automatically by Vivado HLS.
## Please DO NOT edit it.
## Copyright (C) 1986-2016 Xilinx, Inc. All Rights Reserved.
############################################################
open_project packetSlurper
set_top packetSlurper
add_files packetSlurper.cpp
add_files -tb test_packetSlurper.cpp
open_solution "solution1"
set_part {xc7z045ffg900-2} -tool vivado
create_clock -period 10 -name default
#source "./packetSlurper/solution1/directives.tcl"
csim_design
config_rtl -prefix packetSlurper_
csynth_design
#cosim_design -trace_level all
#export_design -sim all -rtl verilog -format ip_catalog -evaluate verilog
export_design -rtl verilog -format ip_catalog
