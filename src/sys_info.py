
# ============================================================================ #
# git version

## use github workflow to automatically generate a version file


# ============================================================================ #
# config files

'''
main.py
import config

def get_module_variables(module):
    # Get all attributes of the module
    attributes = dir(module)
    # Filter out built-in attributes (those that start with "__")
    variables = {attr: getattr(module, attr) for attr in attributes if not attr.startswith("__")}
    return variables

config_variables = get_module_variables(config)

# Print out the variables
for name, value in config_variables.items():
    print(f"{name}: {value}")
'''


# ============================================================================ #
# user logs

'''
# import os

def get_recent_auth_log_events(log_file_path='/var/log/auth.log', num_lines=10):
    try:
        with open(log_file_path, 'r') as file:
            lines = file.readlines() # Read all lines from the log file
            recent_lines = lines[-num_lines:] # Get the most recent 'num_lines' events
            return recent_lines
    except FileNotFoundError:
        print(f"Log file {log_file_path} not found.")
        return []
    except PermissionError:
        print(f"Permission denied when trying to read {log_file_path}.")
        return []

# Example usage:
recent_events = get_recent_auth_log_events(num_lines=10)
for event in recent_events:
    print(event.strip())
'''


# ============================================================================ #
# system log

'''
import os
import subprocess

def get_recent_syslog_events(log_file_path='/var/log/syslog', num_lines=10):
    try:
        with open(log_file_path, 'r') as file:
            lines = file.readlines() # Read all lines from the log file
            # Get the most recent 'num_lines' events
            recent_lines = lines[-num_lines:]
            return recent_lines
    except FileNotFoundError:
        print(f"Log file {log_file_path} not found.")
        return []
    except PermissionError:
        print(f"Permission denied when trying to read {log_file_path}.")
        return []

def get_recent_dmesg_events(num_lines=10):
    try:
        # Use subprocess to call the dmesg command and capture the output
        result = subprocess.run(['dmesg', '-T', '--level=err,warn'], stdout=subprocess.PIPE, text=True)
        dmesg_output = result.stdout.splitlines()
        # Get the most recent 'num_lines' events
        recent_dmesg_lines = dmesg_output[-num_lines:]
        return recent_dmesg_lines
    except Exception as e:
        print(f"An error occurred while running dmesg: {e}")
        return []

# Example usage for syslog:
print("Recent syslog events:")
recent_syslog_events = get_recent_syslog_events(num_lines=10)
for event in recent_syslog_events:
    print(event.strip())

# Example usage for dmesg:
print("\nRecent dmesg events:")
recent_dmesg_events = get_recent_dmesg_events(num_lines=10)
for event in recent_dmesg_events:
    print(event.strip())
'''


# ============================================================================ #
# OS and software

'''
import subprocess

def get_system_info():
    def get_os_version():
        try:
            result = subprocess.run(['lsb_release', '-a'], capture_output=True, text=True, check=True)
            os_info = {}
            for line in result.stdout.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    os_info[key.strip()] = value.strip()
            return os_info.get('Description', 'Unknown OS Version')
        except subprocess.CalledProcessError:
            return 'Unknown OS Version'

    def get_apt_packages():
        try:
            result = subprocess.run(['apt', 'list', '--installed'], capture_output=True, text=True, check=True)
            packages = {}
            lines = result.stdout.splitlines()
            for line in lines:
                if not line.startswith('Listing...') and line:
                    parts = line.split('/')
                    if len(parts) > 1:
                        package_name = parts[0].strip()
                        package_version = parts[1].split(' ')[0].strip()
                        packages[package_name] = package_version
            return packages
        except subprocess.CalledProcessError:
            return {}

    return {
        'OS Version': get_os_version(),
        'APT Packages': get_apt_packages()
    }

# Example usage
system_info = get_system_info()
print(system_info)
'''


# ============================================================================ #
# uptime

'''
import psutil
import datetime

def get_system_uptime():
    # Get the system boot time
    boot_time = psutil.boot_time()
    
    # Calculate uptime
    current_time = datetime.datetime.now().timestamp()
    uptime_seconds = current_time - boot_time
    
    # Convert uptime to days, hours, minutes, seconds
    uptime = str(datetime.timedelta(seconds=uptime_seconds))
    
    # Return a dictionary with the uptime
    return {
        'uptime_seconds': uptime_seconds,
        'uptime': uptime
    }

# Example usage
if __name__ == "__main__":
    uptime_info = get_system_uptime()
    print(uptime_info)
'''
