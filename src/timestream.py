########################################################
### Resonator UDP timestream functions.              ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2023                                  ###
########################################################



###############
### IMPORTS ###

import socket
import numpy as np



########################
### TIMESTREAM CLASS ###

class TimeStream:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))


    def capturePacket(self, buffer_size=9000):
        message, address = self.sock.recvfrom(buffer_size)
        return bytearray(message)
        # return message.decode(), address


    def captureNpackets(self, N, buffer_size=9000):
        return np.array([self.capturePacket(buffer_size) for _ in range(N)])
    

    def byteshiftPackets(self, packets, byteshift=-1):
        return np.array([
            np.roll(p, byteshift) 
            for p in packets])
    

    def convertPackets(self, packets):
        return np.array([
            np.frombuffer(p, dtype="<i").astype("float")
            for p in packets])
    

    def getTimeStreamChunk(self, N):
        """Grab a chunk of N packets from the timestream.
        Returns I and Q.
        """

        x = self.captureNpackets(N)
        x = self.byteshiftPackets(x)
        x = self.convertPackets(x)

        I, Q = x[:,16::2].T, x[:,17::2].T
        
        return I, Q


    # def send_message(self, message, address):
    #     self.sock.sendto(message.encode(), address)


    def __del__(self):
        self.sock.close()


