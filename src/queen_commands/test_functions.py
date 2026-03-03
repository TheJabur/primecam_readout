# ============================================================================ #
# queen_commands/test_functions.py
# Testing functions which run on the control computer.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2025
# ============================================================================ #

import numpy as np
import time
import traceback
from collections import deque

import queen
import alcove
import alcove_commands.alcove_base as alcove_base
import queen_commands.control_io as io
from timestream import TimeStream, parsePtpTimestamp
from bluefors_controller import BlueFTController




# ============================================================================ #
# _sendCom
def _sendCom(bid, drid, com_str, args_str=None):
    """
    """

    com_num = alcove.comNumFromStr(com_str)
    return queen.alcoveCommand(
        com_num, bid=bid, drid=drid, all_boards=False, args=args_str)


# ============================================================================ #
# _sendComAll
def _sendComAll(com_str, args_str=None):
    """
    """

    com_num = alcove.comNumFromStr(com_str)
    return queen.alcoveCommand(
        com_num, all_boards=True, args=args_str)


# ============================================================================ #
# _captureTimestream
def _captureTimestream(N_packets, timestream=None):
    """
    fs = 512e6/(1024*1024) # 488.28125 Hz
    e.g. N_packets=1000 is 2.048 s timestream
    """

    if not timestream:
        ip = "192.168.3.40" # TODO: get from cfg
        port = 4096

        timestream = TimeStream(host=ip, port=port)

    # print(timestream)

    # capture an N packets timestream
    timestream.capturePackets(N_packets) 

    # get the sender IPs
    packet_ips = timestream.packetsIP()

    # slice out II and QQ tods (1024 channel I and Q arrays)    
    II, QQ = timestream.packetsIIQQ()

    # slice out packet info and convert from bytes
    packet_infos = np.array([
        int.from_bytes(p, byteorder='big')
        for p in timestream.packetsHH('packet info')]) 
    
    # slice out channel count and convert from bytes
    channel_counts = np.array([
        int.from_bytes(p, byteorder='big')
        for p in timestream.packetsHH('channel count')]) 

    # slice out packet count tod and convert from bytes
    packet_counts = np.array([
        int.from_bytes(p, byteorder='big')
        for p in timestream.packetsHH('packet count')])    
    
    # slice out ptp timestamps tod
    ptp_timestamps = np.array([
        # parsePtpTimestamp(p)
        parsePtpTimestamp(p)
        for p in timestream.packetsHH('ptp timestamp')
    ])

    return timestream, II, QQ, packet_counts, ptp_timestamps, packet_infos, channel_counts, packet_ips


# ============================================================================ #
# _progressBar
def _progressBar(i, N, msg="", S=10):
    """Progress bar.
    """

    s = int((i/N)*S) 
    bar = f"[{'▮'*s}{'_'*(S-s)}]"
    end = '\r' if i<N else '\n'
    print(f"{msg} {bar} ({i}/{N})", end=end)


# ============================================================================ #
# _setupBlueforsController
def _setupBlueforsController():

    # avoid warnings if no https connection can be established
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    controller = BlueFTController(
        # ip   = '192.168.62.210', 
        ip   = '192.168.0.186', 
        port = 49098, 
        key  = '868c978c-9375-4e74-ae98-512725fe5934', 
        mixing_chamber_channel_id = 6,
        mixing_chamber_heater_id = 4
        )

    # active_channels = [1, 2, 5, 6]

    return controller

# Base – 300 mK:
# In this temperature region, the DR can be operated normally. Simply set the desired value to the PID controller and let it do the job. The PID parameters: P=0.001, I=50, D=0.
# Just in case, set the maximum allowed heater value to 1 mW.

# 300 – 800 mK:
# Still heating should be switched off, parameter P = 0.01, and I = 250 to make it faster to reach the desired temperature. The maximum allowed heater value can be set to 100 mW.

