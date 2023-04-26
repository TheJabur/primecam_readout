import sys
import numpy as np
import random
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, QObject, pyqtSignal

import queen
import alcove



class AlcoveCommandThread(QThread):
    ret = pyqtSignal(object)

    def __init__(self, parent, com_str, com_to, com_args):
        QThread.__init__(self, parent)
        self.com_str = com_str
        self.com_to = com_to
        self.com_args = com_args

    def run(self):
        ret = _sendAlcoveCommand(self.com_str, self.com_to, self.com_args)
        self.ret.emit((ret, self.com_str, self.com_to, self.com_args))



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


        # Time stream figure
        self.figure_timestream = plt.figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure_timestream)
        layout.addWidget(self.canvas)

        layout_timestreamui = QHBoxLayout()
        layout.addLayout(layout_timestreamui)

        self.textbox_timestream_id = QLineEdit()
        self.textbox_timestream_id.setPlaceholderText("KID ID")
        layout_timestreamui.addWidget(self.textbox_timestream_id)

        self.button_timestream = QPushButton("Start Time Stream")
        self.button_timestream.clicked.connect(self.clicked_button_timestream)
        layout_timestreamui.addWidget(self.button_timestream)

        self.timer_timestream = QTimer()
        self.timer_timestream.timeout.connect(self.update_figure_timestream)

        self.data_timestream = ([], []) # x, y


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
        self.button_alcovecoms.clicked.connect(self.clicked_button_alcovecoms)
        layout_alcovecoms.addWidget(self.button_alcovecoms)

        self.label_alcovecoms = QLabel("")
        layout_alcovecoms.addWidget(self.label_alcovecoms)



    def clicked_button_alcovecoms(self):
        com_str = self.pulldown_alcovecoms.currentText()
        com_to = self.textbox_alcovecoms_to.text()
        com_args = self.textbox_alcovecoms_args.text()
        self.sendAlcoveCommand(com_str, com_to, com_args)

    def sendAlcoveCommand(self, com_str, com_to, com_args):
        self.updateAlcoveComsUI(True, com_str, com_to, com_args)
        command_thread = AlcoveCommandThread(self, com_str, com_to, com_args)
        command_thread.ret.connect(self.onAlcoveCommandFinished)
        command_thread.start()

    def onAlcoveCommandFinished(self, ret_tuple):
        ret, com_str, com_to, com_args = ret_tuple
        print(f"Return: {ret}")
        self.updateAlcoveComsUI(False, com_str, com_to, com_args)

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


    def clicked_button_timestream(self):
        self.timer_timestream.start(100)  # milliseconds

    def update_figure_timestream(self):
        # random data for testing
        x = len(self.data_timestream[0]) + 1
        y = random.uniform(0, 1)
        self.data_timestream[0].append(x)
        self.data_timestream[1].append(y)
        self.figure_timestream.clear()
        plt.plot(self.data_timestream[0], self.data_timestream[1])
        self.canvas.draw()
    


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
    # print(f"Sending alcove command {com_str}")
    time.sleep(3)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
