# ============================================================================ #
# queen.py
# Control computer script to send commands to drones.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2022   
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #

# import sys
import time
import redis
import pickle
import logging
from datetime import datetime

from config import queen as cfg
from config import parentDir

import feeds
import redis_channels as chans
import drone_control as drone_control
import queen_commands.control_io as io
import queen_commands.test_functions as test




# ============================================================================ #
# CONFIG
# ============================================================================ #


logging.basicConfig(
    filename=f'{parentDir(__file__)}/logs/queen.log', level=logging.DEBUG,
    style='{', datefmt='%Y-%m-%d %H:%M:%S', 
    format='{asctime} {levelname} {filename}:{lineno}: {message}'
)


# ============================================================================ #
#  queen commands list
def _com():
    return {
        1:alcoveCommand,
        3:getKeyValue,
        4:setKeyValue,
        5:getClientList,
        6:getClientListLight,
        7:drone_control.action,
        8:monitorMode,
        9:pollFeeds,
        # 10:test.tonePowerTest,
        # 11:test.adriansNoiseTest,
        # 12:test.targetSweepPowerTest,
        # 13:test.targetSweepAndNoiseSweep,
        14:test.loopbackCapture,
        15:test.loopbackCaptureLong,
        16:test.timestreamMonitorTest,
        17:test.timestreamMonitorTest_monitorOnly,
        18:test.tls_array_test
    }



# ============================================================================ #
# COMMAND FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# comList
def comList():
    """A list of all Queen command names (strings)."""

    return [com[key].__name__ for key in com.keys()]


# ============================================================================ #
# comNumFromStr
def comNumFromStr(com_str):
    """Command number (int) from command name (str)."""

    _print("comNumFromStr")
    coms = {com[key].__name__:key for key in com.keys()}
    _print(coms)
    return int(coms[com_str])


# ============================================================================ #
#  alcoveCommand
def alcoveCommand(com_num, bid=None, drid=None, all_boards=False, 
                  args=None, ret_data=True, list_bid_drids=None, 
                  timeout=None):
    '''Send an alcove command to given board[s].

    com_num: (int) Command number.
    bid: (int) Board identifier, optional.
    drid: (int) Drone identifier (1-4), optional. Requires bid to be set.
    all_boards: (bool) Send to all boards instead of bid/drid. Overrides bid.
    args: (str) Command arguments.
    ret_data: (bool) Whether the board should return data or be silent.
    list_bid_drids: (list) List of bid.drids to send command to.

    Note: Precedence: all_boards > list_bid_drids > bid.drid > bid
    
    Return: 2-tuples (num_clients, ret_dict)
        num_clients: (int) Number of clients that received the command.
        ret_dict: (dict/None) Conglomerate return dictionary from all clients.
    '''

    # attempt statement
    if all_boards:
        to_str = "all boards"
    elif list_bid_drids:
        to_str = "list"
    elif drid:
        to_str = f"{bid}.{drid}"
    else:
        to_str = f"board {bid}"
    print(f"Command attempt: ({com_num}) to {to_str} with args={args}.")

    # check chan input is validish
    if not all_boards and not list_bid_drids and not bid:
        print("Command not sent: Who am I sending it to?")
        return (0,[])

    # enforce precedence
    if all_boards:
        bid, drid, list_bid_drids = None, None, None
    elif list_bid_drids:
        bid, drid = None, None

    r,p = _connectRedis()

    # build payload for drone[s]
    payload = f'{com_num} {int(ret_data)}' # ret_data: bool->int->str
    payload += '' if args is None else f' {args}'

    # check the process buffer keyval isn't out of sync
    _rectifyProcessBuffer(r)

    # send command to a single chan
    def sendCom(bid, drid, cid=None): # generic alcove command algorithm: 
        chan = chans.comChan(bid, drid, cid=cid)   # get pub/sub chans
        p.psubscribe(chan.subRet)                  # subscribe to returns
        num_clients = r.publish(chan.pub, payload) # publish command
        return num_clients, chan.cid
    
    num_clients = 0

    # send command to all clients in list
    cid = None # common unique command identifier
    list_bid_drids_sent = []
    if list_bid_drids:
        for bid_drid in list_bid_drids:
            bid, drid = _bid_drid(bid_drid)
            if not drid: # don't allow just bid for list method
                print(f"List item ({bid_drid}) invalid: Require drid.")
                continue
            if f"{bid}.{drid}" not in list_bid_drids_sent: # once per chan
                _num_clients, cid = sendCom(bid, drid, cid=cid)
                num_clients += _num_clients
                list_bid_drids_sent.append(f"{bid}.{drid}")

    # send command to all_boards 
    # or specified bid[.drid]
    else:
        num_clients += sendCom(bid, drid)[0]

    # number of clients that received command
    if num_clients == 0:
        print(f"No client received this command!")
        return (0,[])
    print(f"{num_clients} drones received this command.")

    # Listen for a responses
    print(f"Listening for responses... ", end="")
    if timeout is not None:
        resps = _catchAllResponses(p, num_clients, r, timeout)
    else:
        resps = _catchAllResponses(p, num_clients, r)
    print(f"{len(resps)} received. Done.")

    return (num_clients, resps)


