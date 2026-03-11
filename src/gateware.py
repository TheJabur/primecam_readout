# ============================================================================ #
# gateware.py
# Gateware loading/info.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT/FYST 2026
# ============================================================================ #

import os
import re

try: from config import board as cfg_b
except ImportError: cfg_b = None 




# =========================================================================== #
# _loadInfo
def _loadInfo():
    '''Finds the gateware file and fills mutable config info about it.
    '''

    try:
        # MUST use *_v[version]p* as gateware filename
        gateware_file = os.path.join(cfg_b.dir_root, cfg_b.gateware_file)
        gateware_fname = os.path.splitext(os.path.basename(gateware_file))[0]
        gateware_fname_parts = re.search(r'_v(\d+)p(\d+)', gateware_fname)
        gateware_version = int(gateware_fname_parts.group(1)) 
        gateware_version_minor = int(gateware_fname_parts.group(2))

        cfg_b.gateware_error = 0
        cfg_b.gateware_filename = gateware_file
        cfg_b.gateware_version = gateware_version
        cfg_b.gateware_version_minor = gateware_version_minor
    
    except:
        cfg_b.gateware_error = 1


# =========================================================================== #
# info
def info():
    '''Returns a 3-tuple of gateware filename, and major and minor version,
    or (None,None,None) if there is an issue.
    '''

    # board config doesn't exist, assume on control computer
    if cfg_b is None:
        return None,None,None

    # haven't tried loading info before (error=None), do so now
    if cfg_b.gateware_error is None:
         _loadInfo()

    # loading error
    if cfg_b.gateware_error:
        print('Board config or gateware error.')
        return None,None,None
    
    return (cfg_b.gateware_filename,
            cfg_b.gateware_version, 
            cfg_b.gateware_version_minor)


# =========================================================================== #
# loadGateware
def loadGateware():
    '''Load the gateware into Overlay.
    '''

    # board config doesn't exist, assume on control computer
    if cfg_b is None:
        return # do not attempt to load gateware
    
    from pynq import Overlay # type: ignore
    gateware_file,_,_ = info()
    gateware = Overlay(gateware_file, ignore_version=True, download=False)
    cfg_b.gateware = gateware


# =========================================================================== #
# isGen2
def isGen2():
    '''Bool of whether running gen2 gateware.
    '''

    # board config doesn't exist, assume on control computer
    if cfg_b is None:
        return True # default to assuming gen2

    _,versMajor,_ = info()
    return versMajor >= 15