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
    bid = cfg.bid                     # board identifier
    chan_subs = [                     # listening channels
        f'board_{bid}',                # this boards private listening channel
        'all_boards']                  # an all-boards listening channel
    chan_pubs = f'board_rets_{bid}'   # talking channel

    # make a connection to redis-server
    r,p = connectRedis()

    # subscribe and listen for redis messages
    p.psubscribe(chan_subs)
    for new_message in p.listen():
        # how do we exit out of listening mode?

        # remove this later since it's logged by Redis(?)
        print(new_message) 
    
        # only pmessage are commands
        if new_message['type'] != 'pmessage':
            continue

        # the command is the data of a pmessage
        key = int(new_message['data'])

        # ask alcove to execute the command
        print(f"executing command: {key}...")
        ret = alcove.callCom(key)
        
        if ret is None: # note that default return is None
            ret = f"command {key} executed."
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