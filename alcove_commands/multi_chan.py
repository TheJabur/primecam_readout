
#####################
# Global attributes #
#####################
try:
    import _cfg_board as cfg
    import alcove_commands.board_io as io

    import xrfdc
    from pynq import Overlay
    
    # FIRMWARE UPLOAD
    firmware = Overlay("tetra_v5p4.bit",ignore_version=True,download=False)

except Exception as e: 
    firmware = None
    print(f"Error loading firmware: {e}")



######################
# Internal Functions #
######################

def _setNCLO(chan, lofreq):

    import xrfdc
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

def _generateWaveDdr4(freq_list):  

    import numpy as np

    # freq_list may be complex but imag parts should all be zero
    freq_list = np.real(freq_list)

    fs = 512e6 
    lut_len = 2**20
    fft_len = 1024
    k = np.int64(np.round(freq_list/(fs/lut_len)))
    freq_actual = k*(fs/lut_len)
    X = np.zeros(lut_len,dtype='complex')
    phi = np.random.uniform(-np.pi, np.pi, np.size(freq_list))
    X[k] = np.exp(-1j*phi)
    x = np.fft.ifft(X) * lut_len/np.sqrt(2)
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


def _normWave(wave, max_amp=2**15-1):

    import numpy as np

    norm = np.max(np.abs(wave))
    if norm == 0:
        return wave.real, wave.imag
    wave_real = ((wave.real/norm)*max_amp).astype("int16")
    wave_imag = ((wave.imag/norm)*max_amp).astype("int16")
    return wave_real, wave_imag


def _loadBinList(chan, freq_list):

    import numpy as np

    fs = 512e6
    fft_len = 1024
    lut_len = 2**20
    k = np.int64(np.round(-freq_list/(fs/lut_len)))
    freq_actual = k*(fs/lut_len)
    bin_list = np.int64(np.round(freq_actual / (fs / fft_len)))
    pos_bin_idx = np.where(bin_list > 0)
    if np.size(pos_bin_idx) > 0:
        bin_list[pos_bin_idx] = 1024 - bin_list[pos_bin_idx]
    bin_list = np.abs(bin_list)
    # DSP REGS
    if chan == 1:
        dsp_regs = firmware.chan1.dsp_regs_0
    elif chan == 2:
        dsp_regs = firmware.chan2.dsp_regs_0
    elif chan == 3:
        dsp_regs = firmware.chan3.dsp_regs_0
    elif chan == 4:
        dsp_regs = firmware.chan4.dsp_regs_0
    else:
        return "Does not compute"
    # 0x00 -  fft_shift[9 downto 0], load_bins[22 downto 12], lut_counter_rst[11 downto 11] 
    # 0x04 -  bin_num[9 downto 0]
    # 0x08 -  accum_len[23 downto 0], accum_rst[24 downto 24], sync_in[26 downto 26] (start dac)
    # 0x0c -  dds_shift[8 downto 0]
    
    # initialization 
    sync_in = 2**26
    accum_rst = 2**24  # (active low)
    accum_length = (2**19)-1
    ################################################
    # Load DDC bins
    ################################################
    offs=0
    
    # only write tones to bin list
    for addr in range(1024):
        if addr<(np.size(bin_list)):
            #print("addr = {}, bin# = {}".format(addr, bin_list[addr]))
            dsp_regs.write(0x04,int(bin_list[addr]))
            dsp_regs.write(0x00, ((addr<<1)+1)<<12)
            dsp_regs.write(0x00, 0)
        else:
            dsp_regs.write(0x04, 0)
            dsp_regs.write(0x00, ((addr<<1)+1)<<12)
            dsp_regs.write(0x00, 0)
    return


def _resetAccumAndSync(chan, freqs):
    if chan == 1:
        dsp_regs = firmware.chan1.dsp_regs_0
    elif chan == 2:
        dsp_regs = firmware.chan2.dsp_regs_0
    elif chan == 3:
        dsp_regs = firmware.chan3.dsp_regs_0
    elif chan == 4:
        dsp_regs = firmware.chan4.dsp_regs_0
    else:
        return "Does not compute"
    # dsp_regs bitfield map
    # 0x00 -  fft_shift[9 downto 0], load_bins[22 downto 12], lut_counter_rst[11 downto 11] 
    # 0x04 -  bin_num[9 downto 0]
    # 0x08 -  accum_len[23 downto 0], accum_rst[24 downto 24], sync_in[26 downto 26] (start dac)
    # 0x0c -  dds_shift[8 downto 0]
    # initialization
    sync_in = 2**26
    accum_rst = 2**24  # (active rising edge)
    accum_length = (2**19)-1
    
    fft_shift=0
    if len(freqs)<400:
        fft_shift = 2**9-1 #2**9-1
    else:
        fft_shift = 2**5-1 #2**2-1
    dsp_regs.write(0x00, fft_shift) # set fft shift
    ########################
    dsp_regs.write(0x08, accum_length | sync_in)
    dsp_regs.write(0x08, accum_length | accum_rst | sync_in)
    dsp_regs.write(0x0c,260)
    return


