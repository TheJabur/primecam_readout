import gateware as gw

if gw.isGen2():
    from alcove_commands.alcove_base_gen2 import *
else:
    from alcove_commands.alcove_base_gen1 import *