########################################################
### Main remote-side script.                         ###
### Allows execution of remote (board) commands.     ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

import logging
import alcove_commands.test_functions as test
import alcove_commands.board_utilities as utils


##############
### CONFIG ###

logging.basicConfig(filename='alcove.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', format='{asctime} {levelname} {filename}:{lineno}: {message}'
)

# official list of alcove commands
# alcove command keys start at 10
def _com():
    return { 
        10:utils.boardTemps, 
        11:test.my_alcove_func_2
    }


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    _print(*args, **kw)            # print to terminal
    logging.info(' '.join(args))   # log to file

def callCom(key):
    # dictionary keys are stored as integers
    # but redis may convert to string
    key = int(key)                       # want int for com
    
    if key not in com:                   # invalid command
        ret = 'invalid key: '+str(key)
        print(ret)

    else:
        try:                             # attempt command
            ret = com[key]()
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