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
# logging
log_path         = '../logs/board.log'
log_MB           = 10  # size of log files
log_backup_count = 5   # number of log files


# ============================================================================ #
# gateware
gateware_file = 'init/tetra_v13p11.xsa'


# ============================================================================ #
# redis server configuration
#host = 'localhost'
host = '192.168.2.81'
port = 6379
db   = 0
pw   = 'foobared'


# ============================================================================ #
# PTP interface
ptp_interface   = "eth0"
ptp_mac_address = "01:80:C2:00:00:0E"
ptp_ip_address  = "192.168.2.4"


# ============================================================================ #
# timestream configuration
# UDP data ethernet destination
udp_dest_ip  = '192.168.3.40'
udp_dest_mac = '34:97:f6:52:c4:bb'

# UDP data ethernet origin, drones 1-4
udp_ori_ip_1 = '192.168.3.50'
udp_ori_ip_2 = '192.168.3.51'
udp_ori_ip_3 = '192.168.3.52'
udp_ori_ip_4 = '192.168.3.53'
udp_ori_mac  = 'c0:ff:ee:c0:ff:ee'


# ============================================================================ #
# waveform properties
# edit with extreme caution - changes may have unitended consequences
wf_fs      = 512e6 # sample clock
wf_lut_len = 2**20 # look-up table length
wf_fft_len = 1024  # fft length
accum_len  = 2**19 - 1 # determines sample rate: wf_fs/((accum_len+1)*2)


# ============================================================================ #
# frequency sweep properties
sweep_steps    = 500 # number of sweep steps
sweep_accums   = 5   # number of repeats of each sweep (averaging)
target_chan_bw = 1 # target sweep channel bandwidth [MHz]


# ============================================================================ #
# attenuator settings
atten_device = '/dev/ttyACM0' # '/dev/ttyUSB0'
    

# ============================================================================ #
# house keeping feeds
interval_feeds = 60 # s




# ============================================================================ #
# DO NOT MODIFY BELOW
# ============================================================================ #
root_dir = ''
drone_dir = ''
temp_dir = '/tmp'
drid = 0
board_ip = '0.0.0.0'
gateware = None
# ============================================================================ #
# ============================================================================ #