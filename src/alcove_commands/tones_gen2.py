# ============================================================================ #
# tones_gen2.py
# Tone and comb functions and commands.
# Compatible with gateware versions 15+ (gen2).
# James Burgoyne jburgoyne@phas.ubc.ca 
# Adrian Sinclair aksincla@asu.edu
# CCAT Prime 2025  
# ============================================================================ #

import numpy as np

from alcove_commands import alcove_base
import alcove_commands.board_io as io

try: from config import board as cfg_b
except ImportError: cfg_b = None 



# ============================================================================ #
# _gateware_chan
def _gateware_chan(gateware, chan):
    return {
        1: gateware.chan1,
        2: gateware.chan2,
        3: gateware.chan3,
        4: gateware.chan4,
    }[chan]


# ============================================================================ #
# setAccumLength
def setAccumLength():
    """
    Sets the accumulation length in the DSP registers, determining sample rate.

    This function configures the `accum_len` register within the DSP registers, 
    which controls the clock division and consequently the detector sample rate. 

    Note:
        - The function relies on `cfg_b.gateware`, `cfg_b.drid`, 
          and `cfg_b.accum_len`.
        - The DSP register layout is as follows:
            - 0x00: fft_shift[9:0], load_bins[22:12], lut_counter_rst[11]
            - 0x04: bin_num[9:0]
            - 0x08: accum_len[23:0], accum_rst[24], sync_in[26] (start dac)
            - 0x0c: dds_shift[8:0]
        - The clock source is assumed to be 512 MHz.
    """

    dsp_regs = _gateware_chan(cfg_b.gateware, cfg_b.drid).dsp_regs_0
    dsp_regs.write(0x08, cfg_b.accum_len)


# ============================================================================ #
# _resetAccumAndSync
def _resetAccumAndSync(chan, freqs):
    '''Resets the accumulator and synchronizes the DAC.

    chan: The channel identifier (not used anymore - backwards compatible).
    freqs (list or numpy.ndarray): A list or array of frequencies, used to determine the FFT shift value.
    '''

    dsp_regs = _gateware_chan(cfg_b.gateware, cfg_b.drid).dsp_regs_0

    fft_shift    = 2**9-1 if len(freqs)<400 else 2**5-1
    dsp_regs.write(0x00, fft_shift)

    # TODO: the following unused in v>=14?
    sync_in      = 2**26
    accum_length = cfg_b.accum_len # e.g. 2**19-1
    dsp_regs.write(0x08, accum_length)
    dsp_regs.write(0x08, accum_length | sync_in)

    # accum_rst = 2**24  # (active rising edge)
    # dsp_regs.write(0x08, accum_length | accum_rst | sync_in)

    # DDS shift
    dsp_regs.write(0x0c, 180) # 260)


# ============================================================================ #
# _loadBinList
def _loadBinList(chan, freq_list):

    import numpy as np

    fs = 512e6 # cfg_b.wf_fs
    lut_len = 2**20 # cfg_b.wf_lut_len
    fft_len = 1024 # cfg_b.wf_fft_len
    k = np.int64(np.round(-freq_list/(fs/lut_len)))
    freq_actual = k*(fs/lut_len)
    bin_list = np.int64(np.round(freq_actual / (fs / fft_len)))
    pos_bin_idx = np.where(bin_list > 0)
    if np.size(pos_bin_idx) > 0:
        bin_list[pos_bin_idx] = fft_len - bin_list[pos_bin_idx]
    bin_list = np.abs(bin_list)

    dsp_regs = _gateware_chan(cfg_b.gateware, cfg_b.drid).dsp_regs_0
    # gateware.chan1.dsp_regs_0

    # only write tones to bin list
    for addr in range(fft_len):
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


# ============================================================================ #
# _loadDdr4
def _loadDdr4(chan, wave_real, wave_imag, dphi):

    import numpy as np
    from pynq import MMIO

    base_addr_dphis = {
        1: 0xa004c000,
        2: 0xa0040000,
        3: 0xa0042000,
        4: 0xa004e000,
    }[chan]
    
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
    ddr4mux = cfg_b.gateware.axi_ddr4_mux
    ddr4mux.write(8,0) # set read valid 
    ddr4mux.write(0,0) # mux switch
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


