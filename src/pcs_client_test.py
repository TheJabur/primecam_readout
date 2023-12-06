# ============================================================================ #
# pcs_client_test.py
# Script to test the queen_agent.
#
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #

# import argparse
from ocs.ocs_client import OCSClient

# Setting up the queen agent
print("Connecting to queenagent...", end="")
queen_agent = OCSClient('queenagent', args=[])
print(" Done.")

# print("Getting queen client list...", end="")
# clients = queen_agent.getClientList()
# print(" Done.")
# print("Clients: ", clients)

# print("Sending setNCLO command...", end="")
# setNCLO_msg = queen_agent.setNCLO(com_to='1.1', f_lo=500)
# print(" Done.")
# print(f"setNCLO message: {setNCLO_msg}")

# print("Sending setFineNCLO command...", end="")
# msg = queen_agent.setFineNCLO(com_to='1.1', df_lo=1)
# print(" Done.")
# print(f"setFineNCLO message: {msg}")

# print("Sending getSnapData command...", end="")
# msg = queen_agent.getSnapData(com_to='1.1', mux_sel=0)
# print(" Done.")
# print(f"getSnapData message: {msg}")

# print("Sending writeNewVnaComb command...", end="")
# msg = queen_agent.writeNewVnaComb(com_to='1.1')
# print(" Done.")
# print(f"writeNewVnaComb message: {msg}")

# print("Sending writeTargCombFromVnaSweep command...", end="")
# msg = queen_agent.writeTargCombFromVnaSweep(com_to='1.1', cal_tones=False)
# print(" Done.")
# print(f"writeTargCombFromVnaSweep message: {msg}")

# print("Sending writeTargCombFromTargSweep command...", end="")
# msg = queen_agent.writeTargCombFromTargSweep(
#     com_to='1.1', cal_tones=False, new_amps_and_phis=False)
# print(" Done.")
# print(f"writeTargCombFromTargSweep message: {msg}")

# print("Sending writeCombFromCustomList command...", end="")
# msg = queen_agent.writeCombFromCustomList(com_to='1.1')
# print(" Done.")
# print(f"writeCombFromCustomList message: {msg}")

# print("Sending createCustomCombFilesFromCurrentComb command...", end="")
# msg = queen_agent.createCustomCombFilesFromCurrentComb(com_to='1.1')
# print(" Done.")
# print(f"createCustomCombFilesFromCurrentComb message: {msg}")

print("Sending modifyCustomCombAmps command...", end="")
msg = queen_agent.modifyCustomCombAmps(com_to='1.1', factor=1)
print(" Done.")
print(f"modifyCustomCombAmps message: {msg}")


# Parser for collecting the necessary arguments
# Use: python3 pcs_client_test.py posArgValues -namedArgs namedArgValues
# parser = argparse.ArgumentParser()
# parser.add_argument("mode", help="Whether to turn the still heater on or off",
# 					type=str, choices=['on','off'])
# parser.add_argument("-p", "--power", help="The still heater power to set", type=float)
# args = parser.parse_args()
# # use: args.mode, args.power