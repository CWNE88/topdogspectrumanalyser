import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from pyqtgraph.opengl import GLViewWidget, MeshData, GLMeshItem
import numpy as np
from PyQt6 import QtWidgets, QtCore
from stl import mesh

class Logo(QtWidgets.QWidget):
    def __init__(self, stl_file="logo.stl"):
        super().__init__()
        self.widget = GLViewWidget()
        self.widget.opts['elevation'] = 0
        self.widget.opts['disableMouse'] = True

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        # Load and process the STL mesh
        self.stl_mesh = mesh.Mesh.from_file(stl_file)
        self.points = self.stl_mesh.points.reshape(-1, 3)

        # Swap y and z axes and scale y-axis
        self.points[:, [1, 2]] = self.points[:, [2, 1]]
        self.points[:, 1] /= 2

        # Define faces for the mesh
        self.faces = np.arange(self.points.shape[0]).reshape(-1, 3)

        # Create MeshData and GLMeshItem
        self.mesh_data = MeshData(vertexes=self.points, faces=self.faces)
        self.mesh = GLMeshItem(
            meshdata=self.mesh_data,
            color=(88 / 255, 160 / 255, 221 / 255, 255 / 255),
            smooth=False,
            drawFaces=True,
            drawEdges=False
        )
        self.widget.addItem(self.mesh)


        # Setup rotation update

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_rotation)
        #self.timer.start(20)
        self.widget.show()


    def update_rotation(self):
        azimuth = self.widget.opts['azimuth']
        self.widget.setCameraPosition(azimuth=azimuth - 1)

    def show(self):
        self.widget.show()
 