# ============================================================================ #
# genAmpsAndPhis
def genAmpsAndPhis(freqs, amp_max=(2**15-1), phase_trials=5):  
    '''
    Generates amplitudes and optimized phases for a set of frequencies to minimize waveform peak.

    This function calculates amplitudes and phases for a set of sinusoidal components with given frequencies, aiming to reduce the peak amplitude of the resulting composite waveform. It initializes amplitudes with equal values and then iteratively searches for optimal phases by randomly sampling and evaluating
    the waveform's peak.

    Args:
        freqs (numpy.ndarray): An array of frequencies (Hz) for the sinusoidal components.
        amp_max (int, optional): The maximum allowed amplitude for the waveform. Defaults to (2**15-1).
        phase_trials (int, optional): The number of random phase sets to try. Defaults to 5.

    Returns:
        tuple: A tuple containing:
            - amps (numpy.ndarray): An array of calculated amplitudes.
            - best_phis (numpy.ndarray): An array of optimized phases (radians).

    Notes:
        - Phases are randomly sampled within the range [-pi, pi].
    '''

    import numpy as np
    
    # number of tones
    N = len(freqs) 

    # assuming equal amplitudes
    amps = np.ones(N)*(amp_max/np.sqrt(N))
    
    # waveform peak
    def ampPeak(freqs, amps, phis):
        x,_,_ = alcove_base.generateWaveDdr4(freqs, amps, phis)
        return np.max(np.abs(x.real + 1j*x.imag))
    
    # sample random phases, choose best
    best_peak = float('inf')
    best_phis = None
    for _ in range(phase_trials):
        phis = np.random.uniform(-np.pi, np.pi, N)
        peak = ampPeak(freqs, amps, phis)
        if peak < best_peak:
            best_peak = peak
            best_phis = phis
            
    # scale amps with best phase solution so less than amp_max
    amps *= (amp_max/best_peak)
    return amps, best_phis


# ============================================================================ #
# genVariedAmpsAndPhis
def genVariedAmpsAndPhis(freqs, amp_max=(2**15-1)):
    """Generate lists of (varied) amplitudes and phases.
    Varied means that each tone has a unique amplitude.

    freqs: 1D float array of resonator frequencies.
    amp_max: Maximum allowable time stream amplitude.
    """

    return genAmpsAndPhis(freqs, amp_max=amp_max)


# ============================================================================ #
# _waveAmpTest
def _waveAmpTest(wave, max_amp=2**15-1):
    import numpy as np
    maximum = np.max(np.abs(wave))
    print(f"max amplitude {maximum:.10f}")


def _genWave(freqs, amps, phis, fs=1.024e9, lut_len=2**21):
    '''
    Generates a waveform based on requested frequencies, magnitudes, and phases, using np.fft.ifft
    
    Notes:
        Since 2-octave firmware use PSB to synthesize wave, this is only used for genAmpsAndPhis.
    '''
    freqs = np.real(freqs)
    amps  = np.real(amps)
    phis  = np.real(phis)
    
    # Compute frequency bins
    bin_num      = np.round(freqs/(fs/lut_len)).astype(np.int64)
    freqs_actual = bin_num*(fs/lut_len)
    
    # Vectorized X assignment (frequency space)
    X    = np.zeros(lut_len, dtype=np.complex128)
    X[bin_num] = np.exp(-1j*phis)*amps
    
    # Compute IFFT
    x = np.fft.ifft(X, norm='backward')*lut_len
    
    return x, freqs_actual


def _wrap_angle(angle):
    '''
    Args:
        angle (float):
            An angle in [rad].
    Returns:
        (float):
            An equavalent angle within the range [-pi,pi].
    '''
    return np.arctan2(np.sin(angle), np.cos(angle))


def _rad2int(angle_rad):
    '''
    Convert any angle in rad to the uint16 representation in unit [pi rad]
    '''
    wrap = _wrap_angle(angle_rad)
    i16 = np.int16(np.round((wrap / np.pi) * 2**15))
    actual = i16 * (np.pi / 2**15)
    return i16.astype(np.uint16), actual


