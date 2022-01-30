########################################################
### Server side TUI to main (queen) commands.        ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

import queen
import alcove
import sys
import os


##########################
### INTERNAL FUNCTIONS ###

def main():
    '''run when this script directly accessed'''

    # there's no way to access queen functions yet
    # eventually will have a cli arg to specify
    # for now the cli arg is assumed to be an alcove command key

    if len(sys.argv) == 1: # no cli args
        printCom()
    else:
        # consider how we want to implement cli args
        # for now simply assuming a single arg
        # do we want to check the arg here?
        key = sys.argv[1]
        queen.alcoveCommand(key, bid=1) # board is hardcoded for now

    #queen.callCom(key)


######################
### USER FUNCTIONS ###

def printCom():
    '''print available commands (from queen.py)'''

    print(50*"=")
    print("queen commands available (command : name):")
    for key in queen.com.keys():
        print(f"{key} : {queen.com[key].__name__}")
    print("\nalcove commands available (command : name):")
    for key in alcove.com.keys():
        print(f"{key} : {alcove.com[key].__name__}")
    print(50*"=")


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)


if __name__ == "__main__":
    main()