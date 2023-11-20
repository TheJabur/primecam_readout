########################################################
### Remote side on-board TUI to alcove commands.     ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

import alcove
import os


##########################
### INTERNAL FUNCTIONS ###

def main():

    printCom()
    key = 10
    alcove.callCom(key)


######################
### USER FUNCTIONS ###

def printCom():
    '''print available commands (from alcove.py)'''

    print(50*"=")
    print("alcove commands available (command : name):")
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