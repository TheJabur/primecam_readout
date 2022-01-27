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


##########################
### INTERNAL FUNCTIONS ###

def main():
    '''run when this script directly accessed'''


    if len(sys.argv) == 1: # no cli args
        printCom()
    else:
        # consider how we want to implement cli args
        # for now simply assuming a single arg
        # do we want to check the arg here?
        key = sys.argv[1]
        queen.alcoveCommand(key, board=None)

    #queen.callCom(key)


######################
### USER FUNCTIONS ###

def printCom():
    '''print available commands (from queen.py)'''

    print(50*"=")
    print("queen commands available (command : name):")
    for key in queen.com.keys():
        print(f"{key} : {queen.com[key].__name__}")
    print("\nalcove commands available (use alcoveCommand()) (command : name):")
    for key in alcove.com.keys():
        print(f"{key} : {alcove.com[key].__name__}")
    print(50*"=")


########################

if __name__ == "__main__":
    main()