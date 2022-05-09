########################################################
### Main remote-side script.                         ###
### Allows execution of remote (board) commands.     ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

import alcove_funcs
import os
import numpy as np
import logging


##############
### CONFIG ###

logging.basicConfig(filename='alcove.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', format='{asctime} {levelname} {filename}:{lineno}: {message}'
)


#########################
### COMMAND FUNCTIONS ###

com = { 
    10:alcove_funcs.boardTemps, 
    11:alcove_funcs.my_alcove_func_2
}

# def boardTemps():
#     '''temperatures from the board sensors
#     return: tuple of int'''

#     def calc_temp(raw):
#         # Calculate temperature in Celsius from raw 16 bit ADC values
#         # Ref: Equation 2-7, SYSMON User Guide UG580 (v1.10.1) Xilinx
#         return raw*501.3743/2.**16-273.6777

#     # Get raw 16 bit ADC values from on-chip temperature sensors
#     ps_temp_raw = np.loadtxt("/sys/bus/iio/devices/iio:device0/in_temp0_ps_temp_raw",dtype="int32")
#     pl_temp_raw = np.loadtxt("/sys/bus/iio/devices/iio:device0/in_temp2_pl_temp_raw",dtype="int32")
    
#     return calc_temp(ps_temp_raw), calc_temp(pl_temp_raw)
    
# def my_alcove_func_2():
#     '''silly test function 2'''
#     print('...')
#     return 'silly return'

# official list of alcove commands
# alcove command keys start at 10
# com = { 
#     10:boardTemps, 
#     11:my_alcove_func_2
# }


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