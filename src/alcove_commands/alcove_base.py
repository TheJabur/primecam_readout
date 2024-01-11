
# ============================================================================ #
# alcove_base.py
# Alcove commands common base.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #



# ============================================================================ #
# IMPORTS & GLOBALS
# ============================================================================ #


try:
    from config import board as cfg
    import alcove_commands.board_io as io
    import queen_commands.control_io as cio

    import xrfdc # type: ignore
    from pynq import Overlay
    
    # FIRMWARE UPLOAD
    firmware = Overlay(cfg.firmware_file, ignore_version=True, download=False)

except Exception as e: 
    firmware = None
    print(f"Error loading firmware: {e}")



# ============================================================================ #
# GENERAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# freqOffsetFixHackFactor
def freqOffsetFixHackFactor():
    return 1.0009707 # need to check this


# ============================================================================ #
# generateWaveDdr4
def generateWaveDdr4(freq_list, amp_list, phi):  

    import numpy as np

    # freq_list may be complex but imag parts should all be zero
    freq_list = np.real(freq_list)
    amp_list = np.real(amp_list)
    phi = np.real(phi)

    fs = 512e6 
    lut_len = 2**20
    fft_len = 1024
    k = np.int64(np.round(freq_list/(fs/lut_len)))
    freq_actual = k*(fs/lut_len)
    X = np.zeros(lut_len,dtype='complex')
    #phi = np.random.uniform(-np.pi, np.pi, np.size(freq_list))
    for i in range(np.size(k)):
        X[k[i]] = np.exp(-1j*phi[i])*amp_list[i] # multiply by amplitude
    x = np.fft.ifft(X) * lut_len
    bin_num = np.int64(np.round(freq_actual / (fs / fft_len)))
    f_beat = bin_num*fs/fft_len - freq_actual
    dphi0 = f_beat/(fs/fft_len)*2**16
    if np.size(dphi0) > 1:
        dphi = np.concatenate((dphi0, np.zeros(fft_len - np.size(dphi0))))
    else:
        z = np.zeros(fft_len)
        z[0] = dphi0
        dphi = z
    return x, dphi, freq_actual


# ============================================================================ #
# _getSnapData
# capture data from ADC
def _getSnapData(chan, mux_sel, wrap=False):

    import numpy as np
    from pynq import MMIO

    # WIDE BRAM
    if chan==1:
        axi_wide = firmware.chan1.axi_wide_ctrl# 0x0 max count, 0x8 capture rising edge trigger
        base_addr_wide = 0x00_A007_0000
    elif chan==2:
        axi_wide = firmware.chan2.axi_wide_ctrl
        base_addr_wide = 0x00_B000_0000
    elif chan==3:
        axi_wide = firmware.chan3.axi_wide_ctrl
        base_addr_wide = 0x00_B000_8000
    elif chan==4:
        axi_wide = firmware.chan4.axi_wide_ctrl
        base_addr_wide = 0x00_8200_0000
    else:
        return "Does not compute"
    max_count = 32768
    axi_wide.write(0x08, mux_sel<<1) # mux select 0-adc, 1-pfb, 2-ddc, 3-accum
    axi_wide.write(0x00, max_count - 16) # -4 to account for extra delay in write counter state machine
    axi_wide.write(0x08, mux_sel<<1 | 0)
    axi_wide.write(0x08, mux_sel<<1 | 1)
    axi_wide.write(0x08, mux_sel<<1 | 0)
    mmio_wide_bram = MMIO(base_addr_wide,max_count)
    wide_data = mmio_wide_bram.array[0:8192]# max/4, bram depth*word_bits/32bits
    if mux_sel==0:
        #adc parsing
        up0, lw0 = np.int16(wide_data[0::4] >> 16), np.int16(wide_data[0::4] & 0x0000ffff)
        up1, lw1 = np.int16(wide_data[1::4] >> 16), np.int16(wide_data[1::4] & 0x0000ffff)
        I = np.zeros(4096)
        Q = np.zeros(4096)
        Q[0::2] = lw0
        Q[1::2] = up0
        I[0::2] = lw1
        I[1::2] = up1
    elif mux_sel==1:
        # pfb
        chunk0 = (np.uint64(wide_data[1::4]) << np.uint64(32)) + np.uint64(wide_data[0::4])
        chunk1 = (np.uint64(wide_data[2::4]) << np.uint64(32)) + np.uint64(wide_data[1::4])
        q0 = np.int64((chunk0 & 0x000000000003ffff)<<np.uint64(46))/2**32
        i0 = np.int64(((chunk0>>18) & 0x000000000003ffff)<<np.uint64(46))/2**32
        q1 = np.int64(((chunk1>>4)  & 0x000000000003ffff)<<np.uint64(46))/2**32
        i1 = np.int64(((chunk1>>22)  & 0x000000000003ffff)<<np.uint64(46))/2**32
        I = np.zeros(4096)
        Q = np.zeros(4096)
        Q[0::2] = q0/2**14
        Q[1::2] = q1/2**14
        I[0::2] = i0/2**14
        I[1::2] = i1/2**14
    elif mux_sel==2:
        # ddc
        chunk0 = (np.uint64(wide_data[1::4]) << np.uint64(32)) + np.uint64(wide_data[0::4])
        chunk1 = (np.uint64(wide_data[2::4]) << np.uint64(32)) + np.uint64(wide_data[1::4])
        q0 = np.int64((chunk0 & 0x00000000000fffff)<<np.uint64(45))/2**32
        i0 = np.int64(((chunk0>>19) & 0x00000000000fffff)<<np.uint64(45))/2**32
        q1 = np.int64(((chunk1>>6)  & 0x00000000000fffff)<<np.uint64(45))/2**32
        i1 = np.int64(((chunk1>>25)  & 0x00000000000fffff)<<np.uint64(45))/2**32
        I = np.zeros(4096)
        Q = np.zeros(4096)
        Q[0::2] = q0/2**13
        Q[1::2] = q1/2**13
        I[0::2] = i0/2**13
        I[1::2] = i1/2**13
    elif mux_sel==3:
        # accum
        q0 = (np.int32(wide_data[1::4])).astype("float")
        i0 = (np.int32(wide_data[0::4])).astype("float")
        q1 = (np.int32(wide_data[3::4])).astype("float")
        i1 = (np.int32(wide_data[2::4])).astype("float")
        I = np.zeros(4096)
        Q = np.zeros(4096)
        Q[0::2] = q0
        Q[1::2] = q1
        I[0::2] = i0
        I[1::2] = i1
        I, Q = I[4:], Q[4:]

    if wrap:
        return io.returnWrapper(io.file.IQ_generic, (I,Q))
    else:
        return I, Q


