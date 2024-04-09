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
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import traceback

from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QPlainTextEdit, QMessageBox
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool

from config import thisDir

import base_io as io
import queen
import alcove
from timestream import TimeStream
import ip_addr as ip



# ============================================================================ #
# Main Window
# ============================================================================ #


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CCATpHive Readout Development GUI")
        self.setWindowIcon(QIcon(QPixmap('../assets/icon.png')))

        self.threadpool = QThreadPool()

        # store 'loading' gif in memory for common use
        self.movie_loading = QMovie('../assets/loading.gif')
        self.movie_loading.setScaledSize(QSize(10, 10))

        widget = QWidget(self) # main widget
        self.setCentralWidget(widget)
        suplayout = QHBoxLayout(widget) # 1st level: side-by-side
        layout = QVBoxLayout()          # left side: vertical layout
        suplayout.addLayout(layout)     
        layout2 = QVBoxLayout()         # right side: vertical layout
        suplayout.addLayout(layout2)    

        # setup left side (drone monitoring) elements
        self.uisetupDroneMonitor(layout2)

        # setup right side elements
        self.uisetupQueenListen(layout) # Queen listen button
        self.uisetupTimestream(layout)  # Time stream figure
        self.uisetupAlcoveCommand(layout) # Alcove command
        layout3 = QHBoxLayout()         # console and plot
        layout.addLayout(layout3)       
        self.uisetupConsole(layout3)    # Console
        self.uisetupPlot(layout3)       # Plot
    

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
                      QMessageBox.Yes| QMessageBox.No) # type: ignore
        
        return result == QMessageBox.Yes



# ============================================================================ #
# Interface: Drone Monitoring


    def uisetupDroneMonitor(self, layout):
        layout.addWidget(QLabel("Drones Status"))
        self.drone_grid = QGridLayout()
        self.drone_grid.setSpacing(1)
        layout.addLayout(self.drone_grid) 
        
        rows = 40 # num. boards could exceed this
        cols = 4 # each row is a board, 4 drones per board
        for row in range(rows):
            self.drone_grid.addWidget(QLabel(f"{row+1}"), row, 0)
            for col in range(cols):
                square = QLabel(self)
                self.drone_grid.addWidget(square, row, col+1)
                square.setStyleSheet("background-color: lightgrey")

        self.timer_drone_monitor = QTimer()
        self.timer_drone_monitor.timeout.connect(self.updateDroneMonitorUI)
        self.timer_drone_monitor.start(5000) # ms

        # self.updateDroneMonitorUI()


    def updateDroneMonitorUI(self):
        # set all back to grey
        # for i in range(self.drone_grid.count()):
        #     square = self.drone_grid.itemAt(i).widget()
        #     square.setStyleSheet("background-color: lightgrey")
        for row in range(self.drone_grid.rowCount()):
            for col in range(self.drone_grid.columnCount()):
                if col > 0: # first col is bid label
                    square = self.drone_grid.itemAtPosition(row, col).widget()
                    square.setStyleSheet("background-color: lightgrey")

        # set active drones to green
        client_list = self.getClientList()
        for client in client_list:
            try:
                client_name = client.get('name', '')
                bid, drid = list(map(int, client_name[-3:].split('.')))
                square = self.drone_grid.itemAtPosition(bid-1, drid).widget()
                # rows are 0-indexed but bids are 1-indexed
                # same w/ drids but 1st col is row label
                square.setStyleSheet("background-color: green")
            except:
                continue


    def getClientList(self):
        # QueenCommandThread(self, com_str='getClientList', com_args='')
        client_list =  _sendQueenCommand(com_str='getClientList', com_args='do_print=False', progress_callback='')

        return client_list



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
        com_str = 'listenMode'
        com_args = ''
        worker = Worker(_sendQueenCommand, com_str, com_args)
        worker.signals.result.connect(self.onResultQueenlisten)
        # worker.signals.finished.connect(self.onFinishQueenlisten)
        # worker.signals.progress.connect(self.progress_fn)
        self.threadpool.start(worker)
        

    def onResultQueenlisten(self, ret):
        try:
            thread = ret
            self.queenlisten_thread = thread
            running = thread is not None
        except:
            print("### EXCEPTION in onFinishQueenlisten")
            running = False
        self.updateQueenListenUI(running)


    # def onFinishQueenlisten(self):
    #     pass

    '''
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
            print("### EXCEPTION in onFinishQueenlisten")
            running = False
        self.updateQueenListenUI(running)
    '''
    


