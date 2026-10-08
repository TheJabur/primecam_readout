import gateware as gw

if gw.isGen2():
    from queen_agent_gen1 import *
else:
    from queen_agent_gen2 import *