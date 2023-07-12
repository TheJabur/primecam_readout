from pynq import Overlay
import xrfclk
import xrfdc
import ip_addr

try:
    # FIRMWARE UPLOAD
    firmware = Overlay("tetra_v7p1_impl_5.bit",ignore_version=True)

    # PLLs

    clksrc = 409.6 # MHz
    xrfclk.set_all_ref_clks(clksrc)

    # DIGITAL MIXERS
    lofreq = 1000.000 # [MHz]
    rf_data_conv = firmware.usp_rf_data_converter_0
    
    rf_data_conv.adc_tiles[0].blocks[0].MixerSettings['Freq']=lofreq
    rf_data_conv.dac_tiles[1].blocks[3].MixerSettings['Freq']=lofreq
    rf_data_conv.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
    rf_data_conv.dac_tiles[1].blocks[3].UpdateEvent(xrfdc.EVENT_MIXER)

    rf_data_conv.adc_tiles[0].blocks[1].MixerSettings['Freq']=lofreq
    rf_data_conv.dac_tiles[1].blocks[2].MixerSettings['Freq']=lofreq
    rf_data_conv.adc_tiles[0].blocks[1].UpdateEvent(xrfdc.EVENT_MIXER)
    rf_data_conv.dac_tiles[1].blocks[2].UpdateEvent(xrfdc.EVENT_MIXER)
    
    rf_data_conv.adc_tiles[1].blocks[0].MixerSettings['Freq']=lofreq
    rf_data_conv.dac_tiles[1].blocks[1].MixerSettings['Freq']=lofreq
    rf_data_conv.adc_tiles[1].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
    rf_data_conv.dac_tiles[1].blocks[1].UpdateEvent(xrfdc.EVENT_MIXER)
    
    rf_data_conv.adc_tiles[1].blocks[1].MixerSettings['Freq']=lofreq
    rf_data_conv.dac_tiles[1].blocks[0].MixerSettings['Freq']=lofreq
    rf_data_conv.adc_tiles[1].blocks[1].UpdateEvent(xrfdc.EVENT_MIXER)
    rf_data_conv.dac_tiles[1].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
    
    # ETHERNET
    dest_ip = ip_addr.tIP_destination(sep='', asHex=True)
    dest_mac = ip_addr.mac_destination(sep='')
    src_ip_1 = ip_addr.tIP_origin(1, sep='', asHex=True)
    src_ip_2 = ip_addr.tIP_origin(2, sep='', asHex=True)
    src_ip_3 = ip_addr.tIP_origin(3, sep='', asHex=True)
    src_ip_4 = ip_addr.tIP_origin(4, sep='', asHex=True)
    src_mac = ip_addr.mac_origin(sep='')

    def ethRegsPortWrite(eth_regs,
                     src_ip_int32   = int(src_ip_1, 16),
                     dst_ip_int32   = int(dest_ip,16),
                     src_mac0_int32 = int(src_mac[:-4],16),
                     src_mac1_int16 = int(src_mac[-4:],16),
                     dst_mac0_int16 = int(dest_mac[-4:],16),   
                     dst_mac1_int32 = int(dest_mac[:-4],16)): 
        eth_regs.write( 0x00, src_mac0_int32)
        eth_regs.write( 0x04, (dst_mac0_int16<<16) + src_mac1_int16)
        eth_regs.write( 0x08, dst_mac1_int32)
        eth_regs.write( 0x0c, src_ip_int32)
        eth_regs.write( 0x10, dst_ip_int32)

    ethRegsPortWrite(firmware.ethWrapPort0.eth_regs_0, src_ip_int32=int(src_ip_1, 16))
    ethRegsPortWrite(firmware.ethWrapPort1.eth_regs_0, src_ip_int32=int(src_ip_2, 16))
    ethRegsPortWrite(firmware.ethWrapPort2.eth_regs_0, src_ip_int32=int(src_ip_3, 16))
    ethRegsPortWrite(firmware.ethWrapPort3.eth_regs_0, src_ip_int32=int(src_ip_4, 16))


except Exception as e:
    print(e)
