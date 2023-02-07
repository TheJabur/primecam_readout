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


# def testFunction1():

    # import alcove_commands.board_io as io
    # import numpy as np

    # a = np.array([1,2,3,4,5,6]) + 1

    # io.save(io.file.f_res_targ, a)

def testFunction():
    import alcove_commands.board_io as io
    import numpy as np

    a = io.load(io.file.f_res_targ)
    # a = io.loadVersion(io.file.f_res_targ, timestamp='20221006T222045Z')

    print(a)


# def testFunction1(arg1=None, arg2=None):

#     import _cfg_board as cfg

#     ret = f"drid={cfg.drid}, arg1={arg1}, arg2={arg2}"
#     print(f"returning: {ret}")
#     return ret


# def testFunction2(key):

#     import drone

#     ret = drone.getKeyValue(key)
#     print(f"returning: {ret}")

#     return ret