# ============================================================================ #
# getSnapData
def getSnapData(mux_sel, wrap=True):
    chan = cfg.drid
    return _getSnapData(chan, int(mux_sel), wrap=wrap)


# ============================================================================ #
# _setNCLO
def _setNCLO(chan, lofreq):

    lofreq *= freqOffsetFixHackFactor() # Fequency offset fix
    # implemented in tones._writeComb and alcove_base._setNCLO

    # import xrfdc
    rf_data_conv = firmware.usp_rf_data_converter_0
    
    if chan == 1:
        rf_data_conv.adc_tiles[0].blocks[0].MixerSettings['Freq']=lofreq
        rf_data_conv.dac_tiles[1].blocks[3].MixerSettings['Freq']=lofreq
        rf_data_conv.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
        rf_data_conv.dac_tiles[1].blocks[3].UpdateEvent(xrfdc.EVENT_MIXER)
    elif chan == 2:
        rf_data_conv.adc_tiles[0].blocks[1].MixerSettings['Freq']=lofreq
        rf_data_conv.dac_tiles[1].blocks[2].MixerSettings['Freq']=lofreq
        rf_data_conv.adc_tiles[0].blocks[1].UpdateEvent(xrfdc.EVENT_MIXER)
        rf_data_conv.dac_tiles[1].blocks[2].UpdateEvent(xrfdc.EVENT_MIXER)
    elif chan == 3:
        rf_data_conv.adc_tiles[1].blocks[0].MixerSettings['Freq']=lofreq
        rf_data_conv.dac_tiles[1].blocks[1].MixerSettings['Freq']=lofreq
        rf_data_conv.adc_tiles[1].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
        rf_data_conv.dac_tiles[1].blocks[1].UpdateEvent(xrfdc.EVENT_MIXER)
    elif chan == 4:
        rf_data_conv.adc_tiles[1].blocks[1].MixerSettings['Freq']=lofreq
        rf_data_conv.dac_tiles[1].blocks[0].MixerSettings['Freq']=lofreq
        rf_data_conv.adc_tiles[1].blocks[1].UpdateEvent(xrfdc.EVENT_MIXER)
        rf_data_conv.dac_tiles[1].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
    else:
        return "Does not compute" # great error message
    return


def _getNCLO(chan):

    rf_data_conv = firmware.usp_rf_data_converter_0

    # adc tiles; adc blocks; dac tiles; dac blocks
    if chan == 1: 
        i = [0,0,1,3]
    elif chan == 2:
        i = [0,1,1,2]
    elif chan == 3:
        i = [1,0,1,1]
    elif chan == 4:
        i = [1,1,1,0]
    else:
        print("_getNCLO: Invalid chan!")
        return

    adc = rf_data_conv.adc_tiles[i[0]].blocks[i[1]]
    dac = rf_data_conv.dac_tiles[i[2]].blocks[i[3]]

    f_lo = adc.MixerSettings['Freq']

    return f_lo


