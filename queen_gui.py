########################################################
### Queen GUI.                                       ###
### Interfaces with queen.py.                        ###
###                                                  ###
### James Burgoyne jburgoyne@phas.ubc.ca             ###
### CCAT Prime 2023                                  ###
########################################################



###############
### IMPORTS ###

import sys
import numpy as np
import random
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QPlainTextEdit
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, QObject, pyqtSignal

import queen
import alcove
from timestream import TimeStream



###############
### THREADS ###


class ConsoleEmitter(QObject):
    """Custom signal emitter for console output"""
    text_written = pyqtSignal(str)


class QueenCommandThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, parent, com_str, com_args):
        QThread.__init__(self, parent)
        self.com_str = com_str
        self.com_args = com_args

    def run(self):
        # time.sleep(3)
        ret = _sendQueenCommand(self.com_str, self.com_args)
        self.finished.emit((ret, self.com_str, self.com_args))


class AlcoveCommandThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, parent, com_str, com_to, com_args):
        QThread.__init__(self, parent)
        self.com_str = com_str
        self.com_to = com_to
        self.com_args = com_args

    def run(self):
        # time.sleep(3)
        ret = _sendAlcoveCommand(self.com_str, self.com_to, self.com_args)
        self.finished.emit((ret, self.com_str, self.com_to, self.com_args))



