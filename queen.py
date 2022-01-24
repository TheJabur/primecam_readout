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


#########################
### COMMAND FUNCTIONS ###

def alcoveCommand(key, board):
    '''send an alcove command to given board'''

    # by redis

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

def callCom(key):
    '''execute a queen command function by key'''
    
    if key in com:
        com[key]()
    else:
        print('Invalid key: '+key)

# def attachRedis():
#     ''''''
#     r = redis.Redis(host='localhost')
#     p = r.pubsub(ignore_subscribe_messages = True)

