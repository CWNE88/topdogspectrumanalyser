from . import DataSource
from hackrf import *

class HackRFDataSource(DataSource):
    @staticmethod
    def find_devices():
        devices = hackrf_device_list()
        return devices

    def __init__(self, centre_frequency=98e6, sample_rate=20e6, amplifier=True, lna_gain=20, vga_gain=20):
        # self.hackrf = HackRF()
        # self.hackrf.center_freq = centre_frequency
        # self.hackrf.sample_rate = sample_rate
        # self.hackrf.amplifier_on = amplifier
        # self.hackrf.lna_gain = lna_gain
        # self.hackrf.vga_gain = vga_gain
        # self.sample_rate = sample_rate
        self.samples = []

        self.device = HackRF()
        self.device.set_sample_rate(sample_rate)

        self.sample_rate = sample_rate # todo: fix this shit
            
        if amplifier:
            self.device.enable_amp()
        
        self.device.set_lna_gain(lna_gain)
        self.device.set_vga_gain(vga_gain)
        self.device.set_freq(centre_frequency)

    def read_samples(self, sample_size):
        self.samples = self.device.read_samples(sample_size)
        return self.samples

    def cleanup(self):
        self.device.close()