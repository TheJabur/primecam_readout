# ============================================================================ #
# queen_agent.py
# OCS agent to control computer (queen) commands.
#
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2024
# ============================================================================ #

import time
import json
import pickle
import numpy as np

from ocs import ocs_agent, site_config
from ocs.ocs_twisted import TimeoutLock
# from twisted.internet.defer import Deferred, inlineCallbacks

import queen
import alcove
import drone_control

# ======================================================================== #
# main
def main(args=None):
    args = site_config.parse_args(agent_class='ReadoutAgent', args=args)
    agent, runner = ocs_agent.init_site_agent(args)
    readout = ReadoutAgent(agent)

    # convenience function wrapping register_task
    def rt(s, f, b=True):
        return agent.register_task(s, f, blocking=b)

    agent.register_process('feedMonitor', readout.monitorFeeds, readout._stopMonitorFeeds, startup=True)

    # queen commands
    rt('updateMeasurement', readout.updateMeasurement, b=False)
    rt('getKeyValue', readout.getKeyValue)
    rt('setKeyValue', readout.setKeyValue)
    rt('getClientList', readout.getClientList)
    rt('getClientListLight', readout.getClientListLight)
    rt('action', readout.action) # drone control actions

    # drone commands
    rt('setNCLO', readout.setNCLO)
    rt('setFineNCLO', readout.setFineNCLO)
    rt('getSnapData', readout.getSnapData)
    rt('getADCrms', readout.getADCrms)
    rt('writeTestTone', readout.writeTestTone)
    rt('writeNewVnaComb', readout.writeNewVnaComb)
    rt('writeTargCombFromVnaSweep', readout.writeTargCombFromVnaSweep)
    rt('writeTargCombFromTargSweep', readout.writeTargCombFromTargSweep)
    rt('writeCombFromCustomList', readout.writeCombFromCustomList)
    rt('createCustomCombFilesFromCurrentComb', 
       readout.createCustomCombFilesFromCurrentComb)
    rt('modifyCustomCombAmps', readout.modifyCustomCombAmps)
    rt('writeTargCombFromCustomList', readout.writeTargCombFromCustomList)
    rt('vnaSweep', readout.vnaSweep)
    rt('targetSweep', readout.targetSweep)
    rt('customSweep', readout.customSweep)
    rt('findVnaResonators', readout.findVnaResonators)
    rt('findTargResonators', readout.findTargResonators)
    rt('cleanBoardDroneDirs', readout.cleanBoardDroneDirs)
    rt('findCalTones', readout.findCalTones)
    rt('sys_info', readout.sys_info)
    rt('sys_info_v', readout.sys_info_v)
    rt('timestreamOn', readout.timestreamOn)
    rt('userPacketInfo', readout.userPacketInfo)
    rt('setAtten2024', readout.setAtten2024)
    rt('setAtten2025', readout.setAtten2025)
    rt('getAtten', readout.getAtten)
        
    runner.run(agent, auto_reconnect=True)

