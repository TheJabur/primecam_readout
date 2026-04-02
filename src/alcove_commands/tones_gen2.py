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
# _wrap_to_pi
def _wrap_to_pi(angle):
    """Wrap an angle in radians to the principal interval [-pi, pi].

    Parameters:
    angle : float or array-like
        Angle(s) in radians.

    Returns:
    float or ndarray
        Angle(s) wrapped to the interval [-pi, pi].
    """
    return np.arctan2(np.sin(angle), np.cos(angle))


# ============================================================================ #
# _rad2int
def _rad2int(angle_rad):
    """Quantize an angle in radians to a uint16 with π-radian units.

    The angle is first wrapped to [-π, π], then scaled such that ±π maps to
    ±2^15 in signed int16. The returned uint16 is the raw two's-complement
    representation. The corresponding quantized angle in radians is also
    returned.

    Args:
        angle_rad (float or array-like): Angle to quantize. [rad]

    Returns:
        code (uint16 or array): u16int encoding of modified angle.
        angle_q (float or ndarray): Modified angle. [rad]
    """
    wrap = _wrap_to_pi(angle_rad)
    i16 = np.int16(np.round((wrap / np.pi) * 2**15))
    actual = i16 * (np.pi / 2**15)
    return i16.astype(np.uint16), actual


# ============================================================================ #
# _getSafeFrequencies
def _getSafeFrequencies(freqs, min_spacing=None, snap=True):
    """Filter and select frequencies safely for PSB channels.
    
    Args:
        freqs (array_like): Input frequencies. [Hz]
        min_spacing (float or None): Min allowed spacing between tones. [Hz]
        snap (bool): Force the frequencies to snap to output fs.
            (Default is multiples of 488.28125 Hz).
    
    Returns:
        (array): Filtered and sorted frequency array.

    Notes:
        - Filter to Nyquist range [-fs/2, fs/2].
        - Sort ascending.
        - Remove frequencies that are too close together (optional).
        - Limit to at most 2 tones per bin.
    """

    fs = cfg_b.fs # 1024e6
    psb_channel_count = cfg_b.psb_channel_count # 2048
    acc_factor = cfg_b.acc_factor # 1024
    bin_size = fs / psb_channel_count
    nyquist = fs / 2
    fs_out = bin_size/acc_factor
    
    freqs = np.asarray(freqs, dtype=np.float64)
    
    # Filter to Nyquist range [-fs/2, fs/2]
    freqs = freqs[(freqs >= -nyquist) & (freqs <= nyquist)]
    
    if len(freqs) == 0: # early exit if no tones (left)
        return np.array([], dtype=np.float64)

    # Sort ascending
    freqs = np.sort(freqs) 

    # snap to fft bin centers
    if snap:
        freqs = np.round(freqs/fs_out).astype(np.int64)*fs_out
    
    # Remove frequencies that are too close together
    if len(freqs) > 1 and min_spacing:
        diffs = np.diff(freqs)
        # Keep first frequency, then only keep frequencies with sufficient spacing
        keep_mask = np.ones(len(freqs), dtype=bool)
        keep_mask[1:] = diffs >= min_spacing
        freqs = freqs[keep_mask]
    
    # Limit to at most 2 (middle) frequencies per bin
    bin_indices = np.floor((freqs + nyquist) / bin_size).astype(np.int32)
    max_bin = bin_indices[-1] + 1
    bin_counts = np.bincount(bin_indices, minlength=max_bin)
    overcrowded_bins = np.where(bin_counts > 2)[0]
    if len(overcrowded_bins) > 0:
        keep_mask = np.ones(len(freqs), dtype=bool)
        for bin_idx in overcrowded_bins:
            bin_freq_indices = np.where(bin_indices == bin_idx)[0]
            n_in_bin = len(bin_freq_indices)
            start_idx = (n_in_bin - 2) // 2 # middle 1
            end_idx = start_idx + 2         # middle 2
            bin_keep = np.zeros(n_in_bin, dtype=bool)
            bin_keep[start_idx:end_idx] = True
            keep_mask[bin_freq_indices[~bin_keep]] = False
        freqs = freqs[keep_mask]
    
    return freqs


