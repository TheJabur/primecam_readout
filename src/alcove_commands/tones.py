# ============================================================================ #
# tones.py
# Tone and comb functions and commands.
# James Burgoyne jburgoyne@phas.ubc.ca 
# Adrian Sinclair aksincla@asu.edu
# CCAT Prime 2025  
# ============================================================================ #

from alcove_commands import alcove_base
import alcove_commands.board_io as io

try: from config import board as cfg_b
except ImportError: cfg_b = None 



# ============================================================================ #
# _firmware_chan
def _firmware_chan(firmware, chan):
    return {
        1: firmware.chan1,
        2: firmware.chan2,
        3: firmware.chan3,
        4: firmware.chan4,
    }[chan]


# ============================================================================ #
# setAccumLength
def setAccumLength():
    """
    Sets the accumulation length in the DSP registers, determining sample rate.

    This function configures the `accum_len` register within the DSP registers, 
    which controls the clock division and consequently the detector sample rate. 

    Note:
        - The function relies on `cfg_b.firmware`, `cfg_b.drid`, 
          and `cfg_b.accum_len`.
        - The DSP register layout is as follows:
            - 0x00: fft_shift[9:0], load_bins[22:12], lut_counter_rst[11]
            - 0x04: bin_num[9:0]
            - 0x08: accum_len[23:0], accum_rst[24], sync_in[26] (start dac)
            - 0x0c: dds_shift[8:0]
        - The clock source is assumed to be 512 MHz.
    """

    dsp_regs = _firmware_chan(cfg_b.firmware, cfg_b.drid).dsp_regs_0
    dsp_regs.write(0x08, cfg_b.accum_len)


# ============================================================================ #
# _resetAccumAndSync
def _resetAccumAndSync(chan, freqs):
    '''Resets the accumulator and synchronizes the DAC.

    chan: The channel identifier (not used anymore - backwards compatible).
    freqs (list or numpy.ndarray): A list or array of frequencies, used to determine the FFT shift value.
    '''

    dsp_regs = _firmware_chan(cfg_b.firmware, cfg_b.drid).dsp_regs_0

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

    fs = cfg_b.wf_fs # 512e6 
    lut_len = cfg_b.wf_lut_len # 2**20
    fft_len = cfg_b.wf_fft_len # 1024
    k = np.int64(np.round(-freq_list/(fs/lut_len)))
    freq_actual = k*(fs/lut_len)
    bin_list = np.int64(np.round(freq_actual / (fs / fft_len)))
    pos_bin_idx = np.where(bin_list > 0)
    if np.size(pos_bin_idx) > 0:
        bin_list[pos_bin_idx] = fft_len - bin_list[pos_bin_idx]
    bin_list = np.abs(bin_list)

    dsp_regs = _firmware_chan(cfg_b.firmware, cfg_b.drid).dsp_regs_0
    # firmware.chan1.dsp_regs_0

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
    ddr4mux = cfg_b.firmware.axi_ddr4_mux
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


# ============================================================================ #
# _writeComb
def _writeComb(chan, freqs, amps, phi):
   
    import numpy as np

    if np.size(freqs)<1:
        # what do we want to do if freqs empty?
        raise Exception("freqs must not be empty.")

    # freqs *= freqOffsetFixHackFactor() # Fequency offset fix
     # implemented in tones._writeComb and alcove_base._setNCLO
    wave, dphi, freq_actual = alcove_base.generateWaveDdr4(freqs, amps, phi)
    # write number of channels to 16 bit value in UDP packet
    alcove_base.writeChannelCount(len(freqs))
    #wave_real, wave_imag = _normWave(wave, max_amp=2**15-1)
    wave_real, wave_imag = wave.real.astype("int16"), wave.imag.astype("int16") 
    _waveAmpTest(wave, max_amp=2**15-1)
    _loadDdr4(chan, wave_real, wave_imag, dphi)
    _loadBinList(chan, freq_actual)
    _resetAccumAndSync(chan, freq_actual)

    f_center   = io.load(io.file.f_center_vna) # Hz
    freqs_rf_actual = freq_actual + f_center 

    # save the current comb
    io.save(io.file.f_rf_tones_comb, freqs_rf_actual)
    io.save(io.file.a_tones_comb, amps)
    io.save(io.file.p_tones_comb, phi)

    return freq_actual


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
