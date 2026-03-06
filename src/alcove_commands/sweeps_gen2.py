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
        Is, Qs = alcove_base.getSnapData(3, wrap=False, wait=wait2)
        # Is, Qs = alcove_base.getSnapData(chan, 3, wrap=False, wait=wait2)
        data = (Is + 1.j * Qs)  # convert I and Q to complex
        data = data.reshape((-1, 1024))
        Z = np.mean(data, axis=0)
        Z = np.concatenate((Z[test:len(freqs)], Z[0:test]))
        return Z[0:len(freqs)] # only return relevant slice
    
    start_time = time.time()

    # loop over each LO freq and flatten Z and f
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
        chan, f_center/1e6, freqs_bb, sweep_steps, chan_bandwidth=chan_bw)) 

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
        chan, f_center/1e6, freqs_bb, sweep_steps, chan_bandwidth=chan_bw)) 

    return io.returnWrapper(io.file.s21_custom, S21)