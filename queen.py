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
import numpy as np
import logging
import uuid
import pickle
import tempfile

import _cfg_queen as cfg

import queen_commands.test_functions as test



##############
### CONFIG ###


logging.basicConfig(
    filename='logs/queen.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)


# official list of queen commands
# combined with alcove commands
# alcove command keys start at 10
# queen command keys start at 20
def _com():
    return {
        1:alcoveCommand,
        2:listenMode,
        3:getKeyValue,
        4:setKeyValue,
        9:test.testFunc1
    }



#########################
### COMMAND FUNCTIONS ###


def alcoveCommand(com_num, bid=None, drid=None, all_boards=False, args=None):
    '''Send an alcove command to given board.
    com_num: Command number.
    bid: Board identifier.
    drid: Drone identifier (1-4). Requires bid to be set.
    all_boards: Send to all boards instead of bid/drid.
    args: String command arguments.'''

    ## Connect to Redis server
    print(f"Connecting to Redis server... ", end="")
    try:
        r,p = _connectRedis()  # redis and pubsub objects
    except Exception as e: return _fail(e, f'Failed to connect to Redis server.')
    else: _success("Connected to Redis server.")

    ## build payload
    # payload consists of commmand number and arguments
    if args is None:
        payload = com_num
    else:
        payload = f"{com_num} {args}"

    ## Send to all boards
    if all_boards:
        #p.psubscribe(f'board_rets_*')     # all bid return channels
        # don't listen for responses
        # they will go into the log from the monitoring version of queen

        ## Publish command to all boards
        print(f"Publishing command {com_num} to all boards... ", end="")
        try:
            num_clients = r.publish(f'all_boards', payload)     # send command
        except Exception as e: return _fail(e, f'Failed to publish command.')
        else: _success("Published command.")

        print(f"{num_clients} drones received this command. Returns will be logged.")
        return True # done

    ## Send to a single board
    elif bid:

        ## Generate unique channels
        print(f"Generating unique channels... ", end="")
        try:
            id       = f'{bid}.{drid}' if drid else f'{bid}'
            cid      = uuid.uuid4() # unique string
            chanid   = f'{id}_{cid}'
            chan_pub = f'board_{chanid}'
            chan_sub = f'rets_{chan_pub}'
        except Exception as e: return _fail(e, f'Failed to generate unique channel ID.')
        else: _success("Generated unique channel ID.")

        ## Publish command to single board
        print(f"Publishing command {com_num} to board {id}... ", end="")
        try:
            p.psubscribe(chan_sub)                     # return channel
            num_clients = r.publish(chan_pub, payload) # send command
        except Exception as e: return _fail(e, f'Failed to publish command.')
        else: _success("Published command.")

        if num_clients == 0: # no one listening!
            # This may mean the board has crashed
            print(f"No client received this command!")
            return True

        ## Listen for a response
        print(f"Listening for a response... ", end="")
        for new_message in p.listen():              # listen for a return
            if new_message['type'] != 'pmessage': continue # not correct message
            _success("Response received.")

            # add a timeout?

            ## Process response
            print(f"Processing response... ", end="")
            try:
                _processCommandReturn(new_message['data'])
            except Exception as e: return _fail(e, f'Failed to process response.')
            else: _success("Processed response.")

            # stop listening; we only expect a single response
            return True # done

    # not clear who to send command to
    else:
        print("Command not sent: bid required if not sending to all boards.")


def callCom(com_num, args=None):
    '''execute a queen command function by key'''

    # dictionary keys are stored as integers
    # but redis may convert to string
    # key = int(key)                       # want int for com

    if com_num not in com:               # invalid command
        print('Invalid command: '+str(com_num))
        return

    ## build payload
    # payload consists of commmand number and arguments
    if args is None:
        payload = str(com_num)
    else:
        payload = f"{com_num} {args}"
        
    try:
        com_num, args, kwargs = payloadToCom(payload) # split payload into command
        ret = com[com_num](*args, **kwargs)
    except BaseException as e: 
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(e).__name__, e.args)
        ret = message

    if ret is not None:              # default success return is None
        # what if ret is not a string, e.g. data?
        # can we signal that in the ret or need to check?
        # and then what to do with them?
        print(f"{com[com_num].__name__}: {ret}") # monkeypatched to log
    


    # else:
    #     try:                             # attempt to run command
    #         ret = com[key](*args, **kwargs)
    #     except BaseException as e: 
    #         template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    #         message = template.format(type(e).__name__, e.args)
    #         ret = message

    #     if ret is not None:              # default success return is None
    #         # what if ret is not a string, e.g. data?
    #         # can we signal that in the ret or need to check?
    #         # and then what to do with them?
    #         print(f"{com[key].__name__}: {ret}") # monkeypatched to log


