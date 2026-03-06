
# ============================================================================ #
# alcove_base_gen2.py
# Alcove commands common base.
# Compatible with gateware versions 15+ (gen2).
# James Burgoyne jburgoyne@phas.ubc.ca 
# Ruixuan (Matt) Xie  mattxie956@gmail.com
# Adrian Sinclair aksincla@asu.edu
# CCAT Prime 2025  
# ============================================================================ #



# ============================================================================ #
# IMPORTS & GLOBALS
# ============================================================================ #

import os

import alcove_commands.board_io as io
import queen_commands.control_io as cio

try: from config import board as cfg_b
except ImportError: cfg_b = None 

try: import xrfdc # type: ignore
except ImportError: xrfdc = None




# ============================================================================ #
# GENERAL FUNCTIONS
# ============================================================================ #


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
# safe_cast_to_int
def safe_cast_to_int(data_str):
    try:
        if isinstance(data_str, str):
            if data_str.lower().startswith('0x'):   # hex
                return int(data_str, 16)
            elif data_str.lower().startswith('0b'): # bin
                return int(data_str, 2)
            elif data_str.lower().startswith('0o'): # oct
                return int(data_str, 8)
        else:                                   # everything else
            return int(float(data_str)) # catches sci, underscores, etc.
    except (ValueError, SyntaxError) as e:
        # raise ValueError(f"Invalid integer string format: {data_str}") from e
        return None


# ============================================================================ #
# timestreamOn
def timestreamOn(on=True):
    '''Turn the UDP timestream on (or off) for the current drone.'''

    # input parameter casting
    on = str(on) in {True, 1, '1', 'True', 'true'}

    udp_control = cfg_b.gateware.udp_control.gpio_udp_info_control
    
    # current drone channel
    chan = cfg_b.drid

    # bit values for this drone (01 for on, 10 for off)
    val = 0b01 if on else 0b10

    # construct the 8-bit register value with all zeros except for this drone
    reg_value = val << ((chan - 1) * 2)

    # Write the new register value
    udp_control.write(0x00, reg_value)


# ============================================================================ #
# userPacketInfo 
def userPacketInfo(data):
    '''Write 16 bits of data to include in the UDP timestream packet.
    Data is drone specific.

    data: 16 bit int to write.8212+42
        Note that Redis will convert user input to string.
        e.g. 255 can be sent as:
            '255', '255.0', '0xFF', '0b11111111', '0o377'
        If conversion fails, then will write 0 instead.
    '''

    # input parameter casting
    data = safe_cast_to_int(data) # returns None if fails
    data = 0 if data is None else data # fails to 0
    data = data & 0xFFFF # ensure data is 16 bits

    udp_control = cfg_b.gateware.udp_control.gpio_udp_info_control

    # current drone channel
    chan = cfg_b.drid

    drone_shift = 16 # Shift for drone ID
    edge_trigger = 19 # Shift for edge-triggered write

    val = ((chan-1)<<drone_shift) | data

    # Write to tmp reg then trigger write to final reg
    udp_control.write(0x08, val)
    udp_control.write(0x08, (1<<edge_trigger) | val)  # edge trigger
    udp_control.write(0x08, val)


# ============================================================================ #
# writeChannelCount 
def writeChannelCount(num_chans):
    '''Write the number of channels to include in the UDP timestream packet.
    Drone specific.

    num_chans: (int) 16 bits, number of channels.
    '''

    # input parameter casting
    num_chans = safe_cast_to_int(num_chans) # returns None if fails
    num_chans = 0 if num_chans is None else num_chans # fails to 0
    num_chans = num_chans & 0xFFFF # ensure data is 16 bits

    udp_control = cfg_b.gateware.udp_control.gpio_udp_info_control

    # current drone channel
    chan = cfg_b.drid

    count_shift = 18 # Shift for count enable (as opposed to data)
    drone_shift = 16 # Shift for drone ID
    edge_trigger = 19 # Shift for edge-triggered write

    val = (1<<count_shift) | ((chan-1)<<drone_shift) | num_chans

    # Write to tmp reg then trigger write to final reg
    udp_control.write(0x08, val)
    udp_control.write(0x08, (1<<edge_trigger) | val)  # edge trigger
    udp_control.write(0x08, val)


