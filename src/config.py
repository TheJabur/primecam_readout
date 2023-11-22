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

import sys
sys.path.append('../')

from cfg import _cfg_queen as queen
from cfg import _cfg_board as board