# 800 mK – 4 K:
# The turbo pump should be switched off. At some point above 1 K, the pressure p4 will increase above 1 bar, and the overpressure protection valve BPV3 will allow the mixture back into the tanks. When this happens, valve V13 can be opened to set the system in safe circulation mode. Since the main source of cooling power is changing from mixing 3He to 4He to evaporating the mixture, it will take a longer time for the system to reach the setpoint temperature. The maximum allowed heater value can be set to 1 W.


# ============================================================================ #
# _waitForBlueforsTemperatureStable
def _waitForBlueforsTemperatureStable(
    controller,
    setpoint,
    sample_period=60.0,          # seconds
    window_size=10,              # number of samples
    tol_mean=0.002,              # K
    tol_slope=1e-4,              # K / minute
    tol_std=0.001,               # K
    timeout=None                 # seconds, or None
):
    """
    Blocks until temperature is stable according to slope + variance criteria.
    """

    temps = deque(maxlen=window_size)
    times = deque(maxlen=window_size)
    t_start = time.time()
    while True:

        print(f"temps={temps}")
        print(f"times={times}")

        temps.append(controller.get_mxc_temperature())
        times.append(time.time())

        if len(temps) == window_size: # wait for enough samples
            T_arr = np.array(temps)
            t_arr = np.array(times)

            # Mean & std
            T_mean = T_arr.mean()
            T_std = T_arr.std()

            # Linear slope (K / minute)
            t_min = (t_arr - t_arr[0]) / 60.0
            slope, _ = np.polyfit(t_min, T_arr, 1)

            if (abs(T_mean - setpoint) < tol_mean and
                abs(slope) < tol_slope and
                T_std < tol_std):
                return True

        if (timeout is not None and
            (times[-1] - t_start) > timeout):
            return False

        time.sleep(sample_period)




# ============================================================================ #
# TESTS
# ============================================================================ #

# _sendCom()
# _sendComAll()

# _sendComAll("setNCLO", nclo)
# _sendComAll("startChains")

# _sendComAll("writeNewVnaComb")
# _sendComAll("vnaSweep")
# _sendComAll("findVnaResonators")

# _sendComAll("writeTargCombFromVnaSweep")
# _sendComAll("targetSweep")
# _sendComAll("findTargResonators")
# _sendComAll("writeTargCombFromTargSweep")

# _sendComAll("timestreamOn", 1)

# _sendComAll("modifyCustomCombAmps",factor)
# _sendComAll("writeCombFromCustomList")
# _sendComAll("createCustomCombFilesFromCurrentComb")

# _sendComAll("findCalTones")


