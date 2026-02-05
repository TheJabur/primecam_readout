# ============================================================================ #
# board_utilities.py
# Board utility tools. 
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2025
# ============================================================================ #

import numpy as np




# ============================================================================ #
# board_temps
def board_temps():
    """
    Read temperatures from the board sensors.
    
    Returns:
        dict: Dict of temperatures in Celsius with 4 decimal places.
    """

    def calc_temp(raw):
        """Convert raw 16-bit ADC value to Celsius, round to 4 digits.
        Ref: Equation 2-7, SYSMON User Guide UG580 (v1.10.1) Xilinx"""
        return round(raw * 501.3743 / 2**16 - 273.6777, 4)
    
    # File paths for temperature sensor readings
    ps_temp_path = "/sys/bus/iio/devices/iio:device0/in_temp0_ps_temp_raw"
    pl_temp_path = "/sys/bus/iio/devices/iio:device0/in_temp2_pl_temp_raw"
    
    # Read raw temperature values
    ps_temp_raw = np.loadtxt(ps_temp_path, dtype=np.int32)
    pl_temp_raw = np.loadtxt(pl_temp_path, dtype=np.int32)
    
    temp_dict = {
        'ps_processor': calc_temp(ps_temp_raw),
        'pl_fabric': calc_temp(pl_temp_raw)
    }

    print(temp_dict)
    
    return temp_dict