# ============================================================================ #
# generateWaveDdr4 
def generateWaveDdr4(freqs, amps, phis):
    '''
    Generates a DDR4 waveform and associated phase correction data.

    This function synthesizes a waveform by summing multiple sinusoidal components defined by their frequencies, amplitudes, and phases. It also calculates the necessary phase correction values for subsequent signal processing, particularly for FFT-based operations.

    Args:
        freqs (numpy.ndarray): An array of frequencies (Hz) for each sinusoidal component.
        amps (numpy.ndarray): An array of amplitudes for each sinusoidal component.
        phis (numpy.ndarray): An array of initial phases (radians) for each sinusoidal component.

    Returns:
        tuple: A tuple containing:
            - x (numpy.ndarray): The generated waveform in the time domain (complex).
            - dphi (numpy.ndarray): An array of phase correction values (float64).
            - freqs_actual (numpy.ndarray): The actual frequencies used after quantization.
    '''
    
    import numpy as np

    # Ensure real values
    freqs = np.real(freqs)
    amps  = np.real(amps)
    phis  = np.real(phis)

    # System constants
    fs      = 512e6       # Sampling frequency (Hz). cfg_b.wf_fs
    lut_len = 2**20  # Lookup table length. cfg_b.wf_lut_len
    fft_len = 1024  # FFT length. cfg_b.wf_fft_len

    # Compute frequency bins
    k            = np.round(freqs/(fs/lut_len)).astype(np.int64)
    freqs_actual = k*(fs/lut_len)

    # Vectorized X assignment (frequency space)
    X    = np.zeros(lut_len, dtype=np.complex128)
    X[k] = np.exp(-1j*phis)*amps

    # Compute IFFT efficiently
    x = np.fft.ifft(X, norm='backward')*lut_len
    
    # Compute bin numbers & phase correction
    bin_num = np.round(freqs_actual/(fs/fft_len)).astype(np.int64)
    f_beat  = bin_num*(fs/fft_len) - freqs_actual
    dphi0   = (f_beat/(fs/fft_len))*2**16

    # Efficiently initialize dphi
    dphi = np.zeros(fft_len, dtype=np.float64)
    dphi[:len(dphi0)] = dphi0

    return x, dphi, freqs_actual


# ============================================================================ #
# _getSnapData
def _getSnapData(chan, mux_sel, wrap=False, wait=0.02):
    '''
    Fetch data from gateware DSP.
    
    Args:
        chan (int): 
            Channel index (1-4) specifying which readout chain to access.
        mux_sel:
            0: ADC outputs
            1: PSB outputs (DAC inputs)
            3: Receive outputs (time stream data)
    Returns:
        I, Q (numpy.ndarray):
            for data converter data, I and q are flat,
            for time stream data, I and Q have shape (n, bin)
    '''
    import numpy as np
    import time
    from pynq import MMIO
    
    # reset snap
    chan_access = _gateware_chan(cfg_b.gateware, chan)

    print('1')
    chan_access.GPIO.axi_gpio_3.write(0x08, 3)
    chan_access.GPIO.axi_gpio_3.write(0x08, 0)
    time.sleep(wait)
    print('2')
    base_addr_wide = {
        (1,0): 0x00_A001_0000, (1,1): 0x00_A001_0000, (1,3): 0x00_A002_0000,
        (2,0): 0x00_A003_0000, (2,1): 0x00_A003_0000, (2,3): 0x00_A004_0000,
        (3,0): 0x00_A005_0000, (3,1): 0x00_A005_0000, (3,3): 0x00_A006_0000,
        (4,0): 0x00_A007_0000, (4,1): 0x00_A007_0000, (4,3): 0x00_A008_0000,
    }[(chan, mux_sel)]
    print('3')        
    max_count = 65536  # 32x2048 = 65536
    mmio_wide_bram = MMIO(base_addr_wide , max_count)
    wide_data = mmio_wide_bram.array[0:16384]  # max/4, bram depth*word_bits/32bits
    print('4')
    I = np.zeros(8192)
    Q = np.zeros(8192)
    print('5')
    if mux_sel == 0:
        I[0::4] = np.int16(wide_data[4::8] & 0x0000ffff)
        Q[0::4] = np.int16(wide_data[6::8] & 0x0000ffff)
        I[1::4] = np.int16(wide_data[4::8] >> 16)
        Q[1::4] = np.int16(wide_data[6::8] >> 16)
        I[2::4] = np.int16(wide_data[5::8] & 0x0000ffff)
        Q[2::4] = np.int16(wide_data[7::8] & 0x0000ffff)
        I[3::4] = np.int16(wide_data[5::8] >> 16)
        Q[3::4] = np.int16(wide_data[7::8] >> 16)

    elif mux_sel == 1:
        I[0::4] = np.int16(wide_data[0::8] & 0x0000ffff)
        Q[0::4] = np.int16(wide_data[0::8] >> 16)
        I[1::4] = np.int16(wide_data[1::8] & 0x0000ffff)
        Q[1::4] = np.int16(wide_data[1::8] >> 16)
        I[2::4] = np.int16(wide_data[2::8] & 0x0000ffff)
        Q[2::4] = np.int16(wide_data[2::8] >> 16)
        I[3::4] = np.int16(wide_data[3::8] & 0x0000ffff)
        Q[3::4] = np.int16(wide_data[3::8] >> 16)

    elif mux_sel == 3:
        I[0::4] = (np.int32(wide_data[0::8])).astype("float")
        Q[0::4] = (np.int32(wide_data[2::8])).astype("float")
        I[1::4] = (np.int32(wide_data[3::8])).astype("float")
        Q[1::4] = (np.int32(wide_data[4::8])).astype("float")
        I[2::4] = (np.int32(wide_data[5::8])).astype("float")
        Q[2::4] = (np.int32(wide_data[6::8])).astype("float")
        I[3::4] = (np.int32(wide_data[7::8])).astype("float")
        Q[3::4] = (np.int32(wide_data[8::8])).astype("float") 
            
    # return I, Q

    if wrap:
        return io.returnWrapper(io.file.IQ_generic, (I,Q))
    else:
        return I, Q


