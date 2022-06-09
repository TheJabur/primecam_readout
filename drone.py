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
import pickle

import _cfg_board as cfg



######################
### MAIN EXECUTION ###


def main():   
    bid = cfg.bid                       # board identifier
    chan_subs = [                       # listening channels
        f'board_{bid}_*',               # this boards listening channels
        'all_boards']                   # an all-boards listening channel

    r,p = connectRedis()                # redis and pubsub objects

    listenMode(r, p, bid, chan_subs)    # listen for redis messages
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


def connectRedis():
    '''connect to redis server'''
    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db)
    p = r.pubsub()
    return r, p


def listenMode(r, p, bid, chan_subs):
    p.psubscribe(chan_subs)             # channels to listen to
    for new_message in p.listen():      # infinite listening loop
        print(new_message)              # output message to term/log

        if new_message['type'] != 'pmessage': # not a command
            continue                    # skip this message

        channel = new_message['channel'].decode('utf-8')
        com_num = int(new_message['data'])  # the command num
        cid = channel.split('_')[-1]    # recover cid from channel

        com_ret = executeCommand(com_num) # attempt execution
        
        publishResponse(com_ret, r, bid, cid) # send response


def executeCommand(com_num):
    print(f"Executing command: {com_num}... ", end="")
    try:
        ret = alcove.callCom(com_num)   # execute the command

    except Exception as e:              # command execution failed
        ret = f"Command execution error: {e}"
        print("Failed.")

    else:                               # command execution successful
        if ret is None:                 # default return is None (success)
            ret = f"Command {com_num} executed." # success ack.
        print("Done.")

    return ret


def publishResponse(resp, r, bid, cid):
    chanid = f'{bid}_{cid}'             # rebuild chanid
    chan_pubs = f'board_rets_{chanid}'  # talking channel

    print(f"Preparing response... ", end="")
    try:
        ret = pickle.dumps(resp)        # pickle serializes to bytes obj.
        # this is needed because redis pubsub only allows bytes objects
    except Exception as e:
        print("Failed.")
        return                          # exit: need ret to send
    else:
        print("Done.")

    print(f"Sending response... ", end="")
    try:
        r.publish(chan_pubs, ret)
    except Exception as e:
        print("Failed.")
    else:
        print(f"Done.")



if __name__ == "__main__":
    main()