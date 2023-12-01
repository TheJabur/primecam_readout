# ============================================================================ #
# queen_agent.py
# OCS agent to main (queen) commands.
#
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #

from ocs import ocs_agent, site_config
# from twisted.internet.defer import Deferred, inlineCallbacks

import queen
import alcove



# ============================================================================ #
# CLASS: ReadoutAgent
# ============================================================================ #
class ReadoutAgent:
    """Readout agent interfacing with queen.

    Parameters:
        agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.

    Attributes:
        
    """

    def __init__(self, agent):
        self.agent = agent


    # ======================================================================== #
    # .getClientList
    @ocs_agent.param('text', default='hello world', type=str)
    def getClientList(self, session, params):
        """getClientList()

        **Task** -
        """

        # print(queen.getClientList())

        return True, f"client list: {queen.getClientList()}"
        # return True, "Printed client list."


    # ======================================================================== #
    # .setNCLO
    @ocs_agent.param('f_lo', type=float)
    def setNCLO(self, session, params):
        """setNCLO()

        **Task** - set the numerically controlled local oscillator

        Args
        -------
        f_lo: float
            center frequency in [MHz]
        """

        # return is a fail message str or number of clients int
        rtn = _sendAlcoveCommand(
            com_str  ='alcove_base.setNCLO', 
            com_to   ='1.1', 
            com_args ='f_lo=500')
        
        return True, f"setNCLO: {rtn}"



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _comNumAlcove
def _comNumAlcove(com_str):

    print(f"_comNumAlcove... com_str={com_str}, keys:")
    print(alcove.comList())

    return alcove.comNumFromStr(com_str)
    # coms = {alcove.com[key].__name__:key for key in alcove.com.keys()}
    # return coms[com_str]


# ============================================================================ #
# _sendAlcoveCommand
def _sendAlcoveCommand(com_str, com_to, com_args):
    """Send Alcove command.

    com_str:    (str)   String name of command. 
                        See alcove.py::_com(). 
                        E.g. 'alcove_base.setNCLO'
    com_to:     (str)   Drone to send command to.
                        E.g. '1.1' is board 1, drone 1.
    com_args:   (str)   Command arguments.
                        E.g. 'f_lo=500'
    """

    print(com_str, com_to, com_args)

    com_num = _comNumAlcove(com_str)

    print(com_num)

    # specific board/drone command
    if com_to:
        ids = com_to.split('.')
        bid = int(ids[0]) # must exist
        drid = int(ids[1]) if len(ids)>1 else None
        if drid:
            return queen.alcoveCommand(com_num, bid=bid, drid=drid, args=com_args)
        else:
            return queen.alcoveCommand(com_num, bid=bid, args=com_args)

    # all-boards commands
    else:
        return queen.alcoveCommand(com_num, all_boards=True, args=com_args)
    


# ============================================================================ #
# MAIN
# ============================================================================ #
def main(args=None):
    args = site_config.parse_args(agent_class='ReadoutAgent', args=args)
    agent, runner = ocs_agent.init_site_agent(args)
    readout = ReadoutAgent(agent)

    agent.register_task('getClientList', readout.getClientList, blocking=True)
    agent.register_task('setNCLO', readout.setNCLO, blocking=True)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
