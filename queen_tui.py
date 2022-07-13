########################################################
### Server side TUI to main (queen) commands.        ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################


###############
### IMPORTS ###

from re import A
import queen
import alcove
import os
import argparse


######################
### MAIN EXECUTION ###

def main():
    '''run when this script directly accessed'''

    # get command line arguments
    args = setupArgparse()

    # output list of commands
    if args.commands:
        printCom()

    # attempt command execution
    else:
        processCommand(args)


######################
### USER FUNCTIONS ###

def printCom():
    '''print available commands (from queen.py)'''

    print(50*"=")
    print("queen commands available (command : name):")
    for key in queen.com.keys():
        print(f"{key} : {queen.com[key].__name__}")
    print("")
    print("alcove commands available (command : name):")
    for key in alcove.com.keys():
        print(f"{key} : {alcove.com[key].__name__}")
    print(50*"=")


##########################
### INTERNAL FUNCTIONS ###

# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    '''Monkeypatch the print function'''
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)

def setupArgparse():
    '''Setup the argparse arguments'''

    parser = argparse.ArgumentParser(
        description=
            'Terminal interface to queen script. '\
            'Use --commands to see a list of commands.')
    # todo: add printCom() to help

    # add arguments
    parser.add_argument("-c",       # command
        type=int, help="command")
    parser.add_argument("--args",   # command arguments string
        type=str, help="command arguments string")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--commands",
        action="store_true", help="list of available commands")
    target.add_argument("--bid",    # board bid
        type=int, help="board bid")
    target.add_argument("--all",    # all boards
        action="store_true", help="all boards")
    target.add_argument("--queen",  # queen command
        action="store_true", help="queen command")
   
    # return arguments values
    return parser.parse_args()

def processCommand(args):
    '''Process a command (we accept a single command)
    for either: a single bid, all boards, or queen.
    Look at setupArgparse() for arguments setup.'''

    key = args.c
    if not key:         # no command given
        printCom()
    elif args.queen:    # a queen command
        queen.callCom(key, args=args.args)
    elif args.all:      # an all-boards commands
        queen.alcoveCommand(key, all_boards=True, args=args.args)
    elif args.bid:      # a single board command
        queen.alcoveCommand(key, bid=args.bid, args=args.args)
        

if __name__ == "__main__":
    main()