import sys
import numpy as np
import pyqtgraph as pg
from numpy.fft import fft
from PyQt6.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import QTimer
from rtlsdr import RtlSdr

class SDRHandler:
    def __init__(self, center_freq, sample_rate):
        self.sdr = RtlSdr()
        self.sdr.gain = 'auto'
        self.sdr.center_freq = center_freq
        self.sdr.sample_rate = sample_rate

    def get_samples(self, number_of_samples):
        return self.sdr.read_samples(number_of_samples)

class SpectrumAnalyser(QMainWindow):
    CENTER_FREQUENCY = 98e6
    SAMPLE_RATE = 2e6
    SAMPLE_SIZES = [512, 1024, 2048, 4096, 8192]
    INITIAL_SAMPLE_SIZE = 1024
    FREQ_INCREMENT = 1e6
    MAX_AMPLITUDE = 2.0

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Top Dog Spectrum Analyser")
        self.setGeometry(100, 100, 800, 600)

        self.sdr_handler = SDRHandler(self.CENTER_FREQUENCY, self.SAMPLE_RATE)
        self.sample_size = self.INITIAL_SAMPLE_SIZE

        # Create main layout
        main_layout = QVBoxLayout()

        # 2D plot for spectrum display
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)  # Enable grid lines
        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(main_layout)
        main_layout.addWidget(self.plot_widget)

        self.plot_widget.setTitle("Spectrum Analyser")
        self.plot_widget.setLabel('left', 'Amplitude')
        self.plot_widget.setLabel('bottom', 'Frequency (MHz)')
        self.plot_widget.setYRange(0, self.MAX_AMPLITUDE)

        # Initialize frequency bins and curve
        self.frequency_bins = np.linspace(0, 1, self.sample_size // 2)  # Placeholder initialization
        self.curve = self.plot_widget.plot(pen='g')

        # Control panel layout
        control_panel = QDockWidget("Control Panel", self)
        control_widget = QWidget()
        control_layout = QVBoxLayout()

        # Frequency adjustment buttons
        self.buttonup = QPushButton("Increase Frequency")
        self.buttondown = QPushButton("Decrease Frequency")
        self.buttonup.clicked.connect(self.increase_frequency)
        self.buttondown.clicked.connect(self.decrease_frequency)

        control_layout.addWidget(self.buttonup)
        control_layout.addWidget(self.buttondown)

        # Smoothing control buttons (labels swapped)
        self.smooth_button_up = QPushButton("Decrease Smoothing")
        self.smooth_button_down = QPushButton("Increase Smoothing")
        self.smoothing_factor = 1  # Start with no smoothing

        self.smooth_button_up.clicked.connect(self.decrease_smoothing)
        self.smooth_button_down.clicked.connect(self.increase_smoothing)

        control_layout.addWidget(self.smooth_button_up)
        control_layout.addWidget(self.smooth_button_down)

        # Sample size adjustment buttons
        self.size_button_up = QPushButton("Increase Sample Size")
        self.size_button_down = QPushButton("Decrease Sample Size")

        self.size_button_up.clicked.connect(self.increase_sample_size)
        self.size_button_down.clicked.connect(self.decrease_sample_size)

        control_layout.addWidget(self.size_button_up)
        control_layout.addWidget(self.size_button_down)

        control_widget.setLayout(control_layout)
        control_panel.setWidget(control_widget)

        self.smoothed_power_level = np.zeros(self.sample_size // 2)  # Initialize smoothed values
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(20)  # More frequent updates

        self.update_frequency_bins()  # Initialize frequency bins and x-axis

    def perform_fft(self, samples):
        # Apply a Hamming window to the samples
        window = np.hamming(len(samples))
        windowed_samples = samples * window

        # Compute the FFT
        raw_fft = fft(windowed_samples)
        centred_fft = np.fft.fftshift(raw_fft)
        return np.abs(centred_fft / 100)[:self.sample_size // 2]  # Normalize and take positive frequencies

    def update(self):
        samples = self.sdr_handler.get_samples(self.sample_size)
        power_level = self.perform_fft(samples)

        # Apply smoothing
        self.smoothed_power_level = (self.smoothing_factor * power_level + 
                                      (1 - self.smoothing_factor) * self.smoothed_power_level)

        # Limit the amplitude to MAX_AMPLITUDE
        self.smoothed_power_level = np.clip(self.smoothed_power_level, 0, self.MAX_AMPLITUDE)

        self.curve.setData(self.frequency_bins, self.smoothed_power_level)

    def increase_frequency(self):
        self.sdr_handler.sdr.center_freq += self.FREQ_INCREMENT
        self.update_frequency_bins()
        print(f"New Centre Frequency: {self.sdr_handler.sdr.center_freq / 1e6:.3f} MHz")

    def decrease_frequency(self):
        self.sdr_handler.sdr.center_freq -= self.FREQ_INCREMENT
        self.update_frequency_bins()
        print(f"New Centre Frequency: {self.sdr_handler.sdr.center_freq / 1e6:.3f} MHz")

    def increase_smoothing(self):
        self.smoothing_factor = min(self.smoothing_factor + 0.1, 1)  # Max smoothing factor is 1
        print(f"Smoothing Factor: {self.smoothing_factor:.2f}")

    def decrease_smoothing(self):
        self.smoothing_factor = max(self.smoothing_factor - 0.1, 0)  # Min smoothing factor is 0
        print(f"Smoothing Factor: {self.smoothing_factor:.2f}")

    def increase_sample_size(self):
        current_index = self.SAMPLE_SIZES.index(self.sample_size)
        if current_index < len(self.SAMPLE_SIZES) - 1:
            self.sample_size = self.SAMPLE_SIZES[current_index + 1]
            self.update_frequency_bins()
            print(f"Sample Size: {self.sample_size}")

    def decrease_sample_size(self):
        current_index = self.SAMPLE_SIZES.index(self.sample_size)
        if current_index > 0:
            self.sample_size = self.SAMPLE_SIZES[current_index - 1]
            self.update_frequency_bins()
            print(f"Sample Size: {self.sample_size}")

    def update_frequency_bins(self):
        # Calculate frequency bins based on current center frequency
        freq_range = self.SAMPLE_RATE / 2
        self.frequency_bins = np.linspace(
            self.sdr_handler.sdr.center_freq / 1e6 - freq_range / 1e6,
            self.sdr_handler.sdr.center_freq / 1e6 + freq_range / 1e6,
            self.sample_size // 2
        )  # Center around current frequency
        self.smoothed_power_level = np.zeros(self.sample_size // 2)  # Reset smoothed values
        self.curve.setData([], [])  # Clear the plot

        # Update x-axis ticks
        self.update_x_axis_label()

    def update_x_axis_label(self):
        ticks_count = 10  # Maximum number of ticks
        tick_step = (self.SAMPLE_RATE / 2) / ticks_count / 1e6  # Step in MHz
        ticks = np.linspace(
            self.sdr_handler.sdr.center_freq / 1e6 - self.SAMPLE_RATE / (2 * 1e6),
            self.sdr_handler.sdr.center_freq / 1e6 + self.SAMPLE_RATE / (2 * 1e6),
            ticks_count
        )
        tick_labels = [f"{tick:.3f}" for tick in ticks]  # Format ticks to three decimal places
        self.plot_widget.getAxis('bottom').setTicks([list(zip(ticks, tick_labels))])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectrumAnalyser()
    window.show()
    sys.exit(app.exec())
