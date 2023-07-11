from pynq import Overlay
import xrfclk
import xrfdc
import ip_addr
import _cfg_board as cfg

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
    
    dest_ip_udp = "".join(ip_addr.IPtoHex(cfg.destination_ip, as_list=True))
    
    # ETHERNET
    def ethRegsPortWrite(eth_regs,
                     src_ip_int32   = int("c0a80335",16),
                     dst_ip_int32   = int(dest_ip_udp,16),
                     src_mac0_int32 = int("eec0ffee",16),
                     src_mac1_int16 = int("c0ff",16),
                     dst_mac0_int16 = int(cfg.destination_mac[-4:],16),   
                     dst_mac1_int32 = int(cfg.destination_mac[:-4],16)): 
        eth_regs.write( 0x00, src_mac0_int32)
        eth_regs.write( 0x04, (dst_mac0_int16<<16) + src_mac1_int16)
        eth_regs.write( 0x08, dst_mac1_int32)
        eth_regs.write( 0x0c, src_ip_int32)
        eth_regs.write( 0x10, dst_ip_int32)

    ethRegsPortWrite(firmware.ethWrapPort0.eth_regs_0, src_ip_int32=int("c0a80332",16))
    ethRegsPortWrite(firmware.ethWrapPort1.eth_regs_0, src_ip_int32=int("c0a80333",16))
    ethRegsPortWrite(firmware.ethWrapPort2.eth_regs_0, src_ip_int32=int("c0a80334",16))
    ethRegsPortWrite(firmware.ethWrapPort3.eth_regs_0, src_ip_int32=int("c0a80335",16))

except Exception as e:
    print(e)
