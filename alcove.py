########################################################
### Main remote-side script.                         ###
### Allows execution of remote (board) commands.     ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

#


#########################
### COMMAND FUNCTIONS ###

def my_alcove_func_1():
    '''silly test function 1'''
    print('my_alcove_func_1() called') 
    
def my_alcove_func_2():
    '''silly test function 2'''
    print('my_alcove_func_2() called')

# official list of alcove commands
# alcove command keys start at 10
com = { 
    10:my_alcove_func_1, 
    11:my_alcove_func_2
}


##########################
### INTERNAL FUNCTIONS ###

def callCom(key):
    # dictionary keys are stored as integers
    # but redis may convert to string
    key = int(key)  # force key to be int
    if key in com:  # check if command allowed
        com[key]()  # execute command
    else:
        print('Invalid key: '+key)