# ============================================================================ #
# Interface: Timestream 


    def uisetupTimestream(self, layout):
        self.figure_timestream = plt.figure(figsize=(5, 3), dpi=100)
        self.axes_timestream = self.figure_timestream.add_subplot(111)
        self.canvas_timestream = FigureCanvas(self.figure_timestream)
        layout.addWidget(self.canvas_timestream)

        def testPlot():
            I, Q = np.array((
                [np.random.normal(size=(1000)) for i in range(10)],
                [np.random.normal(size=(1000)) for i in range(10)]))
            kid_id = 0
            
            self.figure_timestream.clear()
            self.line1, = plt.plot(I[kid_id]**2 + Q[kid_id]**2, label='power', color='tab:green')
        testPlot()

        layout_timestreamui = QHBoxLayout()
        layout.addLayout(layout_timestreamui)

        self.textbox_timestream_ip = QLineEdit()
        self.textbox_timestream_ip.setText("192.168.3.40")
        layout_timestreamui.addWidget(self.textbox_timestream_ip)

        # self.textbox_timestream_bid_drid = QLineEdit()
        # self.textbox_timestream_bid_drid.setPlaceholderText("bid.drid")
        # layout_timestreamui.addWidget(self.textbox_timestream_bid_drid)

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
#====# 
# -TODO- switch to ip_addr module produced IP
                # tIP = ip.tIP(ip.cIP(r, bid), drid)
                # t_port = ip.getDroneTimestreamPort()
                # tIP = '192.168.3.40'
                tIP = self.textbox_timestream_ip.text()
                t_port = 4096

                # TODO: 
                # self.timestream = TimeStream(host=tIP, port=t_port)
                self.timestream = 'hi'
                
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
            # self.textbox_timestream_bid_drid.setEnabled(False)
            self.textbox_timestream_id.setEnabled(False)
            self.textbox_timestream_ip.setEnabled(False)
        else:
            self.button_timestream.setText('Start Time Stream')
            self.button_timestream.setChecked(False)
            self.button_timestream_save.setEnabled(False)
            # self.textbox_timestream_bid_drid.setEnabled(True)
            self.textbox_timestream_id.setEnabled(True)
            self.textbox_timestream_ip.setEnabled(True)


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
        base_fname = f'timestream_{self.textbox_timestream_ip.text()}_'
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
        if self.timestream is None:
            return

        # KID ID
        try:
            kid_id = max(int(self.textbox_timestream_id.text()), 0)
        except:
            kid_id = 0 # default kid_id
        self.textbox_timestream_id.setText(str(kid_id)) # update GUI

        # # bid.drid
        # try:
        #     bid_drid = self.textbox_timestream_bid_drid.text().split('.')
        #     bid = max(int(bid_drid[0]), 1)
        #     drid = max(int(bid_drid[1]), 1)
        # except:
        #     bid = 1
        #     drid = 1
        # self.textbox_timestream_bid_drid.setText(str(f'{bid}.{drid}')) # update GUI

        # grab a chunk of timestream, hardcoded 100 packets
        # TODO:
        # I, Q = _getTimestreamData(self.timestream, 100, kid_id)
        I, Q = np.array((
            [np.random.normal(size=(1000)) for i in range(10)],
            [np.random.normal(size=(1000)) for i in range(10)]))

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

        if len(I[kid_id]**2 + Q[kid_id]**2) == 1000:
            # plot in timestream figure00
            # self.figure_timestream.clear() # clear figure and replot
            if self.pulldown_timestream.currentText() == 'power':
                # plt.plot(I[kid_id]**2 + Q[kid_id]**2, 
                        #  label='power', color='tab:green')
                self.line1.set_ydata(I[kid_id]**2 + Q[kid_id]**2)
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
        self.updateAlcoveComsUI(True, com_str)
        self.sendAlcoveCommand(com_str, com_to, com_args)


    def updateAlcoveComsUI(self, busy, com_str=''):
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
            self.label_alcovecoms.setMovie(None) # type: ignore
            self.pulldown_alcovecoms.setEnabled(True)
            self.textbox_alcovecoms_to.setEnabled(True)
            self.textbox_alcovecoms_args.setEnabled(True)
            self.button_alcovecoms.setEnabled(True)
            self.button_alcovecoms.setText("Send Alcove Command")  


    def sendAlcoveCommand(self, com_str, com_to, com_args):
        print(f"Sending alcove command {com_str}", end='')
        print(f" to {com_to if com_to != '' else 'all boards'}", end='')
        print(f" with args ({com_args if com_args != '' else 'none'})", end='')
        print("...")

        worker = Worker(_sendAlcoveCommand, com_str, com_to, com_args)
        worker.signals.result.connect(self.onResultAlcoveCommand)
        worker.signals.finished.connect(self.onFinishAlcoveCommand)
        # worker.signals.progress.connect(self.progress_fn)
        worker.signals.error.connect(self.onErrorAlcoveCommand)
        self.threadpool.start(worker)
        

    def onResultAlcoveCommand(self, ret):
        if ret: # assuming return is number of clients
            print(f"... {ret} drone[s] received this command.")
        else:
            print("... NO DRONES RECEIVED THIS COMMAND!")


    def onFinishAlcoveCommand(self):
        self.updateAlcoveComsUI(False)


    def onErrorAlcoveCommand(self, ret):
        print(ret)


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
        layout.addWidget(self.console, stretch=1)
        self.emitter_console = ConsoleEmitter()
        self.emitter_console.text_written.connect(self.console.insertPlainText)
        sys.stdout.write = self.addConsoleMessage
        sys.stderr.write = self.addConsoleMessage


    def addConsoleMessage(self, text):
        """Add a message to the console.

        text: (str) The message to add.
        """

        self.emitter_console.text_written.emit(text) # override
        self.emitter_console.write(text) # also send to console
        self.console.moveCursor(QTextCursor.End) # snap console to bottom
        self.console.ensureCursorVisible()


    
