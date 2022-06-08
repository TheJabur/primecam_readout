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
import _cfg_board as cfg


######################
### MAIN EXECUTION ###

def main():   
    bid = cfg.bid                       # board identifier
    chan_subs = [                       # listening channels
        f'board_{bid}_*',               # this boards listening channels
        'all_boards']                   # an all-boards listening channel

    r,p = connectRedis()                # redis and pubsub objects

    # subscribe and listen for redis messages
    # currently, only way to exit out of listen mode is CTRL-c
    # think about alternatives
    p.psubscribe(chan_subs)
    for new_message in p.listen():
        print(new_message)              # output to terminal/log

        if new_message['type'] != 'pmessage':
            continue                    # only pmessage are commands
        channel = new_message['channel'].decode('utf-8')
        key = int(new_message['data'])  # the command num

        print(f"executing command: {key}...")
        ret = alcove.callCom(key)       # execute the command
                
        if ret is None:                 # default return is None
            ret = f"command {key} executed."

        cid = channel.split('_')[-1]    # recover cid from channel
        chanid = f'{bid}_{cid}'         # rebuild chanid
        chan_pubs = f'board_rets_{chanid}' # talking channel
        r.publish(chan_pubs, ret) 
            

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


if __name__ == "__main__":
    main()