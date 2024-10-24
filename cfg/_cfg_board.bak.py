# ============================================================================ #
# _cfg_board.bak.py
# Board configuration file.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT/FYST 2023  
# ============================================================================ #



# ============================================================================ #
# board identifier
bid = 1    # should match physical id on board


# ============================================================================ #
# Firmware
# firmware_file = '../init/tetra_v7p1_impl_5.bit'
firmware_file = '../init/tetra_v12p15.xsa'


# ============================================================================ #
# redis server configuration
#host = 'localhost'
host = '192.168.2.80'
port = 6379
db   = 0
pw   = None


# ============================================================================ #
# PTP interface
ptp_interface   = "eth0"
ptp_mac_address = "01:80:C2:00:00:0E"
ptp_ip_address  = "192.168.2.4"


# ============================================================================ #
# timestream configuration
# UDP data ethernet destination
udp_dest_ip = '192.168.3.40'
udp_dest_mac = '00:00:00:00:00:00' 

# UDP data ethernet origin, drones 1-4
udp_ori_ip_1 = '192.168.3.50'
udp_ori_ip_2 = '192.168.3.51' 
udp_ori_ip_3 = '192.168.3.52' 
udp_ori_ip_4 = '192.168.3.53' 
udp_ori_mac = 'c0:ff:ee:c0:ff:ee'


# ============================================================================ #
# waveform properties
# edit with extreme caution - changes may have unitended consequences
wf_fs      = 512e6 # sampling rate
wf_lut_len = 2**20 # look-up table length
wf_fft_len = 1024  # fft length


# ============================================================================ #
# frequency sweep properties
sweep_steps    = 500 # number of sweep steps
sweep_accums   = 5   # number of repeats of each sweep (averaging)
target_chan_bw = 0.2 # target sweep channel bandwidth [MHz]




# ============================================================================ #
# DO NOT MODIFY BELOW
# ============================================================================ #
root_dir = ''
drone_dir = ''
drid = 0
board_ip = '0.0.0.0'
# ============================================================================ #
# ============================================================================ #
