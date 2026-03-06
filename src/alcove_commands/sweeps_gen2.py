# ============================================================================ #
# sweeps_gen2.py
# Sweep functions and commands.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2026
# ============================================================================ #

from alcove_commands import alcove_base
import alcove_commands.board_io as io

try: from config import board as cfg_b
except ImportError: cfg_b = None 



# ============================================================================ #
# _toneFreqsAndAmpsFromSweepData
def _toneFreqsAndAmpsFromSweepData(f, Z, amps, N_steps, mod_amps=False):
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

    if mod_amps:
        # Power
        # np.gradient provides the slope at each point.
        # The asymmetry of the resonator shape in frequency space 
        # can be characterized by the sum of the max and min slopes.
        y_grad = np.gradient(y_res, axis=1)         # slope at each point
        a = np.max(y_grad, axis=1) + np.min(y_grad, axis=1)  # sum max and min slopes
        a /= np.max(np.abs(y_grad), axis=1)         # normalize
        amps_new = (1 + a)*amps
    else:
        amps_new = amps

    return (freqs, amps_new)


# ============================================================================ #
# _sweep
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
    import time

    wait1 = 0.003
    wait2 = 0.02

    N_steps  = max(1, int(N_steps)) # minimum 1 step
    f_center = float(f_center)

    # sort ascending and remove exact duplicates
    # for example:
        # target find resonators uses min in tone channel
        # so two resonators in same tone channel will lead to duplicates
    freqs = np.unique(freqs)
    test = np.sum(freqs < 0)
    
    # build LO steps
    if chan_bandwidth: # LO bandwidth given
        bw = float(chan_bandwidth) # MHz
    else:              # use tone difference
        bw = np.diff(freqs)[0]/1e6 # MHz
    flos = np.linspace(f_center-bw/2., f_center+bw/2., N_steps, endpoint=False)

    def _Z(lofreq):
        alcove_base.setFineNCLO(lofreq)
        time.sleep(wait1) # 0.003 s optimum to settle freq from testing
        Is, Qs = alcove_base.getSnapData(chan, 3, wrap=False, wait=wait2)
        data = (Is + 1.j * Qs)  # convert I and Q to complex
        data = data.reshape((-1, 1024))
        Z = np.mean(data, axis=0)
        Z = np.concatenate((Z[test:len(freqs)], Z[0:test]))
        return Z[0:len(freqs)] # only return relevant slice
    
    start_time = time.time()

    # loop over each LO freq and flatten Z and f
    print('using sweeps_gen2')
    Z = (np.array([_Z(lofreq-f_center) for lofreq in flos]).T).flatten()
    # print("freqs = ", freqs)
    f = np.array([flos*1e6 + ftone for ftone in freqs]).flatten()

    print(f"_sweep time: {time.time() - start_time}")
        
    alcove_base.setFineNCLO(0) # reset LO 

    return (f, Z)


# ============================================================================ #
# vnaSweep
def vnaSweep(sweep_steps=None):
    """Perform a stepped frequency sweep with current comb, save as vna sweep.

    sweep_steps: (int) Number of steps per tone in the sweep.
        You must pass this override value to findResontators (stitch_bw?).
    """

    import numpy as np

    chan = cfg_b.drid

    f_center = io.load(io.file.f_center_vna)
    freqs_bb = io.load(io.file.freqs_vna)

    # number of sweep steps
    try:     # attempt to use input
        sweep_steps = int(sweep_steps)
    except:  # fallback to config value
        sweep_steps = cfg_b.sweep_steps

    S21 = np.array(_sweep( # =(f,Z)
        chan, f_center/1e6, freqs_bb, sweep_steps)) # f, Z

    io.save(io.file.s21_vna, S21)
    # io.save(io.file.f_center_vna, f_center)

    return io.returnWrapper(io.file.s21_vna, S21)


# ============================================================================ #
# vnaSweepFull
'''
def vnaSweepFull(f_center, N_steps=500):
    """Write vna comb and perform a stepped frequency sweep.

    f_center:   (float) Center LO frequency for sweep. [MHz]
    N_steps:    (int) Number of LO frequencies to divide each channel into.
    """

    import numpy as np

    chan = cfg_b.drid
    f_center = int(f_center)

    setNCLO(f_center)
    # _setNCLO(chan, f_center)
    writeVnaComb()

    return vnaSweep(f_center, N_steps)
'''


