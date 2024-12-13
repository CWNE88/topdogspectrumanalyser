import sys
import numpy as np
from PyQt6 import QtWidgets
from PyQt6.QtCore import QTimer
from pyqtgraph import opengl as gl
from scipy.fft import fft

class Boxes(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.view = gl.GLViewWidget()
        self.view.opts['azimuth'] = 90
        self.view.opts['elevation'] = 20
        self.view.opts['fov'] = 110
        self.setCentralWidget(self.view)
        self.view.setCameraPosition(distance=10)

        grid = gl.GLGridItem()
        grid.setSize(x=20, y=20)
        grid.setSpacing(x=1, y=1)
        self.view.addItem(grid)

        self.frequency_bins = 2004
        self.n_bins = 2004

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_visualisation)
        #self.timer.start(20)

        # Prepare the initial mesh data
        self.box_item = gl.GLMeshItem()
        self.view.addItem(self.box_item)
        self.init_boxes()

        self.power_levels = None

    def init_boxes(self):
        self.n_bins = self.frequency_bins
        self.vertices = np.zeros((self.n_bins * 8, 3), dtype=float)  # 8 vertices per box
        self.faces = np.zeros((self.n_bins * 12, 3), dtype=int)      # 12 triangles per box
        self.vertex_colours = np.zeros((self.n_bins * 8, 4), dtype=float)  # 4 colors per vertex

        box_spacing = np.linspace(-10, 10, self.n_bins + 1)

        for i in range(self.n_bins):
            box_x1 = box_spacing[i]
            box_x2 = box_spacing[i + 1]

            # Define vertices for the box
            v_start = i * 8  # Starting index for the current box
        
            depth1 = 0
            depth2 = 0.5
            self.vertices[v_start:v_start + 8] = [
                [box_x1, depth2, 0],   # 0
                [box_x2, depth2, 0],   # 1
                [box_x2, depth1, 0],   # 2
                [box_x1, depth1, 0],   # 3
                [box_x1, depth2, 0],   # 4 (top)
                [box_x2, depth2, 0],   # 5 (top)
                [box_x2, depth1, 0],   # 6 (top)
                [box_x1, depth1, 0]    # 7 (top)
            ]

            # Define faces for the box (12 triangles)
            f_start = i * 12  # Starting index for the current box's faces
            self.faces[f_start:f_start + 12] = [
                [v_start + 0, v_start + 1, v_start + 2],
                [v_start + 0, v_start + 2, v_start + 3],
                [v_start + 4, v_start + 5, v_start + 6],
                [v_start + 4, v_start + 6, v_start + 7],
                [v_start + 0, v_start + 1, v_start + 5],
                [v_start + 0, v_start + 5, v_start + 4],
                [v_start + 1, v_start + 2, v_start + 6],
                [v_start + 1, v_start + 6, v_start + 5],
                [v_start + 2, v_start + 3, v_start + 7],
                [v_start + 2, v_start + 7, v_start + 6],
                [v_start + 3, v_start + 0, v_start + 4],
                [v_start + 3, v_start + 4, v_start + 7]
            ]

            # Set vertex colors (blue for the top, black for the bottom)
            self.vertex_colours[v_start:v_start + 8] = [
                [0, 0, 1, 1]] * 4 + [[0, 0, 0, 1]] * 4

        # Create initial mesh data
        mesh_data = gl.MeshData(vertexes=self.vertices, vertexColors=self.vertex_colours, faces=self.faces)
        self.box_item.setMeshData(meshdata=mesh_data)

    def update_visualisation(self):
        """Optimized update for visualization."""
        if self.live_power_levels is None:
            return

        # Calculate the heights based on live power levels
        heights = self.live_power_levels / 50 + 2  # Adjust scaling as needed
        colour_scale_factor = heights / 10  # Color scale factor based on height

        # Vectorized updates for vertices (height of boxes)
        self.vertices[4::8, 2] = heights
        self.vertices[5::8, 2] = heights
        self.vertices[6::8, 2] = heights
        self.vertices[7::8, 2] = heights

        # Vectorized updates for vertex colors (apply color scale)
        self.vertex_colours[4::8, 0] = colour_scale_factor  # Red channel
        self.vertex_colours[5::8, 0] = colour_scale_factor  # Red channel
        self.vertex_colours[6::8, 0] = colour_scale_factor  # Red channel
        self.vertex_colours[7::8, 0] = colour_scale_factor  # Red channel

        # Green channel is always 0 (black bottom)
        self.vertex_colours[4::8, 1] = 0
        self.vertex_colours[5::8, 1] = 0
        self.vertex_colours[6::8, 1] = 0
        self.vertex_colours[7::8, 1] = 0

        # Blue channel, inverse of height for a gradient effect
        self.vertex_colours[4::8, 2] = (10 - heights) / 10
        self.vertex_colours[5::8, 2] = (10 - heights) / 10
        self.vertex_colours[6::8, 2] = (10 - heights) / 10
        self.vertex_colours[7::8, 2] = (10 - heights) / 10

        # Set alpha values for visibility
        alpha = np.ones_like(heights)
        self.vertex_colours[4::8, 3] = alpha
        self.vertex_colours[5::8, 3] = alpha
        self.vertex_colours[6::8, 3] = alpha
        self.vertex_colours[7::8, 3] = alpha

        # Set updated mesh data once
        self.box_item.setMeshData(vertexes=self.vertices, vertexColors=self.vertex_colours, faces=self.faces)

    def update_live_power_levels(self, pwr_lvls):
        """Update live power levels and trigger visual update."""
        self.live_power_levels = pwr_lvls
