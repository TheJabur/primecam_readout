import gateware as gw

if gw.isGen2():
    from alcove_commands.tones_gen2 import *
else:
    from alcove_commands.tones_gen1 import *