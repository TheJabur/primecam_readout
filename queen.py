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
import os


#########################
### COMMAND FUNCTIONS ###

def alcoveCommand(key, bid):
    '''send an alcove command to given board
    key: command key
    bid: board identifier'''

    # each board should have its own sub channel
    # plus it's own pub channel
        # how do we get a list of available boards?
    # plus at least one all boards channel
    # plus a returns channel

    # queen should be listening all the time
    # but for now lets start listening on this boards channel
    # right before pushing the message
    # and then stop after we receive a reply
        # what if there is no reply?
    # eventually implement a listening thread

    r,p = connectRedis()
    p.psubscribe(f'board_rets_{bid}')
    r.publish(f'board_{bid}', key)

    for new_message in p.listen():
        print(new_message)
        if new_message['type'] == 'pmessage':
            break

# thread = p.run_in_thread(sleep_time=0.001)
# thread.stop()
# def custom_handler(message):
#        # do_something with the message
#        print(message)
# p.psubscribe(**{'hello*':custom_handler})
# thread = p.run_in_thread(sleep_time=0.001)

def testFunc1():
    '''test function 1'''

    print('testFunc1() called') 

# official list of queen commands
# combined with alcove commands
# alcove command keys start at 10
# queen command keys start at 30
com = {
    30:alcoveCommand,
    31:testFunc1
}


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)

def callCom(key):
    '''execute a queen command function by key'''

    if key in com:
        com[key]()
    else:
        print('Invalid key: '+key)

def connectRedis(host='localhost', port=6379):
    '''connect to redis server'''
    r = redis.Redis(host=host, port=port, db=0)
    p = r.pubsub()
    return r, p