
#####################
# Global attributes #
#####################
try:
    import _cfg_board as cfg
    import alcove_commands.board_io as io
    import xrfdc
    from pynq import Overlay
    firmware = Overlay("single_chan_4eth_v8p2.bit",ignore_version=True, download=False)
except Exception as e: 
    firmware = None
    print(f"Error loading firmware: {e}")


######################
# Internal Functions #
######################


def set_NCLO(lofreq):

    import xrfdc
    
    rf_data_conv = firmware.usp_rf_data_converter_0
    rf_data_conv.adc_tiles[0].blocks[0].MixerSettings['Freq']=lofreq
    rf_data_conv.dac_tiles[1].blocks[3].MixerSettings['Freq']=lofreq
    rf_data_conv.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
    rf_data_conv.dac_tiles[1].blocks[3].UpdateEvent(xrfdc.EVENT_MIXER)


def phase_shift(ts, phase):

    import numpy as np

    y = ts*np.exp(1j*phase)
    return ts.real + 1j*y.imag


def norm_wave(ts, max_amp=2**15-1):
    '''Re-configure generated data values to fit LUT'''

    # Imax = max(abs(ts.real))
    # Qmax = max(abs(ts.imag))
    norm = max(abs(ts))
    dacI = ((ts.real/norm)*max_amp).astype("int16")
    dacQ = ((ts.imag/norm)*max_amp).astype("int16")
    return dacI, dacQ