def _loadDdr4(chan, wave_real, wave_imag, dphi):

    import numpy as np
    from pynq import MMIO

    if chan == 1:
        base_addr_dphis = 0xa004c000
    elif chan == 2:
        base_addr_dphis = 0xa0040000
    elif chan == 3:
        base_addr_dphis = 0xa0042000
    elif chan == 4:
        base_addr_dphis = 0xa004e000
    else:
        return "Does not compute"
    
    # write dphi to bram
    dphi_16b = dphi.astype("uint16")
    dphi_stacked = ((np.uint32(dphi_16b[1::2]) << 16) + dphi_16b[0::2]).astype("uint32")
    mem_size = 512 * 4 # 32 bit address slots
    mmio_bram_phis = MMIO(base_addr_dphis, mem_size)
    mmio_bram_phis.array[0:512] = dphi_stacked[0:512] # the [0:512] indexing is necessary on .array
    
    # slice waveform for uploading to ddr4
    I0, I1, I2, I3 = wave_imag[0::4], wave_imag[1::4], wave_imag[2::4], wave_imag[3::4]
    Q0, Q1, Q2, Q3 = wave_real[0::4], wave_real[1::4], wave_real[2::4], wave_real[3::4]
    data0 = ((np.int32(I0) << 16) + Q0).astype("int32")
    data1 = ((np.int32(I1) << 16) + Q1).astype("int32")
    data2 = ((np.int32(I2) << 16) + Q2).astype("int32")
    data3 = ((np.int32(I3) << 16) + Q3).astype("int32")
    # write waveform to DDR4 memory
    ddr4mux = firmware.axi_ddr4_mux
    ddr4mux.write(8,0) # set read valid 
    ddr4mux.write(0,0) # mux switch
    ddr4 = firmware.ddr4_0
    base_addr_ddr4 = 0x4_0000_0000 #0x5_0000_0000
    depth_ddr4 = 2**32
    mmio_ddr4 = MMIO(base_addr_ddr4, depth_ddr4)
        
    mmio_ddr4.array[0:4194304][0 + (chan-1)*4::16] = data0
    mmio_ddr4.array[0:4194304][1 + (chan-1)*4::16] = data1
    mmio_ddr4.array[0:4194304][2 + (chan-1)*4::16] = data2
    mmio_ddr4.array[0:4194304][3 + (chan-1)*4::16] = data3

    ddr4mux.write(8,1) # set read valid 
    ddr4mux.write(0,1) # mux switch

    return


# capture data from ADC
def _getSnapData(chan, mux_sel):

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
    return I, Q

def _getCleanAccum(Itemplate, Qtemplate):
    """
    Function to return un-spurious accumuation captures

    input: I and Q template to compare variance of power

    output: I and Q which pass variance ratio threshold
    """
    import numpy as np

    j = 0
    I, Q = getSnapData(3)
    Pt = Itemplate**2 + Qtemplate**2
    Ntrys = 3
    while (j < Ntrys):
        Pdiff = Pt - (I**2 + Q**2)
        ratio = np.var(Pdiff)/np.var(Pt)
        if ratio < 0.00001:
            j = Ntrys
        else:
            I, Q = getSnapData(3)
            #if j==(Ntrys-1):
            #    print("Warning! could not clean data")
            j+= 1    
    return I, Q


def _writeComb(chan, freqs):
    
    wave, dphi, freq_actual = _generateWaveDdr4(freqs)
    wave_real, wave_imag = _normWave(wave, max_amp=2**15-1)
    _loadDdr4(chan, wave_real, wave_imag, dphi)
    _loadBinList(chan, freq_actual)
    _resetAccumAndSync(chan, freq_actual)
    return freq_actual


