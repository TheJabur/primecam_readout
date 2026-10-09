# ============================================================================ #
# queen_agent_gen2.py
# OCS agent to control computer (queen) commands for gen2.
#
# James Burgoyne jamesrburgoyne@icloud.com
# CCAT 2026
# ============================================================================ #

import time
import json
import pickle
from functools import wraps
import numpy as np

from ocs import ocs_agent, site_config # type: ignore
from ocs.ocs_twisted import TimeoutLock # type: ignore

import queen
import alcove
import drone_control




# ============================================================================ #
# main
# ============================================================================ #
def main(args=None):
    args = site_config.parse_args(agent_class='ReadoutAgent', args=args)
    agent, runner = ocs_agent.init_site_agent(args)
    readout = ReadoutAgent(agent)

    agent.register_process('feedMonitor', readout.monitorFeeds, readout._stopMonitorFeeds, startup=True)

    tasks = [ 
        'action',
        'checkWaveformOverflow',
        'cleanBoardDroneDirs',
        'createCustomCombFilesFromCurrentComb', 
        'customSweep',
        'findCalTones',
        'findScaleFactors',
        'findTargResonators',
        'findVnaResonators',
        'getADCrms',
        'getAtten'
        'getClientList',
        'getClientListLight',
        'getKeyValue',
        'getSnapData',
        'modifyCustomCombAmps',
        'performFullVnaSweep',
        'setAtten2024',
        'setAtten2025',
        'setKeyValue',
        'setFineNCLO',
        'setNCLO',
        'sys_info',
        'sys_info_v',
        'targetSweep',
        'timestreamOn',
        'updateMeasurement',
        'userPacketInfo',
        'writeCombFromCustomList',
        'writeTargCombFromCustomList',
        'writeTargCombFromTargSweep',
        'writeTargCombFromVnaSweep',
        'writeTestTone',
        'writeTestTones',
    ]

    for task in tasks:
        agent.register_task(task, getattr(readout, task), blocking=(task != 'updateMeasurement'))

    runner.run(agent, auto_reconnect=True)


