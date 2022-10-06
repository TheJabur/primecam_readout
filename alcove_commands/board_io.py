## board_io.py

#####################
# Global attributes #
#####################

try:
    import _cfg_board as cfg
except Exception as e: 
    print(f"board_io.py global attribute issue.")



#######################
# Internal attributes #
#######################

class file:
# parameters:
    # required:
        # fname           (str) Base filename (sans extension).
        # file_type       (str) Dictates extension and saving method.
        # dname           (str) Absolute directory containing fname. Must exist!
    # optional:
        # use_timestamp   (bool) Append timestamp to filename.

    f_res_vna = {
        'fname'         :'f_res_vna',
        'file_type'     :'npy', 
        'dname'         :cfg.drone_dir+'/vna',
        'use_timestamp' :True}

    f_res_targ = {
        'fname'         :'f_res_targ',
        'file_type'     :'npy', 
        'dname'         :cfg.drone_dir+'/targ',
        'use_timestamp' :True}

    a_res_targ = {
        'fname'         :'a_res_targ',
        'file_type'     :'npy', 
        'dname'         :cfg.drone_dir+'/targ',
        'use_timestamp' :True}



######################
# External Functions #
######################


def save(file, data):
    """
    Save data to a file with given attributes.

    file: (dict) File attributes. See file class.
    data: The data to save to file. Data type dictated by file_type.
    """

    import numpy as np

    # required file attributes
    fname          = file['fname']
    file_type      = file['file_type']
    dname          = file['dname']

    # optional file attributes
    use_timestamp  = file.get('use_timestamp', False)
    
    # timestamp modification
    if use_timestamp:
        timestamp = _timestamp()
        fname += f'_{timestamp}'

    if file_type == 'npy':
        np.save(f'{dname}/{fname}.npy', data)


def load(file):
    """
    Load file with given attributes.
    If file has a version history (timestamps), use most recent.
    Convenience wrapper for loadVersion().

    file: (dict) File attributes. See file class.
    """

    return loadVersion(file, _mostRecentTimestamp(file))


def loadVersion(file, timestamp):
    """
    Load file with given attributes and specific timestamp.

    file:      (dict) File attributes. See file class.
    timestamp: (str) Version timestamp.

    Return:    Data loaded from file. Data type dictated by file_type. 
    """

    import numpy as np

    # required file attributes
    fname          = file['fname']
    file_type      = file['file_type']
    dname          = file['dname']

    # timestamp modification
    if timestamp:
        fname += f'_{timestamp}'
    
    if file_type == 'npy':
        data = np.load(f'{dname}/{fname}.npy')
    
    return data


######################
# Internal Functions #
######################


def _timestamp():
    """
    String timestamp of current time (UTC) for use in filenames.
    ISO 8601 compatible format.
    """

    from datetime import datetime

    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _pathSplit(file, path):
    """
    Separate fname, timestamp, and ext from given path with file attributes.

    file:      (dict) File attributes. See file class.
    path:      (str) Absolute path to attempt separation.
    """

    # required file attributes
    fname          = file['fname']
    file_type      = file['file_type']
    
    rpath = path.split('/')[-1]  # get relative path

    # check path conforms to expectation from file
    if rpath[:len(fname)] != fname or rpath[-len(file_type):] != file_type:
        raise("Path does not match that expected from file type.")

    end0 = rpath[len(fname)+1:]         # remove fname and underscore

    timestamp = None
    if len(end0) > len(file_type)+1:     # if not just ext left...
        timestamp = end0[:-(len(file_type)+1)] # remove extension

    return (fname, timestamp, file_type)
    

def _mostRecentTimestamp(file):
    """
    Timestamp of most recent of given file.

    file:      (dict) File attributes. See file class.
    """

    import os
    import glob
    import numpy as np

    # required file attributes
    fname          = file['fname']
    dname          = file['dname']

    allversions = sorted(
        glob.iglob(os.path.join(dname, f'{fname}*')), 
        reverse=True)
    path0 = allversions[0]         # first index is highest timestamp
    
    _,timestamp,_ = _pathSplit(file, path0)

    return timestamp