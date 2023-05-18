# ============================================================================ #
# ip_addr.py
# Board side module to get local IP addresses for control and timestream networks and some related utilities.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT/FYST 2023 
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #


import socket
import psutil

import _cfg_board as cfg



# ============================================================================ #
# EXTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# getBoardControlIP
def getBoardControlIP():
    """The control network IP address of this board.
    """

    ip_address = _getIPv4WithNIC('eth0')

    return ip_address


# ============================================================================ #
# getDroneTimestreamIP
def getDroneTimestreamIP():
    """The UDP timestream network IP address of this drone.
    """

    cIP = getBoardControlIP()
    cIP_octets = cIP.split('.') # type: ignore
    octets = cIP_octets
    
    # 3rd octet
    octets[2] = '3'
    
    # 4th octet
    # this algorithm makes space for 4 drones for each board
    octets[3] = str(4*(int(cIP_octets[3]) - 1) + cfg.drid)
    
    IP = '.'.join(octets)

    return IP


# ============================================================================ #
# IPtoHex
def IPtoHex(ip_address:str, as_list:bool=False):
    """Convert IP address to hex.
    E.g. 192.168.0.1 -> c0:a8:00:01.
    ip_address: The IP address to convert.
    as_list: Return octet list instead of single string.
    """

    octets = ip_address.split('.')

    # Convert each octet to hexadecimal and pad with zeros if necessary
    hex_octets = [hex(int(octet))[2:].zfill(2) for octet in octets]

    if as_list:
        return hex_octets

    # Join the hexadecimal octets with colons to form the hex IP address
    hex_ip = ':'.join(hex_octets)

    return hex_ip



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _get_ipv4_from_nic
def _getIPv4WithNIC(interface:str):
    """Return the IP address of the given interface.
    interface: The network interface controller (NIC).
    """

    interface_addrs = psutil.net_if_addrs().get(interface) or []
    for snicaddr in interface_addrs:
        if snicaddr.family == socket.AF_INET:
            snicaddr.address
            return snicaddr.address