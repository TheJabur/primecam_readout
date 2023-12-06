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
    def getClientList(self, session, params):
        """getClientList()

        **Task** - Return the current list of clients attached to the Redis server.
        """

        return True, f"client list: {queen.getClientList()}"


    # ======================================================================== #
    # .queenListenMode
    # 2 : listenMode
    # TODO


    # ======================================================================== #
    # .setNCLO
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('f_lo', type=int)
    def setNCLO(self, session, params):
        """setNCLO()

        **Task** - Set the numerically controlled local oscillator.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        f_lo: int
            Center frequency in [MHz].
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'setNCLO', 
            com_to   = params['com_to'], 
            com_args = f'f_lo={params["f_lo"]}')
        
        # return is a fail message str or number of clients int
        return True, f"setNCLO: {rtn}"
    

    # ======================================================================== #
    # .setFineNCLO
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('df_lo', type=float)
    def setFineNCLO(self, session, params):
        """setFineNCLO()

        **Task** - Set the fine frequency shift in the local oscillator.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        df_lo: float
            Center frequency shift, in [MHz].
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'setFineNCLO', 
            com_to   = params['com_to'], 
            com_args = f'f_lo={params["df_lo"]}')
        
        # return is a fail message str or number of clients int
        return True, f"setFineNCLO: {rtn}"


    # ======================================================================== #
    # .getSnapData
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('mux_sel', type=int)
    def getSnapData(self, session, params):
        """getSnapData()

        **Task** - ?

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        mux_sel: float
            ?
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'getSnapData', 
            com_to   = params['com_to'], 
            com_args = f'mux_sel={params["mux_sel"]}')
        
        # return is a fail message str or number of clients int
        return True, f"getSnapData: {rtn}"
    

    # ======================================================================== #
    # .writeTestTone
    @ocs_agent.param('com_to', default=None, type=str)
    def writeTestTone(self, session, params):
        """writeTestTone()

        **Task** - Write a single test tone at 50 MHz.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'writeTestTone', 
            com_to   = params['com_to'])
        
        # return is a fail message str or number of clients int
        return True, f"writeTestTone: {rtn}"


    # ======================================================================== #
    # .writeNewVnaComb
    @ocs_agent.param('com_to', default=None, type=str)
    def writeNewVnaComb(self, session, params):
        """writeNewVnaComb()

        **Task** - Create and write the vna sweep tone comb.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'writeNewVnaComb', 
            com_to   = params['com_to'])
        
        # return is a fail message str or number of clients int
        return True, f"writeNewVnaComb: {rtn}"


    # ======================================================================== #
    # .writeTargCombFromVnaSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('cal_tones', default=False, type=bool)
    def writeTargCombFromVnaSweep(self, session, params):
        """writeTargCombFromVnaSweep()

        **Task** - Write the target comb from the vna sweep resonator frequencies. Note that vnaSweep and findVnaResonators must be run first.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        cal_tones: bool
            Include calibration tones (True) or not (False).
            Note that findCalTones must be run first.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'writeTargCombFromVnaSweep', 
            com_to   = params['com_to'],
            com_args = f'cal_tones={params["cal_tones"]}')
        
        # return is a fail message str or number of clients int
        return True, f"writeTargCombFromVnaSweep: {rtn}"
    

    # ======================================================================== #
    # .writeTargCombFromTargSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('cal_tones', default=False, type=bool)
    @ocs_agent.param('new_amps_and_phis', default=False, type=bool)
    def writeTargCombFromTargSweep(self, session, params):
        """writeTargCombFromTargSweep()

        **Task** - Write the target comb from the target sweep resonator frequencies.
    Note that targSweep and findTargResonators must be run first.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        cal_tones: bool
            Include calibration tones (True) or not (False).
            Note that findCalTones must be run first.
        new_amps_and_phis: bool 
            Generate new amplitudes and phases if True.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'writeTargCombFromTargSweep', 
            com_to   = params['com_to'],
            com_args = f'cal_tones={params["cal_tones"]}, new_amps_and_phis={params["cal_tones"]}')
        
        # return is a fail message str or number of clients int
        return True, f"writeTargCombFromTargSweep: {rtn}"


    # ======================================================================== #
    # .writeCombFromCustomList
    @ocs_agent.param('com_to', default=None, type=str)
    def writeCombFromCustomList(self, session, params):
        """writeCombFromCustomList()

        **Task** - Write the comb from custom tone files:
            alcove_commands/custom_freqs.npy
            alcove_commands/custom_amps.npy
            alcove_commands/custom_phis.npy

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'writeCombFromCustomList', 
            com_to   = params['com_to'])
        
        # return is a fail message str or number of clients int
        return True, f"writeCombFromCustomList: {rtn}"


    # ======================================================================== #
    # .createCustomCombFilesFromCurrentComb
    @ocs_agent.param('com_to', default=None, type=str)
    def createCustomCombFilesFromCurrentComb(self, session, params):
        """createCustomCombFilesFromCurrentComb()

        **Task** - Create custom comb files from the current comb.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'createCustomCombFilesFromCurrentComb', 
            com_to   = params['com_to'])
        
        # return is a fail message str or number of clients int
        return True, f"createCustomCombFilesFromCurrentComb: {rtn}"


    # ======================================================================== #
    # .modifyCustomCombAmps
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('factor', default=1, type=float)
    def modifyCustomCombAmps(self, session, params):
        """modifyCustomCombAmps()

        **Task** - Modify custom tone amps file by multiplying by given factor.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        factor: float
            Factor to multiply tone amps by.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'modifyCustomCombAmps', 
            com_to   = params['com_to'],
            com_args = f'factor={params["factor"]}')
        
        # return is a fail message str or number of clients int
        return True, f"modifyCustomCombAmps: {rtn}"


    # ======================================================================== #
    # .vnaSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('N_steps', default=500, type=int)
    def vnaSweep(self, session, params):
        """vnaSweep()

        **Task** - Perform a stepped frequency sweep with current comb, save as vna sweep.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        N_steps: int
            Number of LO frequencies to divide each channel into.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'vnaSweep', 
            com_to   = params['com_to'],
            com_args = f'N_steps={params["N_steps"]}')
        
        # return is a fail message str or number of clients int
        return True, f"vnaSweep: {rtn}"
    

    # ======================================================================== #
    # .targetSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('N_steps', default=500, type=int)
    @ocs_agent.param('chan_bandwidth', default=0.2, type=float)
    def targetSweep(self, session, params):
        """targetSweep()

        **Task** - Perform a stepped frequency sweep with current comb, save as target sweep.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        N_steps: int
            Number of LO frequencies to divide each channel into.
        chan_bandwidth: float
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'targetSweep', 
            com_to   = params['com_to'],
            com_args = f'N_steps={params["N_steps"]}, chan_bandwidth={params["chan_bandwidth"]}')
        
        # return is a fail message str or number of clients int
        return True, f"targetSweep: {rtn}"


    # ======================================================================== #
    # .findVnaResonators
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('stitch_bw', default=500, type=int)
    @ocs_agent.param('stitch_sw', default=100, type=int)
    @ocs_agent.param('f_hi', default=50, type=int)
    @ocs_agent.param('f_lo', default=1, type=int)
    @ocs_agent.param('prom_dB', default=1, type=int)
    @ocs_agent.param('distance', default=30, type=int)
    @ocs_agent.param('width_min', default=5, type=int)
    @ocs_agent.param('width_max', default=100, type=int)
    def findVnaResonators(self, session, params):
        """findVnaResonators()

        **Task** - Find the resonator peak frequencies from vnaSweep S21. 
            See findResonators() for possible arguments. 
            Note that vnaSweep must be run first.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        stitch_bw: int 
            Width of the stitch bins.
        stitch_sw: int 
            Width of slice (at ends) of each stitch bin to take median.
        f_hi: float
            Highpass filter cutoff frequency. [data units]
        f_lo: float
            lowpass filter cutoff frequency. [data units]
        prom_dB: float
            Peak prominence cutoff. [dB]
        distance: int
            Min distance between peaks. [bins]
        width_min: int
            Peak width minimum. [bins]
        width_max: int
            Peak width maximum. [bins]
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'findVnaResonators', 
            com_to   = params['com_to'],
            com_args = f'stitch_bw={params["stitch_bw"]}, stitch_sw={params["stitch_sw"]}, f_hi={params["f_hi"]}, f_lo={params["f_lo"]}, prom_dB={params["prom_dB"]}, distance={params["distance"]}, width_min={params["width_min"]}, width_max={params["width_max"]}')
        
        # return is a fail message str or number of clients int
        return True, f"findVnaResonators: {rtn}"


    # ======================================================================== #
    # .findTargResonators
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('stitch_bw', default=500, type=int)
    def findTargResonators(self, session, params):
        """findTargResonators()

        **Task** - Find the resonator peak frequencies from targSweep S21.
            See findResonators() for possible arguments.
            Note that targSweep must be run first.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        stitch_bw: int 
            Width of the stitch bins.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'findTargResonators', 
            com_to   = params['com_to'],
            com_args = f'stitch_bw={params["stitch_bw"]}')
        
        # return is a fail message str or number of clients int
        return True, f"findTargResonators: {rtn}"


    # ======================================================================== #
    # .findCalTones
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('f_lo', default=0.1, type=float)
    @ocs_agent.param('f_hi', default=50, type=float)
    @ocs_agent.param('tol', default=2, type=float)
    @ocs_agent.param('max_tones', default=10, type=int)
    def findCalTones(self, session, params):
        """findCalTones()

        **Task** - Determine the indices of calibration tones.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        f_hi: float 
            Highpass filter cutoff frequency (data units).
        f_lo: float 
            lowpass filter cutoff frequency (data units).
        tol: float 
            Reject tones tol*std_noise from continuum.
        max_tones: int 
            Maximum number of tones to return.
        """
  
        rtn = _sendAlcoveCommand(
            com_str  = 'findCalTones', 
            com_to   = params['com_to'],
            com_args = f'f_hi={params["f_hi"]}, f_lo={params["f_lo"]}, tol={params["tol"]}, max_tones={params["max_tones"]}')
        
        # return is a fail message str or number of clients int
        return True, f"findCalTones: {rtn}"



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
def _sendAlcoveCommand(com_str, com_to, com_args=None):
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
    agent.register_task('setFineNCLO', readout.setFineNCLO, blocking=True)
    agent.register_task('getSnapData', readout.getSnapData, blocking=True)
    agent.register_task('writeNewVnaComb', readout.writeNewVnaComb, blocking=True)
    agent.register_task('writeTargCombFromVnaSweep', readout.writeTargCombFromVnaSweep, blocking=True)
    agent.register_task('writeTargCombFromTargSweep', readout.writeTargCombFromTargSweep, blocking=True)
    agent.register_task('writeCombFromCustomList', readout.writeCombFromCustomList, blocking=True)
    agent.register_task('createCustomCombFilesFromCurrentComb', readout.createCustomCombFilesFromCurrentComb, blocking=True)
    agent.register_task('modifyCustomCombAmps', readout.modifyCustomCombAmps, blocking=True)
    agent.register_task('vnaSweep', readout.vnaSweep, blocking=True)
    agent.register_task('targetSweep', readout.targetSweep, blocking=True)
    agent.register_task('findVnaResonators', readout.findVnaResonators, blocking=True)
    agent.register_task('findTargResonators', readout.findTargResonators, blocking=True)
    agent.register_task('findCalTones', readout.findCalTones, blocking=True)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
