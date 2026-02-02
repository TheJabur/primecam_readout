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


# =========================================================================== #
# gatewareInfoFromBoardCfg
def gatewareInfoFromBoardCfg(cfg_b):
    # MUST use *_v[version]p* as gateware filename
    gateware_file = os.path.join(cfg_b.dir_root, cfg_b.gateware_file)
    gateware_fname = os.path.splitext(os.path.basename(gateware_file))[0]
    gateware_fname_parts = re.search(r'_v(\d+)p(\d+)', gateware_fname)
    gateware_version = int(gateware_fname_parts.group(1)) 
    gateware_version_minor = int(gateware_fname_parts.group(2))
    return gateware_file, gateware_version, gateware_version_minor

gateware_file, gateware_version, gateware_version_minor = \
    gatewareInfoFromBoardCfg(cfg_b)

# if gateware_version >= 15:
#     import init_15
# else:
#     import init_14
# TODO:
import init_15