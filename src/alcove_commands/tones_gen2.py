# ============================================================================ #
# tones_gen2.py
# Tone and comb functions and commands.
# Compatible with gateware versions 15+ (gen2).
# James Burgoyne jburgoyne@phas.ubc.ca 
# Adrian Sinclair aksincla@asu.edu
# CCAT Prime 2026
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
        - If `mem` is odd, a pi phase shift is automatically applied to `dphi`.
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
# _filterAndSnapCombTones
def _filterAndSnapCombTones(freqs, amps, phi):
    # Setup constants
    nyquist = cfg_b.fs / 2
    fs_out = (cfg_b.fs / cfg_b.psb_channel_count) / cfg_b.acc_factor

    # Sort and Filter Nyquist
    f, a, p = np.asarray(freqs), np.asarray(amps), np.asarray(phi)
    idx = np.argsort(f)
    f, a, p = f[idx], a[idx], p[idx]
    
    mask = (f >= -nyquist) & (f <= nyquist)
    f, a, p = f[mask], a[mask], p[mask]
    
    # Snap to Grid
    f_snapped = np.round(f / fs_out) * fs_out
    
    return {'freqs': f_snapped, 'amps': a, 'phi': p}


# ============================================================================ #
# _resolveCombBinCollisions
def _resolveCombBinCollisions(chan, sig):
    bin_size = cfg_b.fs / cfg_b.psb_channel_count
    nyquist = cfg_b.fs / 2
    
    # Calculate initial bins
    bins = np.floor((sig['freqs'] + nyquist) / bin_size).astype(np.int32)
    
    # Filter: Max 2 tones per bin
    _, first_idx, counts = np.unique(bins, return_index=True, return_counts=True)
    within_bin_idx = np.arange(len(bins)) - np.repeat(first_idx, counts)
    keep = (within_bin_idx >= (np.repeat(counts, counts) - 2) // 2) & \
           (within_bin_idx < (np.repeat(counts, counts) - 2) // 2 + 2)
    
    # Update signal state
    for key in ['freqs', 'amps', 'phi']:
        sig[key] = sig[key][keep]
    bins = bins[keep]

    # Remap Second Tones
    _, u_idx = np.unique(bins, return_index=True)
    collision_mask = np.ones(len(bins), dtype=bool)
    collision_mask[u_idx] = False
    
    if np.any(collision_mask):
        unused = np.setdiff1d(np.arange(cfg_b.psb_channel_count), bins)
        new_slots = unused[:np.sum(collision_mask)]
        
        _updateToneSelMap(chan, np.vstack([bins[collision_mask], new_slots]))
        
        hw_bins = bins.copy()
        hw_bins[collision_mask] = new_slots
    else:
        _writeToneSelectAll(chan, _genDefaultToneSelMap())
        hw_bins = bins

    sig['bins'] = bins     # Original bins (for dphi)
    sig['hw_bins'] = hw_bins # Remapped bins (for hardware index)
    return sig


# ============================================================================ #
# _executeCombHwWrite
def _executeCombHwWrite(chan, sig):
    psb_count = cfg_b.psb_channel_count
    bin_size = cfg_b.fs / psb_count
    
    # Phase corrections
    dphi = _wrap_to_pi(np.pi * (sig['freqs'] / bin_size - sig['bins']))
    beat_map = np.zeros(psb_count)
    bin_map = np.zeros(psb_count, dtype=int)
    
    n = len(sig['hw_bins'])
    bin_map[:n] = sig['hw_bins']
    beat_map[:n] = _wrap_to_pi(-2 * dphi)
    
    # Device I/O
    _loadBinMap(chan, bin_map)
    _loadBeatDphiMap(chan, beat_map)
    _writeAllTones(chan, sig['bins'], dphi, 
                   sig['amps'] * np.cos(sig['phi']), 
                   sig['amps'] * np.sin(sig['phi']))
    
    alcove_base.writeChannelCount(n)


# ============================================================================ #
# _writeComb
def _writeComb(chan, freqs, amps, phi, save=True):
    '''Orchestrates the generation and hardware-loading of a multi-tone frequency comb.

    This function synchronizes the high-level signal definition with the underlying RFSoC/PSB hardware state through a three-stage pipeline:
    1. Physical Filtering: Truncates frequencies to the Nyquist range and snaps them to the valid FFT bin centers (fs_out).
    2. Logic Resolution: Identifies and resolves bin collisions by limiting occupancy to 2 tones per bin and remapping "second" tones to unused bins via the Tone Selection Map.
    3. Hardware Execution: Calculates phase corrections (dphi/beat_dphi) and performs vectorized writes to the bin maps and tone registers.

    Args:
        chan (int): The target hardware channel index.
        freqs (array_like): Requested tone frequencies in Hz.
        amps (array_like): Linear amplitudes for each tone.
        phi (array_like): Initial phases in radians.
        save (bool): If True, persists the final snapped and filtered comb state 
            to the local filesystem.

    Returns:
        numpy.ndarray: The actual, snapped frequencies [Hz] successfully 
            written to the hardware.
    '''

    # 1. Physical Filtering & Snapping
    sig = _filterAndSnapCombTones(freqs, amps, phi)
    if sig['freqs'].size == 0:
        return np.array([])

    # 2. Logistics: Handle overcrowded bins (max 2) and collisions
    sig = _resolveCombBinCollisions(chan, sig)

    # 3. Hardware Execution
    _executeCombHwWrite(chan, sig)

    # 4. Persistence
    if save:
        f_center   = io.load(io.file.f_center_vna) # 
        freqs_rf_actual = sig['freqs'] + f_center

        io.save(io.file.f_rf_tones_comb, freqs_rf_actual)
        io.save(io.file.a_tones_comb, sig['amps'])
        io.save(io.file.p_tones_comb, sig['phi'])

    return sig['freqs']


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
# _xPeak
def _xPeak(freqs, amps, phis):
    """Peak amplitude of the waveform that will be built from input arrays.

    freqs (array of floats): Frequencies of the tones. [Hz]
    amps: (array of floats): Amplitudes of the tones. 
    phis: (array of floats): Phases of the tones. [rads]

    Return:
        xPeak (float): Waveform peak amplitude.
    """

    import numpy as np
    from math import gcd
    from functools import reduce
    from scipy.fft import ifft

    # Type confirmation (O(1) if already correct)
    freqs = np.asarray(freqs, float)
    amps  = np.asarray(amps, float)
    phis  = np.asarray(phis, float)
    
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

    # Preallocate FFT buffer
    X = np.zeros(L, dtype=np.complex128)

    # Populate spectrum
    X[k] = amps * np.exp(-1j * phis)

    # IFFT at reduced length
    x = L * ifft(X, norm="backward", workers=-1)

    # Peak amplitude
    xPeak = np.max(np.abs(x))

    return xPeak


# ============================================================================ #
# _estimateMaxPhaseTrials
def _estimateMaxPhaseTrials(freqs, amps, confidence=0.99, k=2.5, absolute_max_trials=10):
    """Estimates the number of trials needed to find a phase set keeping 
    the peak under x_peak_max with a target confidence.

    freqs (array of floats): Frequencies of the tones. [Hz]
    amps  (array of floats): Amplitudes of the tones in [0, x_peak_max).
    confidence (float): Desired statistical confidence in result (0 to 1).
                        E.g. % will find solution in # trials.
    absolute_max_trials (int): Upper ceiling on return.
    k (float): Oversampling multiplier for independent peak locations. 

    Returns:
        (int): Recommended max trials, or 0 if success unlikely.
    """

    freqs = np.asarray(freqs, float)
    amps  = np.asarray(amps, float)

    N = len(freqs)
    x_rms = np.sqrt(0.5 * np.sum(amps**2))

    # Hard physical limit check (Parseval / RMS)
    if x_rms >= cfg_b.x_peak_max:
        return 0  # Physically impossible

    # Ratio of target peak to RMS
    gamma_sq = (cfg_b.x_peak_max / x_rms) ** 2
    
    # Probability that a single sample stays below threshold
    p_sample = 1.0 - np.exp(-0.5 * gamma_sq)
    
    # Probability that all M = k*N samples stay below threshold in 1 draw
    M = k * N
    p_draw = p_sample ** M
    
    if p_draw < 1e-12:
        return 0  # Statistically impossible in realistic time
    
    # Number of trials needed for target confidence
    trials = np.log(1.0 - confidence) / np.log(1.0 - p_draw)
    
    return int(np.clip(np.ceil(trials), 1, absolute_max_trials))


# ============================================================================ #
# genPhis
def genPhis(freqs, amps):
    """Generates optimized phases for a tone comb to minimize waveform peak.

    freqs (array of floats): Frequencies of the tones. [Hz]
    amps  (array of floats): Amplitudes of the tones in [0, 2^15-1).

    Return:
        phis: (array of floats or False): Phases of the tones in [-pi, pi).
            Returns False if no phases can satisfy max peak amplitude.
    """

    # Type confirmation (O(1) if already correct)
    freqs = np.asarray(freqs, float)
    amps  = np.asarray(amps, float)

    N = len(freqs)

    # Estimate max number of trials to find a solution
    print("    Estimating max phase trials.")
    max_trials = _estimateMaxPhaseTrials(freqs, amps, cfg_b.x_peak_max)

    # Unlikely (or impossible) to succeed
    if max_trials == 0:
        return False

    # Regenerate phases up to max_trials times
    # and return when a solution is found
    print("    Iterating to find a phase solution.")
    for _ in range(max_trials):

        # Generate random phases
        # If N large then Central Limit Theorem (Rayleigh distribution)
        # says a random draw is likely to get close to optimal solution
        phis = np.random.uniform(-np.pi, np.pi, N)

        # Find the waveform peak amplitude
        xPeak = _xPeak(freqs, amps, phis)
        
        if xPeak < cfg_b.x_peak_max:
            return phis

    # Unable to find a solution
    return False


# ============================================================================ #
# _estimate_safe_amplitude
def _estimate_safe_amplitude(freqs, target_trials=5, confidence=0.99, k=2.5):
    """Estimates the maximum equal amplitude per tone.
    ...such that random phase generation is expected 
    to find a peak below `x_peak_max` within `target_trials`.

    freqs (array of floats): Frequencies of the tones. [Hz]
    target_trials      (in): Target number of random phase trials.
    confidence      (float): Desired statistical confidence (0 to 1).
                             ...of finding a valid phase set within target_trials.
    k               (float): Oversampling factor.

    Return:
        (float): Safe uniform amplitude per tone.
    """

    N = len(freqs)

    # Probability that a random phase draw succeeds within target_trials
    # (1 - p_draw)^target_trials = 1 - confidence
    p_draw = 1.0 - (1.0 - confidence) ** (1.0 / target_trials)

    # Number of independent peak samples per time waveform
    M = k * N

    # Solve Rayleigh extreme value tail for target peak-to-RMS ratio gamma
    # p_draw = (1 - exp(-0.5 * gamma^2))^M
    # then gamma^2 = -2 * ln(1 - p_draw^(1/M))
    gamma_sq = -2.0 * np.log(-np.expm1(np.log(p_draw) / M))
    gamma = np.sqrt(gamma_sq)

    # Convert peak-to-RMS ratio back to single-tone amplitude A
    # x_rms = A * sqrt(N / 2) then x_peak = gamma * x_rms <= x_peak_max
    a_safe = cfg_b.x_peak_max / (gamma * np.sqrt(N / 2.0))

    return float(a_safe)


# ============================================================================ #
# genAmpsAndPhis
def genAmpsAndPhis(freqs):
    """Generates safe amps and phis for a given set of frequencies.
    """

    # equal amplitude tones
    print("   Estimating safe amplitudes.")
    amps = _estimate_safe_amplitude(freqs) * np.ones(len(freqs), dtype=float)

    # safe phis, could be false
    print("   Generating phis.")
    phis = genPhis(freqs, amps)

    # if no solution was found
    # something is wrong with _estimate_safe_amplitude
    if phis == False:
        print("ERROR: No amps/phis solution can be found!")
        
        # we can't just crash, default to something
        amps = np.ones(len(freqs), dtype=float)
        phis = np.zeros(len(freqs), dtype=float)

    return amps, phis


# ============================================================================ #
# writeTestTones
def writeTestTones(N=1, freqs=None):
    """Write requested tones.

    N (int): Number of tones. Step size 1 MHz. 1024 max.
    freqs (array of floats): Specific tone requests. Overrides N.
    """
    
    chan = cfg_b.drid

    # build freqs for number of requested tones
    if freqs is None:
        # 1 MHz step size, max 1024 tones
        freqs = np.arange(0, 1024e6, 1000e3)[:int(N)]

    # type enforcement
    freqs = np.asarray(freqs, float)

    amps, phis = genAmpsAndPhis(freqs)

    freq_actual = _writeComb(chan, freqs, amps, phis)

    return freq_actual


# ============================================================================ #
# writeTestTone
def writeTestTone():
    return writeTestTones(N=1)


# ============================================================================ #
# writeNewVnaComb
def writeNewVnaComb():
    """Create and write the vna sweep tone comb.

    freq_noise: (float) Frequency noise to add to the tone placement.
        This uses a uniform distribution of noise. [Hz]
    """
    
    chan = cfg_b.drid

    freqs_bb = np.array(np.arange(-512e6, 512e6, 1024e3))
    print(f"  VNA comb: {len(freqs_bb)} tones.")

    print("  Generating amps and phis.")
    amps, phis = genAmpsAndPhis(freqs_bb)

    print("  Writing the comb.")
    freqs_bb_actual = _writeComb(chan, freqs_bb, amps, phis)

    print("  Saving the comb files.")
    io.save(io.file.freqs_vna, freqs_bb_actual)
    io.save(io.file.amps_vna, amps)
    io.save(io.file.phis_vna, phis)

    return io.returnWrapperMultiple(
        [io.file.freqs_vna, io.file.amps_vna, io.file.phis_vna], 
        [freqs_bb_actual, amps, phis])


# ============================================================================ #
# writeTargCombFromVnaSweep
def writeTargCombFromVnaSweep():
    """Write the target comb from the vna sweep resonator frequencies.
    Note that vnaSweep and findVnaResonators must be run first.
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
        f_center, freqs_rf)

    # check for overflow of this comb
    alcove_base.checkWaveformOverflow()

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

    # check for overflow of this comb
    alcove_base.checkWaveformOverflow()

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

    ret = writeCombFromCustomList()

    # check for overflow of this comb
    alcove_base.checkWaveformOverflow()

    return ret


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

    # check for overflow of this comb
    alcove_base.checkWaveformOverflow()

    return io.returnWrapperMultiple(
        [io.file.f_rf_tones_comb, io.file.a_tones_comb, io.file.p_tones_comb], 
        [freqs_rf_comb, amps, phis])