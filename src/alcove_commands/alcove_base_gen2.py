# ============================================================================ #
# alcove_base_gen2.py
# Alcove commands common base for gen2.
# James Burgoyne jamesrburgoyne@icloud.com
# Ruixuan (Matt) Xie  mattxie956@gmail.com
# CCAT 2026
# ============================================================================ #

import os
import time
import mmap
import numpy as np

import alcove_commands.board_io as io
import queen_commands.control_io as cio

try: from config import board as cfg_b
except ImportError: cfg_b = None 

try: import xrfdc # type: ignore
except ImportError: xrfdc = None

import gateware as gw




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
# setSamplingStartTime
def setSamplingStartTime(timestamp):
    '''Set the board detector sample collection start time.

    Args:
        timestamp (uint32): Timestamp in seconds. PTP epoch.
    '''

    int(timestamp)

    if not (0 <= timestamp <= 4294967295):
        print("Input must be a 32-bit unsigned integer.")
        return

    gw.gw_chan(1).GPIO.axi_gpio_0.write(0x8, timestamp)


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
# _checkWaveformOverflow
def _checkWaveformOverflow() -> bool:
    """Sample the waveform register to test for DAC overflow.
    
    Returns:
        bool: True if any overflow was detected, False otherwise.
    """

    import time

    chan = cfg_b.drid
    gwc = gw.gw_chan(chan)

    # Reset trigger
    C = cfg_b.C[chan]
    gwc.GPIO.axi_gpio_5.write(0x00, int(0b111<<29 | int(C)))
    gwc.GPIO.axi_gpio_5.write(0x00, int(C))

    # Wait for at least a full waveform to make sure overflow triggered
    time.sleep(0.002)

    # Check if overflow has been triggered
    ov_flag = gwc.GPIO.axi_gpio_5.read(0x08)

    _OV_HELP = { # order matters here
        "psb-ifft": "vIFFT internal overflow -- increase IFFT_scale",
        "psb-overlap-add": "PFB overlap-add overflow -- increase IFFT_scale",
        "psb-post-scale": "constant multiplier saturating -- reduce PSB_scale",
    }
    has_overflow = False
    for i, name in enumerate(_OV_HELP.keys()):
        if ov_flag & (1 << i):
            has_overflow = True
            msg = _OV_HELP.get(name, "reported by gateware.")
            print(f"Overflow detected - {name}: {msg}")

    if not has_overflow:
        print("Overflow not detected.")

    return has_overflow


# ============================================================================ #
# _findOptimalScaleFactors
def _findOptimalScaleFactors(N):
    """Find optimal scale factors for N resonators.
    """

    # TODO: find the optimal values for N
    # LUT?

    IFFT_scale = 7
    PSB_scale  = 1.0
    FFT_scale = 3

    return (IFFT_scale, PSB_scale, FFT_scale)


# ============================================================================ #
# _checkScaleFactors
def _checkScaleFactors(IFFT_scale, PSB_scale, FFT_scale, LOG2N):
    """Check that the scale factor are reasonable.
    Returns a Tuple of Bools, e.g. (True, True, True).
    """

    MIN_PSB_SCALE = 1.0
    MAX_PSB_SCALE = 2.0

    # Running checks [IFFT_scale, PSB_scale, FFT_scale]
    valid = [True, True, True] # Assume all are valid

    # IFFT_scale checks

    if not isinstance(IFFT_scale, (int, np.integer)):
        print(f"Error: IFFT_scale must be an integer.")
        valid[0] = False

    if not (1 <= IFFT_scale <= LOG2N+1):
        print(f"Error: IFFT_scale must be in range [1, {LOG2N}+1].")
        valid[0] = False

    # PSB_scale checks

    if not isinstance(PSB_scale, (float, np.floating)):
        print(f"Error: PSB_scale must be a float.")
        valid[1] = False

    if not (MIN_PSB_SCALE <= PSB_scale <= MAX_PSB_SCALE):
        print(f"Error: PSB_scale must be in range [{MIN_PSB_SCALE}, {MAX_PSB_SCALE}].")
        valid[1] = False

    #  FFT_scale checks

    if not isinstance(FFT_scale, (int, np.integer)):
        print(f"Error: FFT_scale must be an integer.")
        valid[2] = False

    if not (0 <= FFT_scale <= LOG2N):
        print(f"Error: FFT_scale must be in range [0, {LOG2N}].")
        valid[2] = False

    return valid


# ============================================================================ #
# setScaleFactors
def setScaleFactors(IFFT_scale, PSB_scale, FFT_scale):
    """Set the scale factors into fabric.
    """

    chan = cfg_b.drid
    gwc = gw.gw_chan(chan)

    LOG2N   = 11 # both transforms are 2048-point -> 11-bit SI bus
    C_WIDTH = 32

    # Type enforcement
    IFFT_scale = int(IFFT_scale)
    PSB_scale = float(PSB_scale)
    FFT_scale = int(FFT_scale)

    # Check factors: Fallback to defaults if needed
    valid = _checkScaleFactors(IFFT_scale, PSB_scale, FFT_scale, LOG2N)
    IFFT_scale = IFFT_scale if valid[0] else 7
    PSB_scale  = PSB_scale  if valid[1] else 1.0
    FFT_scale = FFT_scale if valid[2] else 3

    # IFFT and FFT Scales
    # -1 on IFFT_scale for halfing in pipeline
    SI_tx = ((1 << (IFFT_scale-1)) - 1) << (LOG2N - (IFFT_scale-1))
    SI_rx = ((1 << FFT_scale) - 1) << (LOG2N - FFT_scale)
    gwc.GPIO.axi_gpio_4.write(0x08, int(SI_tx<<11 | SI_rx))
    
    # PSB Scale
    C = int(round(2**16 * PSB_scale))
    gwc.GPIO.axi_gpio_5.write(0x00, int(C))
    cfg_b.C[chan] = C # save in config


