from pynq import Overlay
import xrfclk
import xrfdc

try:
    # FIRMWARE UPLOAD
    firmware = Overlay("single_chan_4eth_v8p2.bit",ignore_version=True)

    # INITIALIZING PLLs
    clksrc = 409.6 # MHz
    xrfclk.set_all_ref_clks(clksrc)

    lofreq = 1000.000 # [MHz]
    rf_data_conv = firmware.usp_rf_data_converter_0
    rf_data_conv.adc_tiles[0].blocks[0].MixerSettings['Freq']=lofreq
    rf_data_conv.dac_tiles[1].blocks[3].MixerSettings['Freq']=lofreq
    rf_data_conv.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
    rf_data_conv.dac_tiles[1].blocks[3].UpdateEvent(xrfdc.EVENT_MIXER)

except Exception as e:
    print(e)