# ============================================================================ #
# alcove.py
# Responsible for board commands.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #


import logging
import alcove_commands.test_functions as test
import alcove_commands.board_utilities as utils
import alcove_commands.alcove_base as alcove_base
import alcove_commands.tones as tones
import alcove_commands.sweeps as sweeps
import alcove_commands.analysis as analysis
from config import parentDir



# ============================================================================ #
# CONFIG
# ============================================================================ #


logging.basicConfig(
    filename=f'{parentDir(__file__)}/logs/board.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)

# official list of alcove commands
# alcove command keys start at 10
def _com():
    return { 
        # 10:test.testFunction,
        20:alcove_base.setNCLO,
        21:alcove_base.setFineNCLO,
        25:alcove_base.getSnapData,
        30:tones.writeTestTone,
        31:tones.writeNewVnaComb,
        32:tones.writeTargCombFromVnaSweep,
        33:tones.writeTargCombFromTargSweep,
        34:tones.writeCombFromCustomList,
        35:tones.createCustomCombFilesFromCurrentComb,
        36:alcove_base.modifyCustomCombAmps,
        37:tones.writeTargCombFromCustomList,
        40:sweeps.vnaSweep,
        # 41:sweeps.vnaSweepFull,
        42:sweeps.targetSweep,
        # 43:sweeps.targetSweepFull,
        # 45:sweeps.loChopSweep,
        50:analysis.findVnaResonators,
        51:analysis.findTargResonators,
        55:analysis.findCalTones,
    }



# ============================================================================ #
# EXTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# comList
def comList():
    """A list of all Alcove command names (strings)."""

    return [com[key].__name__ for key in com.keys()]


# ============================================================================ #
# comNumFromStr
def comNumFromStr(com_str):
    """Alcove command number (int) from command name (str)."""

    coms = {com[key].__name__:key for key in com.keys()}
    return int(coms[com_str])



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _print
_print = print 
def print(*args, **kw):
    """Monkeypatch the print statement
    """
    
    _print(*args, **kw)            # print to terminal
    logging.info(' '.join(args))   # log to file


# ============================================================================ #
# callCom
def callCom(key, args, kwargs):
    # dictionary keys are stored as integers
    # but redis may convert to string
    key = int(key)                       # want int for com
    
    if key not in com:                   # invalid command
        ret = 'invalid key: '+str(key)
        print(ret)

    else:
        try:                             # attempt command
            ret = com[key](*args, **kwargs)
        except BaseException as e:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            ret = message

        if ret is not None:              # default success return is None
            print(f"{com[key].__name__}: {ret}") # monkeypatched to log

    return ret



# ============================================================================ #
# INIT
# ============================================================================ #


com = _com()