# ============================================================================ #
# == CLASS: ReadoutAgent
# ============================================================================ #
class ReadoutAgent:
    """Readout agent interfacing with queen.

    Parameters:
        agent (OCSAgent): OCSAgent object.
    """

    def __init__(self, agent):
        self.agent = agent
        self.lock = TimeoutLock(default_timeout=5)

        self.r = None
        self._monitorFeeds = False

        self.measurement_name = None
        self.measurement_desc = ""
        self.measurement_start = None

        # agent feeds
        self.agent.register_feed(
            'drone_free_spaces_GB',
            record=True,
            agg_params={'frame_length': 10*60}, # 60 s data polling
            buffer_time=5.)  # Allow a small buffer

        self.agent.register_feed(
            'drone_temperatures_C',
            record=True,
            agg_params={'frame_length': 10*60}, # 60 s data polling
            buffer_time=5.)  # Allow a small buffer

        self.agent.register_feed(
            'active_measurement',
            record=True)

    # ======================================================================== #
    # .updateMeasurement
    @ocs_agent.param('measurement_name', default=None, type=str)
    @ocs_agent.param('measurement_desc', default="", type=str)
    def updateMeasurement(self, session, params):
        with self.lock.acquire_timeout(job='updateMeasurement') as acquired:
            if not acquired:
                print(f"Lock could not be acquired because it is held by {self.lock.job}.")
                return False

            if self.measurement_name is None:
                self.measurement_name = params['measurement_name']
                self.measurement_desc = params['measurement_desc']
                self.measurement_start = time.time()
                return True, f"Starting measurement {self.measurement_name}"
            else:
                measurement_name = self.measurement_name
                measurement_desc = self.measurement_desc
                self.measurement_name = None
                self.measurement_desc = ""
                end_time = time.time()

                message = {'block_name': 'active_measurement', 
                           'timestamp': self.measurement_start,
                           'data': {'name': measurement_name, 'desc': measurement_desc,'TimeStart': int(self.measurement_start * 1e3), 'TimeEnd': int(end_time * 1e3)}}
                
                self.agent.publish_to_feed('active_measurement', message)
                self.agent.feeds['active_measurement'].flush_buffer()

        self.updateMeasurement(session, params)
        return True, f"Finished measurement {measurement_name}"


    # ======================================================================== #
    # .getKeyValue
    @ocs_agent.param('key', type=str)
    def getKeyValue(self, session, params):
        """getKeyValue()

        **Task** - Return the value for the given key.

        Args
        -------
        key: str
            The key to fetch the value for.
        """
        with self.lock.acquire_timeout(job='getKeyValue') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            return True, f"{params['key']}: {queen.getKeyValue(params['key'])}"


    # ======================================================================== #
    # .setKeyValue
    @ocs_agent.param('key', type=str)
    @ocs_agent.param('value', type=str)
    def setKeyValue(self, session, params):
        """getKeyValue()

        **Task** - Set given key to given value.

        Args
        -------
        key: str
            The key to set.
        value: str
            The value to set for key.
        """
        
        with self.lock.acquire_timeout(job='setKeyValue') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            return True, f"{params['key']}: {queen.setKeyValue(params['key'], params['value'])}"


    # ======================================================================== #
    # .getClientList
    def getClientList(self, session, params):
        """getClientList()

        **Task** - Return the list of Redis clients, verbose.
        """
        with self.lock.acquire_timeout(job='getClientList') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            return True, f"client list: {queen.getClientList()}"
    
    
    # ======================================================================== #
    # .getClientListLight
    def getClientListLight(self, session, params):
        """getClientListLight()

        **Task** - Return the list of Redis clients.
        """
        with self.lock.acquire_timeout(job='getClientListLight') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            return True, f"client list: {queen.getClientListLight()}"


    # ======================================================================== #
    # .action
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('action', type=str)
    def action(self, session, params):
        """action()

        **Task** - Perform the drone control action, e.g. 'start'.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
        action: str
            Drone control action to perform:
            'start', 'stop', 'restart', 'status', 
            'startAllDrones', 'stopAllDrones', 'restartAllDrones'
        """

        with self.lock.acquire_timeout(job='action') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            action = params['action']
            bid, drid = drone_control._bid_drid(params['com_to'])
            rtn = drone_control.action(action, bid, drid)
            session.data['data'] = json.dumps(rtn)

            return True, f"action: Done {action}"
    

    # ======================================================================== #
    # .monitorFeeds
    @ocs_agent.param('poll_interval', default=60, type=int)
    @ocs_agent.param('lock_interval', default=0.1, type=float)
    def monitorFeeds(self, session, params):
        """monitorFeeds()

        **Process** - Monitor drone HK data (temp, disk space).

        Args
        -------
        interval: int
            Interval to continue polling data, in seconds.
        """

        def handler(label, data):
            block = data['block_name']
            session.data[f'{label}_{block}'] = data
            self.agent.publish_to_feed(label, data)

        with self.lock.acquire_timeout(timeout=0, job='monitorFeeds') as acquired:
            if not acquired:
                print(f"Lock could not be acquired because it is held by {self.lock.job}.")
                return False
            
            last_release = time.time()
            last_poll = time.time()

            self._monitorFeeds = True

            while self._monitorFeeds:
                # Release and reacquire the lock every ~1 second
                if time.time() - last_release > params['lock_interval']:
                    last_release = time.time()
                    if not self.lock.release_and_acquire(timeout=120):
                        print(f'Could not re-acquire lock now held by {self.lock.job}.')
                        return False

                if time.time() - last_poll > params['poll_interval']:
                    last_poll = time.time()
                    self.r = queen.pollFeeds(handler, self.r)
                time.sleep(params['lock_interval'])
        return True, 'FeedMonitor: Exited.'

    # ======================================================================== #
    # .stopMonitorFeeds
    def _stopMonitorFeeds(self, session, params):
        """stopMonitorFeeds()

        **Task** - Stop monitoring drone HK data feeds.
        """

        if self._monitorFeeds:
            self._monitorFeeds = False
            return True,  'FeedMonitor: Stopping...'
        else:
            return False, 'FeedMonitor: Not currently running.'


    # ======================================================================== #
    # .setNCLO
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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

        with self.lock.acquire_timeout(job='setNCLO') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'setNCLO', 
                com_to   = params['com_to'], 
                silent   = params['silent'],
                com_args = f'f_lo={params["f_lo"]}')
        
        # return is a fail message str or number of clients int
        return True, f"setNCLO: Done"
    

    # ======================================================================== #
    # .setFineNCLO
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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

        with self.lock.acquire_timeout(job='setFineNCLO') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'setFineNCLO', 
                com_to   = params['com_to'], 
                silent   = params['silent'],
                com_args = f'f_lo={params["df_lo"]}')
        
        # return is a fail message str or number of clients int
        return True, f"setFineNCLO: Done"


    # ======================================================================== #
    # .getSnapData
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='getSnapData') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'getSnapData', 
                com_to   = params['com_to'], 
                silent   = params['silent'],
                com_args = f'mux_sel={params["mux_sel"]}')
            session.data['data'] = json.dumps(rtn, cls=ByteEncoder)
        # return is a fail message str or number of clients int
        return True, f"getSnapData: Done"
    
    
    # ======================================================================== #
    # .getADCrms
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    def getADCrms(self, session, params):
        """getADCrms()

        **Task** - Return the ADC RMS.
        """
        with self.lock.acquire_timeout(job='getADCrms') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'getADCrms', 
                com_to   = params['com_to'],
                silent   = params['silent'])
            session.data['data'] = json.dumps(rtn, cls=ByteEncoder)
        # return is a fail message str or number of clients int
        return True, f"getADCrms: Done"
    

    # ======================================================================== #
    # .writeTestTone
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='writeTestTone') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'writeTestTone', 
                com_to   = params['com_to'],
                silent   = params['silent'])
        
        # return is a fail message str or number of clients int
        return True, f"writeTestTone: Done"


    # ======================================================================== #
    # .writeNewVnaComb
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='writeNewVnaComb') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'writeNewVnaComb', 
                com_to   = params['com_to'],
                silent   = params['silent'])
        
        # return is a fail message str or number of clients int
        return True, f"writeNewVnaComb: Done"


    # ======================================================================== #
    # .writeTargCombFromVnaSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='writeTargCombFromVnaSweep') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'writeTargCombFromVnaSweep', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'cal_tones={params["cal_tones"]}')
        
        # return is a fail message str or number of clients int
        return True, f"writeTargCombFromVnaSweep: Done"
    

    # ======================================================================== #
    # .writeTargCombFromTargSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='writeTargCombFromTargSweep') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'writeTargCombFromTargSweep', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'cal_tones={params["cal_tones"]}, new_amps_and_phis={params["cal_tones"]}')
        
        # return is a fail message str or number of clients int
        return True, f"writeTargCombFromTargSweep: Done"


    # ======================================================================== #
    # .writeCombFromCustomList
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    def writeCombFromCustomList(self, session, params):
        """writeCombFromCustomList()

        **Task** - Write the comb from custom tone files.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
        with self.lock.acquire_timeout(job='writeCombFromCustomList') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'writeCombFromCustomList', 
                com_to   = params['com_to'],
                silent   = params['silent'])
        
        # return is a fail message str or number of clients int
        return True, f"writeCombFromCustomList: Done"


    # ======================================================================== #
    # .createCustomCombFilesFromCurrentComb
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='createCustomCombFilesFromCurrentComb') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'createCustomCombFilesFromCurrentComb', 
                com_to   = params['com_to'],
                silent   = params['silent'])
        
        # return is a fail message str or number of clients int
        return True, f"createCustomCombFilesFromCurrentComb: Done"


    # ======================================================================== #
    # .modifyCustomCombAmps
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='modifyCustomCombAmps') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'modifyCustomCombAmps', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'factor={params["factor"]}')
        
        # return is a fail message str or number of clients int
        return True, f"modifyCustomCombAmps: Done"


    # ======================================================================== #
    # .writeTargCombFromCustomList
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    def writeTargCombFromCustomList(self, session, params):
        """writeTargCombFromCustomList()

        **Task** - Write the target comb from custom tone files.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
        with self.lock.acquire_timeout(job='writeTargCombFromCustomList') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'writeTargCombFromCustomList', 
                com_to   = params['com_to'],
                silent   = params['silent'])
        
        # return is a fail message str or number of clients int
        return True, f"writeTargCombFromCustomList: Done"


    # ======================================================================== #
    # .vnaSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('sweep_steps', default=None, type=int)
    def vnaSweep(self, session, params):
        """vnaSweep()

        **Task** - Perform a stepped frequency sweep with current comb, save as vna sweep.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """

        with self.lock.acquire_timeout(job='vnaSweep') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            
            arg_keys = ['sweep_steps']

            rtn = _sendAlcoveCommand(
                com_str  = 'vnaSweep', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = _buildComArgs(params, arg_keys))
        
        # return is a fail message str or number of clients int
        return True, f"vnaSweep: Done"
    

    # ======================================================================== #
    # .targetSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('sweep_steps', default=None, type=int)
    @ocs_agent.param('chan_bw', default=None, type=float)
    def targetSweep(self, session, params):
        """targetSweep()

        **Task** - Perform a sweep with current comb, save as target sweep.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
        with self.lock.acquire_timeout(job='targetSweep') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            
            arg_keys = ['sweep_steps', 'chan_bw']
            rtn = _sendAlcoveCommand(
                com_str  = 'targetSweep', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = _buildComArgs(params, arg_keys))
        
        # return is a fail message str or number of clients int
        return True, f"targetSweep: Done"


    # ======================================================================== #
    # .customSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('bw', default=None, type=float)
    def customSweep(self, session, params):
        """customSweep()

        **Task** - Perform a sweep with current (custom) comb.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        bw: float
            Channel bandwidth.
        """
        with self.lock.acquire_timeout(job='customSweep') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            if params["bw"]:
                rtn = _sendAlcoveCommand(
                    com_str  = 'customSweep', 
                    com_to   = params['com_to'],
                    silent   = params['silent'],
                    com_args = f'bw={params["bw"]}')
            else: # allow func bw default
                rtn = _sendAlcoveCommand(
                    com_str  = 'customSweep', 
                    com_to   = params['com_to'],
                    silent   = params['silent'])
        
        # return is a fail message str or number of clients int
        return True, f"customSweep: Done"


    # ======================================================================== #
    # .findVnaResonators
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('peak_prom_std', default=10, type=float)
    @ocs_agent.param('peak_prom_db', default=0, type=float)
    @ocs_agent.param('peak_dis', default=100, type=int)
    @ocs_agent.param('width_min', default=5, type=int)
    @ocs_agent.param('width_max', default=100, type=int)
    @ocs_agent.param('stitch', default=True, type=bool)
    @ocs_agent.param('stitch_bw', default=None, type=int)
    @ocs_agent.param('stitch_sw', default=100, type=int)
    @ocs_agent.param('remove_cont', default=True, type=bool)
    @ocs_agent.param('continuum_wn', default=300, type=int)
    @ocs_agent.param('remove_noise', default=True, type=bool)
    @ocs_agent.param('noise_wn', default=30_000, type=int)
    def findVnaResonators(self, session, params):
        """findVnaResonators()

        **Task** - Find the resonator peak frequencies from vnaSweep S21. 
        Note that vnaSweep must be run first.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        peak_prom_std: (float) 
            Peak height from surroundings, in noise std multiples.
            Uses larger of peak_prom_db or peak_prom_std.
        peak_prom_db: (float)
            Peak height from surroundings, in Db.
            Uses larger of peak_prom_db or peak_prom_std.
        peak_dis: (int) 
            Min distance between peaks [bins].
        width_min: (int) 
            Peak width minimum. [bins]
        width_max: (int) 
            Peak width maximum. [bins]
        stitch: (bool) 
            Whether to stitch (comb discontinuities).
        stitch_sw: (int) 
            Discontinuity edge size for alignment [bins].
        remove_cont: (bool) 
            Whether to subtract the continuum.
        continuum_wn: (int) 
            Continuum filter cutoff frequency [Hz].
        remove_noise: (bool) 
            Whether to subtract noise.
        noise_wn: (int) 
            Noise filter cutoff frequency [Hz].
        """

        with self.lock.acquire_timeout(job='findVnaResonators') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
        
            arg_keys = ['peak_prom_std', 'peak_prom_db', 'peak_dis', 'width_min', 'width_max', 
                        'stitch', 'stitch_bw', 'stitch_sw', 'remove_cont', 'continuum_wn', 'remove_noise', 'noise_wn']

            rtn = _sendAlcoveCommand(
                com_str  = 'findVnaResonators', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = _buildComArgs(params, arg_keys))
        
        # return is a fail message str or number of clients int
        return True, f"findVnaResonators: Done"


    # ======================================================================== #
    # .findTargResonators
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('stitch_bw', default=None, type=int)
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
        with self.lock.acquire_timeout(job='findTargResonators') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'findTargResonators', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'stitch_bw={params["stitch_bw"]}')
        
        # return is a fail message str or number of clients int
        return True, f"findTargResonators: Done"

    # ======================================================================== #
    # .findCalTones
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
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
        with self.lock.acquire_timeout(job='findCalTones') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            arg_keys = ['f_hi', 'f_lo', 'tol', 'max_tones']

            rtn = _sendAlcoveCommand(
                com_str  = 'findCalTones', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = _buildComArgs(params, arg_keys))
        
        # return is a fail message str or number of clients int
        return True, f"findCalTones: Done"


    # ======================================================================== #
    # .sys_info
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    def sys_info(self, session, params):
        """sys_info()

        **Task** - Get system info from board.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
        with self.lock.acquire_timeout(job='sys_info') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'sys_info', 
                com_to   = params['com_to'],
                silent   = params['silent'])
            session.data['data'] = json.dumps(rtn, cls=ByteEncoder)
        # return is a fail message str or number of clients int
        return True, f"sys_info: Done"
    

    # ======================================================================== #
    # .sys_info_v
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    def sys_info_v(self, session, params):
        """sys_info_v()

        **Task** - Get system info from board, verbose.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        """
        with self.lock.acquire_timeout(job='sys_info_v') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'sys_info_v', 
                com_to   = params['com_to'],
                silent   = params['silent'])
            session.data['data'] = json.dumps(rtn, cls=ByteEncoder)
        # return is a fail message str or number of clients int
        return True, f"sys_info_v: Done"


    # ======================================================================== #
    # .cleanBoardDroneDirs
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('testing', default=True, type=bool)
    @ocs_agent.param('leave_latest', default=True, type=bool)
    @ocs_agent.param('olderThanDate', default=None, type=str)
    @ocs_agent.param('olderThanDaysAgo', default=None, type=str)
    @ocs_agent.param('largerThanMB', default=None, type=str)
    def cleanBoardDroneDirs(self, session, params):
        """cleanBoardDroneDirs()

        **Task** - Delete files in drones dir.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        leave_latest: (bool)
            Whether to leave the most recent version of known files (in board_io).
        ftype: (str) 
            File extension to match.
        olderThanDate: (str) 
            Filter: Match files older than YYYY-mm-dd date.
        olderThanDaysAgo: (int) 
            Filter: Match files older than this number days ago.
        largerThanMB: (int) 
            Filter: Match files larger than this in MB.
        testing: (bool) 
            Whether to actually delete files or not.
        """

        with self.lock.acquire_timeout(job='cleanBoardDroneDirs') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False

            arg_keys = ['leave_latest', 'testing',
                        'olderThanDate', 'olderThanDaysAgo', 'largerThanMB']
        
            rtn = _sendAlcoveCommand(
                com_str  = 'cleanBoardDroneDirs', 
                com_to   = params['com_to'],
                silent   = params['silent'], 
                com_args = _buildComArgs(params, arg_keys))
        
        # return is a fail message str or number of clients int
        return True, f"cleanBoardDroneDirs: Done"


    # ======================================================================== #
    # .timestreamOn
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('on', default=True, type=bool)
    def timestreamOn(self, session, params):
        """timestreamOn()

        **Task** - Turn the boards date timestream on/off.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        on: bool
            Timestream on/off.
        """
        with self.lock.acquire_timeout(job='timestreamOn') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False
            rtn = _sendAlcoveCommand(
                com_str  = 'timestreamOn', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f"on={params['on']},")
        
        # return is a fail message str or number of clients int
        return True, f"timestreamOn: Done"
    

    # ======================================================================== #
    # .userPacketInfo
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('data', type=int)
    def userPacketInfo(self, session, params):
        """userPacketInfo()

        **Task** - Write given data to timestream packet.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        data: 16 bit int
            Data to write to packet.
        """

        with self.lock.acquire_timeout(job='userPacketInfo') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False

            rtn = _sendAlcoveCommand(
                com_str  = 'userPacketInfo', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f"data={params['data']}")
            
        # return is a fail message str or number of clients int
        return True, f"userPacketInfo: Done"

    # ======================================================================== #
    # .setAtten2024
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('direction', type=str)
    @ocs_agent.param('atten', type=float)
    def setAtten2024(self, session, params):
        """setAtten2024()

        **Task** - Set attenuator value on drive/sense gain board.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        direction: (str)
            "sense" or "drive"
        atten: (float)
            Attenuation value in dB min 0 max 31.75
        """

        with self.lock.acquire_timeout(job='setAtten2024') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False

            direction = params['direction']
            atten = params['atten']

            rtn = _sendAlcoveCommand(
                com_str  = 'setAtten2024', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'direction={direction}, atten={atten},')
        
        # return is a fail message str or number of clients int
        return True, f"setAtten2024: Done"
    
    # ======================================================================== #
    # .setAtten2025
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('direction', type=str)
    @ocs_agent.param('atten', type=float)
    def setAtten2025(self, session, params):
        """setAtten2025()

        **Task** - Set attenuator value on drive/sense gain board.

        Args
        -------
        com_to: str
            Drone to send command to in format bid.drid.
            If None, will send to all drones.
            Default is None.
        direction: (str)
            "sense" or "drive"
        atten: (float)
            Attenuation value in dB min 0 max 31.75
        """

        with self.lock.acquire_timeout(job='setAtten2025') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False

            direction = params['direction']
            atten = params['atten']

            rtn = _sendAlcoveCommand(
                com_str  = 'setAtten2025', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'direction={direction}, atten={atten},')
        
        # return is a fail message str or number of clients int
        return True, f"setAtten2025: Done"

    # ======================================================================== #
    # .getAtten
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('direction', type=str)
    def getAtten(self, session, params):
        """getAtten()

        **Task** - Get RF attenuator values on Arduino controlled RF gain board.

        Args
        -------
        direction: (str) "sense" or "drive".

        Return: atten: (float) Attenuation value in dB.
        """

        with self.lock.acquire_timeout(job='getAtten') as acquired:
            if not acquired:
                print(f'Lock could not be acquired because it is held by {self.lock.job}.')
                return False

            direction = params['direction']

            rtn = _sendAlcoveCommand(
                com_str  = 'getAtten', 
                com_to   = params['com_to'],
                silent   = params['silent'],
                com_args = f'direction={direction},')
            session.data['data'] = json.dumps(rtn, cls=ByteEncoder)
        # return is a fail message str or number of clients int
        return True, f"getAtten: Done"
    # # ======================================================================== #
    # # .vnaSweep
    # @ocs_agent.param('com_to', default=None, type=str)
    # @ocs_agent.param('silent', default=False, type=bool)
    # def setAccumLength(self, session, params):
    #     """vnaSweep()

    #     **Task** - Sets the accumulation length in the DSP registers, determining sample rate.

    #     Args
    #     -------
    #     com_to: str
    #         Drone to send command to in format bid.drid.
    #         If None, will send to all drones.
    #         Default is None.
    #     """
  
    #     rtn = _sendAlcoveCommand(
    #         com_str  = 'setAccumLength', 
    #         com_to   = params['com_to'],
    #         silent   = params['silent'])
        
    #     # return is a fail message str or number of clients int
    #     return True, f"setAccumLength: {rtn}"

