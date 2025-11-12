# ============================================================================ #
# feeds.py
# Drone feed functions.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2025
# ============================================================================ #

import time
import shutil

from alcove_commands import board_utilities as utils
from config import board as cfg_b




# ============================================================================ #
# _wilds
def _wilds():
    """Feed wild cards.
    """

    wilds = {
        'temp' : f'temp_*',
        'spc'  : f'spc_*',
    }

    return wilds


# ============================================================================ #
# _keys
def _keys():
    """Feed keys.
    """

    id = f'{cfg_b.bid}_{cfg_b.drid}'

    keys = {
        'temp_ps' : f'temp_{id}_ps', # e.g. 'temp_1_1_ps'
        'temp_pl' : f'temp_{id}_pl', # e.g. "temp_1_1_pl"
        'spc'     : f'spc_{id}', # e.g. "spc_1_1"
    }

    return keys


# ============================================================================ #
# _getKeyValsMatching
def _getKeyValsMatching(r, match):
    """
    """

    result = {}
    cursor = 0
    while True:

        # get batch of data
        # use SCAN to scale efficiently
        cursor, keys = r.scan(cursor=cursor, match=match)
        for key in keys:
            result[key.decode()] = r.get(key).decode() 

        # Exit loop when all data collected
        if cursor == 0:
            break

    return result


# ============================================================================ #
# _dictValsToFloats
def _dictValsToFloats(keyVals):
    """Convert dictionary values to floats.
    If value can't be converted, remove key.
    """

    keyVals_f = {}
    for k in keyVals:
        try:
            keyVals_f[k] = float(keyVals[k])
        except:
            continue
        
    return keyVals_f


# ============================================================================ #
# _setKeyVal
def _setKeyVal(r, key, val, expire=None):
    """Set a val for a key, with optional expiry, in s.
    """

    r.set(key, val)

    if expire is not None:
        r.expire(key, expire)


# ============================================================================ #
# getFeedTemps
def getFeedTemps(r, handler):
    """Get all drones feeds: Temperatures (pl and ps), in celsius.

    ps = processing system
    pl = programmable logic
    """

    pre = _wilds()['temp'][:-1]

    # in keyVals in Redis
    keyVals = _getKeyValsMatching(r, pre)

    # convert values from str to floats 
    keyVals = _dictValsToFloats(keyVals)

    # loop through all boards
    for bid in set([k.split('_')[1] for k in keyVals.keys()]):

        # find keyVals for just this board
        boardVals = {k:v for k,v in keyVals.items() 
                     if k.startswith(f'{pre}_{bid}_')}
        
        # generate expected dict for handler
        data = {'timestamp': time.time(),
                'block_name': f'board_{bid}',
                'data': boardVals}

        # send to provided handler function
        handler('drone_temperatures_C', data)


# ============================================================================ #
# getFeedSpc
def getFeedSpc(r, handler):
    """Get all drones feeds: Free space remaining, in GB.
    """

    pre = _wilds()['spc'][:-1]

    # in keyVals in Redis
    keyVals = _getKeyValsMatching(r, pre)
    
    # convert values from str to floats 
    keyVals = _dictValsToFloats(keyVals)

    # convert val to float
    keyVals = {k: float(keyVals[k]) 
               for k in keyVals 
               if isinstance(keyVals[k], (int, float, str)) 
               and type(keyVals[k]) != str 
               or (type(keyVals[k]) == str 
                   and keyVals[k].replace('.','',1).isdigit())}

    # loop through all boards
    for bid in set([k.split('_')[1] for k in keyVals.keys()]):

        # find keyVals for just this board
        boardVals = {k:v for k,v in keyVals.items() 
                     if k.startswith(f'{pre}_{bid}_')}
        
        # generate expected dict for handler
        data = {'timestamp': time.time(),
                'block_name': f'board_{bid}',
                'data': boardVals}

        # send to provided handler function
        handler('drone_free_spaces_GB', data)


# ============================================================================ #
# setFeedTemps
def setFeedTemps(r, interval):
    """Update the ps and pl temperature feeds.
    """

    temps = utils.board_temps()
    temp_ps = temps['ps_processor']
    temp_pl = temps['pl_fabric']

    _setKeyVal(r, _keys()['temp_ps'], temp_ps, 2*interval)
    _setKeyVal(r, _keys()['temp_pl'], temp_pl, 2*interval)


# ============================================================================ #
# setFeedSpc
def setFeedSpc(r, interval):
    """Update the free disk space feed.
    """

    total, used, free = shutil.disk_usage("/") # bytes
    free = round(free / (1024 ** 3), 4) # GB, round to 4 digits

    _setKeyVal(r, _keys()['spc'], free, 2*interval)