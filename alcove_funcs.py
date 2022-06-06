########################################################
### Remote-side functions module.                    ###
### Stores board and processing related functions.   ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################

#############################################################
### NOTE that all import statements are done IN FUNCTIONS ###
### This is to improve portability and function clarity.  ###
### If function performance becomes an issue              ###
### then move the import to just above the function.      ###
#############################################################

def boardTemps():
    '''temperatures from the board sensors
    return: tuple of int'''

    import numpy as np

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