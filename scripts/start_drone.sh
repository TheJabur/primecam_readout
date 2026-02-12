#!/bin/bash

DRONE_NUMBER=$1

# Become root
sudo bash <<EOF

# Source the environment
source activate

# Change to the directory containing drone.py for PATH issues
cd /home/xilinx/primecam_readout/src

# Run the drone.py script
exec /usr/local/share/pynq-venv/bin/python3 /home/xilinx/primecam_readout/src/drone.py $DRONE_NUMBER
EOF