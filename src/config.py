# ============================================================================ #
# config.py
# Script to manage configuration file imports.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2023   
# ============================================================================ #


import sys, os

def parentDir():
    this_path = os.path.abspath(__file__)
    this_dir = os.path.dirname(this_path)
    par_dir = os.path.dirname(this_dir)
    return par_dir

# add parent dir to path (where cfg/ is)
sys.path.insert(1, parentDir())

from cfg import _cfg_queen as queen
from cfg import _cfg_board as board
