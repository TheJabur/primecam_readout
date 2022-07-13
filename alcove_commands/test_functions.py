########################################################
### ALCOVE (remote-side)                             ###
### Test functions.                                  ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################

#############################################################
### NOTE that all import statements are done IN FUNCTIONS ###
### This is to improve portability and function clarity.  ###
### If function performance becomes an issue              ###
### then move the import to just above the function.      ###
#############################################################


def test_function_1(arg1=None, arg2=None):
    ret = f"arg1={arg1}, arg2={arg2}"
    print(ret)
    return ret