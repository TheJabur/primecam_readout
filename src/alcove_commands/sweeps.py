import gateware

if gateware.isGen2():
    print("Loading sweeps_gen2")
    from alcove_commands.sweeps_gen2 import *
else:
    print("Loading sweeps_gen1")
    from alcove_commands.sweeps_gen1 import *