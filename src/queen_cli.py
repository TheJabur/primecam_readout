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

    parser.add_argument("id", nargs='?',
        type=str, help="Board and drone id: format is 'bid', 'bid.drid', or '[bid.drid]'.")

    parser.add_argument("-q", "--queen",
        action="store_true", help="Queen command instead of board command.")

    parser.add_argument("-s", "--silent", 
        action="store_true", help="Silent command: minimal return.")

    parser.add_argument("-t", "--timeout", 
        type=int, help="Command timeout, s.")

    # bid or -q or neither, but not both
    # g1 = parser.add_mutually_exclusive_group(required=False)
    # g1.add_argument("bid", nargs='?',
    #     type=str, help="Board and drone id: format is 'bid' or 'bid.drid'.")
    # g1.add_argument("-q", "--queen",
    #     action="store_true", help="Queen command instead of board command.")

    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# _processCommand
def _processCommand(args):
    """Process a single command.
    Look at _setupArgparse() for arguments setup.
    """

    # parse args.id
    bid, drid, list_bid_drids = None, None, None
    if args.id:
        list_bid_drids = queen._strToList(args.id)
        if not list_bid_drids: # not a list
            bid, drid = queen._bid_drid(args.id)

    ret_data = not args.silent

    timeout = args.timeout
    # timeout not implemented in queen command yet

    # queen command
    # TODO: not compatible with list yet
    if args.queen:
        print(f"Queen command {args.com_num}... ", flush=True)
        ret = queen.callCom(
            args.com_num, args=args.arguments, bid=bid, drid=drid)
        print(f"Done. ret={ret[1]}")

    # drone command
    else:

        # targeted drone
        if bid and drid:
            print(f"Sending drone {bid}.{drid} " \
                  f"command {args.com_num}... ", flush=True)
            ret = queen.alcoveCommand(args.com_num, timeout=timeout,
                bid=bid, drid=drid, args=args.arguments, ret_data=ret_data)
            
        # targeted board
        elif bid:
            print(f"Sending board {bid} " \
                  f"command {args.com_num}... ", flush=True)
            ret = queen.alcoveCommand(args.com_num, timeout=timeout,
                bid=bid, args=args.arguments, ret_data=ret_data)
            
        # list of targeted drones
        elif list_bid_drids:
            print(f"Sending list " \
                  f"command {args.com_num}... ", flush=True)
            ret = queen.alcoveCommand(args.com_num, timeout=timeout,
                args=args.arguments, ret_data=ret_data,
                list_bid_drids=list_bid_drids)

        # all drones
        else:
            print(f"Processing all boards " \
                  f"command {args.com_num}... ", flush=True)
            ret = queen.alcoveCommand(args.com_num, timeout=timeout,
                all_boards=True, args=args.arguments, ret_data=ret_data)
            
        if ret[0] <= 0:
            print(f"WARNING: No drones received this command.")
        else:
            print(f"Done. {ret[0]} drones received. {len(ret[1])} responses.")




if __name__ == "__main__":
    main()