# ============================================================================ #
# drone.py
# Board side Redis interface script.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT/FYST 2024 
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #


import os
import re
import sys
import time
import redis
import queue
import shutil
import pickle
import hashlib
import logging
import argparse
import builtins
import importlib
import threading
import numpy as np
import logging.handlers

import alcove
from config import board as cfg_b
import redis_channels as chans
import feeds




# ============================================================================ #
# MAIN
# ============================================================================ #


def main():
    # CTRL-c to exit out of listen mode

    # setup logging
    _setupLogging()

    # setup and get the CLI args
    args = _setupArgparse() 

    # modify the configs as necessary
    _modifyConfig(args)

    # setup a drone specific dir in /tmp
    _setupTmpDir()

    # load gateware to config
    _loadGateware()

    # connect to Redis server and establish connection objects
    r,p = connectRedis()
    r.client_setname(f'drone_{cfg_b.bid}.{cfg_b.drid}')

    print(f"Drone {cfg_b.bid}.{cfg_b.drid} is running...")    

    # run loop
    command_queue = queue.Queue()
    returns_queue = queue.Queue()
    listenMode(r, p, chans.subList(cfg_b.bid, cfg_b.drid), 
               command_queue, cfg_b.interval_feeds, returns_queue)

            


# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _setupLogging
def _setupLogging():

    # Create a rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        cfg_b.log_path, 
        maxBytes=cfg_b.log_MB * 1024 * 1024, 
        backupCount=cfg_b.log_backup_count
    )

    # Set the logging format
    formatter = logging.Formatter(
        '{asctime} {levelname} {filename}:{lineno}: {message}',
        datefmt='%Y-%m-%d %H:%M:%S',
        style='{'
    )
    handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level
    logger.addHandler(handler)


# ============================================================================ #
# _print (monkeypatch)
_print = print 
def print(*args, **kw):
    '''Override the print statement.
    '''
    
    msg = ""

    # add drone id
    if cfg_b.bid and cfg_b.drid:
        # msg += f"drone={cfg_b.bid}.{cfg_b.drid}: "
        msg += f"{cfg_b.bid}.{cfg_b.drid}: "

    # add current filename
    # msg += f"{os.path.basename(__file__)}: "

    # add print strings
    msg += " ".join(map(str, args))

    # log msg
    logging.info(msg)

    # print to console
    _print(msg, **kw)

builtins.print = print


# ============================================================================ #
# _setupArgparse
def _setupArgparse():
    '''Setup the argparse arguments'''

    parser = argparse.ArgumentParser(
        description='Terminal interface to drone script.')

    # add arguments
    parser.add_argument(                # positional, required, 1-4
        "drid", type=int, help="drone id", choices=range(1,4+1))
   
    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# _modifyConfig
def _modifyConfig(args):
    '''modify config level variables'''

    # project root directory (src)
    cfg_b.src_dir = os.getcwd()          # assuming this file lives in root dir

    # parent directory
    par_dir = os.path.realpath(os.path.pardir)

    # drone directory
    cfg_b.drone_dir = f'{par_dir}/drones/drone{args.drid}'

    # tmp directory
    cfg_b.temp_dir = f'/tmp/drone{args.drid}'

    # drone config
    sys.path.append(cfg_b.drone_dir)
    cfg_dr = importlib.import_module(f'_cfg_drone{args.drid}')

    # drone identifier
    cfg_b.drid = cfg_dr.drid


# ============================================================================ #
# _setupTmpDir
def _setupTmpDir():
    '''Setup the system tmp directory to use.
    '''

    d = cfg_b.temp_dir

    # Ensure the custom directory is fresh
    if os.path.exists(d):
        shutil.rmtree(d)  # Delete the existing directory
    os.makedirs(d)        # Create a fresh directory

    # Set the TMPDIR environment variable
    os.environ["TMPDIR"] = d


# ============================================================================ #
# _loadGateware
def _loadGateware():

    try:
        from pynq import Overlay # type: ignore

        gateware_file = os.path.join(cfg_b.dir_root, cfg_b.gateware_file)
        cfg_b.gateware = Overlay(gateware_file, ignore_version=True, download=False)

        # gateware version
        gateware_fname = os.path.splitext(os.path.basename(gateware_file))[0]
        print(gateware_fname)
        gateware_fname_parts = re.search(r'_v(\d+)p(\d+)', gateware_fname)
        cfg_b.gateware_version = int(gateware_fname_parts.group(1)) 
        cfg_b.gateware_version_minor = int(gateware_fname_parts.group(2))

    except Exception as e: 
        print(f"Gateware loading issue: {e}")


