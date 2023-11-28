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
    # @inlineCallbacks
    @ocs_agent.param('text', default='hello world', type=str)
    def getClientList(self, session, params):
        """getClientList()

        **Task** -
        """

        # print(queen.getClientList())

        return True, f"client list: {queen.getClientList()}"
        # return True, "Printed client list."



# ============================================================================ #
# MAIN
# ============================================================================ #
def main(args=None):
    args = site_config.parse_args(agent_class='ReadoutAgent', args=args)
    agent, runner = ocs_agent.init_site_agent(args)
    readout = ReadoutAgent(agent)

    agent.register_task('getClientList', readout.getClientList, blocking=True)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
