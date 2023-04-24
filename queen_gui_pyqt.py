import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
import numpy as np
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CCATpHive Experimental Readout GUI (PyQt)")

        # Create the main widget
        widget = QWidget(self)
        self.setCentralWidget(widget)

        # Create the layout
        layout = QVBoxLayout(widget)

        # Create the time stream figure
        self.figure = plt.figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Create the buttons
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        self.start_button = QPushButton("Start Stream")
        self.start_button.clicked.connect(self.start_stream)
        button_layout.addWidget(self.start_button)

        self.update_button = QPushButton("Update Text")
        self.update_button.clicked.connect(self.update_text)
        button_layout.addWidget(self.update_button)

        # Create the label
        self.label = QLabel("Press the Update Text button")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Create the timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        # Initialize the data
        self.xdata = []
        self.ydata = []

    def start_stream(self):
        self.timer.start(100)  # milliseconds

    def update_plot(self):
        # Generate new data
        x = len(self.xdata) + 1
        y = random.uniform(0, 1)

        # Update the data
        self.xdata.append(x)
        self.ydata.append(y)

        # Plot the data
        self.figure.clear()
        plt.plot(self.xdata, self.ydata)
        self.canvas.draw()

    def update_text(self):
        self.label.setText("Text updated!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
