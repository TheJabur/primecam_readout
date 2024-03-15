# ============================================================================ #
# queen_commands/test_functions.py
# Testing functions which run on the control computer.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #

import numpy as np
import time

import queen
# import alcove
import alcove_commands.alcove_base as alcove_base
import queen_commands.control_io as io
from timestream import TimeStream



# ============================================================================ #
# TESTING FUNCTIONS
# ============================================================================ #


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
# tonePowerTest
def tonysHeatingTest():
    """

    Queen listen mode must be running to intercept all the files.
    """

    print("Running tonysHeatingTest()...")

    bid = 1
    drid = 1
    nclo = 500

    def sendCom(com_str, args_str=None):
        com_num = queen.comNumFromStr(com_str)
        print(f"{com_num=}")
        return queen.alcoveCommand(
            com_num, bid=bid, drid=drid, all_boards=False, args=args_str)

    print("   Setting NCLO... ", end="", flush=True)
    sendCom("alcove_base.setNCLO", nclo)
    print("Done.")

    # vna sweep
    print("   Setting NCLO... ", end="", flush=True)
    sendCom("tones.writeNewVnaComb")
    print("Done.")
    print("   Setting NCLO... ", end="", flush=True)
    sendCom("sweeps.vnaSweep")
    print("Done.")

    # loop
    print("   Performing VNA sweep loop:")
    n = 0
    n_max = 48
    while n < n_max:
        n += 1

        print(f"      {n=}/{n_max}")
        
        time.sleep(1800)
        sendCom("sweeps.vnaSweep")


        
