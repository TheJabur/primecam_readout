# ============================================================================ #
# queen.py
# Control computer script to send commands to drones.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2022   
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #

import redis
import numpy as np
import logging
# import uuid
import pickle
from datetime import datetime
# import tempfile

import _cfg_queen as cfg

import queen_commands.control_io as io
import redis_channels as rc
import queen_commands.test_functions as test



# ============================================================================ #
# CONFIG
# ============================================================================ #


logging.basicConfig(
    filename='logs/queen.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)


# ============================================================================ #
#  queen commands list
def _com():
    return {
        1:alcoveCommand,
        2:listenMode,
        3:getKeyValue,
        4:setKeyValue,
        5:getClientList,
        9:test.testFunc1
    }



# ============================================================================ #
# COMMAND FUNCTIONS
# ============================================================================ #


# ============================================================================ #
#  alcoveCommand
def alcoveCommand(com_num, bid=None, drid=None, all_boards=False, args=None):
    '''Send an alcove command to given board.
    com_num: Command number.
    bid: Board identifier.
    drid: Drone identifier (1-4). Requires bid to be set.
    all_boards: Send to all boards instead of bid/drid.
    args: String command arguments.'''

    print(f"Connecting to Redis server... ", end="")
    try:
        r,p = _connectRedis()
    except Exception as e: return _fail(e, f'Failed to connect to Redis server.')
    else: _success("Connected to Redis server.")

    payload = com_num if args is None else f"{com_num} {args}"

    ## Send to all boards
    if all_boards:
        # don't listen for responses here
        # let listening queen pick them up

        ## Publish command to all boards
        print(f"Publishing command {com_num} to all boards... ", end="")
        try:
            num_clients = r.publish(rc.getAllBoardsChan(), payload)
        except Exception as e: return _fail(e, f'Failed to publish command.')
        else: _success("Published command.")

        print(f"{num_clients} drones received this command.")
        return True

    ## Send to a single board
    elif bid:

        # Generate unique command channel
        com_chan = rc.comChan(bid, drid if drid is not None else 0)

        # Publish command
        print(f"Publishing command {com_num} to board {com_chan.id}... ", end="")
        try:
            p.psubscribe(com_chan.sub)                     # return channel
            num_clients = r.publish(com_chan.pub, payload) # send command
        except Exception as e: return _fail(e, f'Failed to publish command.')
        else: _success("Published command.")

        if num_clients == 0: # no one listening!
            # This may mean the board has crashed
            print(f"No client received this command!")
            return True

        # Listen for a response
        print(f"Listening for a response... ", end="")
        for new_message in p.listen():              # listen for a return
            if new_message['type'] != 'pmessage': continue # not correct message
            _success("Response received.")

            # add a timeout?

            # Process response
            print(f"Processing response... ", end="")
            try:
                _processCommandReturn(new_message['data'])
            except Exception as e: return _fail(e, f'Failed to process response.')
            else: _success("Processed response.")

            # stop listening; we only expect a single response
            return True

    # not clear who to send command to
    else:
        print("Command not sent: bid required if not sending to all boards.")


# ============================================================================ #
#  callCom
def callCom(com_num, args=None):
    '''execute a queen command function by key

    com_num: (int) command number (see queen commands list).
    args: (str) arguments for command (see payloadToCom).
    '''

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
        print(f"{com[com_num].__name__}: {ret}") # monkeypatched to log

    return ret


# ============================================================================ #
#  listenMode
def listenMode():
    """Listen for Redis messages (threaded).
    """
    # CTRL-C to exit listening mode

    r,p = _connectRedis()

    def handleMessage(message):
        '''actions to take on receiving message'''
        if message['type'] == 'pmessage':
            # print(message['data'].decode('utf-8')) # log/print message
            # _notificationHandler(message)  # send important notifications
            print(f"{_timeMsg()} Message received on channel: {message['channel']}")
            try:
                _processCommandReturn(message['data'])
            except Exception as e: 
                return _fail(e, f'Failed to process a response.')
            
    # Message received: {'type': 'pmessage', 'pattern': b'rets_*', 'channel': b'rets_board_1.1_f9af519c-bea0-4093-81cf-8f8a423dc549', 'data': b'\x80 ...

    rets_chan = rc.getAllReturnsChan()
    p.psubscribe(**{rets_chan:handleMessage})
    thread = p.run_in_thread(sleep_time=2) # move listening to thread
        # sleep_time is a socket timeout
         # too low and it will bog down server
         # can be set to None but may cause issues
         # more research is recommended
    print('The Queen is listening...') 

    # This thread isn't shut down - could lead to problems
    # thread.stop()
    return thread


# ============================================================================ #
#  get/setKeyValue
def getKeyValue(key):
    """
    GET the value of given key.
    """

    r,p = _connectRedis()
    ret = r.get(bytes(key, encoding='utf-8'))
    ret = None if ret is None else ret.decode('utf-8')

    print(ret) # log/print message
    _notificationHandler(ret)  # send important notifications

def setKeyValue(key, value):
    """
    SET the given value for the given key.
    """

    r,p = _connectRedis()
    r.set(bytes(key, encoding='utf-8'), bytes(value, encoding='utf-8'))   


# ============================================================================ #
#  getClientList
def getClientList(do_print=True):
    """Print the Redis client list.
    do_print: (bool) prints list if True, else returns.
    """
    # args are string only
    do_print = False if not do_print or do_print=='False' else True

    r,p = _connectRedis()

    client_list = r.client_list()

    if do_print:
        for client in client_list:
            # client_address = f"{client['addr']}:{client['port']}"
            client_address = f"{client['addr']}"
            client_name = client.get('name', 'N/A')
            print(f"Client: {client_address} {client_name}")

    else:
        return client_list



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
#  print monkeypatch
_print = print 
def print(*args, **kw):
    _print(*args, **kw)            # print to terminal
    logging.info(' '.join(args))   # log to file


# ============================================================================ #
#  _success/_fail
def _success(msg):
    _print("Done.")
    if msg is not None: logging.info(msg)

def _fail(e, msg=None):
    _print("Failed.")
    if msg is not None: logging.info(msg)
    logging.error(e)
    return e


# ============================================================================ #
#  _connectRedis
def _connectRedis():
    '''connect to redis server'''

    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db)
    p = r.pubsub()

    r.client_setname(f'queen')

    return r, p


