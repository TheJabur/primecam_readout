# ============================================================================ #
# drone_control.py
# Queen drone control script.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2024 
# ============================================================================ #



# ============================================================================ #
# IMPORTS & GLOBALS
# ============================================================================ #

import redis

from config import queen as cfg
import queen_commands.control_io as io

import logging
logging.getLogger("paramiko").setLevel(logging.ERROR)



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _bid_drid
def _bid_drid(id):
    '''Separate id into bid.drid.
    Returns int (bid, drid), (bid, None), or (None, None).

    id: (str) in format 'bid.drid' or 'bid'.
    '''

    import re

    # casting from Redis strings
    id  = str(id)
    
    if re.fullmatch(r'\d+(\.\d+)?', id): # enforce 'x.y' or 'x'

        parts = id.split('.')
        bid = int(parts[0])
        drid = int(parts[1]) if len(parts) > 1 else None
        
    else: # incorrect format
        bid, drid = None, None

    return bid, drid


def _id(bid, drid=None):
    '''Join bid.drid into id.
    '''

    id = f"{bid}.{drid}"

    # check for consistency
    bidc, dridc = _bid_drid(id)
    if bidc != bid or dridc != drid:
        id = None

    return id


# ============================================================================ #
# _droneList
def _droneList():
    '''Get the drone list from the master drone list file.
    '''
    
    import yaml, os

    master_drone_list_file = os.path.join(cfg.dir_root, 
                                          cfg.master_drone_list_file)
    with open(master_drone_list_file, "r") as file:
        drone_list = yaml.safe_load(file)

    return drone_list


# ============================================================================ #
# _droneListAndProps
def _droneListAndProps(bid, drid, drone_list=None):  
    '''Get master drone list and properties for given drone id.
    '''   

    id = _id(bid, drid)

    # get master drone list unless it was passed in
    if drone_list is None:
        drone_list = _droneList()

    # get drone properties from list
    drone_props = drone_list.get(id)

    return drone_list, drone_props


# ============================================================================ #
#  _connectRedis
def _connectRedis():
    '''Connect to the redis server.
    '''

    r = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db, password=cfg.pw)
    p = r.pubsub()

    r.client_setname(f'drone_control')

    # check for connection
    try:
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")

    return r, p


# ============================================================================ #
#  _clientList
def _clientList(r=None):
    """The Redis client list.

    r,p: Redis initialization variables.
    """

    if r is None:
        r,p = _connectRedis()

    client_list = r.client_list()

    props = ['name', 'addr', 'age']
    client_list_light = {}
    for client in client_list:
        client_list_light[client['id']] = {
            prop: client.get(prop, 'N/A')
            for prop in props
        }

    return client_list_light


# ============================================================================ #
# _droneRunning
def _droneRunning(bid, drid, client_list=None, r=None):
    '''Check if drone is running by checking if it's in Redis client list.
    '''

    id = _id(bid, drid)

    if not client_list:
        client_list = _clientList(r)

    running = any(entry.get('name') == f"drone_{id}" 
                  for entry in client_list.values())

    return running


# ============================================================================ #
# _sshExe
def _sshExe(ip, command):
    '''Execute a command via SSH on RFSoC at IP.
    '''

    import paramiko

    # Set up SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # connect to board
        client.connect(
            hostname=ip,
            port=22,
            username=cfg.ssh_user, 
            password=cfg.ssh_pass,
            look_for_keys=False, # only use password login
            allow_agent=False,
            )

        # Execute the command
        stdin, stdout, stderr = client.exec_command(command)
        
        # Capture command output and errors
        output = stdout.read().decode()
        errors = stderr.read().decode()

        # Print or log output/errors as needed
        # if output:
        #     print(f"Output from {ip}:\n{output}")
        if errors:
            print(f"Errors from {ip}:\n{errors}")

        stdin.close()

    except Exception as e:
        print(f"An error occurred with {ip}: {e}")
    
    # Close the connection
    client.close()


# ============================================================================ #
# _fnameOvRide
def _fnameOvRide():
    '''Master drone list override file name.
    '''

    return 'override_drone_list.yaml'