# ============================================================================ #
# targetSweep
def targetSweep(chan_bw=None, sweep_steps=None):
    '''Perform a stepped freq. sweep with current comb, save as target sweep.

    chan_bw: (float) Bandwidth swept around each tone.
    sweep_steps: (int) Number of steps per tone in the sweep.
    '''

    # assume comb is written
    # assume nclo is written

    import numpy as np

    chan = cfg_b.drid
    
    f_center = io.load(io.file.f_center_vna) # Hz
    freqs_rf = io.load(io.file.f_res_targ)
    freqs_bb = freqs_rf - f_center

    # number of sweep steps
    try:     # attempt to use input
        sweep_steps = int(sweep_steps)
    except:  # fallback to config value
        sweep_steps = cfg_b.sweep_steps

    # bandwidth swept around each tone
    try:     # attempt to use input
        chan_bw = float(chan_bw)
    except:  # fallback to config value
        chan_bw = cfg_b.target_chan_bw
    
    S21 = np.array(_sweep(
        chan, f_center/1e6, freqs_bb, sweep_steps, 
        chan_bandwidth=chan_bw, N_accums=cfg_b.sweep_accums)) 

    io.save(io.file.s21_targ, S21)

    return io.returnWrapper(io.file.s21_targ, S21)


# ============================================================================ #
# customSweep
def customSweep(bw=1., sweep_steps=None):
    # assume comb is written
    # assume nclo is written

    import numpy as np

    chan = cfg_b.drid

    # number of sweep steps
    try:     # attempt to use input
        sweep_steps = int(sweep_steps)
    except:  # fallback to config value
        sweep_steps = cfg_b.sweep_steps

    # bandwidth swept around each tone
    try:     # attempt to use input
        chan_bw = float(bw)
    except:  # fallback to config value
        chan_bw = cfg_b.target_chan_bw
    
    f_center = io.load(io.file.f_center_vna) # Hz
    freqs_rf = io.load(io.file.f_rf_tones_comb_cust)
    freqs_bb = freqs_rf - f_center

    S21 = np.array(_sweep(
        chan, f_center/1e6, freqs_bb, sweep_steps, 
        chan_bandwidth=chan_bw, N_accums=cfg_b.sweep_accums)) 

    return io.returnWrapper(io.file.s21_custom, S21)


# ============================================================================ #
# targetSweepFull
'''
def targetSweepFull(freqs=None, f_center=None, N_steps=500, chan_bandwidth=0.2, amps=None, phis=None, save=True):
    """
    Perform a sweep around resonator tones and identify resonator frequencies and tone amplitudes.
    
    freqs:           (1D array of floats) Current comb tone frequencies [Hz].
    f_center:        center LO frequency in [MHz].
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    chan_bandwidth:  (float) Channel bandwidth [MHz].
    amps:            (1D array of floats) Current tone amplitudes.
    phis:            (1D array of floats) Current tone phases. 

    Return:          (2-tuple) Characterized resonator frequencies and normalized tone amplitudes.
    """

    import numpy as np

    chan = cfg_b.drid

    # load resonator frequencies from vna sweep if not passed in
    if freqs is None:
        try:
            freqs = io.load(io.file.f_res_vna) # Hz
        except:
            raise Exception("Error: Perform a VNA sweep first.")
    freqs = freqs.real # may be complex but imag=0
    
    # load f_center from last vna sweep if not passed in
    if f_center is None:
        try:
            f_center = io.load(io.file.f_center_vna) # Hz
        except:
            raise Exception("Error: Need a central LO frequency. Perform a VNA sweep first.")
    else:
        f_center = f_center*1e6 # convert passed param MHz to Hz

    freqs = freqs - f_center

    # calculate amps and phis if amps not passed in
    if amps is None or phis is None:
        # amps = np.ones_like(f_res)
        amps, phis = genAmpsAndPhis(freqs)

    # calculate phis if not passed in
    if phis is None:
        phis = genPhis(freqs, amps)
    
    # write tone comb
    freq_actual = _writeComb(chan, freqs, amps, phis) # returns freq_actual

    # perform targeted sweep
    S21 = np.array(
        _sweep(chan, f_center/1e6, freqs, N_steps, chan_bandwidth)) 
  
    # try to optimise tone power (single iteration)
    freqs_rf, amps = _toneFreqsAndAmpsFromSweepData( *S21, amps, N_steps, mod_amps=False)
    freqs_bb = freqs_rf - f_center 
    # need to determine if freqs returned from _ToneFreqs ... are baseband
    phis = _genPhis(freqs_bb, amps)

    if save:
        io.save(io.file.s21_targ, S21)
        io.save(io.file.f_res_targ, freqs_rf)
        io.save(io.file.a_res_targ, amps)
        io.save(io.file.p_res_targ, phis)
        io.save(io.file.f_center_targ, f_center)

    # return (freqs, A_res)
    return io.returnWrapperMultiple(
        [io.file.f_res_targ, io.file.a_res_targ, io.file.s21_targ, io.file.p_res_targ], 
        [freqs_rf, amps, S21, phis])
'''


# ============================================================================ #
# loChop
'''
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
    
    chan = cfg_b.drid
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
        print(f"Warning: Too many detectors over tolerance(dtol): {n}...", end='')
        print(f"... should run a full loop calibration.")
        # fullLoop()
    else:
        print(f"Info: {n} detectors over tolerance, which is allowable. Done.")
'''
