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


        # Create the time stream figure
        self.figure = plt.figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)


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


        # # Create the buttons
        # button_layout = QHBoxLayout()
        # layout.addLayout(button_layout)

        # # Start time stream button
        # self.button_timestream = QPushButton("Start Time Stream")
        # self.button_timestream.clicked.connect(self.clicked_button_timestream)
        # button_layout.addWidget(self.button_timestream)

        # self.update_button = QPushButton("Update Text")
        # self.update_button.clicked.connect(self.update_text)
        # button_layout.addWidget(self.update_button)

        # # Create the label
        # self.label = QLabel("Press the Update Text button")
        # self.label.setAlignment(Qt.AlignCenter)
        # layout.addWidget(self.label)

        # # Create the timer
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.update_plot)

        # # Initialize the data
        # self.xdata = []
        # self.ydata = []


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



    # def clicked__start_stream(self):
    #     self.timer.start(100)  # milliseconds


    # def update_plot(self):
    #     # Generate new data
    #     x = len(self.xdata) + 1
    #     y = random.uniform(0, 1)

    #     # Update the data
    #     self.xdata.append(x)
    #     self.ydata.append(y)

    #     # Plot the data
    #     self.figure.clear()
    #     plt.plot(self.xdata, self.ydata)
    #     self.canvas.draw()


    # def update_text(self):
    #     self.label.setText("Text updated!")
    


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