# ============================================================================ #
#  callCom
def callCom(com_num, args=None, bid=None, drid=None):
    '''Execute a queen command function by key.

    com_num: (int) command number (see queen commands list).
    args: (str) arguments for command (see payloadToCom).
    '''

    ret = (0,[]) # default return

    # invalid command
    if com_num not in com:
        print('Invalid command: '+str(com_num))
        return ret

    # convert string args to standard arg/kwargs list/dict
    args, kwargs = _strToArgsAndKwargs(args)

    # add bid/drid to kwargs if present
    if bid: 
        kwargs['bid'] = bid
    if bid and drid: 
        kwargs['drid'] = drid

    # execute queen command
    resp = com[com_num](*args, **kwargs)

    ret = (0,[resp]) # format like alcoveCommand return
    return ret


# ============================================================================ #
#  monitorMode
def monitorMode():
    """Monitor/keep-alive the drones, as per the master drone list file.
    """

    # hold a Redis connection
    r,p = _connectRedis() # any problems with holding this for a long time?

    # action taken every monitor loop
    def monitorAction(r):

        # load needed drone lists
        drone_list = drone_control._droneList()      # master drone list
        client_list = drone_control._clientList()    # redis client list
        override_list = drone_control._loadOvRide()  # tmp override list

        # loop over master drone list
        for id in drone_list:

            bid, drid = drone_control._bid_drid(id)

            # ignore if on override list
            if drone_control._hasOvRide(bid, drid, override_list):
                continue

            # check if drone running, start if not
            status = drone_control._monitorDrone(
                bid, drid, drone_list, client_list, r=r)
            
            if status: # not 0
                msg = f"monitorMode: "
                if status == 1:
                    msg += "Starting "
                elif status == 2:
                    msg += "Stopping "
                else:
                    msg += "Unknown status: "
                msg += f"drone {id}."
                print(msg) # queen logs prints
                _notificationHandler(msg)

    # monitor loop
    print('Starting queen monitor mode.') 
    while True:
        monitorAction(r)
        time.sleep(cfg.monitor_interval) 


'''
# ============================================================================ #
#  monitorFeeds
def monitorFeeds(interval=None, handler=None):
    """

    interval (int or None): Seconds between polls.
        If None then only performs once.
    handler (func(str, dict)): Function to handle feed data on each poll.
        Format is handler(label, data_dict).
    """

    # check and cast interval
    if interval is not None:
        interval = max(1, int(interval)) # min 1 s

    # hold a Redis connection
    r,p = _connectRedis() # any problems with holding this for a long time?
    
    # define a default handler if none was given
    if handler is None:
        def handler(label, data):
            print(f"{label}: {data}")

    # monitor loop
    print(f'Starting drone feed monitor mode (polling every {interval} s).') 
    while True:

        feeds.getFeedSpc(r, p, handler)
        feeds.getFeedTemps(r, p, handler)

        if interval is None:
            break # only do one poll
        time.sleep(interval) # sleep until next poll
'''


