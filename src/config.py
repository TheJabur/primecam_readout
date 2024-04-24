# ============================================================================ #
# config.py
# Script to manage configuration file imports.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2023   
# ============================================================================ #


import sys, os

def thisDir(file):
    this_path = os.path.abspath(file)
    this_dir = os.path.dirname(this_path)
    return this_dir

def parentDir(file):
    # this_path = os.path.abspath(file)
    # this_dir = os.path.dirname(this_path)
    par_dir = os.path.dirname(thisDir(file))
    return par_dir

# add parent dir to path (where cfg/ is)
sys.path.insert(1, parentDir(__file__))

try:
    from cfg import _cfg_queen as queen
except ImportError:
    pass

try:
    from cfg import _cfg_board as board
except ImportError:
    pass