def _sweep(chan, f_center, freqs, N_steps, chan_bandwidth=None):
    """
    Perform a stepped LO frequency sweep with existing comb centered at f_center.
    
    INPUTS
    f_center:        (float) Center LO frequency for sweep [MHz].
    freqs:           (1D array of floats) Comb frequencies [Hz].
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    chan_bandwidth:  (float) Bandwidth of each channel [MHz].
    
    RETURN: tuple(f, S21)
    f:               (1D array of floats) Central frequency for each bin.
    Z:               (1D array of complex) S_21 complex I+jQ for each bin.
    """

    import numpy as np
    from time import sleep

    if chan_bandwidth:         # LO bandwidth given
        bw = chan_bandwidth    # MHz
    else:                      # LO bandwidth is tone difference
        bw = np.diff(freqs)[0]/1e6 # MHz
    flos = np.linspace(f_center-bw/2., f_center+bw/2., N_steps)
    _, _ = getSnapData(3) # discard previously collected accum samples
    It, Qt = getSnapData(3) # grab new accumulator samples for template
    def _Z(lofreq, Naccums=5):
        _setNCLO2(chan, lofreq)       # update mixer LO frequency
        # after setting nclo sleep to let old data pass
        # read accumulator snap block a few times to assure
        # new data
        Is, Qs = 0, 0
        accums = 4
        I, Q = getSnapData(3) #
        for i in range(accums):
            #I, Q = _getCleanAccum(It, Qt)
            sleep(0.004)
            I, Q = getSnapData(3) #
            Is += I/accums
            Qs += Q/accums
        Z = Is + 1j*Qs     # convert I and Q to complex
        return Z[0:len(freqs)] # only return relevant slice
    
    # loop over _Z for each LO freq
    # and flatten
    Z = (np.array([_Z(lofreq-f_center) for lofreq in flos]).T).flatten()
    
    # build and flatten all bin frequencies
    f = np.array([flos*1e6 + ftone for ftone in freqs]).flatten()
        
    _setNCLO2(chan, 0)       # update mixer LO frequency

    return (f, Z)


def _stitchS21m(S21m, bw=500, sw=100):
    """Shift S21 mags so the bin ends align.

    S21m: (array of floats) 1D array of S21 complex modulus.
    bw:   (int) Width of the stitch bins.
    sw:   (int) Width of slice (at ends) of each stitch bin to take median.
    """
    
    import numpy as np
    
    a = S21m.reshape(-1, bw)               # reshape into bins
    
    meds_i = np.median(a[:,:sw], axis=1)   # medians on left
    meds_f = np.median(a[:,-sw:], axis=-1) # medians on right
    
    f = meds_i[1:] - meds_f[:-1]           # bin power misalignment
    f = np.pad(f, (1, 0), mode='constant') # 1st bin -> 0 misalignment
    f = np.cumsum(f)                       # misalignments are cumulative
    f = f.reshape((a.shape[0],1))          # reshape for matrix addition
    a_n = a - f                            # misalignment correction (stitch)
    
    return a_n.flatten()                   # reshape to 1D and return


def _resonatorIndicesInS21(f, Z, stitch_bw=500, stitch_sw=100, f_hi=50, f_lo=1, prom_dB=1, testing=False):
    """Find the indices of resonator peaks in given S21 signal.
    
    f:         (1D array of floats) Frequency bins of signal.
    Z:         (1D array of floats) S21 complex values.
    stitch_bw: (int) Width of the stitch bins.
    stitch_sw: (int) Width of slice (at ends) of each stitch bin to take median.
    f_hi:      (float) Highpass filter cutoff frequency (data units).
    f_lo:      (float) lowpass filter cutoff frequency (data units).
    prom_dB:   (float) Peak prominence cutoff, in dB.
    testing:   (bool) Also return intermediate products.
    
    Return:  (1D array of integers) Indices of peaks.
    """
    
    import numpy as np
    from scipy.signal import iirfilter, sosfiltfilt, find_peaks
    
    fs  = abs(f[1] - f[0])                             # sampling frequency
    m   = np.abs(Z)                                    # S21 mags
    m_s   = _stitchS21m(m, bw=stitch_bw, sw=stitch_sw)   # stitch mags
    
    filt_bp = iirfilter(2, (f_lo, f_hi), fs=fs, btype='bandpass', output='sos')
    m_f   = sosfiltfilt(filt_bp, m_s)                    # bandpass filtered
    prom_lin = np.amax(m)*(1-10**(-prom_dB/20)) 
    m_f_dB = 20.*np.log10(m_f + abs(np.min(m_f)) + 1)     # in dB
    peaks, props = find_peaks(x=-m_f, prominence=prom_lin, distance=30, width=(5, 100)) 
    
    if testing: return peaks, (fs, m, m_f, m_f_dB, prom_dB, props)
    return peaks