# ============================================================================ #
# _loadOvRide
def _loadOvRide():
    '''Load the master drone list override file into dict.
    '''

    import yaml, os
    from datetime import datetime
    
    override_list = {}
    if os.path.exists(_fnameOvRide()):
        with open(_fnameOvRide(), "r") as file:
            override_list = yaml.safe_load(file)

    # remove expired entries
    current_time = datetime.now()
    for id in list(override_list.keys()): # editing in place
        if datetime.fromisoformat(override_list[id]) <= current_time:
            del override_list[id]

    return override_list


# ============================================================================ #
# _saveOvRide
def _saveOvRide(override_list):
    '''Save given dict to master drone file override file.
    '''

    import yaml
    from datetime import datetime

    # save to file
    with open(_fnameOvRide(), 'w') as file:
        yaml.dump(override_list, file)


# ============================================================================ #
# _addOvRide
def _addOvRide(bid, drid, timeout=60*60*12):
    '''Add master drone list to_run override.

    timeout: (int) Duration override is valid, [s].
    '''

    from datetime import datetime, timedelta

    id = _id(bid, drid)

    override_list = _loadOvRide()

    # remove existing entry for this drone
    override_list.pop(id, None)

    # calculate timeout time
    current_time = datetime.now()
    timeout_time = current_time + timedelta(seconds=timeout)

    # add timeout time to override list as timestamp
    override_list[id] = timeout_time.isoformat()

    _saveOvRide(override_list)

    return timeout


# ============================================================================ #
# _remOvRide
def _remOvRide(bid, drid):
    '''Remove master drone list to_run override.
    '''

    id = _id(bid, drid)

    override_list = _loadOvRide()

    # remove existing entry for this drone
    override_list.pop(id, None)

    _saveOvRide(override_list)


# ============================================================================ #
# _hasOvRide
def _hasOvRide(bid, drid, override_list=None):
    '''Check if a drone is on the override list (True/False).
    '''
    
    id = _id(bid, drid)

    if not override_list:
        override_list = _loadOvRide()

    return True if override_list.get(id) else False


# ============================================================================ #
# _monitorDrone
def _monitorDrone(bid, drid, drone_list, client_list, r=None):
    '''Used within queen drone monitoring.
    Return: 
        0: Did nothing
        1: Start sent
        2: Stop sent
    '''

    drone_list, drone_props = _droneListAndProps(bid, drid, drone_list)

    to_run = True if drone_props.get('to_run') else False

    # check if drone is already running
    is_running = _droneRunning(bid, drid, client_list, r=r)

    status = 0 # default; did nothing

    # shouldn't be running but is: stop
    if not to_run and is_running:
        command = f"sudo systemctl stop drone@{drid}.service"
        ret = _sshExe(drone_props['ip'], command)
        status = 2

    # should be running but isn't: start
    elif to_run and not is_running:
        command = f"sudo systemctl start drone@{drid}.service"
        ret = _sshExe(drone_props['ip'], command)
        status = 1

    return status




# ============================================================================ #
# COMMANDS
# ============================================================================ #


# ============================================================================ #
# action
def action(action, bid=None, drid=None, drone_list=None):
    '''Convenience function to commands.
    '''

    if action not in ['start', 'stop', 'restart', 'status', 
                      'startAllDrones', 'stopAllDrones', 'restartAllDrones']:
        return None

    if action == 'start':
        return startDrone(bid, drid, drone_list)

    if action == 'stop':
        return stopDrone(bid, drid, drone_list)

    if action == 'restart':
        return restartDrone(bid, drid, drone_list)

    if action == 'status':
        return statusDrone(bid, drid, drone_list)

    if action == 'startAllDrones':
        return startAllDrones()

    if action == 'stopAllDrones':
        return stopAllDrones()

    if action == 'restartAllDrones':
        return restartAllDrones()


# ============================================================================ #
# startDrone
def startDrone(bid, drid, drone_list=None, check=False, r=None):
    '''Start the drone at bid.drid if not running.
    '''

    drone_list, drone_props = _droneListAndProps(bid, drid, drone_list)
    
    # check for drone in master list
    if drone_props is None:
        print(f"Drone {bid}.{drid} not in master drone list.")
        return

    # remove existing override
    _remOvRide(bid, drid)

    # check if drone is already obviously running
    if check and _droneRunning(bid, drid, r=r):
        print(f"Drone {bid}.{drid} is already running.")
        return
    
    # start the drone
    print(f"Starting drone {bid}.{drid}... ", end="", flush=True)
    command = f"sudo systemctl start drone@{drid}.service"
    ret = _sshExe(drone_props['ip'], command)
    print("Done.")

    return ret


