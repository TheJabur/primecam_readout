# ============================================================================ #
# _cfg_queen.bak.py
# CONTROL COMPUTER configuration file TEMPLATE.
# Copy this file and rename to _cfg_queen.py, and edit that.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT/FYST 2026
# ============================================================================ #


## redis server configuration
host = 'localhost'
# host = '192.168.2.80'
port = 6379
db   = 0
pw   = None

## RFSoC SSH credentials
# this could be changed so the boards are given 
# the control computer public key instead
ssh_user = 'xilinx'
ssh_pass = 'xilinx'

## drone monitoring
master_drone_list_file = 'master_drone_list.yaml'
monitor_interval = 10 # s

## drone returns
command_return_timeout = 600 # s




# ============================================================================ #
# DO NOT MODIFY BELOW
# ============================================================================ #
client_output_buffer_limit = 0
# ============================================================================ #
# ============================================================================ #