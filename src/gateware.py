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
        cfg_b.gateware_version = gateware_version # v
        cfg_b.gateware_version_minor = gateware_version_minor # p
    
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
def loadGateware(download=False):
    '''Load the gateware into Overlay.
    '''

    # board config doesn't exist, assume on control computer
    if cfg_b is None:
        return # do not attempt to load gateware
    
    from pynq import Overlay # type: ignore
    gateware_file,_,_ = info()
    gateware = Overlay(gateware_file, ignore_version=True, download=download)
    cfg_b.gateware = gateware

    return gateware


# =========================================================================== #
# isGen2
def isGen2():
    '''Bool of whether running gen2 gateware.
    '''

    # board config doesn't exist, assume on control computer
    if cfg_b is None:
        return True # default to assuming gen2

    _,v,_ = info()
    return v >= 15


# =========================================================================== #
# portMapping
def portMapping(v=None, p=None):

    # xm500; default shipped RF breakout board
    tb_indices_xm500 = {1: [0,0,1,3], 2: [0,1,1,2], 3: [1,0,1,1], 4: [1,1,1,0]}
    port_mapping_xm500 = 0b_11_10_01_00_00_01_10_11 # 32100123

    # ASU breakout board, bespoke for CCAT
    tb_indices_asu = {1: [1,0,1,3], 2: [1,1,1,2], 3: [0,1,1,0], 4: [0,0,1,1]}
    port_mapping_asu = 0b_11_10_00_01_10_11_01_00 # 32012310
    
    # board config doesn't exist, assume on control computer?
    if cfg_b is None:
        return tb_indices_asu, port_mapping_asu # default I guess

    # v is missing from filename? No idea what to do.
    if v is None:
        v = 100 # assume some big numbered version for latest

    try:
        asu_board = cfg_b.asu_board
    except:
        asu_board = False # not in config, old version

    # before v13 only had xm500 mapping, and port_mapping didn't exist
    if v < 13: 
        tb_indices = tb_indices_xm500
        port_mapping = None

    # v13 only had asu, and xm500 was tossed (port_mapping didn't exist)
    elif v == 13:
        tb_indices = tb_indices_asu
        port_mapping = None

    elif v == 14:
        if p is None: # no such version
            p = 1 # assume p1

        if p == 1: # similar to v13
            tb_indices = tb_indices_asu
            port_mapping = None

        if p >= 2: # port mapping introduced
            if asu_board:
                tb_indices = tb_indices_asu
                port_mapping = port_mapping_asu

            else:
                tb_indices = tb_indices_xm500
                port_mapping = port_mapping_xm500

    elif v >= 15: # gen2
        if asu_board:
            tb_indices = tb_indices_asu
            port_mapping = port_mapping_asu

        else:
            tb_indices = tb_indices_xm500
            port_mapping = port_mapping_xm500

    return tb_indices, port_mapping
