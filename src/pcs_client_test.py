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
queen = OCSClient('queenagent', args=[])
print(" Done.")

print("Getting queen client list...", end="")
clients = queen.ReadoutAgent.getClientList()
print(" Done.")
print("Clients: ", clients)





# Parser for collecting the necessary arguments
# Use: python3 pcs_client_test.py posArgValues -namedArgs namedArgValues
# parser = argparse.ArgumentParser()
# parser.add_argument("mode", help="Whether to turn the still heater on or off",
# 					type=str, choices=['on','off'])
# parser.add_argument("-p", "--power", help="The still heater power to set", type=float)
# args = parser.parse_args()
# # use: args.mode, args.power