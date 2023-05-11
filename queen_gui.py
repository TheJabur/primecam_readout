# ============================================================================ #
# queen_gui.py
# Queen GUI: Interfaces with queen.py
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2023  
# ============================================================================ #



# ============================================================================ #
# Imports
# ============================================================================ #


import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QPlainTextEdit, QMessageBox
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, QObject, pyqtSignal

import base_io as io
import queen
import alcove
from timestream import TimeStream



# ============================================================================ #
# Main Window
# ============================================================================ #


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CCATpHive Readout Development GUI")
        self.setWindowIcon(QIcon(QPixmap('./gui_assets/icon.png')))

        # store 'loading' gif in memory for common use
        self.movie_loading = QMovie('./gui_assets/loading.gif')
        self.movie_loading.setScaledSize(QSize(10, 10))

        widget = QWidget(self) # main widget
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget) # use a vertical layout

        # setup UI elements
        self.uisetupQueenListen(layout) # Queen listen button
        self.uisetupTimestream(layout) # Time stream figure
        self.uisetupAlcoveCommand(layout) # Alcove command
        self.uisetupConsole(layout) # Console
    

    def closeEvent(self, event):
        """Standard function that runs when app is being closed.
        """

        # stop the queen listening thread
        if self.queenlisten_thread is not None:
            self.queenlisten_thread.stop()
        
        # ask user for exit confirmation
        event.ignore()
        if self.confirmClose():
            event.accept()


    def confirmClose(self):
        """Dialogue prompt to confirm app exit.
        """

        result = QMessageBox.question(self,
                      "Confirm Exit...",
                      "Are you sure you want to exit ?",
                      QMessageBox.Yes| QMessageBox.No)
        
        return result == QMessageBox.Yes



# ============================================================================ #
# Interface: Queen Listen


    def uisetupQueenListen(self, layout):
        self.button_queenlisten = QPushButton('START Queen Listening', self)
        self.button_queenlisten.setCheckable(True)
        self.button_queenlisten.clicked.connect(self.onClickButtonQueenlisten)
        layout.addWidget(self.button_queenlisten)
        self.queenlisten_thread = None
        self.button_queenlisten.click() # auto start queen listen


    def onClickButtonQueenlisten(self):
        if self.button_queenlisten.isChecked():
            print("Starting Queen listen mode...")
            self.updateQueenListenUI(running=True)
            self.sendQueenListenCommand()
            
        else:
            print("Stopping Queen listen mode...")
            self.updateQueenListenUI(running=False)
            if self.queenlisten_thread is not None:
                self.queenlisten_thread.stop()


    def updateQueenListenUI(self, running):
        if running:
            self.button_queenlisten.setText('STOP Queen listening')

        else:
            self.button_queenlisten.setText('START Queen listening')
            self.button_queenlisten.setChecked(False)


    def sendQueenListenCommand(self):
        self.queenlisten_thread = QueenCommandThread(self, com_str='listenMode', com_args='')
        self.queenlisten_thread.finished.connect(self.onFinishQueenlisten)
        self.queenlisten_thread.start()


    def onFinishQueenlisten(self, ret):
        try:
            thread, com_str, com_args = ret
            self.queenlisten_thread = thread
            running = thread is not None
        except:
            print("onFinishQueenlisten exception")
            running = False
        self.updateQueenListenUI(running)
    


