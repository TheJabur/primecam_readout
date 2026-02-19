# ============================================================================ #
# init_14.py
# Board side initialization script to be called after boot-up.
# Gateware versions 14 and below.
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

print(f"Running init_15.py...")

# Determine the directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))
print(f"Script directory: {script_dir}")

# add src/ to path (where most of the other scripts live)
sys.path.insert(1, os.path.join(os.path.dirname(script_dir), 'src'))

import ip_addr
from config import board as cfg_b


# =========================================================================== #
# gatewareInfoFromBoardCfg
def gatewareInfoFromBoardCfg(cfg_b):
    # MUST use *_v[version]p* as gateware filename
    gateware_file = os.path.join(cfg_b.dir_root, cfg_b.gateware_file)
    gateware_fname = os.path.splitext(os.path.basename(gateware_file))[0]
    gateware_fname_parts = re.search(r'_v(\d+)p(\d+)', gateware_fname)
    gateware_version = int(gateware_fname_parts.group(1)) 
    gateware_version_minor = int(gateware_fname_parts.group(2))
    return gateware_file, gateware_version, gateware_version_minor


try:

    # ======================================================================== #
    # Gateware
    # ======================================================================== #

    gateware_file, gateware_version, gateware_version_minor = \
        gatewareInfoFromBoardCfg(cfg_b)
    print(f"Loading gateware: {gateware_file}")
    gateware = Overlay(gateware_file, ignore_version=True)




    # ======================================================================== #
    # Clocks
    # ======================================================================== #

    clksrc = 409.6 # MHz
    print(f"Setting clocks: {clksrc}")
    xrfclk.set_all_ref_clks(clksrc)



    # ======================================================================== #
    # PTP
    # ======================================================================== #
    # This can also be moved into system services instead. See relevant scripts.

    print(f"PTP enabled: {cfg_b.ptp_enable}")
    if cfg_b.ptp_enable:

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
    # Digital Mixers
    # ======================================================================== #

    print(f"Setting up digital mixers.")

    lofreq = 1000.000 # [MHz]
    print(f"NCLO = {lofreq} MHz.")
    rf_data_conv = gateware.usp_rf_data_converter_0

    # chan: [adc tiles, adc blocks, dac tiles, dac blocks]
    print(f"ASU port mapping: {cfg_b.asu_board}")
    tb_indices = {1: [0,0,1,3], 2: [0,1,1,2], 3: [1,0,1,1], 4: [1,1,1,0]}
    if gateware_version==14 and gateware_version_minor>=2:
        if cfg_b.asu_board:
            tb_indices = {1: [1,0,1,3], 2: [1,1,1,2], 3: [0,1,1,0], 4: [0,0,1,1]}
            port_mapping = 0b_00_01_11_10_10_11_01_00 # 01322310
        else:
            port_mapping = 0b_11_10_01_00_00_01_10_11 # 32100123
        gateware.gpio_chan2DC_mapping.write(0x00, port_mapping)

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

    print("Setting up chains.")
    
    # set the ADC accumulation length
    gateware.chan1.dsp_regs_0.write(0x08, cfg_b.accum_len)
    gateware.chan2.dsp_regs_0.write(0x08, cfg_b.accum_len)
    gateware.chan3.dsp_regs_0.write(0x08, cfg_b.accum_len)
    gateware.chan4.dsp_regs_0.write(0x08, cfg_b.accum_len)

    if gateware_version >= 14:
        # set chain timing gaps
        accum_start_gap = cfg_b.accum_len//4
        gateware.receive_timing_gpio1.write(0x00, accum_start_gap - 4)
        gateware.receive_timing_gpio1.write(0x08, accum_start_gap - 4)
        gateware.receive_timing_gpio2.write(0x00, accum_start_gap - 4)

        # start chains
        gateware.receive_timing_gpio2.write(0x08, 1)




    # ======================================================================== #
    # Ethernet
    # ======================================================================== #

    print(f"Setting up TOD streaming system.")

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




except Exception as e:
    print(e)