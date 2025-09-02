# ============================================================================ #
# timestream.py
# Detector UDP timestream functionality.
# James Burgoyne jburgoyne@phas.ubc.ca 
# Adrian Sinclair aksincla@asu.edu
# CCAT Prime 2025  
# ============================================================================ #

import socket
import numpy as np


# ============================================================================ #
# TimeStream class
# ============================================================================ #
class TimeStream:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set socket options to allow address reuse
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        self.sock.bind((self.host, self.port))

        self.packet_struct = {
            "data payload":             (0,    8191),
            "packet info":              (8192, 8193),
            "channel count":            (8194, 8195),
            "packet count":             (8196, 8199),
            "ptp timestamp":            (8200, 8211)
        }

        self.packets = None
        self.addresses = None


# ============================================================================ #
# capturePackets
    def capturePackets(self, N):
        """
        """

        buffer_size = 9000
        rcv = [self.sock.recvfrom(buffer_size) for _ in range(N)]
        self.packets = np.array([bytearray(data) for data,_ in rcv])
        self.addresses = np.array([addr[0] for _,addr in rcv])

        return True
    

# ============================================================================ #
# packetsIIQQ
    def packetsIIQQ(self):
        """II and QQ 2D arrays from packets.
        II/QQ consist of 1024 I or Q tods.
        """

        if self.packets is None:
            print(f"Error: Capture some packets first!")
            return None
        
        i, f = self.packet_struct['data payload'] # initial and final bytes
        IIQQ = [
            np.frombuffer(p[i:f+1], dtype="<i4").astype("float") 
            for p in self.packets]

        II = np.array([p[0::2] for p in IIQQ]) # 1024 I tods
        QQ = np.array([p[1::2] for p in IIQQ]) # 1024 Q tods

        return II, QQ


# ============================================================================ #
# packetsHH
    def packetsHH(self, field_name):
        """HH array from packets.
        HH is tod where each 'value' is a byte array of header field data.
        """

        if self.packets is None:
            print(f"Error: Capture some packets first!")
            return None
        
        if field_name not in self.packet_struct:
            print(f"Error: Header field '{field_name}' not found.")
            return None

        i, f = self.packet_struct[field_name] # initial and final bytes
        HH = np.array([
            p[i:f+1] # unconverted as each is different, so return bytes
            for p in self.packets])

        return HH
    

    def packetsIP(self):
        """IP (sender) array from packets.
        """

        if self.addresses is None:
            print(f"Error: Capture some packets first!")
            return None
        
        return self.addresses


# ============================================================================ #
# __del__
    def __del__(self):
        self.sock.close()




# ============================================================================ #
# parsePtpTimestamp
def parsePtpTimestamp(b, offset=0):
    """Parses a PTP timestamp from a 12-byte string.

    Args:
        b (bytes): The (12-byte) byte string containing the PTP timestamp
            from an RFSoC detector timestream packet.
        offset (float, optional): An offset to add to the resulting timestamp,
            in seconds. Defaults to 0. 37 to convert from TAI time to UTC.

    Returns:
        float: The PTP timestamp as a floating-point number representing seconds.
    """

    d = np.frombuffer(b, dtype='>u4') 

    seconds = int((d[-3] << 18) | (d[-2] >> 14))
    nanoseconds = int((((d[-2] & 0x00003FFF) << 16) | (d[-1] >> 16)))

    return seconds + nanoseconds*1e-9 + offset