def _toneFreqsAndAmpsFromSweepData(f, Z, amps, N_steps):
    """
    Determine resonator tone frequencies and normalized amplitudes from sweep data.
    
    f:               (1D array of floats) Central frequency for each bin.
    Z:               (1D array of floats) Complex S21 values.
    amps:            (1D array of floats) Current normalized tone amplitudes.
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    """
    
    import numpy as np

    y     = np.abs(Z)                    # magnitude of Z
    f_res = np.reshape(f, (-1, N_steps)) # split f by KID
    y_res = np.reshape(y, (-1, N_steps)) # split Zm by KID
    # _res vars are 2D arrays: one 1D array per resonator
    
    # KID resonance frequencies
    i_res = np.argmin(y_res, axis=1)
    freqs = f_res[tuple([np.arange(0,len(i_res)), i_res])] # multi-dim. array indexing

    # Power
    # np.gradient provides the slope at each point.
    # The asymmetry of the resonator shape in frequency space 
    # can be characterized by the sum of the max and min slopes.
    y_grad = np.gradient(y_res, axis=1)         # slope at each point
    a = np.max(y_grad, axis=1) + np.min(y_grad, axis=1)  # sum max and min slopes
    a /= np.max(np.abs(y_grad), axis=1)         # normalize
    A_res = (1 + a)*amps

    return (freqs, A_res)



#####################
# Command Functions #
#####################
# Arguments are given as strings!

def writeTestTone():

    import numpy as np
    
    chan = cfg.drid # drone (chan) id is from config
    freqs = np.array(np.linspace(50e6, 255.00e6, 1))
    freq_actual = _writeComb(chan, freqs)

def writeVnaComb():

    import numpy as np
    
    chan = cfg.drid # drone (chan) id is from config
    freqs = np.array(np.linspace(-254.4e6, 255.00e6, 1000))
    freq_actual = _writeComb(chan, freqs)
    io.save(io.file.freqs_vna, freq_actual)


def writeTargComb(write_cal_tones=True):
    
    import numpy as np

    targ_freqs = io.load(io.file.f_res_vna)
    f_center   = io.load(io.file.f_center_vna)
    f_cal_tones = io.load(io.file.f_cal_tones) # what if doesnt exist?
    chan = cfg.drid # drone (chan) id is from config
    freqs = targ_freqs.real
    freqs = np.append(freqs, f_cal_tones)
    freqs = freqs - f_center
    freq_actual = _writeComb(chan, freqs)
    # io.save(io.file._f_res_targ, freq_actual)


def getSnapData(mux_sel):
    chan = cfg.drid
    return _getSnapData(chan, int(mux_sel))

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

def vnaSweep(f_center=600):
    """
    vnaSweep: perform a stepped frequency sweep centered at f_center \\
            save result as s21.npy file

    f_center: center frequency for sweep in [MHz]
    """

    import numpy as np

    chan = cfg.drid
    f_center = int(f_center)
    _setNCLO(chan, f_center)
    
    freqs = io.load(io.file.freqs_vna) # what if it doesnt exist?

    writeVnaComb()
    s21 = np.array(_sweep(chan, f_center, freqs, N_steps=500)) # f, Z

    io.save(io.file.s21_vna, s21)
    io.save(io.file.f_center_vna, f_center*1e6)

    return (s21)


def findResonators():
    """
    Find the resonator peak frequencies in previously saved s21.npy file.
    """
    
    import numpy as np

    # load S21 complex mags (Z) and frequencies (f) from file
    f, Z = io.load(io.file.s21_vna)

    i_peaks = _resonatorIndicesInS21(
        f, Z, 
        stitch_bw=500, stitch_sw=100, 
        f_hi=50, f_lo=1, prom_dB=1, 
        testing=False)
    f_res = f[i_peaks]

    io.save(io.file.f_res_vna, f_res)

    return f_res