# ============================================================================ #
# setScaleFactorsFromConfig
def setScaleFactorsFromConfig():

    chan = cfg_b.drid
    scale_factors = cfg_b.scale_factors[chan]

    IFFT_scale = int(scale_factors[0])
    PSB_scale = float(scale_factors[1])
    FFT_scale = int(scale_factors[2])

    setScaleFactors(IFFT_scale, PSB_scale, FFT_scale)


# ============================================================================ #
# _getSnapData
def _getSnapData(chan, mux_sel, wrap=False, wait=0.02):
    '''
    Fetch data from gateware DSP using direct Linux /dev/mem mmap.
    
    Args:
        chan (int): 
            Channel index (1-4) specifying which readout chain to access.
        mux_sel:
            0: ADC outputs
            1: PSB outputs (DAC inputs)
            3: Receive outputs (time stream data)
    Returns:
        I, Q (numpy.ndarray):
            for data converter data, I and Q are flat,
            for time stream data, I and Q have shape (n, bin)
    '''

    # Reset snap
    gwc = gw.gw_chan(chan)
    gwc.GPIO.axi_gpio_3.write(0x08, 3)
    gwc.GPIO.axi_gpio_3.write(0x08, 0)
    time.sleep(wait)
    
    base_addr_wide = {
        (1,0): 0x00_A001_0000, (1,1): 0x00_A001_0000, (1,3): 0x00_A002_0000,
        (2,0): 0x00_A003_0000, (2,1): 0x00_A003_0000, (2,3): 0x00_A004_0000,
        (3,0): 0x00_A005_0000, (3,1): 0x00_A005_0000, (3,3): 0x00_A006_0000,
        (4,0): 0x00_A007_0000, (4,1): 0x00_A007_0000, (4,3): 0x00_A008_0000,
    }[(chan, mux_sel)]
    
    max_bytes = 65536  # 32x2048 words * 4 bytes = 65536 bytes
    
    # Open physical memory and map the address space
    fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    try:
        # Align offset to page size boundary if necessary (AXI base addresses here are 64KB aligned)
        mem = mmap.mmap(
            fd, 
            length=max_bytes, 
            flags=mmap.MAP_SHARED, 
            prot=mmap.PROT_READ | mmap.PROT_WRITE, 
            offset=base_addr_wide
        )
        try:
            # Read 16384 32-bit words directly into numpy
            wide_data = np.frombuffer(mem, dtype=np.uint32, count=16384)
            
            I = np.zeros(8192)
            Q = np.zeros(8192)

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
                Q[0::4] = (np.int32(wide_data[1::8])).astype("float")
                I[1::4] = (np.int32(wide_data[2::8])).astype("float")
                Q[1::4] = (np.int32(wide_data[3::8])).astype("float")
                I[2::4] = (np.int32(wide_data[4::8])).astype("float")
                Q[2::4] = (np.int32(wide_data[5::8])).astype("float")
                I[3::4] = (np.int32(wide_data[6::8])).astype("float")
                Q[3::4] = (np.int32(wide_data[7::8])).astype("float") 
        finally:
            mem.close()
    finally:
        os.close(fd)

    if wrap:
        return io.returnWrapper(io.file.IQ_generic, (I,Q))
    else:
        return I, Q
 

# ============================================================================ #
# getSnapData
def getSnapData(mux_sel, wrap=True, wait=0.02):
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

    tb_indices,_ = gw.portMapping(
        cfg_b.gateware_version, cfg_b.gateware_version_minor)

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

    tb_indices,_ = gw.portMapping(
        cfg_b.gateware_version, cfg_b.gateware_version_minor)

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
        gwc = gw.gw_chan(chan)
        gwc.GPIO.axi_gpio_10.write(0x00, dtw)

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

        with D(cfg_b.atten_device) as dev:
            dev.set_atten(atten_id, attenuation)

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

        with D(cfg_b.atten_device) as dev:
            return dev.get_atten(atten_id)
        
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
    
    amps = io.load(io.file.a_tones_comb_cust)
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


# ============================================================================ #
# findScaleFactors
def findScaleFactors(N):
    """Find the optimal scaling factors for N tones.
    These determine the relationship between amps and output power,
    as well as floating point resolution within waveform generation.
    Altering them will affect both.
    This function is specifically provided to find optimal values
    for the expected number of tones (resonators) on this RF network.
    It is expected that these values will not be changed once set.

    NOTE: These must be set in the board config after finding!

    Args:
        N (int): Expected number of resonators on this RF network.
    """

    if N is None:
        print("findScaleFactors: Require N (# of tones)")
        return

    scale = _findOptimalScaleFactors(N) # (IFFT, PSB, FFT)

    print((f"Optimal scales (N={N}): "
          f"IFFT={scale[0]}, PSB={scale[1]}, FFT={scale[2]}. "
          f"Set scales in board config!"))
    
    return {'IFFT':scale[0], 'PSB':scale[1], 'FFT':scale[2]}


# ============================================================================ #
# checkWaveformOverflow
def checkWaveformOverflow():
    """Sample the waveform to test for DAC overflow.
    """

    return _checkWaveformOverflow()