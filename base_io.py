## base_io.py

########################################################
### IO module base.                                  ###
### Provides functionality to control and board io.  ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2023                                  ###
########################################################



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
    from pathlib import Path

    # required file attributes
    fname          = file['fname']
    file_type      = file['file_type']
    dname          = file['dname']

    # this will make this path exist if possible
    Path(dname).mkdir(parents=True, exist_ok=True)

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


def saveToTmp(data):
    """
    Save a new file to tmp directory.
    
    data: The data to save to file.
    """

    import numpy as np
    import tempfile
    import pickle
    from pathlib import Path

    dname = 'tmp'

    # this will make the tmp dir exist if possible
    Path(dname).mkdir(parents=True, exist_ok=True)

    if isinstance(data, np.ndarray):    # save arrays to tmp .npy file
        with tempfile.NamedTemporaryFile(dir=dname, suffix='.npy', delete=False) as tf:
            np.save(tf, data)

    else:                               # write other types to tmp file
        with tempfile.NamedTemporaryFile(dir=dname, delete=False) as tf:
            tf.write(pickle.dumps(data))



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