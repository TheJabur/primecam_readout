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


######################
### MAIN EXECUTION ###

def main():
    # make a connection to redis-server
    host = 'localhost'
    channels = 'test*'
    r, p = connectRedis(channels, host)

    # primary functionality:
    # listen for redis messages
    for new_message in p.listen():
        # how do we exit out of listening mode?
        print(new_message)
        # currently just printing the message
        # assume its a command and execute it instead

    # execute a command
    # alcove.callCom(key='1')


##########################
### INTERNAL FUNCTIONS ###

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