# ============================================================================ #
# _writeToneSelect
def _writeToneSelect(chan, addr, data):
    """Updates toneSelect parameter memory at one address
    
    Args:
        chan (int): Readout RF channel.
        addr (uint): The address of the write operation.
        data (ufix_12): The data of the write operation.
    """
    chan_access = _gateware_chan(cfg_b.gateware, chan)
    
    chan_access.GPIO.axi_gpio_6.write(0x08, int(addr))
    
    chan_access.GPIO.axi_gpio_7.write(0x00, int((data[1] << 12) + data[0]))
    chan_access.GPIO.axi_gpio_7.write(0x08, int((data[3] << 12) + data[2]))
    chan_access.GPIO.axi_gpio_8.write(0x00, int((data[5] << 12) + data[4]))
    chan_access.GPIO.axi_gpio_8.write(0x08, int((data[7] << 12) + data[6]))
    
    chan_access.GPIO.axi_gpio_6.write(0x00,0)
    chan_access.GPIO.axi_gpio_6.write(0x00,1)
    chan_access.GPIO.axi_gpio_6.write(0x00,0)


# ============================================================================ #
# _writeToneSelectAll
def _writeToneSelectAll(chan, ToneSelMap):
    """Updates the entire toneSelect LUT from ToneSelMap
    
    Args:
        chan (int): Readout RF channel.
        ToneSelMap (numpy.ndarray): The toneSelect LUT.
    """
    for i in range(256):
        _writeToneSelect(chan, i, ToneSelMap[i])


# ============================================================================ #
# _genDefaultToneSelMap
def _genDefaultToneSelMap():
    """Generate a default tone select mapping LUT for initialization/reset.
    Caches instead of regenerating for performance.

    Returns:
        toneSelectMap (array)

    Notes:
        Optimization: Cache output (in cfg file).
    """

    if cfg_b.defaultToneSelMap is None:

        addr = np.arange(256, dtype=np.uint16)[:, None]
        para = np.arange(8, dtype=np.uint16)[None, :]
        onoff = np.uint16(1)
        cfg_b.defaultToneSelMap = (addr << 4) | (para << 1) | onoff

    return cfg_b.defaultToneSelMap


# ============================================================================ #
# _updateToneSelMap
def _updateToneSelMap(chan, toneSelectInfo, turn_off_unused_bin=True):
    """Update toneSelMap based on 2-tone bin reuse mapping.

    Args:
        chan (int): Readout RF channel.
        toneSelectInfo (array): Integer bin-index mapping.
            Row 0 contains the destination (2-tone) bin indices.
            Row 1 contains the source (unused) bin indices whose tone-select
        turn_off_unused_bin (bool): Disable source bins.
    """

    toneSelectMap = _genDefaultToneSelMap() # should cache

    twoTone_bins, unused_bins = toneSelectInfo

    flat = toneSelectMap.ravel()
    flat[twoTone_bins] = flat[unused_bins]

    if turn_off_unused_bin:
        flat[unused_bins] = 0

    _writeToneSelectAll(chan, toneSelectMap)


