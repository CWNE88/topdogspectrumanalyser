from . import SampleDataSource
import numpy as np
import sounddevice as sd

class AudioDataSource(SampleDataSource):

    @staticmethod
    def find_devices():
        pass

    def __init__(self, sample_rate=44100, sample_size=1024):
        #super().__init__()
        super().__init__(centre_freq=0, sample_rate=sample_rate, gain=1.0)


        self.sampling_rate = sample_rate
        self.sample_size = sample_size
        self.stream = sd.InputStream(samplerate=self.sampling_rate, channels=1, blocksize=self.sample_size, callback=self.audio_callback)
        self.stream.start()

        self.window=np.hanning(self.sample_size)

        
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.samples = indata[:, 0]  # Use the first channel


    def read_samples(self, sample_size):
        return self.samples 

    def cleanup(self):
        self.sdr.close()