def get_safe_frequencies(freqs):
    freqs = np.asarray(freqs)

    # Filter range
    freqs = freqs[(freqs >= -cfg_b.fs/2) & (freqs <= cfg_b.fs/2)]

    # nothing in range, end early
    if freqs.size == 0:
        return freqs

    # bin_size = 5e5
    bin_size = cfg_b.fs/cfg_b.psb_channel_count

    # Bin index + sort by bin
    bins = np.floor((freqs + bin_size/2) / bin_size).astype(np.int64)
    order = np.argsort(bins)
    freqs = freqs[order]
    bins  = bins[order]

    # Find start of each new bin
    starts = np.r_[0, np.flatnonzero(bins[1:] != bins[:-1]) + 1]

    # Corresponding ends (inclusive)
    ends = np.r_[starts[1:] - 1, freqs.size - 1]
    idxs = np.unique(np.r_[starts, ends]) # avoid duplicates

    return freqs[idxs]


def _writeToneSelect(chan, addr, data):
    '''
    Updates toneSelect parameter memory at one address
    
    Args:
        chan (int): 
            Channel index (1–4) specifying which readout chain to access.
        addr (uint): 
            The address of the write operation.
        data (ufix_12):
            The data of the write operation.
    '''
    chan_access = _gateware_chan(cfg_b.gateware, chan)
    
    gpio_6_slot_2_word = int(addr)
    chan_access.GPIO.axi_gpio_6.write(0x08,gpio_6_slot_2_word)
    
    gpio_7_slot_1_word = int((data[1] << 12) + data[0])
    chan_access.GPIO.axi_gpio_7.write(0x00,gpio_7_slot_1_word)
    gpio_7_slot_2_word = int((data[3] << 12) + data[2])
    chan_access.GPIO.axi_gpio_7.write(0x08,gpio_7_slot_2_word)
    gpio_8_slot_1_word = int((data[5] << 12) + data[4])
    chan_access.GPIO.axi_gpio_8.write(0x00,gpio_8_slot_1_word)
    gpio_8_slot_2_word = int((data[7] << 12) + data[6])
    chan_access.GPIO.axi_gpio_8.write(0x08,gpio_8_slot_2_word)
    
    chan_access.GPIO.axi_gpio_6.write(0x00,0)
    chan_access.GPIO.axi_gpio_6.write(0x00,1)
    chan_access.GPIO.axi_gpio_6.write(0x00,0)


def _writeToneSelectAll(chan, ToneSelMap):
    '''
    Updates the entire toneSelect LUT from ToneSelMap
    
    Args:
        chan (int): 
            Channel index (1-4) specifying which readout chain to access.
        ToneSelMap (numpy.ndarray):
            The toneSelect LUT.
    '''
    for i in range(256):
        _writeToneSelect(chan, i, ToneSelMap[i])


def genInitToneSelMap():
    '''
    Generate a default tone select mapping LUT for initialization/reset.
    
    Returns:
        toneSelectMap (numpy.ndarray)
    '''
    toneSelectMap = np.arange(2048, dtype=np.uint16).reshape((256,8))
    for i in range(8):
        addr = np.arange(256, dtype=np.uint16)
        para = np.ones(256, dtype=np.uint16) * i
        onoff = np.ones(256, dtype=np.uint16)
        toneSelectMap[:, i] = addr << 4 | para << 1 | onoff
    return toneSelectMap


def _updateToneSelMap(chan, toneSelectInfo, turn_off_unused_bin=True):
    """
    Update toneSelMap based on 2-tone bin reuse mapping.
    """
    toneSelectMap = genInitToneSelMap()
    twoTone_bins, unused_bins = toneSelectInfo
    r_tw, c_tw = divmod(twoTone_bins, 8)
    r_un, c_un = divmod(unused_bins, 8)
    toneSelectMap[r_tw, c_tw] = toneSelectMap[r_un, c_un]

    if turn_off_unused_bin:
        toneSelectMap[r_un, c_un] = 0

    _writeToneSelectAll(chan, toneSelectMap)


