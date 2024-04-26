# ============================================================================ #
# tones.py
# Tone and comb functions and commands.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2024  
# ============================================================================ #

from alcove_commands.alcove_base import *


# ============================================================================ #
# _loadBinList
def _loadBinList(chan, freq_list):

    import numpy as np

    fs = 512e6
    fft_len = 1024
    lut_len = 2**20
    k = np.int64(np.round(-freq_list/(fs/lut_len)))
    freq_actual = k*(fs/lut_len)
    bin_list = np.int64(np.round(freq_actual / (fs / fft_len)))
    pos_bin_idx = np.where(bin_list > 0)
    if np.size(pos_bin_idx) > 0:
        bin_list[pos_bin_idx] = 1024 - bin_list[pos_bin_idx]
    bin_list = np.abs(bin_list)
    # DSP REGS
    if chan == 1:
        dsp_regs = firmware.chan1.dsp_regs_0
    elif chan == 2:
        dsp_regs = firmware.chan2.dsp_regs_0
    elif chan == 3:
        dsp_regs = firmware.chan3.dsp_regs_0
    elif chan == 4:
        dsp_regs = firmware.chan4.dsp_regs_0
    else:
        return "Does not compute"
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
# _resetAccumAndSync
def _resetAccumAndSync(chan, freqs):
    if chan == 1:
        dsp_regs = firmware.chan1.dsp_regs_0
    elif chan == 2:
        dsp_regs = firmware.chan2.dsp_regs_0
    elif chan == 3:
        dsp_regs = firmware.chan3.dsp_regs_0
    elif chan == 4:
        dsp_regs = firmware.chan4.dsp_regs_0
    else:
        return "Does not compute"
    # dsp_regs bitfield map
    # 0x00 -  fft_shift[9 downto 0], load_bins[22 downto 12], lut_counter_rst[11 downto 11] 
    # 0x04 -  bin_num[9 downto 0]
    # 0x08 -  accum_len[23 downto 0], accum_rst[24 downto 24], sync_in[26 downto 26] (start dac)
    # 0x0c -  dds_shift[8 downto 0]
    # initialization
    sync_in = 2**26
    accum_rst = 2**24  # (active rising edge)
    accum_length = (2**19)-1
    
    fft_shift=0
    if len(freqs)<400:
        fft_shift = 2**9-1 #2**9-1
    else:
        fft_shift = 2**5-1 #2**2-1
    dsp_regs.write(0x00, fft_shift) # set fft shift
    ########################
    dsp_regs.write(0x08, accum_length | sync_in)
    dsp_regs.write(0x08, accum_length | accum_rst | sync_in)
    dsp_regs.write(0x0c, 180) # 260)
    return


# ============================================================================ #
# _loadDdr4
def _loadDdr4(chan, wave_real, wave_imag, dphi):

    import numpy as np
    from pynq import MMIO

    if chan == 1:
        base_addr_dphis = 0xa004c000
    elif chan == 2:
        base_addr_dphis = 0xa0040000
    elif chan == 3:
        base_addr_dphis = 0xa0042000
    elif chan == 4:
        base_addr_dphis = 0xa004e000
    else:
        return "Does not compute"
    
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
    ddr4mux = firmware.axi_ddr4_mux
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
def genAmpsAndPhis(
        freqs, amp_max=(2**15-1), amp_factor_init=0.36, phase_loops=10):
    '''Generate the amps and phis from given freqs for a tone comb.
    
    freqs: (1D array of floats) The tone placement frequencies. 
    amp_max: (float) The maximum waveform amplitude allowed (DAC limited). 
    amp_factor_init (float) Initial amp_max factor to try.
        0.36 usually has a quick solution (11+/-5 loops).
    phase_loops: (float) Max number of loops with random phases.
    '''
    
    import numpy as np    
    
    def ampPeak(freqs, amps, phis):
        x, _, _ = generateWaveDdr4(freqs, amps, phis)
        x.real, x.imag = x.real.astype("int16"), x.imag.astype("int16")
        return np.max(np.abs(x.real + 1j*x.imag))
    
    N = len(freqs)
    
    for amp_factor in np.arange(amp_factor_init, 0, -0.02):
        amps = np.ones(N)*amp_max*amp_factor/np.sqrt(N)
           
        for _ in range(phase_loops):
            phis = np.random.uniform(-np.pi, np.pi, N) # phases

            if ampPeak(freqs, amps, phis) < amp_max:
                return amps, phis


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

    wave, dphi, freq_actual = generateWaveDdr4(freqs, amps, phi)
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
    
    chan = cfg.drid # drone (chan) id is from config
    freqs = np.array(np.linspace(50e6, 255.00e6, 1))
    amps = np.ones(1)*(2**15 - 1)
    phi=np.array([np.pi])
    freq_actual = _writeComb(chan, freqs, amps, phi)


# ============================================================================ #
# writeNewVnaComb
def writeNewVnaComb(freq_noise=5_000):
    """Create and write the vna sweep tone comb.

    freq_noise: (float) Frequency noise to add to the tone placement.
        This uses a uniform distribution of noise. [Hz]
    """

    import numpy as np

    freq_noise = float(freq_noise)
    
    chan = cfg.drid # drone (chan) id is from config

    freqs_bb = np.array(np.linspace(-254.4e6, 255.00e6, 1000))
    # freqs_bb += np.random.uniform(-freq_noise, freq_noise, len(freqs_bb))

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

    chan = cfg.drid

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

    chan = cfg.drid

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

    chan = cfg.drid

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

    # chan = cfg.drid

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

    chan = cfg.drid

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