# ============================================================================ #
# getSnapData
def getSnapData(mux_sel, wrap=True):
    chan = cfg_b.drid
    return _getSnapData(chan, int(mux_sel), wrap=wrap)


# ============================================================================ #
# getADCrms
def getADCrms():
    import numpy as np
    chan = cfg_b.drid
    I, Q = _getSnapData(chan,0,wrap=False)
    z = I + 1j*Q
    rms = np.sqrt(np.mean(z*np.conj(z)))
    print("RMS: ",rms)
    return


# ============================================================================ #
# _setNCLO
def _setNCLO(chan, lofreq):
    """
    Set numerically controlled local oscillator (NCLO) frequency for chan.

    Args:
        chan (int): Channel number (1-4) to configure.
        lofreq (float): Desired local oscillator frequency in MHz.
    """

    tb_indices = {1: [0,0,1,3], 2: [0,1,1,2], 3: [1,0,1,1], 4: [1,1,1,0]}
    if cfg_b.asu_board:
        tb_indices = {1: [1,0,1,3], 2: [1,1,1,2], 3: [0,1,1,0], 4: [0,0,1,1]}
    ii = tb_indices[chan]

    rf_data_conv = cfg_b.gateware.usp_rf_data_converter_0
    adc = rf_data_conv.adc_tiles[ii[0]].blocks[ii[1]]
    dac = rf_data_conv.dac_tiles[ii[2]].blocks[ii[3]]

    adc.MixerSettings['Freq'] = -lofreq
    dac.MixerSettings['Freq'] = lofreq
    adc.UpdateEvent(xrfdc.EVENT_MIXER)
    dac.UpdateEvent(xrfdc.EVENT_MIXER)


# ============================================================================ #
# _getNCLO
def _getNCLO(chan):
    """
    Get numerically controlled local oscillator (NCLO) frequency for chan.

    Args:
        chan (int): Channel number (1-4) to configure.

    Returns: (float): Desired local oscillator frequency in MHz.
    """

    tb_indices = {1: [0,0,1,3], 2: [0,1,1,2], 3: [1,0,1,1], 4: [1,1,1,0]}
    if cfg_b.asu_board:
        tb_indices = {1: [1,0,1,3], 2: [1,1,1,2], 3: [0,1,1,0], 4: [0,0,1,1]}
    ii = tb_indices[chan]

    rf_data_conv = cfg_b.gateware.usp_rf_data_converter_0
    adc = rf_data_conv.adc_tiles[ii[0]].blocks[ii[1]]
    dac = rf_data_conv.dac_tiles[ii[2]].blocks[ii[3]]

    return adc.MixerSettings['Freq']


# ============================================================================ #
# setNCLO
def setNCLO(f_lo):
    """
    setNCLO: set the numerically controlled local oscillator
           
    f_lo: center frequency in [MHz]
    """

    import numpy as np

    chan = cfg_b.drid
    f_lo = int(f_lo)
    _setNCLO(chan, f_lo)
    io.save(io.file.f_center_vna, f_lo*1e6)


# ============================================================================ #
# getNCLO
def getNCLO(chan=None):
    """Get the numerically controlled local oscillator value from register.
    """

    import numpy as np

    if chan is None:
        chan = cfg_b.drid

    f_lo = float(_getNCLO(chan))

    return f_lo


# ============================================================================ #
# _setNCLO2
def _setNCLO2(chan, lofreq):
    """
    Set the fine NCO (Numerically Controlled Oscillator) frequency
    for a specified channel.

    chan: The channel number (1-4) to configure.
    lofreq: (float) Desired NCO frequency in MHz.
    """

    import numpy as np

    try: # we don't want to kill the drone in normal operation

        # Compute digital tuning word
        dtw = int(np.round(lofreq*1e6 / cfg_b.freq_resolution))

        # Actual frequency that will be set
        # actual_freq_hz = dtw * cfg_b.freq_resolution

        # Write DTW to firmware register for the given channel
        chan_access = _gateware_chan(cfg_b.gateware, chan)
        chan_access.GPIO.axi_gpio_10.write(0x00, dtw)

    except Exception as e:
        print(f"_setNCLO2 error: {e}")


