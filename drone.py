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
    # think about how the boards get bid, server details, channels
     
    bid = 1                           # board identifier

    host = 'localhost'                # redis server details
    port = 6379
    db = 0

    chan_subs = [                     # listening channels
        f'board_{bid}', 
        'all_boards'] 
    chan_pubs = f'board_rets_{bid}'   # talking channel
    # any other channels?

    # make a connection to redis-server
    r = redis.Redis(host=host, port=port, db=db)
    p = r.pubsub()

# thread = p.run_in_thread(sleep_time=0.001)
# thread.stop()
# def custom_handler(message):
#        # do_something with the message
#        print(message)
# p.psubscribe(**{'hello*':custom_handler})
# thread = p.run_in_thread(sleep_time=0.001)

    # subscribe and listen for redis messages
    p.psubscribe(chan_subs)
    for new_message in p.listen():
        # how do we exit out of listening mode?
            # can also do this in a thread
        print(new_message) 
        # remove this later since it's logged by Redis(?)

        # assuming that any message is a command
        # the command key is then the data of the message
            # we'll have to think about this
        key = int(new_message['data'])

        # ask alcove to execute the command
        print(f"executing command: {key}")
        ret = alcove.callCom(key)
        if ret is not None: # publish returns to pub channel
                # note that default return is None
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


if __name__ == "__main__":
    main()