# ============================================================================ #
# tls_array_test
def tls_array_test():
    """
    TLS test array test.

    Quantify how long this will take.
    Max current through heater?
    Attenuate enough that final tone power doesn't exceed DAC max.
    Confirm attenuation with VNA first.

    Timestreams are ~4 MB/s for a single drone.
        For a 60 s tod with 4 drones: ~1 GB
    """

    # ASSUMING SINGLE DRONE RUNNING!

    print("TLS test starting.")
    
    t_start = time.time()

    # config
    nclo = 600 # MHz
    fs = 512e6/1024/1024 # samples per second (~488 Hz) (single drone)
    timestream = TimeStream(host="192.168.3.40", port=4096)
    bid = 1
    drid = 1

    def sendCom(com_str, args_str=None):
        return _sendCom(bid, drid, com_str, args_str)
    
    # test params
    steps_temp = [50, 75, 100, 125, 150, 175, 200, 300, 400, 500] # mK
    t_stabilize_max = 2*60*60 # max seconds trying to stabilize T before giving up
    steps_tone = [-10, -8, -5, -2, 0] # dB
    t_tod = 60 # s; tod length at each step
    
    # setup the bluefors controller
    controller = _setupBlueforsController()

    # startup the timestream
    sendCom("setNCLO", nclo)
    sendCom("timestreamOn", 1)

    # number of steps
    N_steps_T = len(steps_temp) # temp steps
    N_steps_P = len(steps_tone) # tone power steps
    N_steps = N_steps_T*N_steps_P # total steps

    # number of packets to collect at each step
    N_packets_tod = int(t_tod*fs) 
    N_packets_total = N_packets_tod*N_steps

    i_T = i_P = 0
    msg = f"Running: (max {N_steps_T*t_stabilize_max} s; {N_packets_total} packets):"
    # _progressBar(i_T*N_steps_P + i_P + 1, N_steps, msg)

    status = controller.toggle_mxc_heater('on')

    for i_T,T in enumerate(steps_temp): # step in temperature
        
        # set step cryostat temperature
        status = controller.set_mxc_heater_setpoint(T)
        T_stablized = _waitForBlueforsTemperatureStable( # TODO: check this func
            controller, T, timeout=t_stabilize_max)
        if not T_stablized: 
            break # T didn't stabilise, end test

        for i_P,P in enumerate(steps_tone): # step in probe tone power
            
            # perform a vna sweep (roughly identfy resonances)
            sendCom("writeNewVnaComb")
            sendCom("vnaSweep") # ~ 15 s
            sendCom("findVnaResonators")
            # width_min, width_max, peak_prom_db, peak_dis
            # min width: 5 bins. 1 bin is 500 MHz / (1000 tones * 500 steps) = 5 kHz

            # perform a target sweep (higher resolution to find resonance)
            sendCom("writeTargCombFromVnaSweep")
            sendCom("targetSweep") # ~ 15 s
            sendCom("findTargResonators")
            sendCom("writeTargCombFromTargSweep")

            # create the custom comb files
            if i_T == i_P == 0: # first temp and first tone power
                # for very first test, create all custom comb files
                sendCom("createCustomCombFilesFromCurrentComb", 'fap')
            else:
                # but for subsequent tests don't touch amplitudes
                sendCom("createCustomCombFilesFromCurrentComb", 'fp')

            # change tone amplitudes for this step
            Pl = steps_tone[i_P-1] if i_P>0 else 0
            factor = 10**((P - Pl)/20) # amp factor for last step to this step
            sendCom("modifyCustomCombAmps", factor)

            # write custom comb
            sendCom("writeCombFromCustomList")
            # comb should now be on resonances
            # with amplitudes adjusted for this step
            # adjust initial tone power tuning to test max

            # take timestreams
            packets = _captureTimestream(N_packets_tod, timestream)

            # save timestreams as separate files
            test_name = f"tls_{T}_{P}_"
            packets_tod, packets_I, packets_Q, packets_count, packets_ts, packets_info, packets_chans, packets_ip = packets
            io.saveToTmp(packets_ip, filename=f'{test_name}_ip_', use_timestamp=True)
            io.saveToTmp(packets_I, filename=f'{test_name}_I_', use_timestamp=True)
            io.saveToTmp(packets_Q, filename=f'{test_name}_Q_', use_timestamp=True)
            io.saveToTmp(packets_info, filename=f'{test_name}_info_', use_timestamp=True)
            io.saveToTmp(packets_count, filename=f'{test_name}_count_', use_timestamp=True)
            io.saveToTmp(packets_chans, filename=f'{test_name}_chans_', use_timestamp=True)
            io.saveToTmp(packets_ts, filename=f'{test_name}_ts_',  use_timestamp=True)
            
            _progressBar(i_T*N_steps_P + i_P + 1, N_steps, msg)

    status = controller.toggle_mxc_heater('off')

    if not T_stablized:
        print(f"Test ended prematurely: (T={T} didn't stabilise).")

    print(f"TLS test complete. Elapsed time: {time.time() - t_start:.6f} seconds")

    sendCom("timestreamOn", 0)