# ============================================================================ #
# _setAtten
def _setAtten(chan, direction, attenuation, v2025=True):
    """Sets the attenuation for a specified channel and direction.

    chan: The channel number (1-4) to configure.
    direction: The direction ('drive' or 'sense').
    attenuation: The desired attenuation level in dB (float).
    """

    if v2025:
        from alcove_commands.transceiver_serialdriver import Primecamfe as D
    else:
        from alcove_commands.transceiver_serialdriver import Transceiver as D

    try:
        chan = int(chan)
        attenuation = float(attenuation)

        atten_id = (chan - 1) + {'drive':0, 'sense':4}[direction]

        D(cfg_b.atten_device).set_atten(atten_id, attenuation)

    except Exception as e:
        print(f"_setAtten Error: {e}")


# ============================================================================ #
# _getAtten
def _getAtten(chan, direction):
    """Gets the attenuation for a specified channel and direction.
    Use with 2025 driver.
    """

    from alcove_commands.transceiver_serialdriver import Primecamfe as D

    try:
        chan = int(chan)

        atten_id = (chan - 1) + {'drive':0, 'sense':4}[direction]

        return D(cfg_b.atten_device).get_atten(atten_id)
        
    except Exception as e:
        print(f"_getAtten Error: {e}")


# ============================================================================ #
# setFineNCLO 
def setFineNCLO(df_lo):
    """
    setFineNCLO: set the fine frequency numerically controlled local oscillator
           
    df_lo: Center frequency shift, in [MHz].
    """

    chan = cfg_b.drid
    df_lo = float(df_lo)
    
    return _setNCLO2(chan, df_lo)


# ============================================================================ #
# createCustomCombFiles
def createCustomCombFiles(freqs_rf=None, amps=None, phis=None):
    """Create custom comb files from arrays.
    Used in tones.writeTargCombFromCustomList().
    """

    if freqs_rf is not None:    io.save(io.file.f_rf_tones_comb_cust, freqs_rf)
    if amps is not None:        io.save(io.file.a_tones_comb_cust, amps)
    if phis is not None:        io.save(io.file.p_tones_comb_cust, phis)


# ============================================================================ #
# createCustomCombFilesFromCurrentComb
def createCustomCombFilesFromCurrentComb(s='fap'):
    """Create custom comb files from the current comb.

    s: (str) Which files to write, e.g. 'f' is freqs.
    """

    f_comb = a_comb = p_comb = None
    if 'f' in s:
        f_comb = io.load(io.file.f_rf_tones_comb)

    if 'a' in s:  
        a_comb = io.load(io.file.a_tones_comb)

    if 'p' in s:
        p_comb = io.load(io.file.p_tones_comb)

    createCustomCombFiles(freqs_rf=f_comb, amps=a_comb, phis=p_comb)


# ============================================================================ #
# loadCustomCombFiles
def loadCustomCombFiles():
    """Load custom comb files into arrays.
    Used in tones.writeTargCombFromCustomList().
    """
    
    freqs_rf = io.load(io.file.f_rf_tones_comb_cust)
    amps     = io.load(io.file.a_tones_comb_cust)
    phis     = io.load(io.file.p_tones_comb_cust)

    return freqs_rf, amps, phis


# ============================================================================ #
# modifyCustomCombAmps
def modifyCustomCombAmps(factor=1):
    """Modify custom tone amps file by multiplying by given factor.
    """
    
    amps     = io.load(io.file.a_tones_comb_cust)
    amps *= float(factor)
    io.save(io.file.a_tones_comb_cust, amps)

# ============================================================================ #
# setAtten2025
def setAtten2025(direction, atten, v2025=True):
    """Set RF attenuator values on Arduino controlled RF gain board.

    direction: (str) "sense" or "drive".
    atten: (float) Attenuation value in dB, {0,31.75}.
    """

    chan = cfg_b.drid
    atten = float(atten)
    direction = str(direction)

    return _setAtten(chan, direction, atten, v2025=v2025)


# ============================================================================ #
# setAtten2024
def setAtten2024(direction, atten):
    return setAtten2025(direction, atten, v2025=False)


# ============================================================================ #
# getAtten
def getAtten(direction):
    """Get RF attenuator values on Arduino controlled RF gain board.
    
    direction: (str) "sense" or "drive".

    Return: atten: (float) Attenuation value in dB.
    """

    chan = cfg_b.drid
    direction = str(direction)

    atten = _getAtten(chan, direction)

    print(f"getAtten: direction={direction}, atten={atten}")

    return atten