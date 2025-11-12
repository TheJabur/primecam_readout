from . import test_functions as test
from . import board_utilities as utils
from . import alcove_base
from . import tones
from . import sweeps
from . import analysis
from . import board_io
from . import transceiver_serialdriver

__all__ = ["test", "utils", "alcove_base", "tones", "sweeps", "analysis", "board_io", "transceiver_serialdriver"]




# import os
# import sys

# try:
#     gateware_version = int(os.environ.get('PRIMECAM_READOUT_GATEWARE_VERSION'))
# except:
#     gateware_version = 15 # default, mostly for control computer
    
# if gateware_version >= 15:

#     from . import test_functions as test
#     from . import board_utilities as utils
#     from . import alcove_base_15 as alcove_base
#     from . import tones
#     from . import sweeps
#     from . import analysis
#     from . import board_io
#     from . import transceiver_serialdriver

# else:

#     from . import test_functions as test
#     from . import board_utilities as utils
#     from . import alcove_base_14 as alcove_base
#     from . import tones
#     from . import sweeps
#     from . import analysis
#     from . import board_io

# sys.modules['alcove_commands.alcove_base'] = alcove_base
# __all__ = ["test", "utils", "alcove_base", "tones", "sweeps", "analysis", "board_io", "transceiver_serialdriver"]