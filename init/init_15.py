# ============================================================================ #
# init_15.py
# Board side initialization script to be called after boot-up.
# Gateware versions 15+.
# James Burgoyne jburgoyne@phas.ubc.ca
# Ruixuan (Matt) Xie  mattxie956@gmail.com
# Adrian Sinclair aksincla@asu.edu
# CCAT/FYST 2025
# ============================================================================ #

from pynq import Overlay
import xrfclk
import xrfdc

import os
import re
import sys
import numpy as np
import subprocess

# Determine the directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))

# add src/ to path (where most of the other scripts live)
sys.path.insert(1, os.path.join(os.path.dirname(script_dir), 'src'))

import ip_addr
from config import board as cfg_b




try:

    # ======================================================================== #
    # Gateware
    # ======================================================================== #

    # assuming cfg.gateware_file is a local filename
    # MUST use *_v[version]p* as gateware filename
    gateware_file = os.path.join(cfg_b.dir_root, cfg_b.gateware_file)
    gateware_fname = os.path.splitext(os.path.basename(gateware_file))[0]
    gateware_version = int(re.search(r'_v(\d+)p', gateware_fname).group(1)) 
    gateware = Overlay(gateware_file, ignore_version=True)
    os.environ['PRIMECAM_READOUT_GATEWARE_VERSION'] = gateware_version # OS level flag



    # ======================================================================== #
    # Clocks
    # ======================================================================== #

    clksrc = 409.6 # MHz
    xrfclk.set_all_ref_clks(clksrc)



    # ======================================================================== #
    # PTP
    # ======================================================================== #

    # Bring up the PTP interface
    subprocess.run(["ifconfig", 
                    cfg_b.ptp_interface, 
                    cfg_b.ptp_ip_address, 
                    "up"])

    # Pass the MAC address and interface to the PTP and PHC scripts
    run_ptp4l_path = os.path.join(script_dir, 'run_ptp4l.sh')
    subprocess.run([run_ptp4l_path, 
                    cfg_b.ptp_interface, 
                    cfg_b.ptp_mac_address, 
                    "gPTP_board.cfg"])
    run_phc2sys_path = os.path.join(script_dir, 'run_phc2sys.sh')
    subprocess.run([run_phc2sys_path, 
                    cfg_b.ptp_interface])

    print("PTP configured")



    # ======================================================================== #
    # Ethernet
    # ======================================================================== #

    dest_ip = ip_addr.tIP_destination(sep='', asHex=True)
    dest_mac = ip_addr.mac_destination(sep='')
    src_ip_1 = ip_addr.tIP_origin(1, sep='', asHex=True)
    src_ip_2 = ip_addr.tIP_origin(2, sep='', asHex=True)
    src_ip_3 = ip_addr.tIP_origin(3, sep='', asHex=True)
    src_ip_4 = ip_addr.tIP_origin(4, sep='', asHex=True)
    src_mac = ip_addr.mac_origin(sep='')

    def ethRegsPortWrite(ethWrapPort, src_ip): 
        reg = ethWrapPort.eth_regs_0
        reg.write(0x00, int(src_mac[4:], 16))
        reg.write(0x04, (int(dest_mac[-4:], 16)<<16) + int(src_mac[:4], 16))
        reg.write(0x08, int(dest_mac[:-4], 16))
        reg.write(0x0c, int(src_ip, 16))
        reg.write(0x10, int(dest_ip, 16))
    ethRegsPortWrite(gateware.ethWrapPort0, src_ip_1)
    ethRegsPortWrite(gateware.ethWrapPort1, src_ip_2)
    ethRegsPortWrite(gateware.ethWrapPort2, src_ip_3)
    ethRegsPortWrite(gateware.ethWrapPort3, src_ip_4)

    accum_len = 2048/4*1024 # accum_len = cfg_b.accum_len + 1
    accum_start_gap = accum_len//4
    gateware.eth_timing_ctrl.write(0x00, int(accum_start_gap - 4))  # the gap in clk cycles in between chan start signal




    # ======================================================================== #
    # Digital Mixers
    # ======================================================================== #

    lofreq = 1000.000 # [MHz]
    rf_data_conv = gateware.usp_rf_data_converter_0

    # chan: [adc tiles, adc blocks, dac tiles, dac blocks]        
    tb_indices = {1: [0,0,1,3], 2: [0,1,1,2], 3: [1,0,1,1], 4: [1,1,1,0]}
    
    for chan, ii in tb_indices.items():
        adc = rf_data_conv.adc_tiles[ii[0]].blocks[ii[1]]
        dac = rf_data_conv.dac_tiles[ii[2]].blocks[ii[3]]

        adc.MixerSettings['Freq'] = -lofreq
        dac.MixerSettings['Freq'] = lofreq
        adc.UpdateEvent(xrfdc.EVENT_MIXER)
        dac.UpdateEvent(xrfdc.EVENT_MIXER)




    # ======================================================================== #
    # Chains
    # ======================================================================== #

    for gwc in [gateware.chan1, gateware.chan2, gateware.chan3, gateware.chan4]:

        # FFT scale
        gwc.GPIO.axi_gpio_4.write(0x08, 2016) 

        # accum and snap bin len
        acc_length = int(2048/4 * cfg_b.acc_factor - 4)
        gwc.GPIO.axi_gpio_3.write(0x00, 253*2**23 + acc_length)

        # PSB scale
        gateware.chan1.GPIO.axi_gpio_5.write(0x00, 37170)

        # clear all tones
        gwc.GPIO.axi_gpio_2.write(0x00, 0)
        gwc.GPIO.axi_gpio_2.write(0x08, 0)
        for addr in range(256):
            gwc.GPIO.axi_gpio_1.write(0x08, int(addr << 16))
            for bit in range(8):
                gwc.GPIO.axi_gpio_1.write(0x00, 1 << bit)
                gwc.GPIO.axi_gpio_1.write(0x00, 0)

    # start chan 1 readout
    gateware.chan1.GPIO.axi_gpio_0.write(0x0, 0)
    gateware.chan1.GPIO.axi_gpio_0.write(0x0, 1)




except Exception as e:
    print(e)