from pynq import Overlay
import xrfclk
import xrfdc

import sys
import os
sys.path.insert(1, os.path.realpath(os.path.pardir) + '/src')

import ip_addr
from config import board as cfg

import subprocess

try:


# ============================================================================ #
# Firmware, PTP, clocks

    firmware = Overlay(cfg.firmware_file, ignore_version=True)

    clksrc = 409.6 # MHz
    xrfclk.set_all_ref_clks(clksrc)

    # Bring up the PTP interface
    subprocess.run(["ifconfig", cfg.ptp_interface, cfg.ptp_ip_address, "up"])

    # Pass the MAC address and interface to the PTP and PHC scripts
    subprocess.run(["./run_ptp4l.sh", cfg.ptp_interface, cfg.ptp_mac_address])
    subprocess.run(["./run_phc2sys.sh", cfg.ptp_interface])

    print("PTP configured")


# ============================================================================ #
# Digital Mixers

    lofreq = 1000.000 # [MHz]
    rf_data_conv = firmware.usp_rf_data_converter_0

    # chan: [adc tiles, adc blocks, dac tiles, dac blocks]
    tb_indices = {
        1: [1,1,1,3], 2: [1,0,1,2], 3: [0,1,1,1], 4: [0,0,1,0]}
    
    for chan, ii in tb_indices.items():
        adc = rf_data_conv.adc_tiles[ii[0]].blocks[ii[1]]
        dac = rf_data_conv.dac_tiles[ii[2]].blocks[ii[3]]

        adc.MixerSettings['Freq'] = lofreq
        dac.MixerSettings['Freq'] = lofreq
        adc.UpdateEvent(xrfdc.EVENT_MIXER)
        dac.UpdateEvent(xrfdc.EVENT_MIXER)



# ============================================================================ #
# Ethernet

    dest_ip = ip_addr.tIP_destination(sep='', asHex=True)
    dest_mac = ip_addr.mac_destination(sep='')
    src_ip_1 = ip_addr.tIP_origin(1, sep='', asHex=True)
    src_ip_2 = ip_addr.tIP_origin(2, sep='', asHex=True)
    src_ip_3 = ip_addr.tIP_origin(3, sep='', asHex=True)
    src_ip_4 = ip_addr.tIP_origin(4, sep='', asHex=True)
    src_mac = ip_addr.mac_origin(sep='')

    def ethRegsPortWrite(eth_regs, src_ip_int32): 
        eth_regs.write( 0x00, int(src_mac[4:], 16))
        eth_regs.write( 0x04, (int(dest_mac[-4:], 16)<<16) + int(src_mac[:4], 16))
        eth_regs.write( 0x08, int(dest_mac[:-4], 16))
        eth_regs.write( 0x0c, src_ip_int32)
        eth_regs.write( 0x10, int(dest_ip, 16))
    ethRegsPortWrite(firmware.ethWrapPort0.eth_regs_0, src_ip_int32=int(src_ip_1, 16))
    ethRegsPortWrite(firmware.ethWrapPort1.eth_regs_0, src_ip_int32=int(src_ip_2, 16))
    ethRegsPortWrite(firmware.ethWrapPort2.eth_regs_0, src_ip_int32=int(src_ip_3, 16))
    ethRegsPortWrite(firmware.ethWrapPort3.eth_regs_0, src_ip_int32=int(src_ip_4, 16))



except Exception as e:
    print(e)
