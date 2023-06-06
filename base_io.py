## base_io.py

########################################################
### IO module base.                                  ###
### Provides functionality to control and board io.  ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2023                                  ###
########################################################



#####################
# Global attributes #
#####################

try:
    import _cfg_board as cfg
except Exception as e: 
    print(f"board_io.py global attribute issue.")



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

    return loadVersion(file, mostRecentTimestamp(file))


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


def saveToTmp(data, filename=None, use_timestamp=True):
    """
    Save a new file to tmp directory.
    
    data: The data to save to file.
    filename: (str) The filename to use.
    use_timestamp: (bool) Append timestamp to filename if True.
    """

    # add functionality to clear out old tmp files?

    import numpy as np
    import tempfile
    import pickle
    from pathlib import Path

    dname = 'tmp'
    suffix = ''
    prefix = ''

    # this will make the tmp dir exist if possible
    Path(dname).mkdir(parents=True, exist_ok=True)

    # filename modifiction
    if filename is not None:
        prefix += filename

    # timestamp modification
    if use_timestamp:
        suffix += f'_{_timestamp()}'  

    if isinstance(data, np.ndarray):    # save arrays to tmp .npy file
        suffix += '.npy'
        with tempfile.NamedTemporaryFile(
            dir=dname, prefix=prefix, suffix=suffix, delete=False) as tf:
            np.save(tf, data)
            return tf.name

    else:                               # write other types to tmp file
        with tempfile.NamedTemporaryFile(
            dir=dname, prefix=prefix, suffix=suffix, delete=False) as tf:
            # tf.write(pickle.dumps(data))
            tf.write(data)
            return tf.name


def saveWrappedToTmp(wrappedData):
    """Save returnWrapper output to file in tmp.
    Assumes wrappedData is returnWrapper return or a list of them.
    """

    import numpy as np
    from pathlib import Path
    import pickle

    # d = wrappedData
    def processWrappedData(d):

        data = d['data']
        fname = f"{d['filename']}_{d['bid']}_{d['drid']}_{d['timestamp']}.{d['ext']}"
        dname = 'tmp'
        pathname = Path(dname, fname)

        # this will make the tmp dir exist if possible
        Path(dname).mkdir(parents=True, exist_ok=True)

        if isinstance(data, np.ndarray):
            np.save(pathname, data)  # save arrays w/ numpy

        else: # save everything else w/ pickle
            # should overwrite if file exists
            with open(pathname, 'wb') as handle:
                pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # could be a list of wrapped returns
    if isinstance(wrappedData, list):
        for d in wrappedData:
            processWrappedData(d)

    else:
        processWrappedData(wrappedData)


def returnWrapper(file, data):
    """Create a dictionary wrapper for data to return to queen.

    file:     (dict) File attributes. See file class.
    data:     The data to be saved in the file.
    """

    # we require data instead of doing load(file)
    # because return may be a different version of file

    d = {
        "wrapped":  True,
        "bid":      cfg.bid,
        "drid":     cfg.drid,
        "filename": file['fname'],
        "ext":      file['file_type'],
        "timestamp":_timestamp(),
        "data":     data}

    return d


def returnWrapperMultiple(file_list, data_list):
    """Similar to returnWrapper but accepts lists of inputs.
    Returns a list of returnWrapper outputs.
    """

    return [
        returnWrapper(file, data)
        for file, data in zip(file_list, data_list)]


def unwrapData(wrapped_data):
    """Return the original data input to the wrapping process.
    """

    # could be a list of wrapped data
    if isinstance(wrapped_data, list):
        return [d['data'] for d in wrapped_data]

    # or single wrapped data
    else:
        return wrapped_data['data']


def mostRecentTimestamp(file):
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