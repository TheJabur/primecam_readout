from pynq import Overlay
import xrfclk
import xrfdc

try:
    # FIRMWARE UPLOAD
    firmware = Overlay("single_chan_4eth_v8p2.bit",ignore_version=True)

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

    # ETHERNET
    def ethRegsPortWrite(eth_regs,
                     src_ip_int32   = int("c0a80335",16), # defaults
                     dst_ip_int32   = int("c0a80328",16),
                     src_mac0_int32 = int("deadbeef",16),
                     src_mac1_int16 = int("feed",16),
                     dst_mac0_int16 = int("2bb0",16),     # 
                     dst_mac1_int32 = int("803f5d09",16)):
    eth_regs.write( 0x00, src_mac0_int32) 
    eth_regs.write( 0x04, (dst_mac0_int16<<16) + src_mac1_int16)
    eth_regs.write( 0x08, dst_mac1_int32)
    eth_regs.write( 0x0c, src_ip_int32)
    eth_regs.write( 0x10, dst_ip_int32)
    
    ethRegsPortWrite(firmware.eth_wrap.eth_regs_port0, src_ip_int32=int("c0a80332",16))
    ethRegsPortWrite(firmware.eth_wrap.eth_regs_port1, src_ip_int32=int("c0a80333",16))
    ethRegsPortWrite(firmware.eth_wrap.eth_regs_port2, src_ip_int32=int("c0a80334",16))
    ethRegsPortWrite(firmware.eth_wrap.eth_regs_port3, src_ip_int32=int("c0a80335",16))

    eth_delay_reg = firmware.eth_wrap.eth_delay # programmable delay for eth byte shift
    data_in_mux = firmware.eth_wrap.data_in_mux
    ###############################
    # Ethernet Delay Lines  
    ###############################
    eth_delay_reg.write(0x00, -22 + (4<<16)) # data output from eth buffer delay/ input to eth buffer delay <<16 delay
    eth_delay_reg.write(0x08, 0) # ethernet start pulse out delay
    ###############################
    # Data MUX
    ###############################
    data_in_mux.write( 0x00, 1) #  test vector when 0, data when 1
    data_in_mux.write( 0x08, (509) + ((8189)<<16) ) # ethernet max write count and max read count

except Exception as e:
    print(e)