# ============================================================================ #
# loopbackCapture
def loopbackCapture():

    print("Running loopback capture...")

    packet_per_second = 488 # 512e6/2**20
    # packet_per_second = 976
    t_obs = 60 # s, ~1 GB @ 488 Hz
    # t_obs = 30 # s, ~1 GB @ 976 Hz
    # N_packets = 4*packet_per_second*t_obs
    N_packets = packet_per_second*t_obs
    # N_packets = 4096*4 # 4096 samples ~ 8.4 s
    # N_packets = 10

    # _sendCom(bid, drid, "setNCLO", 600)        # set LO
    # _sendComAll("writeNewVnaComb")     # gen. tone comb
    # _sendComAll("timestreamOn", 1)     # start streaming

    # N_packets = 1

    start = time.time()

    print(f" Assumed packet rate = {packet_per_second} /s")
    print(f" Expected number of packets = {N_packets}")
    print(f" Obs. length = {t_obs} s")
    print(f" Start time = {start}")

    print(f" Attempting to capture packets...", end='')
    packets = _captureTimestream(N_packets)    # capture tods
    print(f"success!")
    print(f" Elapsed time: {time.time() - start:.6f} seconds")

    # _sendComAll("timestreamOn", 0)     # stop streaming

    timestream, II, QQ, packet_counts, ptp_timestamps, packet_infos, channel_counts, packet_ips = packets

    fname = io.saveToTmp(packet_ips, filename=f'loopback_packet_ips_', 
                         use_timestamp=True)
    fname = io.saveToTmp(II, filename=f'loopback_II_', 
                         use_timestamp=True)
    fname = io.saveToTmp(QQ, filename=f'loopback_QQ_', 
                         use_timestamp=True)
    fname = io.saveToTmp(packet_infos, filename=f'loopback_packet_infos_',
                         use_timestamp=True)
    fname = io.saveToTmp(packet_counts, filename=f'loopback_packet_counts_', 
                         use_timestamp=True)
    fname = io.saveToTmp(channel_counts, filename=f'loopback_channel_counts_', 
                         use_timestamp=True)
    fname = io.saveToTmp(ptp_timestamps, filename=f'loopback_ptp_timestamps_',
                         use_timestamp=True)


# ============================================================================ #
# loopbackCaptureLong
def loopbackCaptureLong():
    """Capture some aspects of a longer timestream.
    Make sure NCLO is set and a waveform being generated on all chans.
    E.g. run setNCLO and writeNewVnaComb (for all drones) first.
    """

    t_obs = 60*30 # s; ~0.4 MB/s memory usage    
    t_obs_per_loop = 15 # s; ~100 MB/s memory usage
    # t_obs=1800, t_obs_per_loop=15 -> ~2 GB memory, ~25%

    # sample_rate = 488 # 512e6/2**20
    sample_rate = 976
    num_drones = 4
    packets_per_s = sample_rate*num_drones
    N_packets = packets_per_s*t_obs
    max_packets_per_loop = packets_per_s*t_obs_per_loop

    msg = f"Running long loopback capture ({t_obs} s; {N_packets} packets):"

    _sendComAll("writeNewVnaComb")

    _sendComAll("timestreamOn", 1)
    start = time.time()

    packet_counts  = []
    ptp_timestamps = []
    packet_ips     = []
    i_packet = 0
    timestream = None
    _progressBar(i_packet, N_packets, msg)
    while i_packet < N_packets:
        num_packets_this_loop = min(N_packets - i_packet, max_packets_per_loop)

        packets = _captureTimestream(num_packets_this_loop, timestream)
        timestream, _,_, cnts, tss, _,_, ips = packets
        packet_counts.extend(cnts)
        ptp_timestamps.extend(tss)
        packet_ips.extend(ips)

        i_packet += num_packets_this_loop

        _progressBar(i_packet, N_packets, msg)

    print(f"Elapsed time: {time.time() - start:.6f} seconds")
    _sendComAll("timestreamOn", 0)     # stop streaming

    packet_counts  = np.array(packet_counts)
    ptp_timestamps = np.array(ptp_timestamps)
    packet_ips     = np.array(packet_ips)

    fname = io.saveToTmp(packet_ips, filename=f'loopback_packet_ips_', 
                         use_timestamp=True)
    fname = io.saveToTmp(packet_counts, filename=f'loopback_packet_counts_', 
                         use_timestamp=True)
    fname = io.saveToTmp(ptp_timestamps, filename=f'loopback_ptp_timestamps_',
                         use_timestamp=True)
    

