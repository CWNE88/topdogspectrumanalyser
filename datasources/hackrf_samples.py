import numpy as np
import logging
import threading
import queue
import time
from typing import Optional, Tuple
try:
    from hackrf import HackRF
    _HACKRF_AVAILABLE = True
except (ImportError, OSError):
    _HACKRF_AVAILABLE = False
    HackRF = None
from utils.frequency_selector import FrequencyRange
from utils.constants import DSPConstants
from .base import SampleDataSource

logger = logging.getLogger(__name__)


class HackrfSamplesDataSource(SampleDataSource):
    """
    High-performance HackRF sample source using buffered streaming.

    Optimized for high sample rates with minimal GIL contention.
    Thread-safe with proper synchronization.
    """

    READ_CHUNK = 65536     # 64 K samples ≈ 3.3 ms @ 20 MSPS
    MAX_QUEUE_SIZE = 4     # 4 × 3.3 ms = ~13 ms max latency
    CONSUME_TIMEOUT = 0.5  # Max time to wait for samples
    STOP_TIMEOUT = 2.0    # Timeout for thread join
    _DC_ALPHA = 1.0       # DC tracking smoothing factor; smaller = slower, more stable

    def __init__(self, sample_rate: int, centre_freq: int):
        super().__init__(sample_rate, centre_freq)

        self.num_samples = 1024
        self.device = None
        self.running = False
        self._stop_requested = threading.Event()

        self.last_sample_rate = sample_rate

        self.lna_gain = 16
        self.vga_gain = 20
        self.amplifier = True
        self.use_psd = False

        # Thread synchronization
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        self._device_lock = threading.RLock()  # Separate lock for device operations

        # High-performance queue-based buffering
        self._sample_queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._reader_thread = None

        # FFT resources
        self._window = None
        self._freq_bins = None

        # Slow DC tracker (prevents flicker)
        self._dc_estimate = 0.0 + 0.0j

        # Sample reservoir for fast consumption
        self._reservoir = np.array([], dtype=np.complex64)

        # Last successfully computed power frame — returned instead of zeros on underrun
        self._last_good_power: Optional[np.ndarray] = None

        # Performance monitoring
        self._stats = {
            'samples_dropped': 0,
            'queue_overflows': 0,
            'read_errors': 0,
            'last_read_time': 0
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, frequency: FrequencyRange = None):
        if not _HACKRF_AVAILABLE:
            raise RuntimeError("HackRF library (libhackrf) not available on this system")
        with self._lock:
            if frequency:
                self.centre_freq = int(frequency.centre)
                self.sample_rate = int(frequency.span)

            if self.running:
                logger.warning("Already running")
                return

            self._stop_requested.clear()
            self._setup_device()
            self._allocate_fft_resources()

            # Clear queue and reservoir
            self._flush_buffers()

            self.running = True
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                daemon=True,
                name="HackRF-Reader"
            )
            self._reader_thread.start()
            logger.info("HackRF data source started")

    def _setup_device(self):
        """Setup HackRF device with current settings."""
        with self._device_lock:
            try:
                self.device = HackRF()
                self.device.set_sample_rate(self.sample_rate)
                self.device.set_freq(self.centre_freq)
                self.device.set_lna_gain(self.lna_gain)
                self.device.set_vga_gain(self.vga_gain)

                if self.amplifier:
                    self.device.enable_amp()
                else:
                    self.device.disable_amp()

                logger.debug(f"Device setup: {self.sample_rate/1e6:.1f} MSPS, "
                           f"{self.centre_freq/1e6:.2f} MHz")
                
            except Exception as e:
                logger.error(f"Failed to setup HackRF device: {e}")
                if self.device:
                    try:
                        self.device.close()
                    except:
                        pass
                    self.device = None
                raise

    def stop(self):
        with self._lock:
            if not self.running:
                return

            self.running = False
            self._stop_requested.set()

            # Wait for reader thread to exit
            if self._reader_thread and self._reader_thread.is_alive():
                self._reader_thread.join(timeout=self.STOP_TIMEOUT)
                if self._reader_thread.is_alive():
                    # Thread is stuck in read_samples() — force-close the device
                    # so the USB transfer fails and the thread can exit.
                    logger.warning("Reader thread stuck; force-closing device to unblock it")
                    try:
                        if self.device:
                            self.device.close()
                    except Exception:
                        pass
                    self._reader_thread.join(timeout=1.0)
                    if self._reader_thread.is_alive():
                        logger.error("Reader thread could not be stopped")
                self._reader_thread = None

            # Clean up device
            self._cleanup_device()

            # Clear buffers
            self._flush_buffers()
            
            logger.info("HackRF data source stopped")

    def _cleanup_device(self):
        """Safely cleanup HackRF device."""
        with self._device_lock:
            if self.device:
                try:
                    self.device.close()
                except Exception as e:
                    logger.debug(f"Error closing device: {e}")
                finally:
                    self.device = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.running

    # ------------------------------------------------------------------
    # Internal streaming (OPTIMIZED)
    # ------------------------------------------------------------------

    def _reader_loop(self):
        """Continuously read large blocks from HackRF and queue them."""
        logger.debug("HackRF reader thread started")
        
        read_errors = 0
        max_consecutive_errors = 5

        while self.running and not self._stop_requested.is_set():
            try:
                # Check if device is still valid
                with self._device_lock:
                    if not self.device:
                        logger.error("Device not available in reader loop")
                        break
                    
                    # This should release GIL during USB transfer
                    samples = self.device.read_samples(self.READ_CHUNK)
                
                if samples is None:
                    logger.warning("Received None samples from device")
                    continue
                
                if len(samples) == 0:
                    logger.warning("Received empty samples from device")
                    continue

                read_errors = 0  # Reset error counter on successful read
                self._stats['last_read_time'] = time.time()

                # Non-blocking put with controlled dropping
                try:
                    self._sample_queue.put(samples, block=False)
                except queue.Full:
                    # Queue is full, try to make room
                    try:
                        # Drop oldest chunk to make room for newest
                        dropped = self._sample_queue.get_nowait()
                        self._sample_queue.put(samples, block=False)
                        self._stats['samples_dropped'] += len(dropped)
                        self._stats['queue_overflows'] += 1
                        logger.debug(f"Queue overflow #{self._stats['queue_overflows']} (expected — keeping newest)")
                            
                    except (queue.Empty, queue.Full):
                        # Couldn't make room, drop this chunk
                        self._stats['samples_dropped'] += len(samples)
                        if self._stats['samples_dropped'] % (10 * self.READ_CHUNK) == 0:
                            logger.warning(f"Dropped {self._stats['samples_dropped']} samples total")

            except Exception as e:
                read_errors += 1
                self._stats['read_errors'] += 1
                
                if read_errors >= max_consecutive_errors:
                    logger.error(f"{max_consecutive_errors} consecutive read errors: {e}")
                    with self._lock:
                        self.running = False
                    break
                    
                logger.debug(f"Read error #{read_errors}: {e}")
                time.sleep(0.01)  # Brief pause on error

        logger.debug("HackRF reader thread stopped")

    def _consume_samples(self, count: int) -> np.ndarray:
        """Pull exactly `count` samples, always using the freshest available data.

        Drains the queue on every call so the display is never working from a
        chunk that was captured seconds ago.  Takes the *last* count samples of
        the newest chunk (furthest from the USB transfer boundary) rather than
        the first, which avoids a known lower-amplitude artifact at the very
        start of each bulk transfer.
        Returns None on timeout so the caller can substitute the last good frame.
        """
        if count <= 0:
            return np.array([], dtype=np.complex64)

        # Non-blocking drain: replace reservoir with the newest chunk if available.
        # Keeps existing reservoir untouched when the queue is empty.
        fresh = None
        while True:
            try:
                fresh = self._sample_queue.get_nowait()
            except queue.Empty:
                break
        if fresh is not None:
            self._reservoir = fresh

        # Take the last `count` samples — end of chunk is most recently captured
        # and clear of any USB transfer-start artifact.  Keep the remainder as
        # fallback so low sample rates don't stall waiting for the next chunk.
        if len(self._reservoir) >= count:
            result = self._reservoir[-count:]
            self._reservoir = self._reservoir[:-count]
            return result

        # Reservoir insufficient and queue was empty — wait briefly for reader.
        start_time = time.time()
        while len(self._reservoir) < count:
            if time.time() - start_time > self.CONSUME_TIMEOUT:
                logger.debug(f"Sample timeout: {len(self._reservoir)}/{count} available")
                return None
            try:
                chunk = self._sample_queue.get(timeout=0.01)
                while True:
                    try:
                        chunk = self._sample_queue.get_nowait()
                    except queue.Empty:
                        break
                self._reservoir = chunk
            except queue.Empty:
                continue

        result = self._reservoir[-count:]
        self._reservoir = self._reservoir[:-count]
        return result

    # ------------------------------------------------------------------
    # FFT helpers
    # ------------------------------------------------------------------

    def _allocate_fft_resources(self):
        """Allocate FFT resources with current settings."""
        # Hann window, normalized to preserve power
        window = np.hanning(self.num_samples).astype(np.float32)
        window /= np.sqrt(np.mean(window ** 2))
        self._window = window

        self._freq_bins = (
            np.fft.fftshift(
                np.fft.fftfreq(self.num_samples, 1 / self.sample_rate)
            )
            + self.centre_freq
        )
        logger.debug(f"Allocated FFT resources for {self.num_samples} samples")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_samples(self) -> np.ndarray:
        """Get raw complex samples."""
        with self._lock:
            if not self.running:
                return np.zeros(self.num_samples, dtype=np.complex64)

            samples = self._consume_samples(self.num_samples)
            return samples if samples is not None else np.zeros(self.num_samples, dtype=np.complex64)

    def get_power_levels(self) -> tuple[np.ndarray, np.ndarray]:
        """Get power spectrum and frequency bins."""
        with self._lock:
            if not self.running or self._freq_bins is None:
                # Return zeros with current freq bins (or placeholder if not allocated)
                if self._freq_bins is not None:
                    return np.zeros(self.num_samples), self._freq_bins
                else:
                    return np.zeros(self.num_samples), np.zeros(self.num_samples)

            samples = self._consume_samples(self.num_samples)

            if samples is None or np.mean(np.abs(samples) ** 2) < 1e-20:
                # Underrun or silence — hold the last good frame rather than dipping to noise floor
                if self._last_good_power is not None:
                    return self._last_good_power, self._freq_bins
                return np.zeros(self.num_samples), self._freq_bins

            self._store_raw(samples)

            # Slow DC removal (stable, no flicker)
            mean = np.mean(samples)
            self._dc_estimate = (
                (1.0 - self._DC_ALPHA) * self._dc_estimate
                + self._DC_ALPHA * mean
            )
            samples -= self._dc_estimate

            # Windowing
            samples *= self._window

            spectrum = np.fft.fftshift(np.fft.fft(samples))

            magnitude = np.abs(spectrum)

            if self.use_psd:
                psd = (magnitude ** 2) / (self.sample_rate * self.num_samples)
                psd = self._averager.process(psd)
                power_db = 10 * np.log10(psd + DSPConstants.LOG_FLOOR)
            elif self._averager.is_active:
                power = magnitude ** 2
                power = self._averager.process(power)
                power_db = 10 * np.log10(power + DSPConstants.POWER_LOG_FLOOR)
            else:
                power_db = 20 * np.log10(magnitude + DSPConstants.LOG_FLOOR)

            self._last_good_power = power_db
            return power_db, self._freq_bins

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_num_samples(self, num_samples: int):
        """Set number of samples for FFT."""
        if num_samples <= 0:
            raise ValueError("num_samples must be positive")

        with self._lock:
            if num_samples == self.num_samples:
                return

            self.num_samples = num_samples
            self._averager.reset()
            if self.running:
                self._allocate_fft_resources()
            logger.info(f"FFT size set to {num_samples} samples")

    @property
    def sample_count(self) -> int:
        """Get the number of samples used for FFT."""
        with self._lock:
            return self.num_samples

    @sample_count.setter
    def sample_count(self, value: int):
        """Set the number of samples used for FFT."""
        self.set_num_samples(value)

    def read_samples_only(self) -> np.ndarray | None:
        with self._lock:
            if not self.running:
                return None
            samples = self._consume_samples(self.num_samples)
            if samples is not None:
                self._store_raw(samples)
            return samples

    def set_psd_mode(self, enabled: bool):
        """Enable/disable PSD mode."""
        with self._lock:
            if self.use_psd != enabled:
                self.use_psd = enabled
                logger.info(f"PSD mode {'enabled' if enabled else 'disabled'}")

    # ------------------------------------------------------------------
    # Frequency updates
    # ------------------------------------------------------------------

    def _flush_buffers(self):
        """Clear the sample queue and reservoir to remove stale data."""
        # Clear the queue of all old samples
        while not self._sample_queue.empty():
            try:
                self._sample_queue.get_nowait()
            except queue.Empty:
                break

        # Clear the reservoir
        self._reservoir = np.array([], dtype=np.complex64)
        
        # Reset DC estimate when buffers are cleared
        self._dc_estimate = 0.0 + 0.0j

        # Invalidate cached power frame — freq bins may change after a flush
        self._last_good_power = None

        logger.debug("Flushed sample buffers")

    def update_centre_frequency(self, centre_freq: float):
        """Update centre frequency with proper synchronization."""
        centre_freq = int(centre_freq)
        
        with self._lock:
            if centre_freq == self.centre_freq:
                return

            self.centre_freq = centre_freq

            # Only update hardware if running
            if self.running:
                was_running = True
                
                # Save state for restart
                saved_dc = self._dc_estimate
                saved_lna = self.lna_gain
                saved_vga = self.vga_gain
                saved_amp = self.amplifier
                
                # Stop current operation
                self._stop_internal()
                
                # Restore settings
                self._dc_estimate = saved_dc
                self.lna_gain = saved_lna
                self.vga_gain = saved_vga
                self.amplifier = saved_amp
                
                # Start with new frequency
                self._start_internal()
                
                logger.info(f"Updated centre frequency to {centre_freq/1e6:.2f} MHz")
            else:
                logger.debug(f"Stored centre frequency {centre_freq/1e6:.2f} MHz (will apply on next start)")

    def update_sample_rate(self, sample_rate: float):
        """Update sample rate with proper synchronization."""
        sample_rate = int(sample_rate)

        with self._lock:
            if sample_rate == self.last_sample_rate:
                return

            was_running = self.running
            
            if was_running:
                # Save state for restart
                saved_dc = self._dc_estimate
                
                # Stop current operation
                self._stop_internal()

            # Update rate
            self.sample_rate = sample_rate
            self.last_sample_rate = sample_rate
            
            if was_running:
                # Restore DC estimate
                self._dc_estimate = saved_dc
                
                # Start with new rate
                self._start_internal()
                
                logger.info(f"Updated sample rate to {sample_rate/1e6:.1f} MSPS")

    def update_frequency(self, sample_rate: float, centre_freq: float):
        """Update both sample rate and centre frequency efficiently."""
        sample_rate = int(sample_rate)
        centre_freq = int(centre_freq)
        
        with self._lock:
            rate_changed = (sample_rate != self.last_sample_rate)
            freq_changed = (centre_freq != self.centre_freq)
            
            if not rate_changed and not freq_changed:
                return

            was_running = self.running
            
            if was_running:
                # Save state for restart
                saved_dc = self._dc_estimate
                
                # Stop current operation
                self._stop_internal()

            # Update both values
            if rate_changed:
                self.sample_rate = sample_rate
                self.last_sample_rate = sample_rate
                
            if freq_changed:
                self.centre_freq = centre_freq
            
            if was_running:
                # Restore DC estimate
                self._dc_estimate = saved_dc
                
                # Start with new settings
                self._start_internal()
                
                logger.info(f"Updated to {sample_rate/1e6:.1f} MSPS, {centre_freq/1e6:.2f} MHz")

    # ------------------------------------------------------------------
    # Internal start/stop for updates
    # ------------------------------------------------------------------

    def _stop_internal(self):
        """Internal stop that preserves state."""
        if not self.running:
            return
            
        self.running = False
        self._stop_requested.set()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
            if self._reader_thread.is_alive():
                logger.warning("Reader thread did not exit during update")
            self._reader_thread = None

        # Don't close device, just stop streaming
        # Device will be reused in _start_internal
        self._flush_buffers()

    def _start_internal(self):
        """Internal start that uses existing device."""
        if self.running:
            return
            
        self._stop_requested.clear()
        
        # Reconfigure device if it exists
        with self._device_lock:
            if self.device:
                try:
                    self.device.set_sample_rate(self.sample_rate)
                    self.device.set_freq(self.centre_freq)
                    self.device.set_lna_gain(self.lna_gain)
                    self.device.set_vga_gain(self.vga_gain)
                    
                    if self.amplifier:
                        self.device.enable_amp()
                    else:
                        self.device.disable_amp()
                        
                except Exception as e:
                    logger.error(f"Failed to reconfigure device: {e}")
                    # Try to recover by creating new device
                    self._cleanup_device()
                    self._setup_device()
            else:
                # Create new device
                self._setup_device()
        
        self._allocate_fft_resources()
        self._flush_buffers()
        
        self.running = True
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="HackRF-Reader"
        )
        self._reader_thread.start()

    # ------------------------------------------------------------------
    # Gain control
    # ------------------------------------------------------------------

    def set_gains(self, lna_gain: Optional[int] = None, vga_gain: Optional[int] = None):
        """Set LNA and/or VGA gains."""
        with self._lock:
            if lna_gain is not None:
                if 0 <= lna_gain <= 40:
                    self.lna_gain = lna_gain
                else:
                    raise ValueError(f"LNA gain must be between 0 and 40, got {lna_gain}")
                
            if vga_gain is not None:
                if 0 <= vga_gain <= 62:
                    self.vga_gain = vga_gain
                else:
                    raise ValueError(f"VGA gain must be between 0 and 62, got {vga_gain}")
            
            # Apply if running
            if self.running and self.device:
                with self._device_lock:
                    if lna_gain is not None:
                        self.device.set_lna_gain(self.lna_gain)
                    if vga_gain is not None:
                        self.device.set_vga_gain(self.vga_gain)
                
                logger.info(f"Gains set to LNA={self.lna_gain}dB, VGA={self.vga_gain}dB")

    def set_dc_alpha(self, alpha: float) -> None:
        """Set the DC tracking smoothing factor (0.01 slow … 1.0 instant)."""
        self._DC_ALPHA = max(0.0, min(1.0, float(alpha)))
        logger.info(f"DC alpha set to {self._DC_ALPHA}")

    def set_amplifier(self, enabled: bool):
        """Enable/disable RF amplifier."""
        with self._lock:
            self.amplifier = enabled
            if self.running and self.device:
                with self._device_lock:
                    if enabled:
                        self.device.enable_amp()
                    else:
                        self.device.disable_amp()
                logger.info(f"RF amplifier {'enabled' if enabled else 'disabled'}")

    @property
    def amp_enabled(self) -> bool:
        return self.amplifier

    # ------------------------------------------------------------------
    # Statistics and monitoring
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get performance statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                'queue_size': self._sample_queue.qsize(),
                'reservoir_size': len(self._reservoir),
                'queue_capacity': self._sample_queue.maxsize,
                'is_running': self.running,
                'thread_alive': self._reader_thread.is_alive() if self._reader_thread else False,
                'num_samples': self.num_samples,
                'sample_rate': self.sample_rate,
                'centre_freq': self.centre_freq,
                'dc_estimate_mag': np.abs(self._dc_estimate),
                'dc_estimate_phase': np.angle(self._dc_estimate),
                'timestamp': time.time()
            })
            return stats

    def reset_stats(self):
        """Reset performance statistics."""
        with self._lock:
            self._stats = {
                'samples_dropped': 0,
                'queue_overflows': 0,
                'read_errors': 0,
                'last_read_time': 0
            }

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def __del__(self):
        """Ensure cleanup on destruction."""
        try:
            if self.running:
                self.stop()
        except:
            pass  # Avoid exceptions in destructor