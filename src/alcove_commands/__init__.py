import os

gateware_version = int(os.environ.get('PRIMECAM_READOUT_GATEWARE_VERSION'))
if gateware_version >= 15:

    from . import test_functions as test
    from . import board_utilities as utils
    from . import alcove_base_15 as alcove_base
    from . import tones
    from . import sweeps
    from . import analysis

else:

    from . import test_functions as test
    from . import board_utilities as utils
    from . import alcove_base_14 as alcove_base
    from . import tones
    from . import sweeps
    from . import analysis

__all__ = ["test", "utils", "alcove_base", "tones", "sweeps", "analysis"]