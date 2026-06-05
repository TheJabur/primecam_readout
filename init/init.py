# ============================================================================ #
# init.py
# Board side initialization script to be called after boot-up.
# James Burgoyne jburgoyne@phas.ubc.ca
# Adrian Sinclair aksincla@asu.edu
# CCAT/FYST 2025
# ============================================================================ #

from pynq import Overlay
import xrfclk
import xrfdc

import os
import re
import sys
import subprocess

# Determine the directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))

# add src/ to path (where most of the other scripts live)
sys.path.insert(1, os.path.join(os.path.dirname(script_dir), 'src'))

import ip_addr
from config import board as cfg_b




try:

    # ======================================================================== #
    # Firmware, PTP, clocks
    # ======================================================================== #

    # assuming cfg.firmware_file is a local filename
    firmware_file = os.path.join(cfg_b.dir_root, cfg_b.firmware_file)
    firmware_fname = os.path.splitext(os.path.basename(firmware_file))[0]

    # firmware_V = int(firmware_fname[7:9]) # fragile!
    firmware_fname_parts = re.search(r'_v(\d+)p(\d+)', firmware_fname)
    firmware_V = int(firmware_fname_parts.group(1)) 
    firmware_M = int(firmware_fname_parts.group(2))

    firmware = Overlay(firmware_file, ignore_version=True)

    clksrc = 409.6 # MHz
    xrfclk.set_all_ref_clks(clksrc)

    # Bring up the PTP interface
    subprocess.run(["ifconfig", cfg_b.ptp_interface, cfg_b.ptp_ip_address, "up"])

    # Pass the MAC address and interface to the PTP and PHC scripts
    run_ptp4l_path = os.path.join(script_dir, 'run_ptp4l.sh')
    subprocess.run([run_ptp4l_path, cfg_b.ptp_interface, cfg_b.ptp_mac_address, "gPTP_board.cfg"])
    run_phc2sys_path = os.path.join(script_dir, 'run_phc2sys.sh')
    subprocess.run([run_phc2sys_path, cfg_b.ptp_interface])

    print("PTP configured")




    # ======================================================================== #
    # Digital Mixers
    # ======================================================================== #

    lofreq = 1000.000 # [MHz]
    rf_data_conv = firmware.usp_rf_data_converter_0

    # chan: [adc tiles, adc blocks, dac tiles, dac blocks]
        
    # chan: [adc tiles, adc blocks, dac tiles, dac blocks]
    print(f"ASU port mapping: {cfg_b.asu_board}")
    tb_indices = {1: [0,0,1,3], 2: [0,1,1,2], 3: [1,0,1,1], 4: [1,1,1,0]}
    if firmware_V==14 and firmware_M>=2:
        if cfg_b.asu_board:
            tb_indices = {1: [1,0,1,3], 2: [1,1,1,2], 3: [0,1,1,0], 4: [0,0,1,1]}
            port_mapping = 0b_11_10_00_01_10_11_01_00 # 32012310
        else:
            port_mapping = 0b_11_10_01_00_00_01_10_11 # 32100123
        firmware.gpio_chan2DC_mapping.write(0x00, port_mapping)
    
    for chan, ii in tb_indices.items():
        adc = rf_data_conv.adc_tiles[ii[0]].blocks[ii[1]]
        dac = rf_data_conv.dac_tiles[ii[2]].blocks[ii[3]]

        adc.MixerSettings['Freq'] = lofreq
        dac.MixerSettings['Freq'] = lofreq
        adc.UpdateEvent(xrfdc.EVENT_MIXER)
        dac.UpdateEvent(xrfdc.EVENT_MIXER)




    # ======================================================================== #
    # Chains
    # ======================================================================== #

    # set the ADC accumulation length
    firmware.chan1.dsp_regs_0.write(0x08, cfg_b.accum_len)
    firmware.chan2.dsp_regs_0.write(0x08, cfg_b.accum_len)
    firmware.chan3.dsp_regs_0.write(0x08, cfg_b.accum_len)
    firmware.chan4.dsp_regs_0.write(0x08, cfg_b.accum_len)

    if firmware_V >= 14:
        # set chain timing gaps
        accum_start_gap = cfg_b.accum_len//4
        firmware.receive_timing_gpio1.write(0x00, accum_start_gap - 4)
        firmware.receive_timing_gpio1.write(0x08, accum_start_gap - 4)
        firmware.receive_timing_gpio2.write(0x00, accum_start_gap - 4)

        # start chains
        firmware.receive_timing_gpio2.write(0x08, 1)




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
    ethRegsPortWrite(firmware.ethWrapPort0, src_ip_1)
    ethRegsPortWrite(firmware.ethWrapPort1, src_ip_2)
    ethRegsPortWrite(firmware.ethWrapPort2, src_ip_3)
    ethRegsPortWrite(firmware.ethWrapPort3, src_ip_4)




except Exception as e:
    print(e)