###################
### MAIN WINDOW ###


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CCATpHive Experimental Readout GUI (PyQt)")

        # Loading gif
        self.movie_loading = QMovie('./gui_assets/loading.gif')
        self.movie_loading.setScaledSize(QSize(10, 10))

        # Create the main widget
        widget = QWidget(self)
        self.setCentralWidget(widget)

        # Create the main vertical layout
        layout = QVBoxLayout(widget)


        # Queen listen button
        self.button_queenlisten = QPushButton('START Queen Listening', self)
        self.button_queenlisten.setCheckable(True)
        self.button_queenlisten.clicked.connect(self.onClickButtonQueenlisten)
        layout.addWidget(self.button_queenlisten)
        self.queenlisten_thread = None
        self.button_queenlisten.click() # auto start queen listen


        # Time stream figure
        self.figure_timestream = plt.figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure_timestream)
        layout.addWidget(self.canvas)

        layout_timestreamui = QHBoxLayout()
        layout.addLayout(layout_timestreamui)

        self.textbox_timestream_id = QLineEdit()
        self.textbox_timestream_id.setPlaceholderText("KID ID")
        layout_timestreamui.addWidget(self.textbox_timestream_id)

        self.textbox_timestream_win = QLineEdit()
        self.textbox_timestream_win.setPlaceholderText("last x points")
        layout_timestreamui.addWidget(self.textbox_timestream_win)

        self.button_timestream = QPushButton("Start Time Stream")
        self.button_timestream.clicked.connect(self.onClickedButtonTimestream)
        layout_timestreamui.addWidget(self.button_timestream)

        self.timer_timestream = QTimer()
        self.timer_timestream.timeout.connect(self.updateFigureTimestream)

        self.data_timestream = np.array(([], [])) # I, Q


        # Alcove command
        layout_alcovecoms = QHBoxLayout()
        layout.addLayout(layout_alcovecoms)

        self.pulldown_alcovecoms = QComboBox()
        self.pulldown_alcovecoms.addItems(_comsListAlcove())
        layout_alcovecoms.addWidget(self.pulldown_alcovecoms)

        self.textbox_alcovecoms_to = QLineEdit()
        self.textbox_alcovecoms_to.setPlaceholderText("board.drone")
        layout_alcovecoms.addWidget(self.textbox_alcovecoms_to)

        self.textbox_alcovecoms_args = QLineEdit()
        self.textbox_alcovecoms_args.setPlaceholderText("args")
        layout_alcovecoms.addWidget(self.textbox_alcovecoms_args)

        self.button_alcovecoms = QPushButton("Send Alcove Command")
        self.button_alcovecoms.clicked.connect(self.onClickButtonAlcovecoms)
        layout_alcovecoms.addWidget(self.button_alcovecoms)

        self.label_alcovecoms = QLabel("")
        layout_alcovecoms.addWidget(self.label_alcovecoms)


        # Console
        self.console = QPlainTextEdit()
        # self.setCentralWidget(self.console)
        layout.addWidget(self.console)
        self.emitter_console = ConsoleEmitter()
        self.emitter_console.text_written.connect(self.console.insertPlainText)
        sys.stdout.write = self.stdout_write
        sys.stderr.write = self.stderr_write


    def onClickButtonAlcovecoms(self):
        com_str = self.pulldown_alcovecoms.currentText()
        com_to = self.textbox_alcovecoms_to.text()
        com_args = self.textbox_alcovecoms_args.text()
        self.updateAlcoveComsUI(True, com_str, com_to, com_args)
        self.sendAlcoveCommand(com_str, com_to, com_args)


    def onClickButtonQueenlisten(self):
        if self.button_queenlisten.isChecked():
            self.updateQueenListenUI(running=True)
            self.sendQueenListenCommand()
            
        else:
            self.updateQueenListenUI(running=False)
            if self.queenlisten_thread is not None:
                self.queenlisten_thread.terminate()
                self.button_queenlisten.setChecked(False)


    def onClickedButtonTimestream(self):
        try:
            self.timestream = TimeStream(host='192.168.3.40', port=4096)
            self.timer_timestream.start(100)  # milliseconds
        except Exception as e:
            print(f"Error: Can't start timestream: {e}")


    def onFinishAlcoveCommand(self, ret_tuple):
        ret, com_str, com_to, com_args = ret_tuple
        print(f"Return: {ret}")
        self.updateAlcoveComsUI(False, com_str, com_to, com_args)


    def onFinishQueenlisten(self, ret):
        print(f"Return: {ret}")
        self.queenlisten_thread = None
        self.updateQueenListenUI(False)


    def sendAlcoveCommand(self, com_str, com_to, com_args):
        # self.updateAlcoveComsUI(True, com_str, com_to, com_args)
        alcovecom_thread = AlcoveCommandThread(self, com_str, com_to, com_args)
        alcovecom_thread.finished.connect(self.onFinishAlcoveCommand)
        alcovecom_thread.start()


    # def sendQueenCommand(self, com_str, com_args):
    #     self.updateQueenComsUI(True, com_str, com_args)
    #     queencom_thread = QueenCommandThread(self, com_str, com_args)
    #     queencom_thread.ret.connect(self.onQueenCommandFinished)
    #     queencom_thread.start()


    def sendQueenListenCommand(self):
        self.queenlisten_thread = QueenCommandThread(self, com_str='listenMode', com_args='')
        self.queenlisten_thread.finished.connect(self.onFinishQueenlisten)
        self.queenlisten_thread.start()


    def updateAlcoveComsUI(self, busy, com_str, com_to, com_args):
        if busy: # waiting for command to finish
            self.button_alcovecoms.setText(com_str)
            self.button_alcovecoms.setEnabled(False)
            self.textbox_alcovecoms_to.setEnabled(False)
            self.textbox_alcovecoms_args.setEnabled(False)
            self.pulldown_alcovecoms.setEnabled(False)
            self.label_alcovecoms.setMovie(self.movie_loading)
            self.movie_loading.start()
        else: # on finish
            # print(self)
            self.movie_loading.stop()
            self.movie_loading.start() # what?
            self.movie_loading.stop() # what? why needed?
            self.label_alcovecoms.setMovie(None)
            self.pulldown_alcovecoms.setEnabled(True)
            self.textbox_alcovecoms_to.setEnabled(True)
            self.textbox_alcovecoms_args.setEnabled(True)
            self.button_alcovecoms.setEnabled(True)
            self.button_alcovecoms.setText("Send Alcove Command")   


    def updateQueenListenUI(self, running):
        if running:
            self.button_queenlisten.setText('STOP Queen listening')

        else:
            self.button_queenlisten.setText('START Queen listening')
            self.button_queenlisten.setChecked(False)


    def updateFigureTimestream(self):
        kid_id = self.textbox_timestream_id.text()
        I, Q = _getTimestreamData(self.timestream, 100, kid_id)

        I = np.concatenate((self.data_timestream[0], I), axis=1)
        Q = np.concatenate((self.data_timestream[1], Q), axis=1)

        # for i in range(len(self.data_timestream[0])):
        #     self.data_timestream[0][i].append(I[i])
        #     self.data_timestream[1][i].append(Q[i])

        # self.data_timestream[0].append(I)
        # self.data_timestream[1].append(Q)

        try: 
            ts_win = max(int(self.textbox_timestream_win.text()), 2)
        except:
            ts_win = 100
        I = I[:,-ts_win:]
        Q = Q[:,-ts_win:]
        
        # if len(self.data_timestream[0][0]) > ts_win:
        #     del self.data_timestream[0][:,:-ts_win]
        #     del self.data_timestream[1][:,:-ts_win]

        self.figure_timestream.clear()

        plt.plot(self.data_timestream[0][kid_id]**2 + self.data_timestream[1][kid_id]**2)

        # for i in range(len(self.data_timestream[0])):
        #     I = self.data_timestream[0][i]
        #     Q = self.data_timestream[1][i]
        #     plt.plot(I**2 + Q**2)
        #     break
        # plt.plot(np.array(self.data_timestream[0])**2 + np.array(self.data_timestream[1])**2)
        
        self.canvas.draw()

        # # fake random data for testing
        # x = self.data_timestream[0][-1]+1 if len(self.data_timestream[0])>0 else 1
        # y = random.uniform(0, 1)
        # self.data_timestream[0].append(x)
        # self.data_timestream[1].append(y)
        # try: 
        #     ts_win = max(int(self.textbox_timestream_win.text()), 2)
        # except:
        #     ts_win = 100
        # if len(self.data_timestream[0]) > ts_win:
        #     del self.data_timestream[0][:-ts_win]
        #     del self.data_timestream[1][:-ts_win]
        # self.figure_timestream.clear()
        # plt.plot(self.data_timestream[0], self.data_timestream[1])
        # self.canvas.draw()


    def stdout_write(self, text):
        """Redirects standard output to the console"""
        self.emitter_console.text_written.emit(text)

    def stderr_write(self, text):
        """Redirects standard error to the console"""
        self.emitter_console.text_written.emit(text)
    