# ============================================================================ #
# == INTERNAL ==
# ============================================================================ #


# ============================================================================ #
# _buildComArgs
def _buildComArgs(params, arg_keys):
    '''Create com_args string.

    Note: None valued args are not included in string.
    '''

    kv = ((k, params.get(k)) for k in arg_keys)
    com_args = ", ".join(f"{k}={v}" for k, v in kv if v is not None)
    
    return com_args

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
def _sendAlcoveCommand(com_str, com_to=None, com_args=None, 
                       silent=False, timeout=None):
    """Send Alcove command.

    com_str:    (str)   String name of command. 
                        See alcove.py::_com(). 
                        E.g. 'alcove_base.setNCLO'
    com_to:     (str)   Drone to send command to.
                        E.g. '1.1' is board 1, drone 1.
                        '1' is board 1.
                        List okay: e.g. '[1.1,2.4]' .
    com_args:   (str)   Command arguments.
                        E.g. 'f_lo=500'
    ret_data:   (bool)  Whether the board should return data or be silent.
    """

    com_num = _comNumAlcove(com_str)

    ret_data = not silent

    # parse com_to
    bid, drid, list_bid_drids = None, None, None
    if com_to:
        list_bid_drids = queen._strToList(com_to)
        if not list_bid_drids: # not a list
            bid, drid = queen._bid_drid(com_to)

    if bid and drid:
        return queen.alcoveCommand(
            com_num, args=com_args, ret_data=ret_data, timeout=timeout,
            bid=bid, drid=drid)
    
    elif bid:
        return queen.alcoveCommand(
            com_num, args=com_args, ret_data=ret_data, timeout=timeout,
            bid=bid)

    elif list_bid_drids:
        return queen.alcoveCommand(
            com_num, args=com_args, ret_data=ret_data, timeout=timeout,
            list_bid_drids=list_bid_drids)

    else: # all-boards commands
        return queen.alcoveCommand(
            com_num, args=com_args, ret_data=ret_data, timeout=timeout,
            all_boards=True)

if __name__ == '__main__':
    main()

# ============================================================================ #
# == CLASS: ByteEncoder
# ============================================================================ #

class ByteEncoder(json.JSONEncoder):
    """ByteEncoder

    Custom JSON encoder to handle bytes and bytearray objects.
    """

    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            try:
                return pickle.loads(obj)
            except:
                return obj.decode('ASCII')
        if isinstance(obj, np.ndarray):
            return obj.tolist()

        return super().default(obj)