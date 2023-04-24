import tkinter as tk
from tkinter import ttk
import random
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Tkinter GUI with Live Line Plot")

        # Create the main frame
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Create the line plot
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('X Label')
        self.ax.set_ylabel('Y Label')
        self.ax.set_xlim([0, 10])
        self.ax.set_ylim([0, 1])
        self.line, = self.ax.plot([], [])
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=10, fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()

        # Create the buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(padx=10, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Stream", command=self.start_stream)
        self.start_button.pack(side="left", padx=5, pady=5)

        self.update_button = ttk.Button(button_frame, text="Update Text", command=self.update_text)
        self.update_button.pack(side="left", padx=5, pady=5)

        # Create the label
        self.label = ttk.Label(frame, text="Press the Update Text button")
        self.label.pack(padx=10, pady=10)

        # Create the timer
        self.timer = None

        # Initialize the data
        self.xdata = []
        self.ydata = []

    def start_stream(self):
        # Start the timer to generate new data and update the plot at a fixed interval of 100 milliseconds
        if not self.timer:
            self.timer = self.after(100, self.update_plot)

    def update_plot(self):
        # Generate new data
        x = len(self.xdata) + 1
        y = random.uniform(0, 1)

        # Update the data
        self.xdata.append(x)
        self.ydata.append(y)

        # Update the line data
        self.line.set_data(self.xdata, self.ydata)

        # Update the plot limits
        self.ax.set_xlim([0, max(self.xdata) + 10])
        self.ax.set_ylim([0, 1])

        # Redraw the canvas
        self.canvas.draw()

        # Call this function again after 100 milliseconds
        self.timer = self.after(100, self.update_plot)

    def update_text(self):
        # Update the label text
        self.label.config(text="The Update Text button was pressed")

if __name__ == "__main__":
    window = MainWindow()
    window.mainloop()