##########################
### INTERNAL FUNCTIONS ###

def _comsListQueen():
    return [queen.com[key].__name__ for key in queen.com.keys()]

def _comsListAlcove():
    return [alcove.com[key].__name__ for key in alcove.com.keys()]

def _comNumQueen(com_str):
    coms = {queen.com[key].__name__:key for key in queen.com.keys()}
    return coms[com_str]

def _comNumAlcove(com_str):
    coms = {alcove.com[key].__name__:key for key in alcove.com.keys()}
    return coms[com_str]


def _sendAlcoveCommand(com_str, com_to, com_args):
    com_num = _comNumAlcove(com_str)

    # specific board/drone command
    if com_to:
        ids = com_to.split('.')
        bid = int(ids[0]) # must exist
        drid = int(ids[1]) if len(ids)>1 else None
        if drid:
            return queen.alcoveCommand(com_num, bid=bid, drid=drid, args=com_args)
        else:
            return queen.alcoveCommand(com_num, bid=bid, args=com_args)

    # all-boards commands
    else:
        return queen.alcoveCommand(com_num, all_boards=True, args=com_args)
    

def _sendQueenCommand(com_str, com_args):
    com_num = _comNumQueen(com_str)

    return queen.callCom(com_num, com_args)


def _getTimestreamData(timestream, packets=100, kid_id=None):
    """Get a chunk of time stream data.
    timestream: (TimeStream) the timestream object.
    packets: (int) number of packets to capture.
    kid_id:  (int) ID of resonator. If None get all.
    """

    I, Q = timestream.getTimeStreamChunk(packets)
    # print(I[0][:100])

    # todo: filter by kid_id

    return I, Q



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