# ============================================================================ #
#  pollFeeds
def pollFeeds(handler=None, r=None):

    # establish a Redis connection unless one is passed in
    if r is None:
        r,p = _connectRedis()

    # define a default handler if none was given
    if handler is None:
        def handler(label, data):
            print(f"{label}: {data}")

    feeds.getFeedSpc(r, handler)
    feeds.getFeedTemps(r, handler)

    return r


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
        print("START CLIENT LIST", "="*20)
        for client in client_list:
            # client_address = f"{client['addr']}:{client['port']}"
            client_address = f"{client['addr']}"
            client_name = client.get('name', 'N/A')
            print(f"Client: {client_address} {client_name}")
        print("END CLIENT LIST", "="*22)

    return client_list


# ============================================================================ #
#  getClientListLight
def getClientListLight():
    """Print the Redis client list.
    """

    r,p = _connectRedis()

    client_list = r.client_list()

    props = ['name', 'addr', 'age']
    client_list_light = {}
    for client in client_list:
        client_list_light[client['id']] = {
            prop: client.get(prop, 'N/A')
            for prop in props
        }

    return client_list_light



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
#  print monkeypatch
_print = print 
def print(*args, **kw):
    
    # _print(*args, **kw) # print to terminal
    # terminal printing can cause issues with asynchronous tasks

    args = [str(arg) for arg in args] # not all args are str, so cast
    msg = ' '.join(args) # convert to a single str
    msg = msg.strip() # remove trailing space
    logging.info(msg) # output to log


# ============================================================================ #
#  _connectRedis
def _connectRedis():
    '''connect to redis server'''

    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db, password=cfg.pw)
    p = r.pubsub()

    r.client_setname(f'queen')

    # check for connection
    try:
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")

    return r, p


# ============================================================================ #
#  _processCommandReturn
def _processCommandReturn(dat, r):
    '''Process the return data from a command.'''

    # increment processing counter and set timestamp
    r.incr('proc_cmd_rtn_cnt')
    r.set('proc_cmd_rtn_ts', datetime.now().timestamp())

    # unpickle the returned data
    d = pickle.loads(dat)

    # just print strings
    if isinstance(d, str):
        print(d) 

    # otherwise save
    try:
        io.saveWrappedToTmp(d)        # save a wrapped return
    except:
        io.saveToTmp(dat)             # or save as tmp

    # done; decrement processing counter
    r.decr('proc_cmd_rtn_cnt')

    # processed: increase available buffer by the size of this return data
    payload_size_bytes = len(dat)
    r.incr('rtn_data_max_bytes', payload_size_bytes) #


# ============================================================================ #
# _catchAllResponses
def _catchAllResponses(p, num_clients, r, timeout=60):
    """Listen for Redis responses, with a timeout.

    p: Redis pubsub object that listens for responses.
    num_clients (int): Number of responses to wait for.
    timeout (int): Timeout in seconds.

    Returns: (list) Collected responses.
    Raises: TimeoutError: If listening times out.
    """

    resps = [] # return list

    # nothing to listen for!
    if num_clients <= 0:
        return resps
    
    # timeout
    deadline = time.monotonic() + timeout

    # listen for new messages in subscribed channels
    while time.monotonic() < deadline:

        new_message = p.get_message(timeout=0.1)

        if (not new_message) or (new_message['type'] != 'pmessage'):
            continue

        # process this return
        resps.append(new_message)
        _processCommandReturn(new_message['data'], r)  # print and save

        # stop when all expected returns received
        if len(resps) >= num_clients:
            return resps

    # if we get here then not all expected returns were recieved
    print(f"Warning: Only {len(resps)}/{num_clients} returns received before timeout.")
    return resps


# ============================================================================ #
# _redisConfigBufferLimitPubsubSoft
def _redisConfigBufferLimitPubsubSoft(r):

    config = r.config_get('client-output-buffer-limit')
    buf_lims = config.get('client-output-buffer-limit', '')
    # Example format: "normal 0 0 0 pubsub 33554432 8388608 60 ..."
    # Split into: [class, hard limit, soft limit, soft seconds]
    parts = buf_lims.split()
    grouped = [parts[i:i+4] for i in range(0, len(parts), 4)]

    # Find the pubsub group
    for group in grouped:
        if group[0] == 'pubsub':
            pubsub_buf_lim_soft = int(group[2])
            break
    else:
        raise ValueError("Pubsub buffer limit not found.")

    return pubsub_buf_lim_soft