def _writeBinMap(chan, addr, data):
    '''
    Write to firmware registers via GPIO.
    Updates the bin select mapping (LUT) in the receive.
    
    Args:
        chan (int): 
            Channel index (1–4) specifying which readout chain to access.
        addr (uint): 
            The address of the write operation.
        data (ufix_22):
            The data of the write operation.
            
    Notes:
        The bin map RAM are accecced 2 addrs at a time, 
        only the first addr need to be supplied, each addr take two values
        each 11 bits concatenated.
        For example, if addr=n, then 
        concact(data[1],data[0])LSB -> addr n
        concact(data[3],data[2])LSB -> addr n+1
    '''
    chan_access = _gateware_chan(cfg_b.gateware, chan)
    
    gpio_9_slot_1_word = int((data[1]<<21) + (data[0]<<10) + addr)
    chan_access.GPIO.axi_gpio_9.write(0x00, gpio_9_slot_1_word)
    gpio_9_slot_2_word = int((data[3]<<12) + (data[2]<<1) + 0)
    chan_access.GPIO.axi_gpio_9.write(0x08, gpio_9_slot_2_word)
    
    gpio_9_slot_2_word = int((data[3]<<12) + (data[2]<<1) + 1)
    chan_access.GPIO.axi_gpio_9.write(0x08, gpio_9_slot_2_word)
    gpio_9_slot_2_word = int((data[3]<<12) + (data[2]<<1) + 0)
    chan_access.GPIO.axi_gpio_9.write(0x08, gpio_9_slot_2_word)


def _loadBinMap(chan, bin_map):
    '''
    Updates the bin select mapping (LUT) in the receive.
    
    Args:
        chan (int): 
            Channel index (1–4) specifying which readout chain to access.
        bin_map (numpy.ndarray):
            Array of bin select mapping LUT.
    '''
    bin_map_reshape = bin_map.reshape((512, 4))
    for i in range(512):
        _writeBinMap(chan, 2*i, bin_map_reshape[i])


def _writeBeatDphi(chan, mem, addr, beatDphi):
    '''
    Write to firmware registers via GPIO.
    Updates the beat frequencies corresponding to each tone, 
    for the digital down conversion (DDC) in receive.
    
    Args:
        chan (int): 
            Channel index (1–4) specifying which readout chain to access.
        mem (int {0,1,2,3}):
            An index that maps to one of the 4 BRAMs on 4 parallel paths.
        addr (uint): 
            The address of the write operation.
        beatDphi (float):
            The step in phase that defines the beat frequency, in unit [rad].     
    '''
    chan_access = _gateware_chan(cfg_b.gateware, chan)
    
    beatDphi_write,_ = _rad2int(beatDphi)
    gpio_4_slot_1_word = int((addr << 20) + (beatDphi_write << 4))
    
    chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word)
    if mem == 0:
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word + 2**0)
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word)
    elif mem == 1:
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word + 2**1)
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word)
    elif mem == 2:
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word + 2**2)
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word)
    elif mem == 3:
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word + 2**3)
        chan_access.GPIO.axi_gpio_4.write(0x00,gpio_4_slot_1_word)


def _loadBeatDphiMap(chan, beat_dphi_map):
    '''
    Updates the beat frequencies corresponding to each tone, 
    for the digital down conversion (DDC) in receive.
    
    Args:
        chan (int): 
            Channel index (1–4) specifying which readout chain to access.
        beat_dphi_map (numpy.ndarray):
            beat dphi LUT values.
    '''
    beat_dphi_map_reshape = beat_dphi_map.reshape((512, 4))
    for addr in range(512):
        for mem in range(4):
            _writeBeatDphi(chan, mem, addr, beat_dphi_map_reshape[addr, mem])


