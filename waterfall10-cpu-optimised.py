import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from PyQt6 import QtCore
from rtlsdr import RtlSdr
from scipy.fft import fft
from concurrent.futures import ThreadPoolExecutor

class WaterfallPlot:
    def __init__(self):
        self.app = QApplication(sys.argv)
        #self.win = pg.GraphicsLayoutWidget()
        self.win = pg.GraphicsLayoutWidget(show=True)
        self.win.setWindowTitle('Waterfall Display')

        # Configure SDR
        self.sdr = RtlSdr()
        self.sdr.center_freq = 100e6
        self.sdr.sample_rate = 2e6
        self.sdr.gain = 40
        
        # Prepare data
        self.n_frames = 500
        self.n_bins = 2048
        self.waterfall_array = np.zeros((self.n_frames, self.n_bins))

        # Create a plot item
        self.plot_item = self.win.addPlot()
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        # Set plot labels once
        self.plot_item.setLabel('left', 'History (Frames)')
        self.plot_item.setLabel('bottom', 'Frequency Bins')

        # Set up thread pool for FFT computation
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Set up timer to update the display
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)  # Maintain 50 FPS

    def compute_fft(self, samples):
        # Compute FFT using SciPy
        fft_result = np.abs(fft(samples))  # Perform FFT
        return fft_result  # Return to CPU

    def update_plot(self):
        # Read samples
        samples = self.sdr.read_samples(self.n_bins)  # Read 1024 samples
        if samples is not None and len(samples) > 0:
            # Use the thread pool to compute the FFT
            future = self.executor.submit(self.compute_fft, samples)
            future.add_done_callback(self.plot_result)  # Add a callback for when it's done

    def plot_result(self, future):
        try:
            fft_result = future.result()  # Get the result of the computation

            # Shift the waterfall array up and insert the new FFT result
            self.waterfall_array[:-1] = self.waterfall_array[1:]  # Shift
            self.waterfall_array[-1] = fft_result  # Add new data

            # Update the image item with fixed levels
            min_val = 0  # Set this to the minimum expected value
            max_val = 20  # Set this to the maximum expected value (adjust as needed)
            self.image_item.setImage(self.waterfall_array.T, autoLevels=False, levels=(min_val, max_val))
        except Exception as e:
            print(f"Error in FFT computation: {e}")

    def run(self):
        try:
            self.app.exec()
        finally:
            self.sdr.close()  # Ensure SDR is properly closed
            self.executor.shutdown()  # Clean up the thread pool

if __name__ == '__main__':
    waterfall = WaterfallPlot()
    waterfall.run()