# ============================================================================ #
# Interface: Timestream 


    def uisetupTimestream(self, layout):
        self.figure_timestream = plt.figure(figsize=(5, 3), dpi=100)
        self.canvas_timestream = FigureCanvas(self.figure_timestream)
        layout.addWidget(self.canvas_timestream)

        layout_timestreamui = QHBoxLayout()
        layout.addLayout(layout_timestreamui)

        self.textbox_timestream_id = QLineEdit()
        self.textbox_timestream_id.setPlaceholderText("KID ID")
        layout_timestreamui.addWidget(self.textbox_timestream_id)

        self.textbox_timestream_win = QLineEdit()
        self.textbox_timestream_win.setPlaceholderText("last x points")
        layout_timestreamui.addWidget(self.textbox_timestream_win)

        self.pulldown_timestream = QComboBox()
        self.pulldown_timestream.addItems(['power', 'phase'])
        layout_timestreamui.addWidget(self.pulldown_timestream)

        self.button_timestream = QPushButton("Start Time Stream")
        self.button_timestream.setCheckable(True)
        self.button_timestream.clicked.connect(self.onClickedButtonTimestream)
        layout_timestreamui.addWidget(self.button_timestream)

        self.button_timestream_save = QPushButton("Start Capture")
        self.button_timestream_save.setCheckable(True)
        self.button_timestream_save.clicked.connect(self.onClickedButtonTimestreamSave)
        layout_timestreamui.addWidget(self.button_timestream_save)
        self.button_timestream_save.setEnabled(False)

        self.label_timestream_save = QLabel("")
        layout_timestreamui.addWidget(self.label_timestream_save)

        self.timer_timestream_save = QTimer()
        self.timer_timestream_save.timeout.connect(self.updateTimeStreamTimer)
        self.timestream_save_time = 0

        self.timer_timestream = QTimer()
        self.timer_timestream.timeout.connect(self.updateFigureTimestream)

        self.timestream = None
        self.data_timestream = None 
        # 3D array of format: [[I], [Q]]
        # where I and Q have format: [[res1], [res2], [res3], ..., [resM]]
        # and resM have format: [val1, val2, ..., valN]
        self.data_timestream_save = None


    def onClickedButtonTimestream(self):
        if self.button_timestream.isChecked():
            try:
                # self.timestream = TimeStream(host='192.168.3.40', port=4096)
                self.timer_timestream.start(100)  # milliseconds
                self.updateTimeStreamUI(running=True)
            except Exception as e:
                self.timer_timestream.stop()
                self.updateTimeStreamUI(running=False)
                print(f"Error: Can't start timestream: {e}")

        else:
            self.timestream = None
            self.timer_timestream.stop()
            self.updateTimeStreamUI(running=False)

            self.data_timestream_save = None
            self.button_timestream_save.setChecked(False)


    def updateTimeStreamUI(self, running):
        if running:
            self.button_timestream.setText('Stop Time Stream')
            self.button_timestream.setChecked(True)
            self.button_timestream_save.setEnabled(True)
        else:
            self.button_timestream.setText('Start Time Stream')
            self.button_timestream.setChecked(False)
            self.button_timestream_save.setEnabled(False)


    def onClickedButtonTimestreamSave(self):
        if self.button_timestream_save.isChecked():
            # assuming can only click if timestream running
            # isChecked used in updateFigureTimestream()
            self.updateTimeStreamSaveUI(running=True)
            self.timestream_save_time = 0
            self.timer_timestream_save.start(1000) # 1 s

        else:
            self.saveToFileTimestreamSave()
            self.updateTimeStreamSaveUI(running=False)
            self.timer_timestream_save.stop()
            self.timestream_save_time = 0


    def saveToFileTimestreamSave(self):
        base_fname = f'timestream_{self.textbox_timestream_id.text()}_'
        fname = io.saveToTmp(self.data_timestream_save, 
                             filename=base_fname, use_timestamp=True)
        print(f"Saving captured timestream to file: {fname}")
        self.data_timestream_save = None


    def updateTimeStreamSaveUI(self, running):
        if running:
            self.button_timestream_save.setText("Save Capture")
            self.label_timestream_save.setText(f"{self.timestream_save_time}")

        else:
            self.button_timestream_save.setText("Start Capture")
            self.label_timestream_save.setText("")

        
    def updateTimeStreamTimer(self):
        self.timestream_save_time += 1
        self.label_timestream_save.setText(f"{self.timestream_save_time}")


    def updateFigureTimestream(self):
        # if self.timestream is None:
        #     return

        try:
            kid_id = max(int(self.textbox_timestream_id.text()), 0)
        except:
            kid_id = 0 # default kid_id
            # update GUI textbox to show using this kid_id
            self.textbox_timestream_id.setText(str(kid_id))

        # grab a chunk of timestream, hardcoded 100 packets
        I, Q = _getTimestreamData(self.timestream, 100, kid_id)

        # add new data to capture data
        if self.button_timestream_save.isChecked():
            if self.data_timestream_save is None:
                self.data_timestream_save = np.array([I, Q])
            else:
                I_save = np.concatenate((self.data_timestream_save[0], I), axis=1)
                Q_save = np.concatenate((self.data_timestream_save[1], Q), axis=1)
                self.data_timestream_save = np.array([I_save, Q_save])


        # add new data to already collected data 
        if self.data_timestream is not None: # None if first loop
            I = np.concatenate((self.data_timestream[0], I), axis=1)
            Q = np.concatenate((self.data_timestream[1], Q), axis=1)

        # crop to desired data length (# of packets)
        try: 
            ts_win = max(int(self.textbox_timestream_win.text()), 2)
        except:
            ts_win = 1000 # default ts_win length (# of packets)
        I = I[:,-ts_win:] # crop each res stream to ts_win packets
        Q = Q[:,-ts_win:]

        # save to instance variable for next loop
        self.data_timestream = np.array([I, Q])

        # plot in timestream figure
        self.figure_timestream.clear() # clear figure and replot
        if self.pulldown_timestream.currentText() == 'power':
            plt.plot(I[kid_id]**2 + Q[kid_id]**2, 
                     label='power', color='tab:green')
        else:
            plt.plot(np.arctan2(Q[kid_id], I[kid_id]), 
                    label='phase', color='tab:green')
        self.canvas_timestream.draw()



