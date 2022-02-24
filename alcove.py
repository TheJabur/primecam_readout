########################################################
### Main remote-side script.                         ###
### Allows execution of remote (board) commands.     ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

import os
import numpy as np


#########################
### COMMAND FUNCTIONS ###

def boardTemps():
    '''temperatures from the board sensors
    return: tuple of int'''

    def calc_temp(raw):
        # Calculate temperature in Celsius from raw 16 bit ADC values
        # Ref: Equation 2-7, SYSMON User Guide UG580 (v1.10.1) Xilinx
        return raw*501.3743/2.**16-273.6777

    # Get raw 16 bit ADC values from on-chip temperature sensors
    ps_temp_raw = np.loadtxt("/sys/bus/iio/devices/iio:device0/in_temp0_ps_temp_raw",dtype="int32")
    pl_temp_raw = np.loadtxt("/sys/bus/iio/devices/iio:device0/in_temp2_pl_temp_raw",dtype="int32")
    
    return calc_temp(ps_temp_raw), calc_temp(pl_temp_raw)
    
def my_alcove_func_2():
    '''silly test function 2'''
    print('...')
    return 'silly return'

# official list of alcove commands
# alcove command keys start at 10
com = { 
    10:boardTemps, 
    11:my_alcove_func_2
}


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)

def callCom(key):
    # dictionary keys are stored as integers
    # but redis may convert to string
    key = int(key)  # force key to be int
    
    if key not in com:  # check if command allowed
        ret = 'invalid key: '+str(key) # otherwise we'll return this

    else: # attempt command execution
        try: # if successful, we'll return what the command returns
            ret = com[key]()
        except BaseException as e: # if there's an exception
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            ret = message          # we'll return the exception

    if ret is not None:
        print(f"{com[key].__name__}: {ret}") # print the return (monkeypatched to log)
    return ret # and send it back