# ============================================================================ #
# _rectifyProcessBuffer
def _rectifyProcessBuffer(r):
    """Reset queens Redis buffer keyval if out of sync.

    Args:
        r (redis.Redis): Redis connection object.
    """

    # set buffer size if needed
    if cfg.client_output_buffer_limit == 0:
        pubsub_buf_lim_soft = _redisConfigBufferLimitPubsubSoft(r)
        cfg.client_output_buffer_limit = pubsub_buf_lim_soft
        print(f"buff: {pubsub_buf_lim_soft}")

    # oldest that the last started command process can be
    ts_min = datetime.now().timestamp() - cfg.command_return_timeout

    # parse required redis keyvals
    def parse_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0
    proc_cmd_rtn_cnt = parse_int(r.get('proc_cmd_rtn_cnt'))
    proc_cmd_rtn_ts = parse_int(r.get('proc_cmd_rtn_ts'))

    # rectify buffer keyval if out of whack
    if (proc_cmd_rtn_cnt == 0) or (proc_cmd_rtn_ts < ts_min):
        r.set('rtn_data_max_bytes', str(cfg.client_output_buffer_limit))


# ============================================================================ #
#  _notificationHandler
def _notificationHandler(message):
    '''process given messages for sending notifications to end-users'''

    print(f"notificationHandler(): Not implemented yet. Message: {message}")
    # todo
     # look through given message[s?]
     # and look through configured notifications
     # and send emails as appropriate


# ============================================================================ #
#  _strToArgsAndKwargs
def _strToArgsAndKwargs(args_str=''):
    '''Convert string arguments to stanard args/kwargs list/dict.

    args_str: (str) Arguments string, e.g. 'arg1=val1, arg2=val2'.
    '''

    # convert None to blank str
    if not args_str:
        args_str = ''

    # cleanup string formatting (user inputted)
    args_str = args_str.replace(",", " ")
    args_str = args_str.replace("=", " = ")
    args_str = ' '.join(args_str.split()) # remove excess whitespace
    l = args_str.split()
    
    # build args and kwargs
    args = []
    kwargs = {}
    while len(l)>0:
        e = l.pop(0)

        # named kwarg
        if len(l)>0 and l[0]=='=':
            l.pop(0) # get rid of =
            kwargs[e] = l.pop(0)

        # positional arg
        else: 
            args.append(e)

    return args, kwargs


# ============================================================================ #
# _strToList
def _strToList(s):
    '''Convert string to list, if reasonable to do so.
    Otherwise return None.
    '''

    if s:

        s = s.strip()
        
        # Check if the string is enclosed in square brackets
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]  # Remove brackets
            elements = [elem.strip(" \"'") for elem in s.split(',')]
            return [str(elem) for elem in elements]  # elements -> strings
    
    return None


# ============================================================================ #
# _bid_drid
def _bid_drid(id):
    '''Separate id into bid.drid.
    Returns int (bid, drid), (bid, None), or (None, None).

    id: (str) in format 'bid.drid' or 'bid'.
    '''

    import re

    # casting from Redis strings
    id  = str(id)
    
    if re.fullmatch(r'\d+(\.\d+)?', id): # enforce 'x.y' or 'x'

        parts = id.split('.')
        bid = int(parts[0])
        drid = int(parts[1]) if len(parts) > 1 else None
        
    else: # incorrect format
        bid, drid = None, None

    return bid, drid


# ============================================================================ #
# _id
def _id(bid, drid=None):
    '''Join bid.drid into id.
    '''

    id = f"{bid}.{drid}"

    # check for consistency
    bidc, dridc = _bid_drid(id)
    if bidc != bid or dridc != drid:
        id = None

    return id




# ============================================================================ #
# INIT
# ============================================================================ #
 

com = _com()