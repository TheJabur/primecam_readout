# ============================================================================ #
# Server side CLI to main (queen) commands.
#
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2022  
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #

import queen
import alcove
import os
import argparse



# ============================================================================ #
# main
def main():
    """
    Run when this script directly accessed.
    """

    # attempt command execution
    _processCommand(_setupArgparse())



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# print
# monkeypatch the print statement
_print = print 
def print(*args, **kw):
    '''Monkeypatch the print function'''
    # add current filename in front
    _print(f"{os.path.basename(__file__)}: ", end='')
    _print(*args, **kw)


# ============================================================================ #
# _comsStr
def _comsStr():
    """
    Output queen and alcove commands as a string.
    """

    s = ""
    s += "\nqueen commands [com_num : name]:"
    for key in queen.com.keys():
        s+= f"\n  {key} : {queen.com[key].__name__}"
    s += "\n"
    s += "\nalcove commands [com_num : name]:"
    for key in alcove.com.keys():
        s += f"\n  {key} : {alcove.com[key].__name__}"

    return s


# ============================================================================ #
# _setupArgparse
def _setupArgparse():
    """
    Setup command line arguments.
    """

    # If only one arg then its com_num to all boards.
    # If two arguments then its com_num to bid.drid (string).
        # If no period then no drid.
    # If one argument and -q then it's com_num for queen.

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Terminal interface to queen script.",
        epilog = _comsStr())

    # com_num is required
    parser.add_argument("com_num",
        type=int, help="Command number.")

    # -a is optional
    parser.add_argument("-a", "--arguments", 
        type=str, help="Arguments to send with command, e.g. 'bar' or '-foo bar' or 'baz -foo bar'."\
        " Note: Avoid subargs starting with '-a' or '-q' due to known bug.")

    # bid or -q or neither, but not both
    g1 = parser.add_mutually_exclusive_group(required=False)
    g1.add_argument("bid", nargs='?',
        type=str, help="Board and drone id: format is 'bid' or 'bid.drid'.")
    g1.add_argument("-q", "--queen",
        action="store_true", help="Queen command instead of board command.")

    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# _processCommand
def _processCommand(args):
    """
    Process a single command.
    Can be for a single bid.drid, all bid.drid, or queen.
    Look at _setupArgparse() for arguments setup.
    """

    # queen command
    if args.queen:
        print(f"Queen command {args.com_num}... ", flush=True)
        ret = queen.callCom(args.com_num, args.arguments)

    # specific board/drone command
    elif args.bid:
        print(f"Sending board {args.bid} command {args.com_num}... ", flush=True)
        ids = args.bid.split('.')
        bid = int(ids[0]) # must exist
        drid = int(ids[1]) if len(ids)>1 else None
        if drid:
            ret = queen.alcoveCommand(
                args.com_num, bid=bid, drid=drid, args=args.arguments)
        else:
            ret = queen.alcoveCommand(
                args.com_num, bid=bid, args=args.arguments)

    # all-boards commands
    else:
        print(f"Processing all boards command {args.com_num}... ", flush=True)
        ret = queen.alcoveCommand(
            args.com_num, all_boards=True, args=args.arguments)
        
    print(f"Done. {ret=}")



if __name__ == "__main__":
    main()