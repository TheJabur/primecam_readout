# ============================================================================ #
# analysis.py
# Signal processing functions and commands.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #

from alcove_commands.alcove_base import *



# ============================================================================ #
# _butterFilter
def _butterFilter(y, x, btype, cutoff_freqs, order=3, x_time=False):
    '''Butterworth digital and analog filter.
    
    x, y: (1D array of floats) The data.
    btype: (str) {'lowpass', 'highpass', 'bandpass', 'bandstop'}.
    cutoff_freq: (float or 2-tuple of floats) The cutoff frequencies.
    order: (int) Filter order.
    x_time: (bool) x axis is time (default is frequency).
    '''

    import numpy as np
    from scipy.signal import butter, filtfilt

    fs = np.abs(x[1] - x[0])
    nyquist = 0.5*fs
    normal_cutoff = cutoff_freqs / nyquist
    b, a = butter(order, normal_cutoff, btype=btype, fs=fs)
    filtered_data = filtfilt(b, a, y)

    return filtered_data


# ============================================================================ #
# _stitchS21m
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


# ============================================================================ #
# _resonatorIndicesInS21
def _resonatorIndicesInS21(f, Z, stitch_bw=500, stitch_sw=100, f_hi=50, f_lo=1, prom_dB=1, distance=30, width=(5,100), testing=False):
    """Find the indices of resonator peaks in given S21 signal.
    
    f:         (1D array of floats) Frequency bins of signal.
    Z:         (1D array of floats) S21 complex values.
    stitch_bw: (int) Width of the stitch bins.
    stitch_sw: (int) Width of slice (at ends) of each stitch bin to take median.
    f_hi:      (float) Highpass filter cutoff frequency (data units).
    f_lo:      (float) lowpass filter cutoff frequency (data units).
    prom_dB:   (float) Peak prominence cutoff, in dB.
    distance:  (float) Min distance between peaks, in bins.
    width      (tuple of 2 floats) Peak width (min, max), in bins.
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
    peaks, props = find_peaks(x=-m_f, prominence=prom_lin, 
                              distance=distance, width=width) 
    
    if testing: return peaks, (fs, m, m_f, m_f_dB, prom_dB, props)
    return peaks


# ============================================================================ #
# _findResonators
def _findResonators(f, Z,
                   stitch_bw=500, stitch_sw=100, 
                   f_hi=50, f_lo=1, prom_dB=1, 
                   distance=30, width_min=5, width_max=100):
    """Find the resonator peak frequencies in previously saved s21.npy file.

    f:         (1D array of floats) Frequency bins of signal.
    Z:         (1D array of floats) S21 complex values.
    stitch_bw: (int) Width of the stitch bins.
    stitch_sw: (int) Width of slice (at ends) of each stitch bin to take median.
    f_hi:      (float) Highpass filter cutoff frequency. [data units]
    f_lo:      (float) lowpass filter cutoff frequency. [data units]
    prom_dB:   (float) Peak prominence cutoff. [dB]
    distance:  (int) Min distance between peaks. [bins]
    width_min  (int) Peak width minimum. [bins]
    width_max  (int) Peak width maximum. [bins]
    """
    
    import numpy as np

    # All params are str from Redis so need to cast
    stitch_bw   = int(stitch_bw)
    stitch_sw   = int(stitch_sw)
    f_hi        = float(f_hi)
    f_lo        = float(f_lo)
    prom_dB     = float(prom_dB)
    distance    = int(distance)
    width       = (int(width_min), int(width_max))

    i_peaks = _resonatorIndicesInS21(
        f, Z, stitch_bw, stitch_sw, f_hi, f_lo, prom_dB, 
        distance, width, testing=False)
    f_res = f[i_peaks]

    return f_res


# ============================================================================ #
# _findResonators_alt
def _findResonators_alt(f, Z, 
                      peak_prom_std=10, peak_prom_db=0, 
                      peak_dis=100, peak_width_min=10, peak_width_max=200,
                      stitch=True, stitch_bw=500, stitch_sw=100, 
                      remove_cont=True, continuum_wn=300, 
                      remove_noise=True, noise_wn=30_000,
                     ):
    '''
    
    f:   (1D array of floats) Frequency of S21 samples.
    Z: (1D array of complex) Forward transmission S_21 as complex.
    peak_prom_std: (float) Peak height from surroundings, in noise std multiples.
                    Uses larger of peak_prom_db or peak_prom_std.
    peak_prom_db:  (float) Peak height from surroundings, in Db.
                    Uses larger of peak_prom_db or peak_prom_std.
    peak_dis:      (int) Min distance between peaks [bins].
    peak_width:    (2-tuple of ints) Min/max peak width [bins].
    stitch:        (bool) Whether to stitch (comb discontinuities).
    stitch_bw:     (int) Discontinuity period [bins].
    stitch_sw:     (int) Discontinuity edge size for alignment [bins].
    remove_cont:   (bool) Whether to subtract the continuum.
    continuum_wn:  (int) Continuum filter cutoff frequency [Hz].
    remove_noise:  (bool) Whether to subtract noise.
    noise_wn:      (int) Noise filter cutoff frequency [Hz].
    '''
    
    from scipy.signal import find_peaks
    import numpy as np
    
    # type enforcement
    # required since parameters can get passed as strings
    peak_prom_std = float(peak_prom_std)
    peak_prom_db  = float(peak_prom_db)
    peak_dis      = int(peak_dis)
    # peak_width    = np.array(peak_width).astype(int)
    peak_width    = (int(peak_width_min), int(peak_width_max))
    stitch_bw     = int(stitch_bw)
    stitch_sw     = int(stitch_sw)
    continuum_wn  = int(continuum_wn)
    noise_wn      = int(noise_wn)
    
    x = f
    y = np.abs(Z)
    
    # convert Db input to linear
    peak_prom_lin = np.amax(y)*(1 - 10**(-peak_prom_db/20))
    
    # stitch discontinuities
    if stitch:
        y = _stitchS21m(y, bw=stitch_bw, sw=stitch_sw)
        
    # remove continuum
    if remove_cont:
        y -= _butterFilter(y, x, 'low', continuum_wn, order=3)
        
    # remove noise
    y_noise = _butterFilter(y, x, 'high', noise_wn, order=3)
    noise_std = np.std(y_noise)
    if remove_noise:
        y -= y_noise
        
    # prominence
    prom = max(peak_prom_std*noise_std, peak_prom_lin)
    
    # find peaks
    i_peaks, peak_properties = find_peaks(
        x=-y, prominence=prom, distance=peak_dis, width=peak_width) 
        
    f_res = f[i_peaks]

    return f_res


# ============================================================================ #
# _findMins
def _findMins(f, Z,
    stitch_bw=500, stitch_sw=100,
    f_hi=50, f_lo=1, prom_dB=1,
    distance=30, width_min=5, width_max=100):
    """Find the minimum (resonator peak) in each targ bin.

    Parameters are consistent with _findResonators.
    """
    
    import numpy as np

    m = np.abs(Z)
    
    a = m.reshape(-1, stitch_bw)               # reshape into targ bins
    f_reshaped = f.reshape(-1, stitch_bw)      # reshape into targ bins
    num_res = f_reshaped.shape[0]
    row_indices = np.arange(num_res)

    # indices of mins in each row
    col_indices = np.argmin(a, axis=1) 
    
    f_res = f_reshaped[row_indices, col_indices]

    # f_res = [
    #     f_reshaped[r][np.argmin(a, axis=1)[r]]
    #     for r in range(num_res)]

    return f_res.real


# ============================================================================ #
# findVnaResonators
def findVnaResonators(**kwargs):
    """Find the resonator peak frequencies from vnaSweep S21.
    See findResonators() for possible arguments.
    Note that vnaSweep must be run first.
    """

    f, Z = io.load(io.file.s21_vna)
    # f_res = _findResonators(f, Z, **kwargs)
    f_res = _findResonators_alt(f, Z, **kwargs)

    io.save(io.file.f_res_vna, f_res)

    return io.returnWrapper(io.file.f_res_vna, f_res)


# ============================================================================ #
# findTargResonators
def findTargResonators(**kwargs):
    """Find the resonator peak frequencies from targSweep S21.
    See findResonators() for possible arguments.
    Note that targSweep must be run first.
    """
    f, Z = io.load(io.file.s21_targ)
    f_res = _findMins(f, Z, **kwargs)

    io.save(io.file.f_res_targ, f_res)

    return io.returnWrapper(io.file.f_res_targ, f_res)


# ============================================================================ #
# findCalTones
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
    
    # return f_cal_tones
    return io.returnWrapper(io.file.f_cal_tones, f_cal_tones)