def findCalTones(f_lo=0.1, f_hi=50, tol=2, max_tones=10):
    """Determine the indices of calibration tones.
    
    f_hi:      (float) Highpass filter cutoff frequency (data units).
    f_lo:      (float) lowpass filter cutoff frequency (data units).
    tol:       (float) Reject tones tol*std_noise from continuum.
    max_tones: (int) Maximum number of tones to return.
    """
    
    import numpy as np
    from scipy.signal import iirfilter, sosfiltfilt

    ## load data from file
    f, Z = io.load(io.file.s21_vna)
    m = np.abs(Z)
    freqs = io.load(io.file.f_res_vna).real
    
    fs  = abs(f[1] - f[0])                        ## sampling frequency
    freqs_i = [np.abs(f - v).argmin() for v in freqs] ## indices of freqs
    freqs_i = np.append(np.insert(freqs_i, 0, 0), len(f)) ## add end gaps
    
    ## isolate continuum w/ lowpass filter
    filt_lo = iirfilter(2, f_lo, fs=fs, btype='lowpass', output='sos')
    m_lo   = sosfiltfilt(filt_lo, m)

    ## isolate noise w/ highpass filter
    filt_hi = iirfilter(2, f_hi, fs=fs, btype='highpass', output='sos')
    m_hi   = sosfiltfilt(filt_hi, m)
    std_hi = np.std(m_hi)                         ## calculate std of noise

    ## find gaps between resonators
    gaps = np.diff(freqs_i)
    gaps_i = (freqs_i[:-1] + freqs_i[1:]) // 2    ## gap center indices
    
    ## sort gaps (descending; w/ indices)
    sort_i = np.argsort(gaps)[::-1]
    # gaps_s = gaps[sort_i]
    gaps_s_i = gaps_i[sort_i]
   
    ## filter any too far from continuum (m_lo)
    cal_tones_i = gaps_s_i[(abs(m[gaps_s_i] - m_lo[gaps_s_i])) < tol*std_hi]
    
    ## limit to max_tones
    cal_tones_i = cal_tones_i[:max_tones] 

    f_cal_tones = f[cal_tones_i]

    io.save(io.file.f_cal_tones, f_cal_tones)
    
    return f_cal_tones
    

def targetSweep(f_res=None,f_center=None, N_steps=500, chan_bandwidth=0.2, amps=None, save=True):
    """
    Perform a sweep around resonator tones and identify resonator frequencies and tone amplitudes.
    
    f_res:           (1D array of floats) Current comb tone frequencies [Hz].
    f_center:        center frequency in [MHz].
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    chan_bandwidth:  (float) Channel bandwidth [MHz].
    amps:            (1D array of floats) Current normalized tone amplitudes.

    Return:          (2-tuple) Characterized resonator frequencies and normalized tone amplitudes.
    """

    import numpy as np

    chan = cfg.drid

    if f_res is None:
        try:
            f_res = io.load(io.file.f_res_vna) # Hz
            # f_res = np.load(f'{cfg.drone_dir}/f_res.npy')
        except:
            raise("Required file missing: f_res_vna. Perform a vna sweep first.")

    if amps is None:
        amps = np.ones_like(f_res)
    if f_center is None:
        try:
            # load center LO frequency - stored in Hz
            f_center = io.load(io.file.f_center_vna) # Hz
        except:
            raise("Required file missing: f_center_vna. Write NCLO frequency first.")
    else:
        f_center = f_center*1e6 # convert param MHz to Hz
    
    # perform target sweep after loading f_center
    S21 = np.array(_sweep(chan, f_center/1e6, f_res-f_center, N_steps, chan_bandwidth)) 
  
    freqs, A_res = _toneFreqsAndAmpsFromSweepData( *S21, amps, N_steps)

    if save:
        io.save(io.file.s21_targ, S21)
        io.save(io.file.f_res_targ, freqs)
        io.save(io.file.a_res_targ, amps)
        io.save(io.file.f_center_targ, f_center)

    # return an array here
    return (freqs, A_res)


