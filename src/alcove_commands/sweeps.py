import gateware as gw

if gw.isGen2():
    from alcove_commands.sweeps_gen2 import *
else:
    from alcove_commands.sweeps_gen1 import *