# ============================================================================ #
# init.py
# Board side initialization script to be called after boot-up.
# 
# James Burgoyne jburgoyne@phas.ubc.ca
# Adrian Sinclair aksincla@asu.edu
# CCAT/FYST 2025
# ============================================================================ #

import os
import re
import sys


# Determine the directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))

# add src/ to path (where most of the other scripts live)
sys.path.insert(1, os.path.join(os.path.dirname(script_dir), 'src'))

from config import board as cfg_b
import gateware


if gateware.isGen2():
    # import init_15
    print("gen2")
else:
    # import init_14
    print("gen1")