def targetSweepLoop(chan_bandwidth=0.2, f_center=600, N_steps=500, 
                    f_tol=0.1, A_tol=0.3, loops_max=20):
    """
    chan_bandwidth:  (float) Channel bandwidth [MHz].
    f_center:        (float) Center LO frequency for sweep [MHz].
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    f_tol: Frequency difference tolerance between vna sweep and target sweep (MHz).
    A_tol: Amplitude relative adjustment factor tolerance.
    loops_max: 
    """
    
    import numpy as np
    
    try:
        freqs = io.load(io.file.f_res_vna)
    except:
        raise("Required file missing: f_res_vna. Perform a vna sweep first.")

    try: # current channel amplitudes
        # amps = np.load(f'{cfg.drone_dir}/amps.npy')
        amps = io.load(io.file.a_res_targ)
        if len(amps) != len(freqs): # could be an old file
            raise NameError("Target amps and f_res are not the same length!")
    except:
        amps = np.ones_like(freqs)

    # should we look at whether chan_bandwidth was large enough / too large?
        
    loop_num = 0; sweep = True
    while sweep:
        sweep = False # default to not performing another sweep
        
        freqs_new, amps_new = targetSweep(
            freqs, f_center=f_center, N_steps=N_steps, 
            chan_bandwidth=chan_bandwidth, amps=amps, 
            plot_step=200, save=False)
    
        if (np.any(np.abs(freqs - freqs_new) > f_tol*1e6) 
            or np.any(np.abs(1 - amps_new/amps) > A_tol)):
            sweep = True
            
        freqs, amps = freqs_new, amps_new

        if loop_num > loops_max:
            sweep = False # override any sweep=True statements
        loop_num += 1
        
    io.save(io.file.f_res_targ, freqs)
    io.save(io.file.a_res_targ, amps)
    io.save(io.file.f_center_targ, f_center*1e6)

    return np.array([freqs, amps])


def fullLoop(max_loops_full=2, max_loops_funcs=2, verbose=False):
    '''
    Complete resonator calibration.

    max_loops_full:  (int) Max number of times to retry if fail.
    max_loops_funcs: (int) Similar to max_loops_full but for individual funcs.
    verbose:         (bool) All messages to standard out.
    '''
    
    def fail(e):
        print(" FAILED!")
        if verbose: print(e)
    def retry(f, s, **params):
        for _ in range(max_loops_funcs):
            try: print(s+"...", end=""); f(**params)
            except Exception as e: fail(e)
            else: success(); return True
        raise Exception("Retry failed.") 
    def success(): print(" Done."); return True
    def fullFail(l): print(f"\n* Full loop failed ({l}).")
    def fullSuccess(l): print(f"\n* Full loop complete ({l}).")
    
    for l in range(max_loops_full):
            
        try: retry(vnaSweep, 
                   "Perform VNA sweep", 
                   f_center=600)
        except: fullFail(l); continue
        
        try: retry(findResonators, 
                   "Finding resonators")
        except: fullFail(l); continue
        
        try: retry(targetSweepLoop, 
                   "Perform target sweep loop", 
                   chan_bandwidth=0.2, f_center=600, N_steps=500, 
                   f_tol=0.1, A_tol=0.3, loops_max=20)
        except: fullFail(l); continue
        
        fullSuccess(l)
        break


def loChop(f_center=600, freq_offset=0.012, tol=0.01e6, dtol=0):
    """
    Do a quick sweep using only 2 (symmetric) points per resonator.
    Trigger a full sweep if dtol detectors are over tol.
    
    f_center:        (float) Center LO frequency for sweep [MHz].
    freq_offset:     (float) +/- offset from res. freq. for measurement [MHz].
    tol:             (float) Allowed |S21| difference between offsets [unit?].
    dtol:            (float) Max number of KIDs allowed to be over tolerance.
    """

    import numpy as np
    
    chan = cfg.drid
    freqs = io.load(io.file.f_res_targ)
    
    # if this comb is already set we could bypass this step for efficiency
    # how can we know?
    writeTargComb() 
    
    N_steps = 2                          # 2 symmetric points
    f, Z  = _sweep(chan, f_center, freqs, N_steps=N_steps, chan_bandwidth=2*freq_offset)
    
    y     = np.abs(Z)                    # magnitude of Z
    f_res = np.reshape(f, (-1, N_steps)) # split f by KID
    y_res = np.reshape(y, (-1, N_steps)) # split Zm by KID
    # _res vars are 2D arrays: one 1D array per resonator
  
    d = np.diff(y_res)
    n = np.sum(d>tol)                    # > tol count
    # how do we decide on a reasonable tol?
    # will it be consistent?
    # with only 2 measurements per KID it's hard to normalize...
    
    if n > dtol:
        print(f"{n} detectors over tolerance. Running full loop.")
        fullLoop()
    else:
        print(f"{n} detectors over tolerance (<dtol). Done.")