def genWaveform(freq_list, vna=False, verbose=False):
    '''Takes a list of specified frequencies and generates....stuff and things, then 
    uploads to the bram.
    
    params
        freq_list: np.array
            list of tones to generate [Hz]
        verbose: bool
            enable / disable printing (and or) plotting of data'''
    
    import numpy as np

    # HARDCODED LUT PARAMS
    addr_size=18   # address bit width
    channels= 2    # data points per memory address for DAC
    fs = 1024e6    # sampling rate of D/A, FPGA fabric = fs/2
    C=2            # decimation factor
    data_p = channels*2**(addr_size) # length of timestream or length of LUT+1
    
    #  SET FREQ for LUT
    if vna:
        N = 1000 # number of tones to make
        #freqs = -1*C*np.linspace(-250.0e6, 250.0e6,N) # equally spaced tones
        freqs_up = 1*C*np.linspace(-251e6,-1e6, N//2)
        freqs_lw = 1*C*np.linspace(2.15e6,252.15e6,N//2)
        freqs = np.append(freqs_up,freqs_lw)
        #freqs = freqs_up
    else:
        freqs = C*freq_list # equally spaced tones
    phases = np.random.uniform(-np.pi,np.pi,len(freqs))
    
    # DAC Params
    A = 2**15-1 # 16 bit D/A, expecting signed values.
    freq_res = fs/data_p # Hz
    fftbin_bw = 500e3 # Hz for effective bandwidth of 512MHz/1024 point fft on adc
    if verbose:
        print(freq_res)
    
    # GENERATE LUT WAVEFORM FROM FREQ LIST
    freqs = np.round(freqs/(freq_res))*freq_res

    if verbose:
        print("{} Frequencies Generated:".format(len(freqs)))
        print(freqs/C*1e-6)

    delta = np.zeros(data_p,dtype="complex") # empty array of deltas
    fft_bin_nums=np.zeros(len(freqs),dtype=int) # array of all dac bin index
    for i in range(len(freqs)):
        bin_num = np.round((freqs[i]/freq_res)).astype('int')
        fft_bin_nums[i]=(np.round((freqs[i]/fftbin_bw/C)).astype('int'))*C
        delta[bin_num] = np.exp(1j*phases[i]) 
    ts = np.fft.ifft(delta)

    # GENERATE DDC WAVEFORM FROM BEAT FREQS
    f_fft_bin = fft_bin_nums*fftbin_bw
    f_beat = (freqs/C - f_fft_bin/C)
    
    if verbose:
        print("\nBeat Frequencies:")
        print(f_beat)
        print(freqs/C)
    
    # new DDC
    wave_ddc = np.zeros( int(data_p), dtype="complex") # empty array of deltas
    delta_ddc = np.zeros( shape=(len(freqs),2**9), dtype="complex") # empty array of deltas
    beat_ddc = np.zeros(shape=(len(freqs),2**9), dtype="complex")
    bin_num_ddc = np.round(f_beat*2/freq_res) # factor of 2 for half a bin width
    
    if verbose:
        print("bin num ddc "+str(bin_num_ddc))

    for i in range(len(freqs)): 
        delta_ddc[i,int(bin_num_ddc[i])] = np.exp(-1j*phases[i])
        beat_ddc[i] = np.conj(np.fft.ifft(delta_ddc[i]))
        
    for i in range(1024):
        if (i<len(freqs)):
            wave_ddc[i::1024] = beat_ddc[i]
        else:
            wave_ddc[i::1024] = 0
    
    dacI, dacQ = norm_wave(ts)
    ddcI, ddcQ = norm_wave(wave_ddc, max_amp=(2**13)-1)

    return dacI, dacQ, ddcI, ddcQ, freqs


def load_DAC(wave_real, wave_imag, verbose=False):

    from pynq import MMIO
    import numpy as np

    base_addr_DAC_I = 0x0400000000
    base_addr_DAC_Q = 0x0400100000
    mem_size = 262144*4 # 32 bit address slots
    mmio_bramI = MMIO(base_addr_DAC_I,mem_size)
    mmio_bramQ = MMIO(base_addr_DAC_Q,mem_size)
    I0, I1 = wave_real[0::2], wave_real[1::2]
    Q0, Q1 = wave_imag[0::2], wave_imag[1::2]
    dataI = ((np.int32(Q1) << 16) + I1).astype("int32")
    dataQ = ((np.int32(Q0) << 16) + I0).astype("int32")
    mmio_bramI.array[0:262144] = dataI[0:262144]
    mmio_bramQ.array[0:262144] = dataQ[0:262144]

    if verbose:
        print("DAC waveform uploaded to AXI BRAM")


def load_DDS(wave_real, wave_imag, verbose=False):
    
    from pynq import MMIO
    import numpy as np

    base_addr_DDS_I = 0x0080000000
    base_addr_DDS_Q = 0x0080100000
    mem_size = 262144*4 # 32 bit address slots
    mmio_bramI = MMIO(base_addr_DDS_I,mem_size)
    mmio_bramQ = MMIO(base_addr_DDS_Q,mem_size)
    I0, I1 = wave_real[0::2], wave_real[1::2]
    Q0, Q1 = wave_imag[0::2], wave_imag[1::2]
    dataI = ((np.int32(I1) << 16) + I0).astype("int32")
    dataQ = ((np.int32(Q1) << 16) + Q0).astype("int32")
    mmio_bramI.array[0:262144] = dataI[0:262144]
    mmio_bramQ.array[0:262144] = dataQ[0:262144]

    if verbose:
        print("DDC waveform uploaded to AXI BRAM")
    

def load_bin_list(freqs, verbose=False):

    import numpy as np

    bin_list = np.int64( np.round(freqs/1e6) )

    if verbose:
        print("bin_list:"+str(bin_list))

    # DSP REGS
    dsp_regs = firmware.dsp_regs_0
    # 0x00 -  fft_shift[9 downto 0], load_bins[22 downto 12], lut_counter_rst[11 downto 11] 
    # 0x04 -  bin_num[9 downto 0]
    # 0x08 -  accum_len[23 downto 0], accum_rst[24 downto 24], sync_in[26 downto 26] (start dac)
    # 0x0c -  dds_shift[8 downto 0]
    
    # initialization 
    sync_in = 2**26
    accum_rst = 2**24  # (active low)
    accum_length = (2**19)-1
    
    # Load DDC bins
    offs=0
    
    # only write tones to bin list
    for addr in range(1024):
        if addr<(len(bin_list)):
            if verbose:
                print("addr = {}, bin# = {}".format(addr, bin_list[addr]))
            dsp_regs.write(0x04,int(bin_list[addr]))
            dsp_regs.write(0x00, ((addr<<1)+1)<<12)
            dsp_regs.write(0x00, 0)
        else:
            dsp_regs.write(0x04,0)
            dsp_regs.write(0x00, ((addr<<1)+1)<<12)
            dsp_regs.write(0x00, 0)
    
    
def load_waveform_into_mem(freqs, dac_r,dac_i,dds_r,dds_i):

    from time import sleep

    # Load configured LUT values into FPGA memory
    
    # Arming DDC Waveform
    dsp_regs = firmware.dsp_regs_0
    # 0x00 -  fft_shift[9 downto 0], load_bins[22 downto 12], lut_counter_rst[11 downto 11] 
    # 0x04 -  bin_num[9 downto 0]
    # 0x08 -  accum_len[23 downto 0], accum_rst[24 downto 24], sync_in[26 downto 26] (start dac)
    # 0x0c -  dds_shift[8 downto 0]
    # initialization  
    sync_in = 2**26
    accum_rst = 2**24  # (active rising edge)
    accum_length = (2**19)-1 # (2**18)-1
    
    fft_shift=0
    if len(freqs)<400:
        fft_shift = 2**9-1
    else:
        fft_shift = 2**5-1 #2**2-1
    
    # WRITING TO DDS SHIFT
    dsp_regs.write(0x0c,262)
    dsp_regs.write(0x08,accum_length)
    
    # reset DAC/DDS counter
    dsp_regs.write(0x00, 2**11) # reset dac/dds counter
    dsp_regs.write(0x00, 0) # reset dac/dds counter
    dsp_regs.write(0x08,accum_length | accum_rst)
    
    load_DAC(dac_r,dac_i)
    load_DDS(dds_r,dds_i)
    sleep(.5)
    dsp_regs.write(0x00, fft_shift) # set fft shift
    ########################
    dsp_regs.write(0x08, accum_length | sync_in)
    sleep(0.5)
    dsp_regs.write(0x08, accum_length | accum_rst | sync_in)

    return 0


def get_snap_data(mux_sel):

    import numpy as np
    from pynq import MMIO

    # WIDE BRAM
    axi_wide = firmware.axi_wide_ctrl# 0x0 max count, 0x8 capture rising edge trigger
    max_count = 32768
    axi_wide.write(0x08, mux_sel<<1) # mux select 0-adc, 1-pfb, 2-ddc, 3-accum
    axi_wide.write(0x00, max_count - 16) # -4 to account for extra delay in write counter state machine
    axi_wide.write(0x08, mux_sel<<1 | 0)
    axi_wide.write(0x08, mux_sel<<1 | 1)
    axi_wide.write(0x08, mux_sel<<1 | 0)
    base_addr_wide = 0x00_A007_0000

    # For simple peripherals with a small number of memory accesses, or where performance is not critical, MMIO is usually sufficient for most developers. If performance is critical, or large amounts of data need to be transferred between PS and PL, using the Zynq HP interfaces with DMA IP and the PYNQ DMA class may be more appropriate.
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
        Q[0::2] = q0
        Q[1::2] = q1
        I[0::2] = i0
        I[1::2] = i1
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
        Q[0::2] = q0
        Q[1::2] = q1
        I[0::2] = i0
        I[1::2] = i1
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
    
    return I, Q

# single_chan.sweep replacement

def sweep(f_center, freqs, N_steps, chan_bandwidth=None):
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

    if chan_bandwidth:         # LO bandwidth given
        bw = chan_bandwidth    # MHz
    else:                      # LO bandwidth is tone difference
        bw = np.diff(freqs)[0]/1e6 # MHz
    # flos = np.arange(f_center-bw/2., f_center+bw/2., bw/N_steps)
    flos = np.linspace(f_center-bw/2., f_center+bw/2., N_steps)
    
    def _Z(lofreq, Naccums=5):
        set_NCLO(lofreq)       # update mixer LO frequency
        # get accum data Naccums times and take median
        # this is done to deal with a periodically dirty signal
        # we don't understand why this happens
        IQ = [getSnapData(3) for i in range(Naccums)] 
        Imed,Qmed = np.median(IQ, axis=0)
        Z = Imed + 1j*Qmed     # convert I and Q to complex
        return Z[0:len(freqs)] # only return relevant slice
    
    # loop over _Z for each LO freq
    # and flatten
    Z = np.array([_Z(lofreq) for lofreq in flos]).T.flatten()
    
    # build and flatten all bin frequencies
    f = np.array([flos*1e6 + ftone for ftone in freqs]).flatten()

    return (f, Z)


def variationInS21m(S21m):
    '''Find small signal variation in S21 complex modulus.
    S21m: 1D array of S21 complex modulus floats.
    This has only been tested on fake data with <2000 resonators.'''

    import numpy as np

    w = 10                      # min of 10 for reasonable results
    l = len(S21m)
    while l%w != 0:             # need w to be a factor of len(S21m) for reshape
        w += 1
        if w>l: raise("Error: No width found!")

    x = np.reshape(S21m, (len(S21m)//w, w))

    vars = np.std(x, axis=1)    # variation in each bin
    var = np.median(vars)       # median of variations
    
    return var

def resonatorIndicesInS21(Z):
    """
    Find the indices in given complex S21 values for resonator peaks.
    Z: Complex S21 values.
    """

    import numpy as np
    import scipy.signal

    # complex modulus
    sig = -np.abs(Z)              # find_peaks looks at positive peaks

    var  = variationInS21m(sig)
    prom = 10*var

    i_peaks = scipy.signal.find_peaks(
        x          = sig,       
        prominence = prom,        # 
        height     = (np.nanmin(sig), np.nanmax(sig)-prom)
    )[0]                          # [0] is peaks, [1] is properties

    return i_peaks


def toneFreqsAndAmpsFromSweepData(f, Z, amps, N_steps):
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

def writeVnaComb():

    import numpy as np

    LUT_I, LUT_Q, DDS_I, DDS_Q, freqsx2 = genWaveform(np.linspace(20.2e6,50.0e6,1), vna=True, verbose=False)
    load_bin_list(freqsx2)
    load_waveform_into_mem(freqsx2, LUT_I, LUT_Q, DDS_I, DDS_Q)

    io.save(io.file.freqs_vna, freqsx2/2.)


def writeTargComb():
    
    targ_freqs = io.load(io.file.f_res_vna)
    f_center   = io.load(io.file.f_center_vna)

    LUT_I, LUT_Q, DDS_I, DDS_Q, freqsx2 = genWaveform( targ_freqs.real-f_center, vna=False, verbose=False)
    load_bin_list(freqsx2)
    load_waveform_into_mem(freqsx2, LUT_I, LUT_Q, DDS_I, DDS_Q)


def writeTestTone():

    import numpy as np

    LUT_I, LUT_Q, DDS_I, DDS_Q, freqsx2 = genWaveform(np.linspace(20.2e6,50.0e6,1), vna=False, verbose=False)
    load_bin_list(freqsx2)
    load_waveform_into_mem(freqsx2, LUT_I, LUT_Q, DDS_I, DDS_Q)


def writeLoChopComb():

    targ_freqs = io.load(io.file.f_res_targ)
    f_center   = io.load(io.file.f_center_targ)

    LUT_I, LUT_Q, DDS_I, DDS_Q, freqsx2 = genWaveform(targ_freqs.real-f_center, vna=False, verbose=False)
    load_bin_list(freqsx2)
    load_waveform_into_mem(freqsx2, LUT_I, LUT_Q, DDS_I, DDS_Q)


def getAdcData():
    return get_snap_data(0)


def getSnapData(mux_sel):
    return get_snap_data(int(mux_sel))


def vnaSweep(f_center=600):
    """
    vnaSweep: perform a stepped frequency sweep centered at f_center \\
            save result as s21.npy file

    f_center: center frequency for sweep in [MHz]
    """

    import numpy as np

    f_center = int(f_center)
    freqs = io.load(io.file.freqs_vna)

    writeVnaComb()

    s21 = np.array(sweep(f_center, freqs, N_steps=500)) # f, Z

    io.save(io.file.s21_vna, s21)
    io.save(io.file.f_center_vna, f_center*1e6)

    return (s21)


def findResonators():
    """
    Find the resonator peak frequencies in previously saved s21.npy file.
    """
    
    import numpy as np

    # load S21 complex mags (Z) and frequencies (f) from file
    f, Z = np.load(f'{cfg.drone_dir}/s21.npy')

    i_peaks = resonatorIndicesInS21(Z)
    f_res = f[i_peaks]

    io.save(io.file.f_res_vna, f_res)


def targetSweep(f_res=None, f_center=600, N_steps=500, chan_bandwidth=0.2, amps=None, save=True):
    """
    Perform a sweep around resonator tones and identify resonator frequencies and tone amplitudes.
    
    f_res:           (1D array of floats) Current comb tone frequencies [Hz].
    f_center:        (float) Center LO frequency for sweep [MHz].
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    chan_bandwidth:  (float) Channel bandwidth [MHz].
    amps:            (1D array of floats) Current normalized tone amplitudes.

    Return:          (2-tuple) Characterized resonator frequencies and normalized tone amplitudes.
    """

    import numpy as np

    if f_res is None:
        try:
            f_res = np.load(f'{cfg.drone_dir}/f_res.npy')
        except:
            raise("Required file missing: f_res.npy. Perform a vna sweep first?")

    if amps is None:
        amps = np.ones_like(f_res)
    
    writeTargComb()

    # load S21 complex mags (Z) and frequencies (f) from file
    f, Z  = sweep(f_center, f_res, N_steps, chan_bandwidth)
    
    freqs, A_res = toneFreqsAndAmpsFromSweepData(f, Z, amps, N_steps)

    if save:
        io.save(io.file.f_res_targ, freqs)
        io.save(io.file.a_res_targ, amps)
        io.save(io.file.f_center_targ, f_center*1e6)

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
    
    try: # current resonance frequencies
        freqs = np.load(f'{cfg.drone_dir}/f_res.npy') # f'{cfg.drone_dir}/f_res.npy'
    except:
        raise("Required file missing: f_res.npy. Perform a vna sweep first?")

    try: # current channel amplitudes
        amps = np.load(f'{cfg.drone_dir}/amps.npy')
        if len(amps) != len(freqs): # could be an old file... how to deal with?
            raise NameError("amps.npy and f_res.npy are not the same length!")
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
    
    def retry(f, s, **params):
        for _ in range(max_loops_funcs):
            try: print(s+"...", end=""); f(**params)
            except Exception as e: fail(e)
            else: success(); return True
        raise Exception("Retry failed.") 
    def success(): print(" Done."); return True
    def fail(e):
        print(CFL.strcol('red', ' FAILED!'))
        if verbose: print(CFL.strcol('red', e))
    def fullFail(l): print(f"\n* Full loop failed ({l}).")
    def fullSuccess(l): print(f"\n* Full loop complete ({l}).")
    
    for l in range(max_loops_full)
            
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
    
    freqs = io.load(io.file.f_res_targ)
    
    # if this comb is already set we could bypass this step for efficiency
    # how can we know?
    writeLoChopComb() 
    
    N_steps = 2                          # 2 symmetric points
    f, Z  = sweep(f_center, freqs, N_steps=N_steps, chan_bandwidth=2*freq_offset)
    
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