# ============================================================================ #
# stopDrone
def stopDrone(bid, drid, drone_list=None, check=False, timeout=None, r=None):
    '''Stop the drone bid.drid if running.
    '''

    drone_list, drone_props = _droneListAndProps(bid, drid, drone_list)
    
    # check for drone in master list
    if drone_props is None:
        print(f"Drone {bid}.{drid} not in master drone list.")
        return

    # add an override so monitor doesn't restart (until timeout)
    if timeout:
        timeout = _addOvRide(bid, drid, timeout=timeout)
    else:
        timeout = _addOvRide(bid, drid)

    # check if drone is obviously running
    if check and not _droneRunning(bid, drid, r=r):
        print(f"Drone {bid}.{drid} is not running.")
        return
    
    # stop the drone
    print(f"Stopping drone {bid}.{drid} (for {timeout} s)... ", end="", flush=True)
    command = f"sudo systemctl stop drone@{drid}.service"
    ret = _sshExe(drone_props['ip'], command)
    print("Done.")

    return ret


# ============================================================================ #
# restartDrone
def restartDrone(bid, drid, drone_list=None, r=None):
    '''Restart the drone bid.drid, whether running or not.
    '''

    drone_list, drone_props = _droneListAndProps(bid, drid, drone_list)
    
    # check for drone in master list
    if drone_props is None:
        print(f"Drone {bid}.{drid} not in master drone list.")
        return
    
    # remove existing override
    _remOvRide(bid, drid)

    # stop the drone
    print(f"Restarting drone {bid}.{drid}... ", end="", flush=True)
    command = f"sudo systemctl restart drone@{drid}.service"
    ret = _sshExe(drone_props['ip'], command)
    print("Done.")

    return ret


# ============================================================================ #
# statusDrone
def statusDrone(bid, drid, drone_list=None, r=None):
    '''
    '''

    drone_list, drone_props = _droneListAndProps(bid, drid, drone_list)
    
    # check for drone in master list
    if drone_props is None:
        print(f"Drone {bid}.{drid} not in master drone list.")
        return

    id = _id(bid, drid)

    # basic drone master list properties
    ip = drone_props.get('ip')
    to_run = drone_props.get('to_run')

    # drone is running
    running = _droneRunning(bid, drid, r=r)

    # status message
    msg = f"Status: Drone {id}: ip={ip}, to_run={to_run}, running={running}"
    
    print(msg)
    return msg

    # ip, to_run, running (or the msg string)


# ============================================================================ #
# startAllDrones
def startAllDrones(r=None):
    '''Start all drones in master drone list (if to_run=True).
    '''

    # this could potentially be threaded to run connections in parallel
    
    if r is None:
        r,p = _connectRedis()

    # load the master drone list
    drone_list = _droneList()

    # iterate through row by row
    for id, props in drone_list.items():

        # skip this drone if it's not supposed to be running
        if props.get('to_run') != True:
            continue

        bid, drid = _bid_drid(id)

        # start drone
        startDrone(bid=bid, drid=drid, drone_list=drone_list, r=r)      


# ============================================================================ #
# stopAllDrones
def stopAllDrones(r=None):
    '''Stop all drones in master drone list (if running).
    '''

    # this could potentially be threaded to run connections in parallel
    
    if r is None:
        r,p = _connectRedis()

    # load the master drone list
    drone_list = _droneList()

    # iterate through row by row
    for id, props in drone_list.items():

        bid, drid = _bid_drid(id)

        # stop drone
        stopDrone(bid=bid, drid=drid, drone_list=drone_list, r=r)


# ============================================================================ #
# restartAllDrones
def restartAllDrones(r=None):
    '''Restart all drones in master drone list.
    '''

    # this could potentially be threaded to run connections in parallel
    
    if r is None:
        r,p = _connectRedis()

    # load the master drone list
    drone_list = _droneList()

    # iterate through row by row
    for id, props in drone_list.items():

        bid, drid = _bid_drid(id)

        # stop drone
        restartDrone(bid=bid, drid=drid, drone_list=drone_list, r=r)
