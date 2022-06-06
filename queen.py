########################################################
### Main server-side script.                         ###
### Allows execution of server command functions     ###
### and remote alcove (on board) functions.          ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

import redis
import logging
import queen_commands.test_functions as test


##############
### CONFIG ###

logging.basicConfig(
    filename='queen.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)

# official list of queen commands
# combined with alcove commands
# alcove command keys start at 10
# queen command keys start at 20
def _com():
    return {
        20:alcoveCommand,
        21:listenMode,
        22:test.testFunc1
    }


#########################
### COMMAND FUNCTIONS ###

def alcoveCommand(key, bid=None, all_boards=False):
    '''send an alcove command to given board
    key: command key
    bid: board identifier
    all_boards: send to all boards instead of bid'''

    r,p = connectRedis()

    if all_boards:
        #p.psubscribe(f'board_rets_*')     # all bid return channels
        # don't listen for responses
        # they will go into the log from the monitoring version of queen
        r.publish(f'all_boards', key)     # send command
    
    elif bid is None:
        print('error: if all_boards is not True then must provide a bid')

    else: # send to a single board: bid
        p.psubscribe(f'board_rets_{bid}') # bid return channel
        r.publish(f'board_{bid}', key)    # send command
        for new_message in p.listen():    # listen for a return
            # add a timeout?
            if new_message['type'] == 'pmessage':
                print(new_message['data'].decode('utf-8'))
                break # stop listening; we only expect a single response

def listenMode():
    '''listen for Redis messages in thread'''
    # the only way to stop listening is to kill process

    r,p = connectRedis()

    def handleMessage(message):
        '''actions to take on receiving message'''
        if message['type'] == 'pmessage':
            print(message['data'].decode('utf-8')) # log/print message
            notificationHandler(message)  # send important notifications

    p.psubscribe(**{'board_rets_*':handleMessage}) # all board return chans
    thread = p.run_in_thread(sleep_time=2) # move listening to thread
        # sleep_time is a socket timeout
         # too low and it will bog down server
         # can be set to None but may cause issues
         # more research is recommended
    print('The Queen is listening...') 

    # todo
     # when do we stop listening?
     # thread.stop()


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    _print(*args, **kw)            # print to terminal
    logging.info(' '.join(args))   # log to file

def callCom(key):
    '''execute a queen command function by key'''

    # dictionary keys are stored as integers
    # but redis may convert to string
    key = int(key)                       # want int for com
    
    if key not in com:                   # invalid command
        print('invalid key: '+str(key))

    else:
        try:                             # attempt to run command
            ret = com[key]()
        except BaseException as e: 
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            ret = message

        if ret is not None:              # default success return is None
            print(f"{com[key].__name__}: {ret}") # monkeypatched to log

def connectRedis(host='localhost', port=6379):
    '''connect to redis server'''

    r = redis.Redis(host=host, port=port, db=0)
    p = r.pubsub()
    return r, p

def notificationHandler(message):
    '''process given messages for sending notifications to end-users'''

    print("notificationHandler(): Not implemented yet!")
    # todo
     # look through given message[s?]
     # and look through configured notifications
     # and send emails as appropriate


############
### INIT ###

com = _com()