# ============================================================================ #
# connectRedis
def connectRedis():
    '''connect to redis server'''
    r = redis.Redis(host=cfg_b.host, port=cfg_b.port, db=cfg_b.db, password=cfg_b.pw)
    p = r.pubsub()

    # check for connection
    try:
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")

    return r, p


# ============================================================================ #
# _loopExecuteCommands
def _loopExecuteCommands(r, command_queue, returns_queue):
    '''Loop to listen for and sequentially execute commands.
    '''

    while True:

        # Get next command from queue
        chan_str, payload = command_queue.get()  
        try:
            com_num, ret_data, args, kwargs = payloadToCom(payload)
            com_ret = executeCommand(com_num, ret_data, args, chan_str, kwargs)
        except Exception as e:
            com_ret = f"Payload error ({payload}): {e}"
            print(com_ret)
        
        # publishResponse(com_ret, r, chan_str)  # Send response

        # Queue the return to publish
        returns_queue.put((com_ret, r, chan_str))
        
        command_queue.task_done()


# ============================================================================ #
# _loopUpdateFeeds
def _loopUpdateFeeds(r, interval):
    """Loop to update feeds.
    """

    while True:

        try:
            feeds.setFeedSpc(r, interval)   # free disk space
            feeds.setFeedTemps(r, interval) # temperatures 

            time.sleep(interval)

        except Exception as e:
            print(f"ERROR in drone.py._loopUpdateFeeds: {e}")
            time.sleep(5)  # Prevent crashing loop from overloading CPU


# ============================================================================ #
# _loopReturnsQueue
def _loopReturnsQueue(r, returns_queue):
    '''Loop to listen for and sequentially execute commands.
    '''

    while True:

        # Get next return from queue
        com_ret, r, chan_str = returns_queue.get()

        # publish the return
        publishResponse(com_ret, r, chan_str)  # Send response
        
        returns_queue.task_done()


# ============================================================================ #
# listenMode
def listenMode(r, p, chan_subs, command_queue, interval_feeds, returns_queue):
    '''
    '''

    # Start feeds thread
    threading.Thread(
        target=_loopUpdateFeeds, 
        args=(r, interval_feeds), daemon=True
        ).start()

    # Start command processing thread
    threading.Thread(
        target=_loopExecuteCommands, 
        args=(r, command_queue, returns_queue), daemon=True
        ).start()
    
    # Start returns queue thread
    threading.Thread(
        target=_loopReturnsQueue, 
        args=(r, returns_queue), daemon=True
        ).start()

    # Command loop: listens for messages and adds them to the queue
    p.psubscribe(chan_subs)  # Subscribe to channels
    last_chan_str = ''
    for new_message in p.listen():
        if new_message['type'] != 'pmessage':
            continue  # Ignore non-command messages

        chan_str = new_message['channel'].decode('utf-8')

        if chan_str == last_chan_str: # command unique
            continue  # Prevent duplicate processing
        last_chan_str = chan_str

        payload = new_message['data'].decode('utf-8')

        # Queue the command for execution
        command_queue.put((chan_str, payload))


# ============================================================================ #
# executeCommand
def executeCommand(com_num, ret_data, args, chan_str, kwargs):
    '''
    ret_data: (bool) Whether to return data from command func.
    '''

    print(f"Exe com {com_num} (chan: {chan_str} args={args} {kwargs})")

    # execute the command
    try:
        ret = alcove.callCom(com_num, args, kwargs)

    # command execution failed
    except Exception as e:
        ret = f"Command execution error: {e}"
        print(f" Command {com_num} execution failed.")

    # command execution successful
    else:
        if ret is None or not ret_data:
            ret = f"Command {com_num} executed." # success ack.
        # print(f" Command {com_num} execution done.")

    return ret


