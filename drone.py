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


######################
### MAIN EXECUTION ###

def main():
    # make a connection to redis-server
        # currently just using a test channel
        # in future will want a channel for each board
        # plus an all board channel (others?)
    host = 'localhost'
    channels = 'test*'
    r, p = connectRedis(channels, host)

    # primary functionality:
    # listen for redis messages
    for new_message in p.listen():
        # how do we exit out of listening mode?
            # can also do this in a thread
        print(new_message)
        key = int(new_message['data'])
        # assuming that the data of any message is a command
            # we'll have to think about this
        print(f"executing command: {key}")
        alcove.callCom(key)


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)

def connectRedis(channels, host, port=6379, db=0):
    '''connect to redis server'''
    # if there are other potential args
    # then may want to use kwargs

    r = redis.Redis(host=host, port=port, db=db)
    p = r.pubsub()
    p.psubscribe(channels)
    return r, p


if __name__ == "__main__":
    main()