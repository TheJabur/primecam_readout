# ============================================================================ #
# config.py
# Script to manage configuration file imports.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2023   
# ============================================================================ #

# import os
# print(os.listdir('../cfg'))

# from ..cfg import _cfg_queen as queen
# from ..cfg import _cfg_board as board

import sys, os
# sys.path.append('/')
sys.path.insert(1, os.path.realpath(os.path.pardir))

from cfg import _cfg_queen as queen
from cfg import _cfg_board as board
