########################################################
### Main remote-side script.                         ###
### Allows execution of remote (board) commands.     ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

from audioop import mul
import logging
import alcove_commands.test_functions as test
import alcove_commands.board_utilities as utils
import alcove_commands.single_chan as single_chan
import alcove_commands.multi_chan as multi_chan


##############
### CONFIG ###

logging.basicConfig(
    filename='logs/board.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)

# official list of alcove commands
# alcove command keys start at 10
def _com():
    return { 
        # 10:utils.boardTemps, 
        # 12:single_chan.writeVnaComb,
        # 13:single_chan.writeTestTone,
        # 14:single_chan.getAdcData,
        15:test.testFunction,
        # 16:single_chan.getSnapData,
        # 17:single_chan.vnaSweep,
        # 18:single_chan.findResonators,
        # 20:single_chan.writeTargComb,
        # 21:single_chan.targetSweep,
        # 22:single_chan.fullLoop,
        40:multi_chan.setNCLO,
        41:multi_chan.writeTestTone,
        42:multi_chan.writeVnaComb,
        43:multi_chan.writeTargComb,
        44:multi_chan.getSnapData,
        45:multi_chan.vnaSweep,
        46:multi_chan.findResonators,
        47:multi_chan.targetSweep,
        48:multi_chan.fullLoop,
        49:multi_chan.loChop,
        50:multi_chan.findCalTones,
        # 51:multi_chan.updateTargComb,
        52:multi_chan.setFineNCLO
    }


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    _print(*args, **kw)            # print to terminal
    logging.info(' '.join(args))   # log to file

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


############
### INIT ###

com = _com()