# ============================================================================ #
# with_lock
def with_lock(func):
    """Decorator to acquire and release self.lock around task execution."""
    @wraps(func)
    def wrapper(self, session, params, *args, **kwargs):
        job_name = func.__name__
        with self.lock.acquire_timeout(job=job_name) as acquired:
            if not acquired:
                print(f"Lock could not be acquired because it is held by {self.lock.job}.")
                return False
            return func(self, session, params, *args, **kwargs)
    return wrapper




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
            agg_params={'frame_length': 10*60},
            buffer_time=5.)

        self.agent.register_feed(
            'drone_temperatures_C',
            record=True,
            agg_params={'frame_length': 10*60},
            buffer_time=5.)

        self.agent.register_feed(
            'active_measurement',
            record=True)
        

    # ======================================================================== #
    # _exec_alcove
    def _exec_alcove(self, session, params, com_str, arg_keys=None, save_data=False):
        """Helper to dispatch commands to _sendAlcoveCommand."""
        if isinstance(arg_keys, list):
            com_args = _buildComArgs(params, arg_keys) or None
        elif isinstance(arg_keys, str):
            com_args = arg_keys
        else:
            com_args = None

        rtn = _sendAlcoveCommand(
            com_str=com_str,
            com_to=params.get('com_to'),
            silent=params.get('silent', False),
            com_args=com_args
        )

        if save_data:
            session.data['data'] = json.dumps(rtn, cls=ByteEncoder)

        return True, f"{com_str}: Done"


    # ======================================================================== #
    # .action
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('action', type=str)
    @with_lock
    def action(self, session, params):
        """Perform drone control action."""
        action = params['action']
        bid, drid = drone_control._bid_drid(params['com_to'])
        rtn = drone_control.action(action, bid, drid)
        session.data['data'] = json.dumps(rtn)
        return True, f"action: Done {action}"


    # ======================================================================== #
    # .updateMeasurement
    @ocs_agent.param('measurement_name', default=None, type=str)
    @ocs_agent.param('measurement_desc', default="", type=str)
    @with_lock
    def updateMeasurement(self, session, params):
        """Start or stop an active measurement session."""
        if self.measurement_name is None:
            self.measurement_name = params['measurement_name']
            self.measurement_desc = params['measurement_desc']
            self.measurement_start = time.time()
            return True, f"Starting measurement {self.measurement_name}"
        
        old_name = self.measurement_name
        old_desc = self.measurement_desc
        end_time = time.time()

        message = {
            'block_name': 'active_measurement',
            'timestamp': self.measurement_start,
            'data': {
                'name': old_name,
                'desc': old_desc,
                'TimeStart': int(self.measurement_start * 1e3),
                'TimeEnd': int(end_time * 1e3)
            }
        }
        self.agent.publish_to_feed('active_measurement', message)
        self.agent.feeds['active_measurement'].flush_buffer()

        if params.get('measurement_name'):
            self.measurement_name = params['measurement_name']
            self.measurement_desc = params['measurement_desc']
            self.measurement_start = time.time()
            return True, f"Finished measurement {old_name}; started {self.measurement_name}"
        
        self.measurement_name = None
        self.measurement_desc = ""
        self.measurement_start = None
        return True, f"Finished measurement {old_name}"


    # ======================================================================== #
    # .getClientList
    @with_lock
    def getClientList(self, session, params):
        """Return the list of Redis clients, verbose."""
        return True, f"client list: {queen.getClientList()}"


    # ======================================================================== #
    # .getClientListLight
    @with_lock
    def getClientListLight(self, session, params):
        """Return the list of Redis clients."""
        return True, f"client list: {queen.getClientListLight()}"


    # ======================================================================== #
    # .getKeyValue
    @ocs_agent.param('key', type=str)
    @with_lock
    def getKeyValue(self, session, params):
        """Return the value for the given key."""
        return True, f"{params['key']}: {queen.getKeyValue(params['key'])}"
    

    # ======================================================================== #
    # .monitorFeeds
    @ocs_agent.param('poll_interval', default=60, type=int)
    @ocs_agent.param('lock_interval', default=0.1, type=float)
    def monitorFeeds(self, session, params):
        """Monitor drone HK data (temp, disk space)."""
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
    # .setKeyValue
    @ocs_agent.param('key', type=str)
    @ocs_agent.param('value', type=str)
    @with_lock
    def setKeyValue(self, session, params):
        """Set given key to given value."""
        return True, f"{params['key']}: {queen.setKeyValue(params['key'], params['value'])}"
    

    # ======================================================================== #
    # .stopMonitorFeeds
    def _stopMonitorFeeds(self, session, params):
        """Stop monitoring drone HK data feeds."""
        if self._monitorFeeds:
            self._monitorFeeds = False
            return True, 'FeedMonitor: Stopping...'
        return False, 'FeedMonitor: Not currently running.'




    # ======================================================================== #
    # = ALCOVE TASK DISPATCHES
    # ======================================================================== #


    # ======================================================================== #
    # .checkWaveformOverflow
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def checkWaveformOverflow(self, session, params):
        """Sample the waveform to test for DAC overflow."""
        return self._exec_alcove(session, params, 'checkWaveformOverflow')
    
     
    # ======================================================================== #
    # .cleanBoardDroneDirs
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('testing', default=True, type=bool)
    @ocs_agent.param('leave_latest', default=True, type=bool)
    @ocs_agent.param('olderThanDate', default=None, type=str)
    @ocs_agent.param('olderThanDaysAgo', default=None, type=str)
    @ocs_agent.param('largerThanMB', default=None, type=str)
    @with_lock
    def cleanBoardDroneDirs(self, session, params):
        """Delete files in drones dir."""
        arg_keys = ['leave_latest', 'testing', 'olderThanDate', 'olderThanDaysAgo', 'largerThanMB']
        return self._exec_alcove(session, params, 'cleanBoardDroneDirs', arg_keys=arg_keys)


    # ======================================================================== #
    # .createCustomCombFilesFromCurrentComb
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('s', default='fap', type=str)
    @with_lock
    def createCustomCombFilesFromCurrentComb(self, session, params):
        """Create custom comb files from current comb."""
        return self._exec_alcove(session, params, 'createCustomCombFilesFromCurrentComb', arg_keys=['s'])


    # ======================================================================== #
    # .customSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('bw', default=None, type=float)
    @ocs_agent.param('sweep_steps', default=None, type=int)
    @with_lock
    def customSweep(self, session, params):
        """Perform sweep with custom comb."""
        return self._exec_alcove(session, params, 'customSweep', arg_keys=['bw', 'sweep_steps'])


    # ======================================================================== #
    # .findCalTones
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('f_lo', default=0.1, type=float)
    @ocs_agent.param('f_hi', default=50, type=float)
    @ocs_agent.param('tol', default=2, type=float)
    @ocs_agent.param('max_tones', default=10, type=int)
    @with_lock
    def findCalTones(self, session, params):
        """Determine indices of calibration tones."""
        return self._exec_alcove(session, params, 'findCalTones', arg_keys=['f_hi', 'f_lo', 'tol', 'max_tones'])


    # ======================================================================== #
    # .findScaleFactors
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('N', default=None, type=int)
    @with_lock
    def findScaleFactors(self, session, params):
        """Find the optimal scaling factors for N tones."""
        return self._exec_alcove(session, params, 'findScaleFactors', arg_keys=['N'])


    # ======================================================================== #
    # .findTargResonators
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('stitch_bw', default=None, type=int)
    @with_lock
    def findTargResonators(self, session, params):
        """Find resonator peak frequencies from targSweep S21."""
        return self._exec_alcove(session, params, 'findTargResonators', arg_keys=['stitch_bw'])


    # ======================================================================== #
    # .findVnaResonators
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('peak_prom_std', default=15, type=float)
    @ocs_agent.param('peak_prom_db', default=0, type=float)
    @ocs_agent.param('peak_dis', default=500, type=int)
    @ocs_agent.param('width_min', default=2, type=int)
    @ocs_agent.param('width_max', default=1000, type=int)
    @ocs_agent.param('stitch', default=True, type=bool)
    @ocs_agent.param('stitch_bw', default=None, type=int)
    @ocs_agent.param('stitch_sw', default=100, type=int)
    @ocs_agent.param('remove_cont', default=True, type=bool)
    @ocs_agent.param('continuum_wn', default=300, type=int)
    @ocs_agent.param('remove_noise', default=True, type=bool)
    @ocs_agent.param('noise_wn', default=30_000, type=int)
    @ocs_agent.param('peak_dis_hz', default=0, type=float)
    @ocs_agent.param('width_min_hz', default=0, type=float)
    @ocs_agent.param('width_max_hz', default=0, type=float)
    @ocs_agent.param('peak_prom_auto', default=False, type=bool)
    @ocs_agent.param('wlen', default=None, type=int)
    @ocs_agent.param('min_shelf_len', default=1, type=float)
    @ocs_agent.param('min_prom', default=1, type=float)
    @ocs_agent.param('max_prom', default=100, type=float)
    @ocs_agent.param('shelf_thresh', default=1, type=int)
    @with_lock
    def findVnaResonators(self, session, params):
        """Find resonator peak frequencies from vnaSweep S21."""
        arg_keys = [
            'peak_prom_std', 'peak_prom_db', 'peak_dis', 'width_min',
            'width_max', 'stitch', 'stitch_bw', 'stitch_sw', 'remove_cont',
            'continuum_wn', 'remove_noise', 'noise_wn', 'peak_dis_hz',
            'width_min_hz', 'width_max_hz', 'peak_prom_auto', 'wlen',
            'min_shelf_len', 'min_prom', 'max_prom', 'shelf_thresh'
        ]
        return self._exec_alcove(session, params, 'findVnaResonators', arg_keys=arg_keys)


    # ======================================================================== #
    # .getADCrms
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def getADCrms(self, session, params):
        """Return the ADC RMS."""
        return self._exec_alcove(session, params, 'getADCrms', save_data=True)
    

    # ======================================================================== #
    # .getAtten
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('direction', type=str)
    @with_lock
    def getAtten(self, session, params):
        """Get RF attenuator values on Arduino controlled RF gain board."""
        return self._exec_alcove(session, params, 'getAtten', arg_keys=['direction'], save_data=True)
    

    # ======================================================================== #
    # .getSnapData
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('mux_sel', type=int)
    @with_lock
    def getSnapData(self, session, params):
        """Fetch SNAP data."""
        return self._exec_alcove(session, params, 'getSnapData', arg_keys=['mux_sel'], save_data=True)


    # ======================================================================== #
    # .modifyCustomCombAmps
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('factor', default=1, type=float)
    @with_lock
    def modifyCustomCombAmps(self, session, params):
        """Modify custom tone amps file by multiplying by given factor."""
        return self._exec_alcove(session, params, 'modifyCustomCombAmps', arg_keys=['factor'])


    # ======================================================================== #
    # .performFullVnaSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('peak_prom_std', default=15, type=float)
    @ocs_agent.param('peak_prom_db', default=0, type=float)
    @ocs_agent.param('peak_dis', default=500, type=int)
    @ocs_agent.param('width_min', default=2, type=int)
    @ocs_agent.param('width_max', default=1000, type=int)
    @ocs_agent.param('stitch', default=True, type=bool)
    @ocs_agent.param('stitch_bw', default=None, type=int)
    @ocs_agent.param('stitch_sw', default=100, type=int)
    @ocs_agent.param('remove_cont', default=True, type=bool)
    @ocs_agent.param('continuum_wn', default=300, type=int)
    @ocs_agent.param('remove_noise', default=True, type=bool)
    @ocs_agent.param('noise_wn', default=30_000, type=int)
    @ocs_agent.param('peak_dis_hz', default=0, type=float)
    @ocs_agent.param('width_min_hz', default=0, type=float)
    @ocs_agent.param('width_max_hz', default=0, type=float)
    @ocs_agent.param('peak_prom_auto', default=False, type=bool)
    @ocs_agent.param('wlen', default=None, type=int)
    @ocs_agent.param('min_shelf_len', default=1, type=float)
    @ocs_agent.param('min_prom', default=1, type=float)
    @ocs_agent.param('max_prom', default=100, type=float)
    @ocs_agent.param('shelf_thresh', default=1, type=int)
    @with_lock
    def performFullVnaSweep(self, session, params):
        """Perform a full VNA sweep.
        This wraps together the following:
        Comb generation, sweep, resonator finding, and targ comb writing.
        The input parameters are a mirror of findVnaResonators.
        """
        arg_keys = [
            'peak_prom_std', 'peak_prom_db', 'peak_dis', 'width_min',
            'width_max', 'stitch', 'stitch_bw', 'stitch_sw', 'remove_cont',
            'continuum_wn', 'remove_noise', 'noise_wn', 'peak_dis_hz',
            'width_min_hz', 'width_max_hz', 'peak_prom_auto', 'wlen',
            'min_shelf_len', 'min_prom', 'max_prom', 'shelf_thresh'
        ]
        return self._exec_alcove(session, params, 'performFullVnaSweep', arg_keys=arg_keys)


    # ======================================================================== #
    # .setAtten2024
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('direction', type=str)
    @ocs_agent.param('atten', type=float)
    @with_lock
    def setAtten2024(self, session, params):
        """Set attenuator value on 2024 drive/sense gain board."""
        return self._exec_alcove(session, params, 'setAtten2024', arg_keys=['direction', 'atten'])


    # ======================================================================== #
    # .setAtten2025
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('direction', type=str)
    @ocs_agent.param('atten', type=float)
    @with_lock
    def setAtten2025(self, session, params):
        """Set attenuator value on 2025 drive/sense gain board."""
        return self._exec_alcove(session, params, 'setAtten2025', arg_keys=['direction', 'atten'])
    

    # ======================================================================== #
    # .setNCLO
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('f_lo', type=int)
    @with_lock
    def setNCLO(self, session, params):
        """Set the numerically controlled local oscillator."""
        return self._exec_alcove(session, params, 'setNCLO', arg_keys=['f_lo'])


    # ======================================================================== #
    # .setFineNCLO
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('df_lo', type=float)
    @with_lock
    def setFineNCLO(self, session, params):
        """Set fine frequency shift in the local oscillator."""
        return self._exec_alcove(session, params, 'setFineNCLO', arg_keys=f'f_lo={params["df_lo"]}')


    # ======================================================================== #
    # .sys_info
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def sys_info(self, session, params):
        """Get system info from board."""
        return self._exec_alcove(session, params, 'sys_info', save_data=True)
    

    # ======================================================================== #
    # .sys_info_v
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def sys_info_v(self, session, params):
        """Get verbose system info from board."""
        return self._exec_alcove(session, params, 'sys_info_v', save_data=True)


    # ======================================================================== #
    # .targetSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('sweep_steps', default=None, type=int)
    @ocs_agent.param('chan_bw', default=None, type=float)
    @with_lock
    def targetSweep(self, session, params):
        """Perform sweep with current comb, save as target sweep."""
        return self._exec_alcove(session, params, 'targetSweep', arg_keys=['sweep_steps', 'chan_bw'])


    # ======================================================================== #
    # .timestreamOn
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('on', default=True, type=bool)
    @with_lock
    def timestreamOn(self, session, params):
        """Turn the boards data timestream on/off."""
        return self._exec_alcove(session, params, 'timestreamOn', arg_keys=['on'])


    # ======================================================================== #
    # .userPacketInfo
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('data', type=int)
    @with_lock
    def userPacketInfo(self, session, params):
        """Write given data to timestream packet."""
        return self._exec_alcove(session, params, 'userPacketInfo', arg_keys=['data'])


    # ======================================================================== #
    # .writeCombFromCustomList
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def writeCombFromCustomList(self, session, params):
        """Write comb from custom tone files."""
        return self._exec_alcove(session, params, 'writeCombFromCustomList')


    # ======================================================================== #
    # .writeTargCombFromCustomList
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def writeTargCombFromCustomList(self, session, params):
        """Write target comb from custom tone files."""
        return self._exec_alcove(session, params, 'writeTargCombFromCustomList')


    # ======================================================================== #
    # .writeTargCombFromTargSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('cal_tones', default=False, type=bool)
    @ocs_agent.param('new_amps_and_phis', default=False, type=bool)
    @with_lock
    def writeTargCombFromTargSweep(self, session, params):
        """Write target comb from target sweep frequencies."""
        return self._exec_alcove(session, params, 'writeTargCombFromTargSweep', arg_keys=['cal_tones', 'new_amps_and_phis'])
    

    # ======================================================================== #
    # .writeTargCombFromVnaSweep
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('cal_tones', default=False, type=bool)
    @with_lock
    def writeTargCombFromVnaSweep(self, session, params):
        """Write the target comb from vna sweep frequencies."""
        return self._exec_alcove(session, params, 'writeTargCombFromVnaSweep', arg_keys=['cal_tones'])


    # ======================================================================== #
    # .writeTestTone
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @with_lock
    def writeTestTone(self, session, params):
        """Write a single test tone at LO."""
        return self._exec_alcove(session, params, 'writeTestTone')
    

    # ======================================================================== #
    # .writeTestTones
    @ocs_agent.param('com_to', default=None, type=str)
    @ocs_agent.param('silent', default=False, type=bool)
    @ocs_agent.param('N', default=1, type=int)
    # @ocs_agent.param('freqs', default=None, type=list)
    @with_lock
    def writeTestTones(self, session, params):
        """Write N evenly spaced tones or at freqs."""
        # return self._exec_alcove(session, params, 'writeTestTones', arg_keys=['N', 'freqs'])
        return self._exec_alcove(session, params, 'writeTestTones', arg_keys=['N'])




