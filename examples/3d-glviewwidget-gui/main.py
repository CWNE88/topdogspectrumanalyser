import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph import opengl as gl
from PyQt6 import QtWidgets, uic
from visualiser import Visualiser

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the UI file
        uic.loadUi('topdogspectrumanalysermainwindow.ui', self)

        # Create a PyQtGraph GLViewWidget
        self.plot_widget = gl.GLViewWidget()
        self.plot_widget.setMinimumSize(800, 600)  # Set a minimum size for the widget

        # Find the placeholder QWidget
        placeholder_widget = self.findChild(QtWidgets.QWidget, 'graphical_display')

        if placeholder_widget is not None:
            # Get the existing layout of the placeholder
            layout = placeholder_widget.layout()
            if layout is None:
                # If there is no layout, create one
                layout = QtWidgets.QVBoxLayout(placeholder_widget)
            else:
                # Clear existing layout items
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

            # Add the GLViewWidget to the layout
            layout.addWidget(self.plot_widget)

            # Initialize Visualiser with the plot_widget
            self.visualiser = Visualiser(self.plot_widget)

            # Start the animation
            self.visualiser.animation()
            print ("animation started")
        else:
            print("Error: Placeholder widget not found.")
        
        

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
