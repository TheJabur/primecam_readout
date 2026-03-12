# ============================================================================ #
# config.py
# Script to manage configuration file imports.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2023   
# ============================================================================ #


import sys, os


def thisDir(file):
    '''Directort where given file is located.'''
    return os.path.dirname(os.path.abspath(file))
    # return os.path.dirname(os.path.realpath(file))


def parentDir(file):
    '''Parent directory of given file.'''
    return os.path.dirname(thisDir(file))


# define primecam_readout base dir
dir_root = parentDir(__file__)

# add parent dir to path
sys.path.insert(1, dir_root)

import_queen = False
try:
    from cfg import _cfg_queen as queen
    queen.dir_root = dir_root
    import_queen = True
except ImportError:
    pass
    
import_board = False
try:
    from cfg import _cfg_board as board
    board.dir_root = dir_root
    import_board = True
except ImportError:
    pass

if not import_queen and not import_board:
    print("Error: Require a queen or board config file.")
    raise

if import_queen and import_board:
    print("Warning: Both a queen and board config file detected.")