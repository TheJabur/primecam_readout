########################################################
### update_boards.py                                 ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2022                                  ###
########################################################
### Python script that logs into each board and      ###
### executes the necessary commands to update        ###
### CCATpHive from a centralized computer            ###
### (likely the control computer).                   ###
### This script could be run automatically on a      ###
### regular basis, or triggered manually when        ###
### updates are available.                           ###

import paramiko

def update_boards():
    # Define a list of board IP addresses
    # At some point this may come from a separate cfg file
    board_ips = ['192.168.0.1', '192.168.0.2', '192.168.0.3']

    # Define the SSH credentials for the Queen computer
    ssh_username = 'username'
    ssh_password = 'password'

    # Define the commands to update Hive
    update_commands = [
        'cd /path/to/CCATpHive',
        'git pull'
    ]

    # Loop through the list of board IPs
    for board_ip in board_ips:
        # Connect to the board via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(board_ip, username=ssh_username, password=ssh_password)

        # Execute the update commands on the board
        for command in update_commands:
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            print(f'{board_ip}: {command}')
            if output:
                print(output)
            if error:
                print(error)

        # Close the SSH connection to the board
        ssh.close()

if __name__ == '__main__':
    update_boards()