# I and Q too much to hold in memory for longtimestreams
# could save as binary instead, and append each loop
# then convert to array using np.memmap


# ============================================================================ #
# timestreamMonitorTest
def timestreamMonitorTest():

    running = True
 
    _sendComAll("startChains")
    _sendComAll("writeNewVnaComb")

    _sendComAll("timestreamOn", 1)

    import signal
    def signal_handler(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, signal_handler)

    try:
        timestream = None
        while running:
            print(f" "*100, end='\r')
            packets = _captureTimestream(122, timestream)
            timestream, _,_,_,_,_,_, ips = packets
            ips_unique = np.unique(ips)
            print(ips_unique, end='\r')
            time.sleep(0.75)

    except KeyboardInterrupt:
        running = False
    finally:
        print()

        _sendComAll("timestreamOn", 0)


# ============================================================================ #
# timestreamMonitorTest
def timestreamMonitorTest_monitorOnly():

    running = True

    import signal
    def signal_handler(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, signal_handler)

    try:
        timestream = None
        while running:
            print(f" "*100, end='\r')
            packets = _captureTimestream(122, timestream)
            timestream, _,_,_,_,_,_, ips = packets
            ips_unique = np.unique(ips)
            print(ips_unique, end='\r')
            time.sleep(0.75)

    except KeyboardInterrupt:
        running = False
    finally:
        print()



