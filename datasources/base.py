class SweepDataSource:
    def start(self, frequency=None):
        pass

    def stop(self):
        pass

    def get_data(self):
        pass

    def get_number_of_points(self):
        pass

class SampleDataSource:
    def __init__(self, sample_rate=None, centre_freq=None):
        self.sample_rate = sample_rate
        self.centre_freq = centre_freq

    def start(self, frequency=None):
        pass

    def stop(self):
        pass

    def get_power_levels(self):
        pass

    def set_window_type(self, window_type):
        pass

    def set_fft_size(self, fft_size):
        pass

    def update_frequency(self, sample_rate, centre_freq):
        pass

    def update_center_frequency(self, centre_freq):
        pass