# ============================================================================ #
# Interface: Alcove Commands 


    def uisetupAlcoveCommand(self, layout):
        """Alcove commands interface.
        """

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


    def onClickButtonAlcovecoms(self):
        com_str = self.pulldown_alcovecoms.currentText()
        com_to = self.textbox_alcovecoms_to.text()
        com_args = self.textbox_alcovecoms_args.text()
        self.updateAlcoveComsUI(True, com_str, com_to, com_args)
        self.sendAlcoveCommand(com_str, com_to, com_args)


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


    def sendAlcoveCommand(self, com_str, com_to, com_args):
        # self.updateAlcoveComsUI(True, com_str, com_to, com_args)
        alcovecom_thread = AlcoveCommandThread(self, com_str, com_to, com_args)
        alcovecom_thread.finished.connect(self.onFinishAlcoveCommand)
        alcovecom_thread.start()


    def onFinishAlcoveCommand(self, ret_tuple):
        ret, com_str, com_to, com_args = ret_tuple
        print(f"Return: {ret}")
        self.updateAlcoveComsUI(False, com_str, com_to, com_args)


    # def sendQueenCommand(self, com_str, com_args):
    #     self.updateQueenComsUI(True, com_str, com_args)
    #     queencom_thread = QueenCommandThread(self, com_str, com_args)
    #     queencom_thread.ret.connect(self.onQueenCommandFinished)
    #     queencom_thread.start()


    
# ============================================================================ #
# Interface: Console 


    def uisetupConsole(self, layout):
        """Console interface.
        """

        self.console = QPlainTextEdit()
        layout.addWidget(self.console)
        self.emitter_console = ConsoleEmitter()
        self.emitter_console.text_written.connect(self.console.insertPlainText)
        sys.stdout.write = self.addConsoleMessage
        sys.stderr.write = self.addConsoleMessage


    def addConsoleMessage(self, text):
        """Add a message to the console.

        text: (str) The message to add.
        """

        self.emitter_console.text_written.emit(text)
        self.console.moveCursor(QTextCursor.End)
        # self.console.ensureCursorVisible()
    


# ============================================================================ #
# Threading Classes
# ============================================================================ #


class QueenCommandThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, parent, com_str, com_args):
        QThread.__init__(self, parent)
        self.com_str = com_str
        self.com_args = com_args

    def run(self):
        ret = _sendQueenCommand(self.com_str, self.com_args)
        self.finished.emit((ret, self.com_str, self.com_args))

#region
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
#endregion



# ============================================================================ #
# Internal Functions
# ============================================================================ #


class ConsoleEmitter(QObject):
    """Custom signal emitter for console output"""
    text_written = pyqtSignal(str)


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

    # I, Q = timestream.getTimeStreamChunk(packets)

    # fake data for testing
    X = 10 # number of kids
    N = packets # number of packets
    I = np.random.rand(X, N)
    Q = np.random.rand(X, N)

    return I, Q



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.aboutToQuit.connect(lambda: print("Closing..."))
    sys.exit(app.exec_())