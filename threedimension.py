#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph.opengl as gl
import pyqtgraph as pg

class ThreeD(QtWidgets.QWidget):  # Inherit from QWidget to make it usable as a widget in your main application
    timer: QtCore.QTimer = None

    def __init__(self):
        super().__init__()

        # Create the GLViewWidget
        self.widget = gl.GLViewWidget()
        self.widget.opts['distance'] = 40
        self.widget.setWindowTitle('This is a GLViewWidget object within the pyqtgraph (top-level library) opengl (submodule)')
        self.widget.setGeometry(0, 110, 1920, 1080)

        # Create the background grids
        gx = gl.GLGridItem()
        gx.rotate(90, 0, 1, 0)
        gx.translate(-10, 0, 0)
        self.widget.addItem(gx)

        gy = gl.GLGridItem()
        gy.rotate(90, 1, 0, 0)
        gy.translate(0, -10, 0)
        self.widget.addItem(gy)

        gz = gl.GLGridItem()
        gz.translate(0, 0, -10)
        self.widget.addItem(gz)

        # Prepare data
        self.n = 50                             # number of lines
        self.m = 1000                           # number of points along the lines

        self.y = np.linspace(-10, 10, self.n)
        self.x = np.linspace(-10, 10, self.m)
        self.phase = 0

        # Create traces
        self.traces = dict()
        for i in range(self.n):
            yi = np.array([self.y[i]] * self.m)
            d = np.sqrt(self.x ** 2 + yi ** 2)
            z = 10 * np.cos(d + self.phase) / (d + 1)
            pts = np.vstack([self.x, yi, z]).transpose()
            self.traces[i] = gl.GLLinePlotItem(pos=pts, color=pg.glColor((i, self.n * 1.3)), width=(i + 1) / 10, antialias=True)
            self.widget.addItem(self.traces[i])

    def start_animation(self):
        print("in threedimension.ThreeD.start_animation")
        self.animation()

    def stop_animation(self):
        print("in threedimension.ThreeD.stop_animation")
        if self.timer is not None:
            self.timer.stop()

    def get_widget(self):
        return self.widget

    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)

    def update(self):
        print ("in threedimension.ThreeD.update")
        for i in range(self.n):
            yi = np.array([self.y[i]] * self.m)
            d = np.sqrt(self.x ** 2 + yi ** 2)
            z = 10 * np.cos(d + self.phase) / (d + 1)
            pts = np.vstack([self.x, yi, z]).transpose()
            self.set_plotdata(
                name=i, points=pts,
                color=pg.glColor((i, self.n * 1.3)),
                width=(i + 1) / 10
            )
            self.phase -= .003

    ### THIS METHOD NEVER GETS CALLED
    def animation(self):
        print("in threedimension.ThreeD.animation")
        if self.timer is None:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(20)
            self.timer.timeout.connect(self.update)

        self.timer.start()

# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)  # Only create QApplication if this is being run standalone
    v = ThreeD()
    v.animation()
    sys.exit(app.exec())
