from . import SampleDataSource
import numpy as np
import sounddevice as sd
import threading

class AudioDataSource(SampleDataSource):

    @staticmethod
    def find_devices():
        pass

    def __init__(self, sample_rate=44100, sample_size=1024):
        super().__init__(centre_freq=0, sample_rate=sample_rate, gain=1.0)

        self.sampling_rate = sample_rate
        self.sample_size = sample_size
        self.samples = np.zeros((sample_size,))  # Initialize samples
        self.lock = threading.Lock()  # Lock for thread safety
        self.stream = sd.InputStream(samplerate=self.sampling_rate, channels=1,
                                      blocksize=self.sample_size, callback=self.audio_callback)
        self.stream.start()

        self.window = np.hanning(self.sample_size)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        with self.lock:  # Ensure thread safety
            self.samples = indata[:, 0]  # Use the first channel

    def read_samples(self, sample_size):
        with self.lock:  # Ensure thread safety when accessing samples
            return self.samples.copy()  # Return a copy to avoid issues with concurrent modification

    def cleanup(self):
        self.stream.stop()
        self.stream.close()