# ============================================================================ #
# == HELPER FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _comNumAlcove
def _comNumAlcove(com_str):
    print(f"_comNumAlcove... com_str={com_str}, keys:")
    print(alcove.comList())
    return alcove.comNumFromStr(com_str)


# ============================================================================ #
# _buildComArgs
def _buildComArgs(params, arg_keys):
    """Create com_args string.

    Note: None valued args are not included in string.
    """
    kv = ((k, params.get(k)) for k in arg_keys)
    return ", ".join(f"{k}={v}" for k, v in kv if v is not None)


# ============================================================================ #
# _sendAlcoveCommand
def _sendAlcoveCommand(com_str, com_to=None, com_args=None, silent=False, timeout=None):
    """Send Alcove command."""
    com_num = _comNumAlcove(com_str)
    ret_data = not silent

    bid, drid, list_bid_drids = None, None, None
    if com_to:
        list_bid_drids = queen._strToList(com_to)
        if not list_bid_drids:
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
    else:
        return queen.alcoveCommand(
            com_num, args=com_args, ret_data=ret_data, timeout=timeout,
            all_boards=True)


# ============================================================================ #
# class: ByteEncoder
class ByteEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle bytes, bytearray objects, and numpy arrays."""

    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            try:
                return pickle.loads(obj)
            except Exception:
                return obj.decode('ASCII')
        if isinstance(obj, np.ndarray):
            return obj.tolist()

        return super().default(obj)




if __name__ == '__main__':
    main()