# ============================================================================ #
# _requestPublishReturnPermission
def _requestPublishReturnPermission(r, payload_size_bytes):
    """
    Attempt to reserve space in a shared Redis byte counter before publishing return data.

    This function uses a Lua script to atomically check whether a given number of bytes (payload_size_bytes) can be "acquired" from the Redis key 'rtn_data_max_bytes'. If enough bytes are available, it decrements the counter by that amount and returns 1. Otherwise, it returns 0 without modifying the counter.

    Args:
        r (redis.Redis): Redis client instance.
        payload_size_bytes (int): Number of bytes to reserve.

    Returns:
        int: 1 if reservation succeeded (enough space available), 0 otherwise.
    """

    lua_script = """
        local available_bytes = tonumber(redis.call('GET', KEYS[1]) or '0')
        local bytes_to_acquire = tonumber(ARGV[1])

        if available_bytes >= bytes_to_acquire then
            redis.call('DECRBY', KEYS[1], bytes_to_acquire)
            return 1
        else
            return 0
        end
    """
    reserve_bytes = r.register_script(lua_script)

    reserved = reserve_bytes(
        keys=['rtn_data_max_bytes'],
        args=[payload_size_bytes])
    

    # print(f"payload_size_bytes={payload_size_bytes}")
    # print(f"reserved={reserved}")

    return reserved


# ============================================================================ #
# publishResponse
def publishResponse(resp, r, chan_str):
    '''Publish a response on return channel.
    '''

    chan = chans.comChan(chan=chan_str)

    # convert return to bytes object; required by Redis
    try:
        ret = pickle.dumps(resp) 
    except:
        print(f' Publish response failed: Cannot pickle.')
        return

    # request publish permission
    t_retry = 0.1 # s; intial retry delay, then exponential
    retries = 50 # total number of retry attempts
    payload_size_bytes = len(ret)
    while not _requestPublishReturnPermission(r, payload_size_bytes):
        time.sleep(t_retry)

        # exponential wait before retry 
        # with some randomness to spread load
        # max 5 s
        t_retry = min(5., t_retry*np.random.uniform(1.5, 2.5))

        # too many retries, failing
        if retries <= 0:
            print(" Publish response failed: Too many retries.")
            return
        retries -= 1

    # publish response
    try: 
        r.publish(chan.pubRet, ret) # publish resp with Redis on return channel

    except Exception as e:
        print(f' Publish response failed with error: {e}')


# ============================================================================ #
# listToArgsAndKwargs
def listToArgsAndKwargs(args_list):
    """Split an arg list into args and kwargs.
    l: Args list to split.
    Returns args (list) and kwargs (dictionary)."""
    
    args_str = ' '.join(args_list)
    args_str = args_str.replace(",", " ")
    args_str = args_str.replace("=", " = ")
    args_str = ' '.join(args_str.split()) # remove excess whitespace
    l = args_str.split()
    
    args = []
    kwargs = {}
    while len(l)>0:
        v = l.pop(0)

        if len(l)>0 and l[0]=='=': # kwarg
            l.pop(0) # get rid of =
            kwargs[v] = l.pop(0)

        else: # arg
            args.append(v)

    return args, kwargs


# ============================================================================ #
# payloadToCom
def payloadToCom(payload):
    """
    Convert payload to com_num, args, kwargs.
        payload: Command string data.
            Payload format: [com_num] [positional arguments] [named arguments].
            Named arguments format: -[argument name] [value].
    """
    
    paylist = payload.split()
    com_num = int(paylist.pop(0)) # assuming first item is com_num
    ret_data = int(paylist.pop(0)) # assuming second item is ret_data
    args, kwargs = listToArgsAndKwargs(paylist)
    
    return com_num, ret_data, args, kwargs


# ============================================================================ #
# get/setKeyValue
def getKeyValue(key):
    """
    GET the value of given key.
    """

    r,p = connectRedis()
    ret = r.get(bytes(key, encoding='utf-8'))
    ret = None if ret is None else ret.decode('utf-8')

    return ret

def setKeyValue(key, value):
    """
    SET the given value for the given key.
    """

    r,p = connectRedis()
    r.set(bytes(key, encoding='utf-8'), bytes(value, encoding='utf-8'))   



# ============================================================================ #
# MAIN
# ============================================================================ #


if __name__ == "__main__":
    main()