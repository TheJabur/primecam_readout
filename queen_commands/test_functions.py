############################
### QUEEN test functions ###
############################

import queen_commands.control_io as io

def testFunc1(arg1=None):
    '''test function 1'''

    print("Saving to tmp file...")
    io.saveToTmp('some junk 1')

    # print(f"arg1={arg1}") 