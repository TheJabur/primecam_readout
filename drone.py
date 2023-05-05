########################################################
### Remote-side Redis interface.                     ###
### Interfaces with redis-client to execute alcove   ###
### commands from queen.                             ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################



###############
### IMPORTS ###


import alcove
import redis
import os
import sys
import importlib
import logging
import pickle
import argparse

import _cfg_board as cfg
# import _cfg_drone done in main()



##############
### CONFIG ###

logging.basicConfig(
    filename='logs/board.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)



######################
### MAIN EXECUTION ###


def main():   

    args = setupArgparse()              # get command line arguments

    modifyConfig(args)                  # modify execution level configs

    bid  = cfg.bid                      # board identifier
    drid = cfg.drid                     # drone identifier
    chan_subs = [                       # listening channels
        f'board_{bid}_*',               # this boards listening channels
        f'board_{bid}.{drid}_*',        # this drones listening channels
        'all_boards']                   # an all-boards listening channel

    print(chan_subs)

    r,p = connectRedis()                # redis and pubsub objects

    # listenMode(r, p, bid, chan_subs)    # listen for redis messages
    listenMode(r, p, chan_subs)
    # currently, only way to exit out of listen mode is CTRL-c
            


##########################
### INTERNAL FUNCTIONS ###


# monkeypatch the print statement
# the print statement should be further modified
# to save all statements into a log file
_print = print 
def print(*args, **kw):
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)


def setupArgparse():
    '''Setup the argparse arguments'''

    parser = argparse.ArgumentParser(
        description='Terminal interface to drone script.')

    # add arguments
    parser.add_argument(                # positional, required, 1-4
        "drid", type=int, help="drone id", choices=range(1,4+1))
   
    # return arguments values
    return parser.parse_args()


def modifyConfig(args):
    '''modify config level variables'''

    ## project root directory
    cfg.root_dir = os.getcwd()          # assuming this file lives in root dir

    ## drone directory
    cfg.drone_dir = f'{cfg.root_dir}/drones/drone{args.drid}'

    ## drone config
    sys.path.append(cfg.drone_dir)
    cfg_dr = importlib.import_module(f'_cfg_drone{args.drid}')

    ## drone identifier
    cfg.drid = cfg_dr.drid


def connectRedis():
    '''connect to redis server'''
    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db)
    p = r.pubsub()
    return r, p


# def listenMode(r, p, bid, chan_subs):
def listenMode(r, p, chan_subs):
    p.psubscribe(chan_subs)             # channels to listen to
    for new_message in p.listen():      # infinite listening loop
        print(new_message)              # output message to term/log

        if new_message['type'] != 'pmessage': # not a command
            continue                    # skip this message

        chan_sub = new_message['channel'].decode('utf-8')
        # channel = new_message['channel'].decode('utf-8')
        # cid = channel.split('_')[-1]    # recover cid from channel

        payload = new_message['data'].decode('utf-8')
        try:
            com_num, args, kwargs = payloadToCom(payload) # split payload into command
            print(com_num, args, kwargs)
            com_ret = executeCommand(com_num, args, kwargs) # attempt execution
        except Exception as e:
            com_ret = f"Payload error ({payload}): {e}"
            print(com_ret)
        
        # publishResponse(com_ret, r, bid, cid) # send response
        publishResponse(com_ret, r, chan_sub) # send response


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


# def publishResponse(resp, r, bid, cid):
def publishResponse(resp, r, chan_sub):
    # chanid = f'{bid}_{cid}'             # rebuild chanid
    # chan_pubs = f'board_rets_{chanid}'  # talking channel

    chan_pub = f'rets_{chan_sub}'
    if chan_sub == 'all_boards': # to know who sent
        chan_pub += f'_{cfg.bid}.{cfg.drid}'

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
        # r.publish(chan_pubs, ret)       # publish with redis
        r.publish(chan_pub, ret)       # publish with redis
    except Exception as e:
        _print("Failed.")
        logging.info(f'Publish response failed.')
    else:
        _print(f"Done.")
        logging.info(f'Publish response successful.')


def listToArgsAndKwargs(args_list):
    """Split an arg list into args and kwargs.
    l: Args list to split.
    Returns args (list) and kwargs (dictionary)."""
    
    args_str = ' '.join(args_list)
    args_str = args_str.replace(",", " ")
    args_str = args_str.replace("=", " = ")
    args_str = ' '.join(args_str.split()) # remove excess whitespace
    l = args_str.split(' ')
    
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


def getKeyValue(key):
    """
    GET the value of given key.
    """

    r,p = connectRedis()
    ret = r.get(bytes(key, encoding='utf-8')).decode('utf-8')

    return ret


def setKeyValue(key, value):
    """
    SET the given value for the given key.
    """

    r,p = connectRedis()
    r.set(bytes(key, encoding='utf-8'), bytes(value, encoding='utf-8'))   



if __name__ == "__main__":
    main()