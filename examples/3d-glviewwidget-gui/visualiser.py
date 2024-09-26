import numpy as np
from PyQt6 import QtCore
import pyqtgraph.opengl as gl
import pyqtgraph as pg

class Visualiser(object):
    def __init__(self, plot_widget):
        self.traces = dict()
        self.w = plot_widget  # Use the provided GLViewWidget

        self.w.opts['distance'] = 40
        self.w.setWindowTitle('3D Visualization')

        # Create background grids
        self.create_grids()

        self.n = 50  # number of lines
        self.m = 1000  # number of points along the lines
        self.y = np.linspace(-10, 10, self.n)
        self.x = np.linspace(-10, 10, self.m)
        self.phase = 0

        self.initialize_lines()

        # Start the animation
        self.animation()

    def create_grids(self):
        gx = gl.GLGridItem()
        gx.rotate(90, 0, 1, 0)
        gx.translate(-10, 0, 0)
        self.w.addItem(gx)

        gy = gl.GLGridItem()
        gy.rotate(90, 1, 0, 0)
        gy.translate(0, -10, 0)
        self.w.addItem(gy)

        gz = gl.GLGridItem()
        gz.translate(0, 0, -10)
        self.w.addItem(gz)

    def initialize_lines(self):
        for i in range(self.n):
            yi = np.array([self.y[i]] * self.m)
            d = np.sqrt(self.x ** 2 + yi ** 2)
            z = 10 * np.cos(d + self.phase) / (d + 1)
            pts = np.vstack([self.x, yi, z]).transpose()
            self.traces[i] = gl.GLLinePlotItem(pos=pts, color=pg.glColor((i, self.n * 1.3)), width=(i + 1) / 10, antialias=True)
            self.w.addItem(self.traces[i])

    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)

    def update(self):
        for i in range(self.n):
            yi = np.array([self.y[i]] * self.m)
            d = np.sqrt(self.x ** 2 + yi ** 2)
            z = 10 * np.cos(d + self.phase) / (d + 1)
            pts = np.vstack([self.x, yi, z]).transpose()
            self.set_plotdata(name=i, points=pts, color=pg.glColor((i, self.n * 1.3)), width=(i + 1) / 10)
        self.phase -= .003

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(20)

        # Start the animation loop
        self.update()  # Initial call to ensure the first frame is drawn
