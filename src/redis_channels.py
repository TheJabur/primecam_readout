# ============================================================================ #
# redis_channels.py
# Module to produce Redis channels.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT/FYST 2023
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #


import uuid
# from dataclasses import dataclass, field

from config import board as cfg_b



# ============================================================================ #
# FUNCTIONS
# ============================================================================ #



# ============================================================================ #
# subscribe channels


def getAllBoardsChan():
    return 'all_boards'


def getBoardChan(bid:int):
    return f'board_{bid}_*'
    

def getDroneChan(bid:int, drid:int):
    return f'board_{bid}.{drid}_*'


def getChanList(bid:int, drid:int):
    """The Redis listening channels that drones subscribe to.
    bid: Board identifier.
    drid: Drone identifier.
    """

    chans = [
        getAllBoardsChan(),
        getBoardChan(bid),
        getDroneChan(bid, drid)
    ]

    return chans



# ============================================================================ #
# this board/drone sub chans


def getThisBoardChan():
    return getBoardChan(cfg_b.bid)


def getThisDroneChan():
    return getDroneChan(cfg_b.bid, cfg_b.drid)


def getThisChanList():
    return getChanList(cfg_b.bid, cfg_b.drid)



# ============================================================================ #
# command channel class
# - each command has a unique command channel


# @dataclass
# class comChan:
#     bid: int
#     drid: int = 0
#     id: str = field(init=False)
#     cid: str = field(init=False)
#     pub: str = field(init=False)
#     sub: str = field(init=False)

#     def __post_init__(self):
#         self.id = f'{self.bid}.{self.drid}' if self.drid else f'{self.bid}'
#         self.cid = str(uuid.uuid4())
#         chanid   = f'{self.id}_{self.cid}'
#         self.pub = f'board_{chanid}'
#         self.sub = f'rets_{self.pub}'

class comChan:
    def __init__(self, bid: int, drid: int = 0):
        self.bid = bid
        self.drid = drid
        self.id = f'{self.bid}.{self.drid}' if self.drid else f'{self.bid}'
        self.cid = str(uuid.uuid4())
        chanid = f'{self.id}_{self.cid}'
        self.pub = f'board_{chanid}'
        self.sub = f'rets_{self.pub}'


# @dataclass
# class thisComChan(comChan):
#     bid = cfg_b.bid
#     drid = cfg_b.drid

class thisComChan(comChan):
    def __init__(self, cfg_b):
        self.bid = cfg_b.bid
        self.drid = cfg_b.drid
        self.id = f'{self.bid}.{self.drid}' if self.drid else f'{self.bid}'
        self.cid = str(uuid.uuid4())
        chanid = f'{self.id}_{self.cid}'
        self.pub = f'board_{chanid}'
        self.sub = f'rets_{self.pub}'



# ============================================================================ #
# return channels


def _returnChanPrefix():
    return 'rets'


def getAllReturnsChan():
    return f'{_returnChanPrefix()}_*'


def getReturnChan(chan:str):
    ret_chan = f'{_returnChanPrefix()}_{chan}'
    if ret_chan == getAllBoardsChan(): # to know who sent
        ret_chan += f'_{cfg_b.bid}.{cfg_b.drid}'

    return ret_chan


