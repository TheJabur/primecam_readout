# ============================================================================ #
# drone.py
# Board side Redis interface script.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT/FYST 2023 
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #


import alcove
import redis
import os
import sys
import importlib
import logging
import pickle
import argparse

from config import board as cfg
import redis_channels as rc



# ============================================================================ #
# CONFIG
# ============================================================================ #


logging.basicConfig(
    filename='../logs/board.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)



# ============================================================================ #
# MAIN
# ============================================================================ #


def main():
    # CTRL-c to exit out of listen mode

    args = setupArgparse() # get command line arguments

    modifyConfig(args) # modify execution level configs

    r,p = connectRedis()
    r.client_setname(f'drone_{cfg.bid}.{cfg.drid}')

    print(f"Drone {cfg.bid}.{cfg.drid} is running...")
    sub_chan_list = rc.getThisChanList()
    listenMode(r, p, sub_chan_list)
            


# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# print monkeypatch
# the print statement should be further modified
# to save all statements into a log file
_print = print 
def print(*args, **kw):
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)


# ============================================================================ #
# setupArgparse
def setupArgparse():
    '''Setup the argparse arguments'''

    parser = argparse.ArgumentParser(
        description='Terminal interface to drone script.')

    # add arguments
    parser.add_argument(                # positional, required, 1-4
        "drid", type=int, help="drone id", choices=range(1,4+1))
   
    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# modifyConfig
def modifyConfig(args):
    '''modify config level variables'''

    # sys.path.insert(1, os.path.realpath(os.path.pardir))

    ## project root directory (src)
    cfg.root_dir = os.getcwd()          # assuming this file lives in root dir

    ## parent directory
    par_dir = os.path.realpath(os.path.pardir)

    ## drone directory
    cfg.drone_dir = f'{par_dir}/drones/drone{args.drid}'

    ## drone config
    sys.path.append(cfg.drone_dir)
    cfg_dr = importlib.import_module(f'_cfg_drone{args.drid}')

    ## drone identifier
    cfg.drid = cfg_dr.drid


# ============================================================================ #
# connectRedis
def connectRedis():
    '''connect to redis server'''
    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db)
    p = r.pubsub()

    # check for connection
    try:
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")

    return r, p


# ============================================================================ #
# listenMode
def listenMode(r, p, chan_subs):
    p.psubscribe(chan_subs)             # channels to listen to

    for new_message in p.listen():      # infinite listening loop
        # print(new_message)

        if new_message['type'] != 'pmessage': # not a command
            continue                    # skip this message

        chan_sub = new_message['channel'].decode('utf-8')
        # channel = new_message['channel'].decode('utf-8')
        # cid = channel.split('_')[-1]    # recover cid from channel

        payload = new_message['data'].decode('utf-8')
        try:
            com_num, args, kwargs = payloadToCom(payload) # split payload into command
            # print(com_num, args, kwargs)
            com_ret = executeCommand(com_num, args, kwargs) # attempt execution
        except Exception as e:
            com_ret = f"Payload error ({payload}): {e}"
            print(com_ret)
        
        # publishResponse(com_ret, r, bid, cid) # send response
        publishResponse(com_ret, r, chan_sub) # send response


# ============================================================================ #
# executeCommand
def executeCommand(com_num, args, kwargs):
    print(f"Executing command: {com_num}... ")
    try: #####
        ret = alcove.callCom(com_num, args, kwargs)   # execute the command

    except Exception as e:              # command execution failed
        ret = f"Command execution error: {e}"
        print(f"Command {com_num} execution failed.")
        logging.info('Command {com_num} execution failed.')

    else:                               # command execution successful
        if ret is None:                 # default return is None (success)
            ret = f"Command {com_num} executed." # success ack.
        print(f"Command {com_num} execution done.")
        logging.info(f'Command {com_num} execution successful.')

    return ret


# ============================================================================ #
# publishResponse
def publishResponse(resp, r, chan_sub):

    chan_pub = rc.getReturnChan(chan_sub)
    print(chan_pub)

    print(f"Preparing response... ", end="")
    try: #####
        ret = pickle.dumps(resp)        # pickle serializes to bytes obj.
        # this is needed because redis pubsub only allows bytes objects
    except Exception as e:
        _print("Failed.")
        logging.info(f'Publish response failed.')
        return                          # exit: need ret to send
    else:
        _print("Done.")

    print(f"Sending response... ", end="")
    try: #####
        r.publish(chan_pub, ret)       # publish with redis
    except Exception as e:
        _print("Failed.")
        logging.info(f'Publish response failed.')
    else:
        _print(f"Done.")
        logging.info(f'Publish response successful.')


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
    args, kwargs = listToArgsAndKwargs(paylist)
    
    return com_num, args, kwargs


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