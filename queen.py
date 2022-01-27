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
import alcove
import redis
import os


#########################
### COMMAND FUNCTIONS ###

def alcoveCommand(key, board):
    '''send an alcove command to given board'''

    # each board should have its own channel
        # how do we get a list of available boards?
    # plus at least one all boards channel
    # for testing we'll just use a single channel

    channels = 'test'
    r,p = connectRedis()
    r.publish('test', key)

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