# ============================================================================ #
# Interface: Plot 


    def uisetupPlot(self, layout):
        """Plot interface.
        """

        self.figure_plot = plt.figure(figsize=(4, 2.5))#, dpi=100)
        self.canvas_plot = FigureCanvas(self.figure_plot)
        layout.addWidget(self.canvas_plot, stretch=1)

        self.plotS21(*self.getLatestS21())


    def getLatestS21(self):
        dname = thisDir(__file__) + '/tmp'
        # dname = 'tmp'

        files = _getFiles(dname)

        for fname in files:
            if fname.startswith('s21_'):
                s21 = _getFileContents(f"{dname}/{fname}")
                return (s21, fname)
        return (None, 'no matching files')


    def plotS21(self, s21, fname):
        """
        """
        # TODO: CURRENTLY LOOKS LIKE JUNK
        # CAN WE PLOT IN INTERACTIVE MODE?

        self.figure_plot.clear()
        ax = self.figure_plot.add_subplot(111)
        ax.set_xlabel("Frequency")
        ax.set_ylabel("S21")

        if s21 is not None:
            f, Z = s21
            # ax.set_title(fname, y=0.85, size=8)
            ax.set_title(fname, y=1.01, size=8)
            ax.plot(f, np.abs(Z))
            ax.ticklabel_format(axis='both', style='sci', scilimits=(0,0))
            # ax.ticklabel_format(axis='both', style='sci', scilimits=None, useOffset=None, useLocale=None, useMathText=None)
            

        plt.tight_layout()
        self.canvas_plot.draw()


    # s21_targ_1_1_20230714T181021Z.npy
    # s21_vna_1_1_20230613T211111Z.npy
    # phis_vna_1_1_20230714T163936Z.npy
    # p_res_targ_1_1_20230714T185519Z.npy
    # f_res_targ_1_1_20230714T185519Z.npy
    # f_res_vna_1_1_20230714T180013Z.npy
    # f_cal_tones_1_1_20230714T190539Z.npy
    # amps_vna_1_1_20230714T163936Z.npy
    # a_res_targ_1_1_20230714T185519Z.npy





# ============================================================================ #
# Worker Classes
# ============================================================================ #

'''
class QueenCommandThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, parent, com_str, com_args):
        QThread.__init__(self, parent)
        self.com_str = com_str
        self.com_args = com_args

    def run(self):
        ret = _sendQueenCommand(self.com_str, self.com_args)
        self.finished.emit((ret, self.com_str, self.com_args))
'''

'''
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
'''

# WorkerSignals and Worker are from:
# https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
class WorkerSignals(QObject):
    '''Defines the signals available from a running worker thread.
    Supported signals are:
        finished: No data
        error: tuple (exctype, value, traceback.format_exc() )
        result: object data returned from processing, anything
    progress: int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


# WorkerSignals and Worker are from:
# https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
class Worker(QRunnable):
    '''Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# ConsoleEmitter
class ConsoleEmitter(QObject):
    """Custom signal emitter for console output
    """

    text_written = pyqtSignal(str) # override
    write = sys.stdout.write # hold connection console


# ============================================================================ #
# Alcove/Queen Commands

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


def _sendAlcoveCommand(com_str, com_to, com_args, progress_callback):
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
    

def _sendQueenCommand(com_str, com_args, progress_callback):
    com_num = _comNumQueen(com_str)

    return queen.callCom(com_num, com_args)


# ============================================================================ #
# Time Stream

def _getTimestreamData(timestream, packets=100, kid_id=None):
    """Get a chunk of time stream data.
    timestream: (TimeStream) the timestream object.
    packets: (int) number of packets to capture.
    kid_id:  (int) ID of resonator. If None get all.
    """

    I, Q = timestream.getTimeStreamChunk(packets)

    # # fake data for testing
    # X = 10 # number of kids
    # N = packets # number of packets
    # I = np.random.rand(X, N)
    # Q = np.random.rand(X, N)

    return I, Q


# ============================================================================ #
# File System

def _getFiles(dname):
    """
    """

    files = [os.path.join(dname, f) for f in os.listdir(dname)]
    files = [f for f in files if os.path.isfile(f)] # only files
    files.sort(reverse=True)
    # file_list.sort(key=lambda x: os.path.getmtime(x), reverse=True) # sort by mod time
    fnames = [os.path.basename(f) for f in files]

    return fnames

def _getFileContents(file_path):
        with open(file_path, 'r') as file:
            return np.load(file_path, allow_pickle=True)
            # return file.read()




# ============================================================================ #
# __main__
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.aboutToQuit.connect(lambda: print("Closing..."))
    sys.exit(app.exec_())