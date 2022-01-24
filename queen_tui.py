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


##########################
### INTERNAL FUNCTIONS ###

def main():
    '''run when this script directly accessed'''
    
    printCom()
    key = 31
    queen.callCom(key)


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