def listenMode():
    """
    Listen for Redis messages in thread.
    """
    # the only way to stop listening is to kill process

    r,p = _connectRedis()

    def handleMessage(message):
        '''actions to take on receiving message'''
        if message['type'] == 'pmessage':
            print(message['data'].decode('utf-8')) # log/print message
            _notificationHandler(message)  # send important notifications

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


def getKeyValue(key):
    """
    GET the value of given key.
    """

    r,p = _connectRedis()
    ret = r.get(bytes(key, encoding='utf-8')).decode('utf-8')

    print(ret) # log/print message
    _notificationHandler(ret)  # send important notifications


def setKeyValue(key, value):
    """
    SET the given value for the given key.
    """

    r,p = _connectRedis()
    r.set(bytes(key, encoding='utf-8'), bytes(value, encoding='utf-8'))   



##########################
### INTERNAL FUNCTIONS ###


# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    _print(*args, **kw)            # print to terminal
    logging.info(' '.join(args))   # log to file


def _success(msg):
    _print("Done.")
    if msg is not None: logging.info(msg)


def _fail(e, msg=None):
    _print("Failed.")
    if msg is not None: logging.info(msg)
    logging.error(e)
    return e


def _connectRedis():
    '''connect to redis server'''

    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db)
    p = r.pubsub()
    return r, p


def _processCommandReturn(dat):
    '''Process the return data from a command.'''

    dat = pickle.loads(dat)                # assuming msg is pickled

    if isinstance(dat, str):            # print only if string
        print(dat) 

    elif isinstance(dat, np.ndarray):   # save arrays to tmp .npy file
        with tempfile.NamedTemporaryFile(dir='tmp', suffix='.npy', delete=False) as tf:
            np.save(tf, dat)

    else:                               # write other types to tmp file
        with tempfile.NamedTemporaryFile(dir='tmp', delete=False) as tf:
            tf.write(pickle.dumps(dat))

    # note that these tmp files are not currently ever cleared out


def _notificationHandler(message):
    '''process given messages for sending notifications to end-users'''

    print("notificationHandler(): Not implemented yet!")
    # todo
     # look through given message[s?]
     # and look through configured notifications
     # and send emails as appropriate


def listToArgsAndKwargs(l):
    '''Split a list into args and kwargs.
    l: List to split.
    Returns args (list) and kwargs (dictionary).'''

    args = []
    kwargs = {}
    while len(l)>0:
        v = l.pop(0)

        # if this doesn't have a dash in front
        # or theres no more items
        # or the next item has a dash in front
        if v[0]!='-' or len(l)==0 or l[0][0]=='-':
            args.append(v)             # then this is an arg

        else:
            v = v.lstrip('-')          # remove dashes in front
            kwargs[v] = l.pop(0)       # this is a kwarg

    return args, kwargs


def payloadToCom(payload):
    '''Convert payload to com_num, args, kwargs.
    payload: Command string data.
        Payload format: [com_num] [positional arguments] [named arguments].
        Named arguments format: -[argument name] [value].'''
    
    paylist = payload.split()
    com_num = int(paylist.pop(0)) # assuming first item is com_num
    args, kwargs = listToArgsAndKwargs(paylist)
    
    return com_num, args, kwargs



############
### INIT ###

com = _com()