def _loadAllTones(chan, bin_num, dphi, init_re, init_im):
    '''
    Writes all tones listed in 1darrays
    
    Args:
        chan (int): 
            Channel index (1–4) specifying which readout chain to access.
        bin_num (int);
            The FFT bin number of which the tone is in.
        dphi (float): 
            The step in phase which defines the frequency of the tone from bin center.
            Note: In unit [rad]
        init_re (float),
        init_im (float): 
            The real and imarinary parts of the initial vector.
            Note: The maximum magnitude of the initial vector is 1.
    
    '''
    for i in range(bin_num.size):
        _writeTone(chan, bin_num[i]%8, bin_num[i]//8, dphi[i], init_re[i], init_im[i])


def _writeTone(chan, mem, addr, dphi, init_re, init_im):
    """
    Writes one tone defined by its frequency (dphi) and initial vector (init_re, init_im).
    """

    # TODO:
    print(f"_writeTone")

    if not (0 <= mem <= 7):
        return

    chan_access = _gateware_chan(cfg_b.gateware, chan)

    chan_access.GPIO.axi_gpio_2.write(0x00, int(round(init_re*(1 << 16))) & 0x3FFFF)
    chan_access.GPIO.axi_gpio_2.write(0x08, int(round(init_im*(1 << 16))) & 0x3FFFF)

    # TODO:
    print(f"_wrap_angle next")

    if mem & 1:  # mem odd: add π
        dphi = _wrap_angle(dphi + np.pi)
    dphi_int, _ = _rad2int(dphi)

    # word = (addr << 16) | dphi_int
    word = int((addr << 16) + dphi_write)
    bit_value = [1,16,2,32,4,64,8,128][mem]

    # TODO:
    print(f"writes next next")
    print(f"word = {word}")
    print(f"Type of word: {type(word)}")
    
    chan_access.GPIO.axi_gpio_1.write(0x08, word)

    # TODO:
    print(f"bit_value = {bit_value}")

    chan_access.GPIO.axi_gpio_1.write(0x00, bit_value)
    chan_access.GPIO.axi_gpio_1.write(0x00, 0)

    # TODO:
    print(f"_writeTone done")



# ============================================================================ #
# _writeComb
def _writeComb(chan, freqs, amps, phi, save=True):
    '''
    '''

    freqs = get_safe_frequencies(freqs)

    f_step = cfg_b.fs/cfg_b.lut_len
    freqs_actual = np.round(freqs / (f_step)) * f_step
    
    bin_step = cfg_b.fs/cfg_b.psb_channel_count
    bin_num = np.round(freqs_actual/bin_step).astype(np.int64)
    
    # dphi/2pi ratio corresponds to the channel bandwidth of PSB which is 2*fs/2048
    dphi = _wrap_angle(np.pi*(freqs_actual/bin_step - bin_num))
    beat_dphi = _wrap_angle(-2*dphi)  # Careful with different sampling frequency

    bin_num[bin_num < 0] += cfg_b.psb_channel_count # all positive
    
    bin_count = np.bincount(bin_num, minlength=cfg_b.psb_channel_count)

    bin_map = np.zeros(cfg_b.psb_channel_count, dtype=int)
    beat_dphi_map = np.zeros(cfg_b.psb_channel_count, dtype=float)
    beat_dphi_2048 = np.zeros(cfg_b.psb_channel_count, dtype=float)

    # For any two tones per bin instances, the second bin index will be replaced
    # with an unused bin index, and this mapping is saved in toneSelectInfo
    second_tone_index = np.where(np.diff(bin_num)==0)[0] + 1
    if second_tone_index.size > 0:
        secondTone_flag = True
        toneSelectInfo = np.zeros((2,second_tone_index.size), dtype=int)
        toneSelectInfo[0] = bin_num[second_tone_index]
        all_bins = np.arange(cfg_b.psb_channel_count)
        unused_bins = np.setdiff1d(all_bins, bin_num)
        bin_num[second_tone_index] = unused_bins[0:second_tone_index.size]
        toneSelectInfo[1] = bin_num[second_tone_index]
        
        _updateToneSelMap(chan, toneSelectInfo)
        
        beat_dphi_2048[bin_num] = beat_dphi
        temp = beat_dphi_2048[toneSelectInfo[1]]
        beat_dphi_2048[toneSelectInfo[1]] = 0
        beat_dphi_2048_stack = np.vstack([beat_dphi_2048,beat_dphi_2048])
        beat_dphi_2048_stack[1, toneSelectInfo[0]] = temp

        transmit_bin_count = 0
        for i in range(2048):
            if bin_count[i] == 2:
                bin_map[transmit_bin_count] = i
                beat_dphi_map[transmit_bin_count] = beat_dphi_2048_stack[0, i]
                transmit_bin_count += 1
                bin_map[transmit_bin_count] = i
                beat_dphi_map[transmit_bin_count] = beat_dphi_2048_stack[1, i]
                transmit_bin_count += 1
            elif bin_count[i] == 1:
                bin_map[transmit_bin_count] = i
                beat_dphi_map[transmit_bin_count] = beat_dphi_2048_stack[0, i]
                transmit_bin_count += 1
    else:
        secondTone_flag = False
        _writeToneSelectAll(chan, genInitToneSelMap())
        
        beat_dphi_2048[bin_num] = beat_dphi
        transmit_bin_count = 0
        for i in range(2048):
            if bin_count[i] == 1:
                bin_map[transmit_bin_count] = i
                beat_dphi_map[transmit_bin_count] = beat_dphi_2048[i]
                transmit_bin_count += 1

    _loadBinMap(chan, bin_map)
    _loadBeatDphiMap(chan, beat_dphi_map)
    
    Z = amps*np.exp(1.j*phi)

    _loadAllTones(chan, bin_num, dphi, Z.real, Z.imag)

    # TODO:
    # write number of channels to 16 bit value in UDP packet
    # alcove_base.writeChannelCount(len(freqs))

    if save:
        f_center   = io.load(io.file.f_center_vna) # 
        freqs_rf_actual = freqs_actual + f_center

        io.save(io.file.f_rf_tones_comb, freqs_rf_actual)
        io.save(io.file.a_tones_comb, amps)
        io.save(io.file.p_tones_comb, phi)

    return freqs_actual
    # return freqs_actual, bin_map, transmit_bin_count, secondTone_flag


# ============================================================================ #
# writeTestTone
def writeTestTone():

    import numpy as np
    
    chan = cfg_b.drid # drone (chan) id is from config
    freqs = np.array(np.linspace(50e6, 255.00e6, 1))
    amps = np.ones(1)*(2**15 - 1)
    phi=np.array([np.pi])
    freq_actual = _writeComb(chan, freqs, amps, phi)


# ============================================================================ #
# writeNewVnaComb
def writeNewVnaComb(freq_noise=0):
    """Create and write the vna sweep tone comb.

    freq_noise: (float) Frequency noise to add to the tone placement.
        This uses a uniform distribution of noise. [Hz]
    """

    import numpy as np

    freq_noise = float(freq_noise)
    
    chan = cfg_b.drid # drone (chan) id is from config

    freqs_bb = np.array(np.linspace(-254.4e6, 255.00e6, 1000))

    # add some frequency noise (could be useful for evenly spaced tones)
    if freq_noise:
        freqs_bb += np.random.uniform(-freq_noise, freq_noise, len(freqs_bb))

    amps, phis = genAmpsAndPhis(freqs_bb)
    freqs_bb_actual = _writeComb(chan, freqs_bb, amps, phis)
    
    io.save(io.file.freqs_vna, freqs_bb_actual)
    io.save(io.file.amps_vna, amps)
    io.save(io.file.phis_vna, phis)

    return io.returnWrapperMultiple(
        [io.file.freqs_vna, io.file.amps_vna, io.file.phis_vna], 
        [freqs_bb_actual, amps, phis])


# ============================================================================ #
# _writeTargComb
def _writeTargComb(f_center, freqs_rf, amps=None, phis=None, cal_tones=False):
    """Write the target comb from the given frequencies.

    f_center:   (float) Center LO frequency for sweep [Hz].
    freqs_rf:   (1D array of floats) Resonator frequencies [Hz].
    cal_tones:  (bool) Include calibration tones (True).
        Note that findCalTones must be run first.
        Note that this will force new_amps_and_phis=True.
    """

    import numpy as np

    if not isinstance(cal_tones, bool):
        cal_tones = cal_tones == "True" # force to bool; Redis args are strings

    chan = cfg_b.drid

    freqs_bb = freqs_rf - f_center

    if cal_tones:
        f_cal_tones_rf = io.load(io.file.f_cal_tones).real
        freqs_rf = np.append(freqs_rf, f_cal_tones_rf)
        freqs_bb = freqs_rf - f_center
        amps = None # force recalculation of amps and phis with cal tones
        phis = None

    if amps is None or phis is None:
        amps, phis = genVariedAmpsAndPhis(freqs_bb)

    freqs_bb_actual = _writeComb(chan, freqs_bb, amps, phis)
    freqs_rf_actual = freqs_bb_actual + f_center 

    return freqs_rf_actual, amps, phis


# ============================================================================ #
# writeTargCombFromVnaSweep
def writeTargCombFromVnaSweep(cal_tones=False):
    """Write the target comb from the vna sweep resonator frequencies.
    Note that vnaSweep and findVnaResonators must be run first.

    cal_tones:  (bool) Include calibration tones (True) or not (False).
    Note that findCalTones must be run first.
    """

    import numpy as np

    chan = cfg_b.drid

    f_center   = io.load(io.file.f_center_vna) # Hz
    freqs_rf = io.load(io.file.f_res_vna).real
    freqs_bb = freqs_rf - f_center

    amps, phis = genVariedAmpsAndPhis(freqs_bb)

    io.save(io.file.f_res_targ, freqs_rf)
    io.save(io.file.a_res_targ, amps)
    io.save(io.file.p_res_targ, phis)

    freqs_rf_comb, amps_comb, phis_comb = _writeTargComb(
        f_center, freqs_rf, cal_tones=cal_tones)
    # these may have cal_tones added in (not just resonators)

    return io.returnWrapperMultiple(
        [io.file.f_rf_tones_comb, io.file.a_tones_comb, io.file.p_tones_comb], 
        [freqs_rf_comb, amps_comb, phis_comb])


# ============================================================================ #
# writeTargCombFromTargSweep
def writeTargCombFromTargSweep(cal_tones=False, new_amps_and_phis=False):
    """Write the target comb from the target sweep resonator frequencies.
    Note that targSweep and findTargResonators must be run first.

    cal_tones:  (bool) Include calibration tones (True).
        Note that findCalTones must be run first.
        Note that this will force new_amps_and_phis=True.
    new_amps_and_phis: (bool) Generate new amplitudes and phases (True).
    """

    import numpy as np

    chan = cfg_b.drid

    f_center   = io.load(io.file.f_center_vna)
    freqs_rf = io.load(io.file.f_res_targ).real
    amps = io.load(io.file.a_res_targ)
    phis = io.load(io.file.p_res_targ)

    if new_amps_and_phis:   
        amps = None
        phis = None

    freqs_rf_comb, amps_comb, phis_comb = _writeTargComb(
        f_center, freqs_rf, amps, phis, cal_tones=cal_tones)
    # These will include cal tones (if cal_tones=True)
    # not just resonator tones.

    return io.returnWrapperMultiple(
        [io.file.f_rf_tones_comb, io.file.a_tones_comb, io.file.p_tones_comb], 
        [freqs_rf_comb, amps_comb, phis_comb])


# ============================================================================ #
# writeTargCombFromCustomList
def writeTargCombFromCustomList():
    """Write the target comb from the custom tone files:
    alcove_commands/custom_freqs.npy
    alcove_commands/custom_amps.npy
    alcove_commands/custom_phis.npy

    This differs from tones.writeCombFromCustomList only in that it assumes these are resonator frequencies and writes f_res_targ (to be used in a target sweep).
    """

    freqs_rf = io.load(io.file.f_rf_tones_comb_cust)
    io.save(io.file.f_res_targ, freqs_rf)

    return writeCombFromCustomList()

    # chan = cfg_b.drid

    # f_center   = io.load(io.file.f_center_vna)
    # freqs_rf = io.load(io.file.f_rf_tones_comb_cust)
    # amps = io.load(io.file.a_tones_comb_cust)
    # phis = io.load(io.file.p_tones_comb_cust)

    # freqs_bb = freqs_rf - f_center

    # io.save(io.file.f_res_targ, freqs_rf)

    # freqs_bb_comb = _writeComb(chan, freqs_bb, amps, phis)
    # freqs_rf_comb = freqs_bb_comb + f_center

    # return io.returnWrapperMultiple(
    #     [io.file.f_rf_tones_comb, io.file.a_tones_comb, io.file.p_tones_comb], 
    #     [freqs_rf_comb, amps, phis])


# ============================================================================ #
# writeCombFromCustomList
def writeCombFromCustomList():
    """Write the comb from custom tone files:
    alcove_commands/custom_freqs.npy
    alcove_commands/custom_amps.npy
    alcove_commands/custom_phis.npy
    """

    chan = cfg_b.drid

    f_center   = io.load(io.file.f_center_vna)
    freqs_rf = io.load(io.file.f_rf_tones_comb_cust)
    amps = io.load(io.file.a_tones_comb_cust)
    phis = io.load(io.file.p_tones_comb_cust)

    freqs_bb = freqs_rf - f_center
        
    freqs_bb_comb = _writeComb(chan, freqs_bb, amps, phis)
    freqs_rf_comb = freqs_bb_comb + f_center

    return io.returnWrapperMultiple(
        [io.file.f_rf_tones_comb, io.file.a_tones_comb, io.file.p_tones_comb], 
        [freqs_rf_comb, amps, phis])