# ============================================================================ #
# _writeBinMap
def _writeBinMap(chan, addr, data):
    '''Write to firmware registers via GPIO.
    Updates the bin select mapping (LUT) in the receive.
    
    Args:
        chan (int): Readout RF channel.
        addr (uint): The address of the write operation.
        data (ufix_22): The data of the write operation.
            
    Notes:
        The bin map RAM are accessed 2 addrs at a time, 
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


# ============================================================================ #
# _loadBinMap
def _loadBinMap(chan, bin_map):
    '''Updates the bin select mapping (LUT) in the receive.
    
    Args:
        chan (int): Readout RF channel.
        bin_map (numpy.ndarray): Array of bin select mapping LUT.
    '''

    bin_map_reshape = bin_map.reshape((512, 4))
    for i in range(512):
        _writeBinMap(chan, 2*i, bin_map_reshape[i])


# ============================================================================ #
# _loadBeatDphiMap
def _loadBeatDphiMap(chan, beat_dphi_map):
    '''Updates the beat frequencies corresponding to each tone, 
    for the digital down conversion (DDC) in receive.
    
    Args:
        chan (int): Readout RF channel.
        beat_dphi_map (array): beat dphi LUT values.
    '''
    chan_access = _gateware_chan(cfg_b.gateware, chan)

    dphi_i16, _ = _rad2int(beat_dphi_map)
    dphi_i16 = dphi_i16.reshape(512, 4)
    for addr in range(512):
        base = addr << 20
        row = dphi_i16[addr]
        for mem in range(4):
            word = base | (int(row[mem]) << 4)
            chan_access.GPIO.axi_gpio_4.write(0x00, word)
            chan_access.GPIO.axi_gpio_4.write(0x00, word | (1 << mem))
            chan_access.GPIO.axi_gpio_4.write(0x00, word)


# ============================================================================ #
# _writeTone
def _writeTone(chan, mem, addr, dphi, init_re, init_im):
    """Writes one tone.

    The function converts physical units (radians, floating-point vectors) into 
    the fixed-point integers required by the gateware. It also handles 18-bit 
    signed vector components and packs address/frequency data into a single 32-bit word.

    Args:
        chan (int): The hardware channel index to access.
        mem (int): The memory slot index (0-7). Determines the trigger bit in 
            the control register and applies a phase shift if odd.
        addr (int): The destination address within the tone selection map.
        dphi (float): The phase increment (frequency) in radians.
        init_re (float): Real component of the initial starting vector. 
            Converted to 18-bit fixed point (Q2.16).
        init_im (float): Imaginary component of the initial starting vector. 
            Converted to 18-bit fixed point (Q2.16).

    Note:
        - If `mem` is odd, a $\pi$ phase shift is automatically applied to `dphi`.
        - `axi_gpio_2` handles the initial vector (I/Q) components.
        - `axi_gpio_1` handles the packed (Address + Frequency) word and the 
          strobe/trigger bit defined by `mem`.
    """

    if not (0 <= mem <= 7):
        return

    chan_access = _gateware_chan(cfg_b.gateware, chan)

    chan_access.GPIO.axi_gpio_2.write(0x00, int(round(init_re*(1 << 16))) & 0x3FFFF)
    chan_access.GPIO.axi_gpio_2.write(0x08, int(round(init_im*(1 << 16))) & 0x3FFFF)

    if mem & 1:  # mem odd: add π
        dphi = _wrap_to_pi(dphi + np.pi)
    dphi_int, _ = _rad2int(dphi)

    word = int((addr << 16) + dphi_int)
    bit_value = [1,16,2,32,4,64,8,128][mem]
    
    chan_access.GPIO.axi_gpio_1.write(0x08, word)
    chan_access.GPIO.axi_gpio_1.write(0x00, bit_value)
    chan_access.GPIO.axi_gpio_1.write(0x00, 0)


# ============================================================================ #
# _writeAllTones
def _writeAllTones(chan, bin_num, dphi, init_re, init_im):
    '''Writes all tones listed in 1darrays
    
    Args:
        chan (int): Readout RF channel.
        bin_num (int): The FFT bin number of which the tone is in.
        dphi (float): The step in phase which defines the frequency 
            of the tone from bin center. In unit [rad].
        init_re (float),
        init_im (float): 
            The real and imaginary parts of the initial vector.
            Note: The maximum magnitude of the initial vector is 1.
    
    '''
    for i in range(bin_num.size):
        _writeTone(chan, bin_num[i]%8, bin_num[i]//8, 
                   dphi[i], init_re[i], init_im[i])


# ============================================================================ #
# _calculateCombParameters
def _calculateCombParameters(freqs):
    '''
    '''

    freqs = _getSafeFrequencies(freqs)
    f_step = cfg_b.fs / cfg_b.lut_len
    freqs_actual = np.round(freqs / f_step) * f_step
    
    bin_step = cfg_b.fs / cfg_b.psb_channel_count
    bin_num = np.round(freqs_actual / bin_step).astype(np.int64)
    bin_num[bin_num < 0] += cfg_b.psb_channel_count
    
    # dphi/2pi ratio corresponds to the channel bandwidth of PSB which is 2*fs/2048
    dphi = _wrap_to_pi(np.pi * (freqs_actual / bin_step - bin_num))
    beat_dphi = _wrap_to_pi(-2 * dphi) # Careful with different sampling frequency
    
    return freqs_actual, bin_num, dphi, beat_dphi


# ============================================================================ #
# _generateToneMaps
def _generateToneMaps(chan, bin_num, beat_dphi):
    '''Handles bin collisions and generates the hardware mapping.
    '''

    psb_count = cfg_b.psb_channel_count # 2048
    
    # 1. Identify Collsions
    # 'inverse' gives the index of the first occurrence for every element in bin_num
    _, unique_indices, counts = np.unique(bin_num, return_index=True, return_counts=True)
    
    # Mask out the first occurrences to find the second (colliding) tones
    collision_mask = np.ones(len(bin_num), dtype=bool)
    collision_mask[unique_indices] = False
    collision_idx = np.where(collision_mask)[0]

    if collision_idx.size > 0:
        # 2. Find replacement bins
        # np.setdiff1d is highly efficient for finding 'holes' in the bin range
        all_bins = np.arange(psb_count)
        unused_bins = np.setdiff1d(all_bins, bin_num)
        
        # Assign new bins to the collisions
        new_bins = unused_bins[:collision_idx.size]
        
        # 3. Update Tone Selection Map (Hardware-specific call)
        # toneSelectInfo[0] = original bin, [1] = remapped bin
        toneSelectInfo = np.vstack([bin_num[collision_idx], new_bins])
        _updateToneSelMap(chan, toneSelectInfo)
        
        # 4. Final mapping for hardware write
        # Use the remapped bins for the second tones
        final_bins = bin_num.copy()
        final_bins[collision_idx] = new_bins
    else:
        # No collisions: reset map to 1:1 identity
        _writeToneSelectAll(chan, _genDefaultToneSelMap())
        final_bins = bin_num

    # 5. Populate the fixed-length 2048 arrays
    # We place all active tones at the front of the map
    bin_map = np.zeros(psb_count, dtype=int)
    beat_map = np.zeros(psb_count, dtype=float)
    
    num_active = len(final_bins)
    bin_map[:num_active] = final_bins
    beat_map[:num_active] = beat_dphi

    return bin_map, beat_map


# ============================================================================ #
# _writeComb
def _writeComb(chan, freqs, amps, phi, save=True):
    '''
    '''

    # frequency, bin, and dphi (safe frequencies)
    freqs_actual, bin_num, dphi, beat_dphi = _calculateCombParameters(freqs)

    # map generation (bin collision handling)
    bin_map, beat_dphi_map = _generateToneMaps(chan, bin_num, beat_dphi)

    # hardware write
    _loadBinMap(chan, bin_map)
    _loadBeatDphiMap(chan, beat_dphi_map)
    _writeAllTones(chan, bin_num, dphi, amps*np.cos(phi), amps*np.sin(phi))
    alcove_base.writeChannelCount(len(freqs))

    # persistence
    if save:
        f_center   = io.load(io.file.f_center_vna) # 
        freqs_rf_actual = freqs_actual + f_center

        io.save(io.file.f_rf_tones_comb, freqs_rf_actual)
        io.save(io.file.a_tones_comb, amps)
        io.save(io.file.p_tones_comb, phi)

    return freqs_actual


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
        amps, phis = genAmpsAndPhis(freqs_bb)

    freqs_bb_actual = _writeComb(chan, freqs_bb, amps, phis)
    freqs_rf_actual = freqs_bb_actual + f_center 

    return freqs_rf_actual, amps, phis


# ============================================================================ #
# genPhis
def genPhis(freqs, amps_rel, amp_max=1., phase_trials=5):
    """Generates optimized phases for a tone comb to minimize waveform peak.

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
    """
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
    """See genPhis(...)"""

    # equal amplitude tones
    amps = amp_max*np.ones(len(freqs))

    return genPhis(freqs, amps, amp_max, phase_trials)


# ============================================================================ #
# writeTestTone
def writeTestTone(freq=50e6):
    """Write a single tone.

    Args:
        freq (float): Tone frequency, base band. [Hz]

    Returns:
        (float): The actual frequency written.
    """
    
    chan = cfg_b.drid

    freqs = np.array([freq])
    amps = np.array([1.])
    phis = np.array([np.pi])

    freq_actual = _writeComb(chan, freqs, amps, phis)

    return freq_actual


# ============================================================================ #
# writeNewVnaComb
def writeNewVnaComb(freq_noise=0):
    """Create and write the vna sweep tone comb.

    freq_noise: (float) Frequency noise to add to the tone placement.
        This uses a uniform distribution of noise. [Hz]
    """

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

    amps, phis = genAmpsAndPhis(freqs_bb)

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