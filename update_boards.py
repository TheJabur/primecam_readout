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

    # Define the SSH credentials for the control computer
    ssh_username = 'username'
    ssh_password = None # None if using key (see below)

    # Generate an SSH key pair on the control computer:
    #ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    # Should now be in ~/.ssh/id_rsa and ~/.ssh/id_rsa.pub.
    # Copy to the boards:
    #ssh-copy-id board_username@board_ip
    ssh_private_key_path = '/path/to/private/key'

    # Define the commands to update Hive
    update_commands = [
        'cd /path/to/CCATpHive',
        'git pull'
    ]

    # Loop through the list of board IPs
    for board_ip in board_ips:
        # Connect to the board via SSH
        ssh = paramiko.SSHClient()
        if ssh_password is not None: # use password
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(board_ip, username=ssh_username, password=ssh_password)
        else: # use key
            ssh.load_system_host_keys()
            ssh.connect(board_ip, username=ssh_username, 
                        key_filename=ssh_private_key_path)

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
