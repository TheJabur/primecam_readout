
import os

try:
    gateware_version = int(os.environ.get('PRIMECAM_READOUT_GATEWARE_VERSION'))
except:
    gateware_version = 15 # default, mostly for control computer
    
if gateware_version >= 15:
    from alcove_commands.alcove_base_15 import *
else:
    from alcove_commands.alcove_base_14 import *