# ============================================================================ #
# setNCLO
def setNCLO(f_lo):
    """
    setNCLO: set the numerically controlled local oscillator
           
    f_lo: center frequency in [MHz]
    """

    import numpy as np

    chan = cfg.drid
    f_lo = int(f_lo)
    _setNCLO(chan, f_lo)
    io.save(io.file.f_center_vna, f_lo*1e6)


# ============================================================================ #
# getNCLO
def getNCLO(chan=None):
    """Get the numerically controlled local oscillator value from register.
    """

    import numpy as np

    if chan is None:
        chan = cfg.drid

    f_lo = float(_getNCLO(chan))

    return f_lo


# ============================================================================ #
# _setNCLO2
def _setNCLO2(chan, lofreq):
    import numpy as np
    mix = firmware.mix_freq_set_0
    if chan == 1:
        offset = 0
    elif chan == 2:
        offset = 4
    elif chan == 3:
        offset = 8
    elif chan == 4:
        offset = 12
    else:
        return "Does not compute"
    # set fabric nclo frequency 
    # only for small frequency sweeps
    # 0x00 -  frequency[21 downto 0] 
    def nclo_num(freqMHz):
        # freq in MHz
        # returns 32 bit signed integer for setting nclo2
        MHz_per_int = 512.0/2**22 #MHz per_step !check with spec-analyzer
        digi_val = int(np.round(freqMHz/MHz_per_int))
        actual_freq = digi_val*MHz_per_int
        return digi_val, actual_freq

    digi_val, actual_freq = nclo_num(lofreq)
    mix.write(offset, digi_val) # frequency
    return


# ============================================================================ #
# setFineNCLO 
def setFineNCLO(df_lo):
    """
    setFineNCLO: set the fine frequency numerically controlled local oscillator
           
    df_lo: Center frequency shift, in [MHz].
    """

    # import numpy as np

    chan = cfg.drid
    df_lo = float(df_lo)
    return _setNCLO2(chan, df_lo)
    # TODO: modify f_center to reflect this fine adjustment
    # io.save(io.file.f_center_vna, f_lo*1e6)


# ============================================================================ #
# _customCombFilename
def _customCombFilename(type):
    """Relative filename string for custom comb file.

    Type: The file ("freqs_rf", "amps", "phis")
    """

    fnames = {
        "freqs_rf":"alcove_commands/custom_freqs.npy",
        "amps":"alcove_commands/custom_amps.npy",
        "phis":"alcove_commands/custom_phis.npy"
    }
    return fnames[type]

# ============================================================================ #
# createCustomCombFiles
def createCustomCombFiles(freqs_rf=None, amps=None, phis=None):
    """Create custom comb files from arrays.
    Used in tones.writeTargCombFromCustomList().
    """

    import numpy as np

    if freqs_rf:    np.save(_customCombFilename("freqs_rf"), freqs_rf)
    if amps:        np.save(_customCombFilename("amps"), amps)
    if phis:        np.save(_customCombFilename("phis"), phis)


# ============================================================================ #
# createCustomCombFilesFromCurrentComb
def createCustomCombFilesFromCurrentComb():
    """Create custom comb files from the current comb.
    """

    f_comb = io.load(io.file.f_res_targ)
    a_comb = io.load(io.file.a_res_targ)
    p_comb = io.load(io.file.p_res_targ)

    createCustomCombFiles(freqs_rf=f_comb, amps=a_comb, phis=p_comb)


'''
# ============================================================================ #
# createCustomCombFilesFromTarget
def createCustomCombFilesFromTarget():
    """Create the custom comb files from the most recent target files.
    """

    f_res_targ = io.load(io.file.f_res_targ)
    a_res_targ = io.load(io.file.a_res_targ)
    p_res_targ = io.load(io.file.p_res_targ)

    createCustomCombFiles(freqs_rf=f_res_targ, amps=a_res_targ, phis=p_res_targ)
'''


# ============================================================================ #
# loadCustomCombFiles
def loadCustomCombFiles():
    """Load custom comb files into arrays.
    Used in tones.writeTargCombFromCustomList().
    """
    
    import numpy as np

    freqs_rf =  np.load(_customCombFilename("freqs_rf"))
    amps =      np.load(_customCombFilename("amps"))
    phis =      np.load(_customCombFilename("phis"))

    return freqs_rf, amps, phis


# ============================================================================ #
# modifyCustomCombAmps
def modifyCustomCombAmps(factor=1):
    """Modify custom tone amps file by multiplying by given factor.
    """
    
    import numpy as np

    amps = np.load(_customCombFilename("amps"))
    amps *= float(factor)
    np.save(_customCombFilename("amps"), amps)