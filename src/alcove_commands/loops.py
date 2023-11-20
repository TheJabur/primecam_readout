# ============================================================================ #
# loops.py
# Integrated command loops.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #

from alcove_commands.alcove_base import *


# ============================================================================ #
# targetSweepLoop
'''
def targetSweepLoop(chan_bandwidth=0.2, f_center=600, N_steps=500, 
                    f_tol=0.1, A_tol=0.3, loops_max=20):
    """Perform targetSweep iteratively until results are optimum.
    chan_bandwidth:  (float) Channel bandwidth [MHz].
    f_center:        (float) Center LO frequency for sweep [MHz].
    N_steps:         (int) Number of LO frequencies to divide each channel into.
    f_tol:           (float) Frequency change tolerance (MHz).
    A_tol:           (float) Amplitude max relative change tolerance.
    loops_max:       (int) Max loops to perform.
    """

    import numpy as np

    # do initial target sweep
    freqs, amps, _, phis = io.unwrapData(
        targetSweep(f_center=f_center, N_steps=N_steps, chan_bandwidth=chan_bandwidth, save=False))

    # should we look at whether chan_bandwidth was large enough / too large?

    # now do iterative sweeps to optimise amps/phis
    loop_num = 0; sweep = True
    while sweep:
        sweep = False # default to not performing another sweep
        
        freqs_new, amps_new, _, phis_new = io.unwrapData(
            targetSweep(freqs=freqs, amps=amps, f_center=f_center, N_steps=N_steps, chan_bandwidth=chan_bandwidth, save=False))
        # we don't pass phis in because there may be a new optimum
        # by not passing it forces a re-calculation of them

        # sweep again if any freq changed by more than f_tol
        # or if any tone amp change is more than A_tol
        if (np.any(np.abs(freqs - freqs_new) > f_tol*1e6) 
            or np.any(np.abs(1 - amps_new/amps) > A_tol)):
            sweep = True
            
        freqs, amps, phis = freqs_new, amps_new, phis_new

        # stop re-sweeping after loops_max sweeps
        # even if not in tolerances
        if loop_num > loops_max:
            sweep = False
        loop_num += 1
        
    io.save(io.file.f_res_targ, freqs)
    io.save(io.file.a_res_targ, amps)
    io.save(io.file.p_res_targ, phis)
    io.save(io.file.f_center_targ, f_center*1e6)

    # return np.array([freqs, amps, phis])    
    return io.returnWrapperMultiple(
        [io.file.f_res_targ, io.file.a_res_targ, io.file.p_res_targ], 
        [freqs, amps, phis])
'''

'''
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
        raise Exception("Required file missing: f_res_vna. Perform a vna sweep first.")

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
    
        # sweep again if res freqs changed by more than f_tol
        # or if tone amp change is more than A_tol
        if (np.any(np.abs(freqs - freqs_new) > f_tol*1e6) 
            or np.any(np.abs(1 - amps_new/amps) > A_tol)):
            sweep = True
            
        freqs, amps = freqs_new, amps_new

        # stop re-sweeping after loops_max sweeps
        # even if not in tolerances
        if loop_num > loops_max:
            sweep = False
        loop_num += 1
        
    io.save(io.file.f_res_targ, freqs)
    io.save(io.file.a_res_targ, amps)
    io.save(io.file.f_center_targ, f_center*1e6)

    # return np.array([freqs, amps])    
    return io.returnWrapperMultiple(
        [io.file.f_res_targ, io.file.a_res_targ], 
        [freqs, amps])
'''


# ============================================================================ #
# fullLoop
'''
def fullLoop(max_loops_full=2, max_loops_funcs=2, verbose=False):
    """
    Complete resonator calibration.

    max_loops_full:  (int) Max number of times to retry if fail.
    max_loops_funcs: (int) Similar to max_loops_full but for individual funcs.
    verbose:         (bool) All messages to standard out.
    """
    
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
            
        # vna sweep
        try: retry(vnaSweep, "Perform VNA sweep", f_center=600)
        except: fullFail(l); continue
        
        # find resonators
        try: retry(findResonators, "Finding resonators")
        except: fullFail(l); continue
        
        # target sweep
        try: retry(targetSweepLoop, "Perform target sweep loop", 
                  chan_bandwidth=0.2, f_center=600, N_steps=500, 
                  f_tol=0.1, A_tol=0.3, loops_max=20)
        except: fullFail(l); continue
        
        fullSuccess(l)
        break
'''