# ============================================================================ #
#  _processCommandReturn
def _processCommandReturn(dat):
    '''Process the return data from a command.'''

    d = pickle.loads(dat)             # assuming msg is pickled
    
    if isinstance(dat, str):          # print if string
        print(dat) 

    try:
        io.saveWrappedToTmp(d)        # save a wrapped return
    except:
        io.saveToTmp(dat)             # or save as tmp


# ============================================================================ #
#  _notificationHandler
def _notificationHandler(message):
    '''process given messages for sending notifications to end-users'''

    print("notificationHandler(): Not implemented yet!")
    # todo
     # look through given message[s?]
     # and look through configured notifications
     # and send emails as appropriate


# ============================================================================ #
#  _timeMsg
def _timeMsg():
    """A clear and concise time string for print statements."""

    fmt = "%H:%M:%S_%y%m%d"

    time_now = datetime.now()
    time_str = time_now.strftime(fmt)
    # ms_str = f".{time_now.microsecond // 1000:03}"
    
    return time_str


# ============================================================================ #
#  listToArgsAndKwargs
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
#  payloadToCom
def payloadToCom(payload):
    '''Convert payload to com_num, args, kwargs.
    payload: Command string data.
        Payload format: [com_num] [positional arguments] [named arguments].
        Named arguments format: -[argument name] [value].'''
    
    paylist = payload.split()
    com_num = int(paylist.pop(0)) # assuming first item is com_num
    args, kwargs = listToArgsAndKwargs(paylist)
    
    return com_num, args, kwargs




# ============================================================================ #
# INIT
# ============================================================================ #
 

com = _com()