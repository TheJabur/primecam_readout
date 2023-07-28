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
import redis
import _cfg_board as cfg



# ============================================================================ #
# EXTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# Control IP (cIP)


def cIPofThisBoard():
    """The control network IP address of this board.
    Assumes it is eth0.
    """

    ip_address = _getIPv4WithNIC('eth0')

    return ip_address


def cIP(r:redis.Redis, bid:int):
    """The control network IP address of board with bid. 
    Uses the Redis client list to find IP (or returns None).
    """

    client_list = r.client_list()
    for client in client_list:
        if client.get('name', '').startswith(f'drone_{bid}.'):
            cIP = f"{client['addr']}"

            return cIP

    return None


# ============================================================================ #
# Time Stream IP (tIP)


def tIP_origin(drid:int, sep='.', asHex=False):
    """The UDP timestream network IP address origin (this drone)
    """

    ip = None
    if drid == 1: ip = cfg.udp_ori_ip_1
    if drid == 2: ip = cfg.udp_ori_ip_2
    if drid == 3: ip = cfg.udp_ori_ip_3
    if drid == 4: ip = cfg.udp_ori_ip_4

    if asHex:
        hexip =  IPtoHex(ip)
        return strSep(hexip, ':', sep)
    
    return strSep(ip, '.', sep)

# def tIP(cIP:str, drid:int):
#     """The UDP timestream network IP address algorithmically generated from the control IP (cIP) and drone ID (drid).
#     """

#     cIP_octets = cIP.split('.') # type: ignore
#     octets = cIP_octets
    
#     # 3rd octet
#     octets[2] = '3'
    
#     # 4th octet
#     # this algorithm makes space for 4 drones for each board
#     octets[3] = str(4*(int(cIP_octets[3]) - 1) + drid)
    
#     IP = '.'.join(octets)

#     return IP


def mac_origin(sep=':'):
    """The UDP timestream network mac address origin (this board)
    """

    return strSep(cfg.udp_ori_mac, ':', sep)


def getDroneTimestreamPort():
    """The UDP timestream network port.
    """

    return 4096


def tIP_destination(sep='.', asHex=False):
    """The UDP timestream destination IP address.
    """
    
    if asHex:
        return strSep(IPtoHex(cfg.udp_dest_ip), ':', sep)
    
    return strSep(cfg.udp_dest_ip, '.', sep)


def mac_destination(sep=':'):
    """The UDP timestream destination mac address.
    """
    
    return strSep(cfg.udp_dest_mac, ':', sep)


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
# strSep
def strSep(str, sep0, sep):
    """Replace sep0 separators in str with sep separators
    """

    elements = str.split(sep0)
    str_new = sep.join(elements)

    return str_new



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
