# ============================================================================ #
# queen_commands/test_functions.py
# Testing functions which run on the control computer.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2025
# ============================================================================ #

import numpy as np
import time
import traceback

import queen
import alcove
import alcove_commands.alcove_base as alcove_base
import queen_commands.control_io as io
from timestream import TimeStream, parsePtpTimestamp




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
# TESTS
# ============================================================================ #


# ============================================================================ #
# loopbackCapture
def loopbackCapture():

    print("Running loopback capture...")

    packet_per_second = 488 # 512e6/2**20
    # packet_per_second = 976
    # t_obs = 60 # s, ~1 GB @ 488 Hz
    t_obs = 30 # s, ~1 GB @ 976 Hz
    N_packets = 4*packet_per_second*t_obs
    # N_packets = 4096*4 # 4096 samples ~ 8.4 s
    # N_packets = 10

    # _sendCom(bid, drid, "setNCLO", 600)        # set LO
    _sendComAll("writeNewVnaComb")     # gen. tone comb
    _sendComAll("timestreamOn", 1)     # start streaming

    start = time.time()
    packets = _captureTimestream(N_packets)    # capture tods
    print(f"Elapsed time: {time.time() - start:.6f} seconds")

    _sendComAll("timestreamOn", 0)     # stop streaming

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
# captureTimestream
def captureTimestream(packets, ip, port=4096):
    """Capture I and Q of timestream.

    packets: Number of packets to capture.
    ip: IP address to capture from.
    port: IP port.
    """

    timestream = TimeStream(host=ip, port=port)
    I, Q = timestream.getTimeStreamChunk(packets)

    return I,Q


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