'''

# ============================================================================ #
# targetSweepPowerTest 
def targetSweepPowerTest():
    """Run a number of varied tone power sweeps and record output.

    Queen listen mode must be running to intercept all the files.
    """

    bid = 1
    drid = 1
    nclo = 600

    def sendCom(com_str, args_str=None):
        com_num = alcove.comNumFromStr(com_str)
        return queen.alcoveCommand(
            com_num, bid=bid, drid=drid, all_boards=False, args=args_str)

    print("setting NCLO")
    sendCom("setNCLO", nclo)
    print("done setting NCLO")

    N_sweeps = 10
    factor = 10**(-1/(2*N_sweeps))

    print("   Performing initial target sweep... ", end="", flush=True)
    sendCom("targetSweep")
    print("Done. ", end="", flush=True)

    for i in range(N_sweeps):
        print(i)
        print("   Modify comb amplitudes... ", end="", flush=True)
        sendCom("modifyCustomCombAmps",factor)
        print("  Done. ", end="", flush=True)
        print("   Write new custom comb ... ", end="", flush=True)
        sendCom("writeCombFromCustomList")
        print("  Done. ", end="", flush=True)
        print("   Performing target sweep... ", end="", flush=True)
        sendCom("targetSweep")
        print("Done. ", end="", flush=True)


# ============================================================================ #
# tonePowerTest
def tonePowerTest():
    """Run a number of varied tone power sweeps and record output.

    Queen listen mode must be running to intercept all the files.
    """

    bid = 1
    drid = 1
    nclo = 500

    def sendCom(com_str, args_str=None):
        return queen.alcoveCommand(queen.comNumFromStr(com_str), 
                        bid=bid, drid=drid, all_boards=False, args=args_str)

    sendCom("alcove_base.setNCLO", nclo)

    # vna sweep
    sendCom("tones.writeNewVnaComb")
    sendCom("sweeps.vnaSweep")
    sendCom("analysis.findVnaResonators")

    # target sweep
    sendCom("tones.writeTargCombFromVnaSweep")
    sendCom("sweeps.targetSweep")
    sendCom("analysis.findTargResonators")

    # add calibration tones
    sendCom("analysis.findCalTones")
    sendCom("tones.writeTargCombFromTargSweep", "cal_tones=True")

    # create custom comb files
    sendCom("tones.createCustomCombFilesFromCurrentComb")

    # loop with varying tone power
    # assume unmodified tone power (1.0) is overdriven
    f_step = 0.1 # start here and step by this size
    f_parts = np.arange(2, 1/f_step + 1)
    factors = f_parts/(f_parts - 1) # build factors
    factors = np.insert(factors, 0, f_step) # add first factor
    for f in factors:
        sendCom("tones.modifyCustomCombAmps", f)
        sendCom("tones.writeCombFromCustomList")
        
        # we have a comb with reduced amps running
        # how do we get a target sweep with reduced amps?
        # if we do that then we can find resonators
        # and the timestreams will be on resonance at each tone power
        # The alternative is leave the time streams where they are
        # which actually would be good info too
        
        # save timestream
        ip = "192.168.3.40"
        port = 4096
        packets = 500*10 # 10 seconds?
        I,Q = captureTimestream(packets, ip, port)
        # power: I[kid_id]**2 + Q[kid_id]**2
        # phase: np.arctan2(Q[kid_id], I[kid_id])
        fname = io.saveToTmp(np.array([I, Q]), filename=f'timestream_{f}', use_timestamp=True)
        
 
 # ============================================================================ #
# adriansNoiseTest
def adriansNoiseTest():
    """

    Queen listen mode must be running to intercept all the files.
    """

    print("Running adriansNoiseTest()...")

    bid = 1
    drid = 1
    nclo = 500
    t_tod = 10

    # fnclos = np.concatenate((-np.logspace(-4, -1, 50)[::-1], 
    #                          np.logspace(-4, -1, 50)))
    fnclos = np.linspace(-0.02, 0.02, 100)

    def sendCom(com_str, args_str=None):
        com_num = alcove.comNumFromStr(com_str)
        return queen.alcoveCommand(
            com_num, bid=bid, drid=drid, all_boards=False, args=args_str)
    
    def capTOD(t, fnclo):
        # save timestream
        ip = "192.168.3.40"
        port = 4096
        # packets = t*489
        packets = int(t*512e6/2**20) # assuming sample rate
        # sample rate could be different
        I,Q = captureTimestream(packets, ip, port)
        # power: I[kid_id]**2 + Q[kid_id]**2
        # phase: np.arctan2(Q[kid_id], I[kid_id])
        fname = io.saveToTmp(np.array([I, Q]), filename=f'timestream_{fnclo}', use_timestamp=True)


    try: 

        print(f"   Setting NCLO (={nclo})... ", end="", flush=True)
        sendCom("setNCLO", nclo)
        print("Done.")

        
        print("   Performing target sweep... ", end="", flush=True)
        sendCom("targetSweep")
        print("Done.")

        print("   Looping over fine NCLOs...")
        for fnclo in fnclos:
        
            print(f"   Setting fine NCLO (={fnclo})... ", end="", flush=True)
            sendCom("setFineNCLO", fnclo)
            print("Done.")

            time.sleep(1) # dont catch blip

            # capture timestream
            print("   Capturing timestream...", end="", flush=True)
            capTOD(t_tod, fnclo)
            print("Done.")

        print("Well Done! :)")

    except Exception: 
        traceback.print_exc()
'''

'''
def tonysHeatingTest():
    """

    Queen listen mode must be running to intercept all the files.
    """

    print("Running tonysHeatingTest()...")

    bid = 1
    drid = 1
    nclo = 500

    time_to_run = 
    time_between_sweeps = 
    time_tod = # tod length per temperature

    def sendCom(com_str, args_str=None):
        com_num = alcove.comNumFromStr(com_str)
        return queen.alcoveCommand(
            com_num, bid=bid, drid=drid, all_boards=False, args=args_str)

    try:

        print("   Setting NCLO... ", end="", flush=True)
        sendCom("setNCLO", nclo)
        print("Done.")

        # vna sweep
        print("   Writing VNA comb... ", end="", flush=True)
        sendCom("writeNewVnaComb")
        print("Done.")
        print("   Performing VNA sweep... ", end="", flush=True)
        sendCom("vnaSweep")
        print("Done.")

        # loop
        print("   Performing VNA sweep loop:")
        n = 0
        n_max = 48
        while n < n_max:
            n += 1

            print(f"      {n=}/{n_max}")
            
            time.sleep(900)
            sendCom("vnaSweep")

    except Exception: 
        traceback.print_exc()
'''