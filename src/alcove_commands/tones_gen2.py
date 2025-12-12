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
# genPhis
def genPhis(freqs, amps_rel, amp_max=1., phase_trials=5):
    '''
    Generates optimized phases for a tone comb to minimize waveform peak.

    Args:
        freqs (array): Frequencies of the tones. [Hz]
        amps_rel: (array) Relative amplitudes of the tones. 
            These will be scaled so largest = amp_max.
        amp_max (float, default=1): Largest tone amplitude.
            In gen2, amp_max=1 scales the waveform to DAC max.
        phase_trials (int, default=5): The number of random phase sets to try.

    Returns:
        tuple: A tuple containing:
            - amps (array): An real array of scaled amplitudes.
            - phis (array): An real array of optimized phases.
                In radians, [-pi, pi).
    '''
    import numpy as np
    from math import gcd
    from functools import reduce
    from scipy.fft import ifft

    freqs = np.asarray(freqs, float)
    amps_rel  = np.asarray(amps_rel, float)

    N = len(freqs)

    # Map frequencies to bins of the full LUT FFT
    k_full = np.round(freqs * cfg_b.lut_len / cfg_b.fs).astype(np.int64)

    # Compute maximum downsampling factor g = gcd(k_full)
    g = reduce(gcd, k_full)
    if g <= 0:
        # Degenerate cases: at least one bin index is zero
        g = reduce(gcd, k_full[k_full != 0]) if np.any(k_full != 0) else 1

    # Reduced FFT length and bin sizes
    L = cfg_b.lut_len // g
    k = (k_full // g).astype(np.int64)
    unique_k = np.unique(k)

    X = np.zeros(L, dtype=np.complex128) # Preallocate FFT buffer
    best_peak = np.inf
    best_phis = None
    for _ in range(phase_trials):
        # Clear only relevant bins
        X[unique_k] = 0.0

        # Random phases
        phis = np.random.uniform(-np.pi, np.pi, N)

        # Populate spectrum
        X[k] = amps_rel * np.exp(-1j * phis)

        # IFFT at reduced length
        x = L * ifft(X, norm="backward", workers=-1)

        # Peak amplitude
        peak = np.max(np.abs(x))

        if peak < best_peak:
            best_peak = peak
            best_phis = phis
    
    return amp_max*amps_rel/amps_rel.max(), best_phis


# ============================================================================ #
# genAmpsAndPhis
def genAmpsAndPhis(freqs, amp_max=1.0, phase_trials=5):
    '''See genPhis(...)'''

    # equal amplitude tones
    amps = amp_max*np.ones(len(freqs))

    return genPhis(freqs, amps, amp_max, phase_trials)


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

    if not (0 <= mem <= 7):
        return

    chan_access = _gateware_chan(cfg_b.gateware, chan)

    chan_access.GPIO.axi_gpio_2.write(0x00, int(round(init_re*(1 << 16))) & 0x3FFFF)
    chan_access.GPIO.axi_gpio_2.write(0x08, int(round(init_im*(1 << 16))) & 0x3FFFF)

    if mem & 1:  # mem odd: add π
        dphi = _wrap_angle(dphi + np.pi)
    dphi_int, _ = _rad2int(dphi)

    word = int((addr << 16) + dphi_int)
    bit_value = [1,16,2,32,4,64,8,128][mem]
    
    chan_access.GPIO.axi_gpio_1.write(0x08, word)
    chan_access.GPIO.axi_gpio_1.write(0x00, bit_value)
    chan_access.GPIO.axi_gpio_1.write(0x00, 0)


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

    # freqs_bb = np.array(np.linspace(-254.4e6, 255.00e6, 1000))
    freqs_bb = np.array(np.arange(-256e6, 256e6, 500e3))

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