# ============================================================================ #
# drone_manager.py
# Responsible for monitoring, starting, stopping, and restarting drones.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2024
# ============================================================================ #


import os
import time
import json
import errno
import psutil
import signal
import argparse
import subprocess


# CONFIG IN DroneManager CLASS


# ============================================================================ #
# _main
def _main():

    # get the CLI arguments
    args = _parseArgs()

    # Create an instance of MyClass
    drone_manager = DroneManager(args.drid)
    
    if args.command == "start":
        drone_manager.startDrone()

    elif args.command == "stop":
        drone_manager.stopDrone()

    elif args.command == "restart":
        drone_manager.restartDrone()

    elif args.command == "status":
        drone_manager.checkStatus()

    else:
        print("Unknown command. Use --help for more details.")
        # sys.exit(1) # is this necessary?


# ============================================================================ #
# _drid_type
def _dridType(value):
    """Custom type for drid (drone ID)."""

    try:
        drid = int(value)

        if drid < 1 or drid > 4:
            raise argparse.ArgumentTypeError(f"Drone ID {drid} is out of range (1-4).")
        
        return drid
    
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid Drone ID '{value}', must be an integer between 1 and 4.")
    

# ============================================================================ #
# _parseArgs
def _parseArgs():

    parser = argparse.ArgumentParser(description="Manage drone processes.")
    
    # Define subcommands: start, stop, restart, status
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # common drid argument
    def add_drid_argument(parser):
        parser.add_argument("drid", nargs='?', type=_dridType, 
                            help="Drone ID (1-4)")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a drone")
    add_drid_argument(start_parser)

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a drone")
    add_drid_argument(stop_parser)

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart a drone")
    add_drid_argument(restart_parser)

    # Status command
    status_parser = subparsers.add_parser("status", help="Drone status")
    add_drid_argument(status_parser)

    # Parse the arguments
    args = parser.parse_args()

    return args


# ============================================================================ #
# DroneManager class
class DroneManager:

# ============================================================================ #
# CONFIG
    dir_drones = '../drones'
    state_file = 'drone_state.json'
    drone_file = '../src/drone.py'
# ============================================================================ #

    drid        = None
    should_run  = False
    pid         = None

    def __init__(self, drid):

        self.drid = drid

        # construct needed paths (absolute)
        self.state_file = os.path.abspath(os.path.join(
            self.dir_drones, f'drone{drid}/', self.state_file))
        self.drone_file = os.path.abspath(self.drone_file)
        self.dir_drones = os.path.abspath(self.dir_drones)

        # Load the state of running drones on startup
        self.loadState() 


# ============================================================================ #
# validateProcess
    def validateProcess(self, pid):
        """Check if the process with the given pid is running."""

        print(pid)

        try:
            process = psutil.Process(pid)
        except psutil.Error as error:  # includes NoSuchProcess error
            return False
        if psutil.pid_exists(pid) and process.status() not in (psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE):
            return True
        return False

        # try:
        #     os.kill(pid, 0)  # check if running (doesn't kill)
        # except OSError as e:
        #     if e.errno == errno.ESRCH: # no such process
        #         return False
        # return True
    

# ============================================================================ #
# recoverDrone
    def recoverDrone(self):
        """Handle the recovery of a drone based on its state."""
        
        validated = self.validateProcess(self.pid)

        print(f"should_run={self.should_run}")
        print(f"validated={validated}")

        if self.should_run and not validated: # should be running but isn't
            self.startDrone()

        if not self.should_run and validated: # shouldn't be running but is
            self.stopDrone()


# ============================================================================ #
# loadState
    def loadState(self):
        """Load the state of this drone from file."""

        # check if state file exists
        if not os.path.exists(self.state_file):
            return
        
        # open state file
        with open(self.state_file, 'r') as f:

            # load state for this drone
            state = json.load(f)

            try:
                # json forced str keys back to int
                state = {int(key):value for key, value in state.items()}
            except: # something wrong with state file
                return 

            if self.drid in state:
                d = state[self.drid]

                # update drone params
                self.should_run = d.get('should_run', self.should_run)
                self.pid        = d.get('pid', self.pid)

                # recover drone process
                self.recoverDrone()


# ============================================================================ #
# saveState
    def saveState(self):
        """Save the state of this drone to file."""

        state = {self.drid:{
            'should_run':self.should_run, 
            'pid':self.pid}}
        
        # save state to file
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)
        

# ============================================================================ #
# startDrone
    def startDrone(self):

        self.should_run = True

        # check if already running
        if self.pid and self.validateProcess(self.pid):
            return

        # start
        process = subprocess.Popen(
            ['sudo', 'python3', self.drone_file, str(self.drid)])
        
        # check if started and capture pid
        if process.poll() is None:
            self.pid = process.pid
            
        self.saveState()


# ============================================================================ #
# stopDrone
    def stopDrone(self):
        self.should_run = False

        # Ensure there's a PID
        if not self.pid:
            return

        try:
            # Fetch process and check if it exists
            process = psutil.Process(self.pid)

            if not psutil.pid_exists(self.pid):
                raise psutil.NoSuchProcess(self.pid)

            # Check if the script has permission to kill the process
            if process.username() != os.getlogin():
                # Use sudo to terminate
                subprocess.run(["sudo", "kill", "-15", str(self.pid)], check=True)
                time.sleep(1)

                if psutil.pid_exists(self.pid):  # Check if process is still running before sending SIGKILL
                    subprocess.run(["sudo", "kill", "-9", str(self.pid)], check=True)

            else:
                # If the same user, kill normally
                process.terminate()
                process.wait(timeout=1)

        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            print(f"Process {self.pid} does not exist or is already terminated.")
        except subprocess.CalledProcessError as e:
            print(f"Error when killing process with sudo: {e}")
        except psutil.AccessDenied:
            print("Access denied when trying to manage process.")
        
        # Validate and reset PID if necessary
        if not self.validateProcess(self.pid):
            self.pid = None

        self.saveState()


    # def stopDrone(self):

    #     self.should_run = False

    #     # need a pid
    #     if not self.pid:
    #         return

    #     # stop the drone process
    #     try:
    #         os.kill(self.pid, signal.SIGTERM) # terminate
    #         time.sleep(1)                     # wait
    #         os.kill(self.pid, signal.SIGKILL) # kill
    #     except:
    #         pass
        
    #     # remove pid if not running
    #     if not self.validateProcess(self.pid):
    #         self.pid = None

    #     self.saveState()


# ============================================================================ #
# restartDrone
    def restartDrone(self):
        self.stopDrone()
        self.startDrone()


# ============================================================================ #
# checkStatus
    def checkStatus(self):
        """Print the status this drone."""

        stmt = f"drid={self.drid}; "
        stmt += f"should_run={self.should_run}; "
        stmt += f"pid={self.pid}; "
        stmt += f"running={self.validateProcess(self.pid)}"

        print(stmt)




if __name__ == "__main__":
    _main()