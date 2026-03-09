import numpy as np
import scipy.signal as signal
import pyloudnorm as pyln

class AudioProcessor:
    """
    Core audio DSP processor using 64-bit float representations for maximum headroom.
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.loudness_analyzer = LoudnessAnalyzer()

    def process(self, audio_data: np.ndarray, input_gain_db: float = 0.0, air_gain_db: float = 2.0, drive_db: float = 0.0, target_lufs: float = None) -> np.ndarray:
        """
        Process the incoming audio data array.
        Forces audio_data to np.float64 to maximize headroom during DSP chain.
        """
        # Ensure the correct dtype for processing to prevent clipping
        if audio_data.dtype != np.float64:
            audio_data = audio_data.astype(np.float64)

        # 0. Input Gain Staging
        if input_gain_db != 0.0:
            input_gain_linear = 10 ** (input_gain_db / 20.0)
            audio_data = audio_data * input_gain_linear

        # 1. M/S Encoding
        # If stereo, split into Mid/Side
        is_stereo = (audio_data.ndim > 1 and audio_data.shape[1] > 1)
        if is_stereo:
            L = audio_data[:, 0]
            R = audio_data[:, 1]
            
            # Encode M/S with correct power compensation
            mid = (L + R) / 1.414
            side = (L - R) / 1.414
            
            # Reshape back to column vectors for scipy signals
            mid = mid.reshape(-1, 1)
            side = side.reshape(-1, 1)

            # 2. Targeted Processing
            
            # Linear Phase EQ (Air Shelf targeted strictly on the Side Channel for width)
            # We keep the Mid channel 'flat' for EQ, just filtering out extreme sub rumble
            mid = self.linear_phase_eq(mid, air_gain_db=0.0)
            side = self.linear_phase_eq(side, air_gain_db=air_gain_db)

            # Soft-Clipper (Saturation driven hard on Mid for drum/vocal punch, lighter on Side)
            # For the sides, we halve the drive DB to keep the stereo image clean
            mid = self.soft_clip(mid, drive_db)
            side = self.soft_clip(side, drive_db / 2.0)

            # 3. M/S Decoding
            # Recombining back into L/R with proper gain structure
            dec_L = (mid + side) / 1.414
            dec_R = (mid - side) / 1.414
            
            # Reconstruct the stereo array
            audio_data = np.hstack((dec_L, dec_R))
            
        else:
            # Mono fallback (just process the single channel normally without M/S)
            audio_data = self.linear_phase_eq(audio_data, air_gain_db)
            audio_data = self.soft_clip(audio_data, drive_db)
            

        # 4. Loudness Matching (LUFS target)
        if target_lufs is not None:
            self.loudness_analyzer.target_lufs = target_lufs
            # pyln requires (samples, channels) so we ensure correct shaped wrapper later, but process receives mono
            # We skip loudness inside real-time stereo buffer to save CPU cycle unless it's full render
            pass # Usually loudness is applied across full file, wait till export

        # 5. True Peak Limiter
        audio_data = self.limit(audio_data)

        return audio_data

    def calculate_rms(self, audio_data: np.ndarray) -> float:
        """
        Calculates the Root Mean Square (RMS) level of the signal in dBFS.
        Useful for visualizing headroom before saturation stages.
        """
        # Avoid log(0)
        if np.all(audio_data == 0):
            return -np.inf
            
        rms_linear = np.sqrt(np.mean(np.square(audio_data)))
        rms_db = 20 * np.log10(rms_linear)
        return rms_db

    def linear_phase_eq(self, audio_data: np.ndarray, air_gain_db: float = 2.0) -> np.ndarray:
        """
        Applies a Linear Phase EQ (zero-phase filtering via filtfilt).
        - High-pass at 30Hz to remove rumble.
        - 'Air' shelf at 12kHz.
        """
        nyquist = self.sample_rate / 2.0

        # --- High-pass filter (30Hz) ---
        hp_freq = 30.0 / nyquist
        # 4th order high-pass butterworth
        b_hp, a_hp = signal.butter(4, hp_freq, btype='high')
        
        # Zero-phase forward-backward filtering
        audio_data = signal.filtfilt(b_hp, a_hp, audio_data, axis=0)

        # --- High-shelf 'Air' filter (12kHz) ---
        # Since filtfilt gives zero phase shift, we can create a linear-phase high-shelf
        # by isolating the high frequencies and mixing them back into the signal.
        air_freq = 12000.0 / nyquist
        if air_freq < 1.0: # Ensure valid frequency for sample rate
            b_air, a_air = signal.butter(2, air_freq, btype='high')
            air_signal = signal.filtfilt(b_air, a_air, audio_data, axis=0)
            
            # Gain staging: Apply user-defined boost to the air band. 
            if air_gain_db != 0.0:
                air_gain_linear = 10 ** (air_gain_db / 20.0) - 1.0 
                audio_data = audio_data + (air_signal * air_gain_linear)

        return audio_data

    def soft_clip(self, audio_data: np.ndarray, drive_db: float = 0.0) -> np.ndarray:
        """
        Soft-clipper using a tangent (tanh) function.
        Avoids harsh digital clipping.
        """
        if drive_db != 0.0:
            drive_linear = 10 ** (drive_db / 20.0)
            audio_data = audio_data * drive_linear
            
        # Apply tanh for smooth saturation / soft clipping
        clipped_data = np.tanh(audio_data)
        
        return clipped_data

    def limit(self, audio_data: np.ndarray, ceiling_db: float = -1.0, lookahead_ms: float = 5.0) -> np.ndarray:
        """
        True Peak Limiter using 4x oversampling for ISP detection.
        Applies a look-ahead for smooth gain reduction.
        """
        ceiling_linear = 10 ** (ceiling_db / 20.0)
        oversample_factor = 4
        
        # 1. 4x Oversampling for inter-sample peak detection
        oversampled_data = signal.resample_poly(audio_data, oversample_factor, 1, axis=0)
        
        # 2. Look-ahead calculation
        lookahead_samples = int((lookahead_ms / 1000.0) * self.sample_rate * oversample_factor)
        
        abs_data = np.abs(oversampled_data)
        
        # Shift the signal to peek ahead (zero-padded at the end)
        if lookahead_samples > 0:
            pad_width = [(0, lookahead_samples)] + [(0, 0)] * (oversampled_data.ndim - 1)
            padded_abs = np.pad(abs_data, pad_width, mode='constant')
            lookahead_abs = padded_abs[lookahead_samples:]
        else:
            lookahead_abs = abs_data
            
        # Required gain multiplier to stay under ceiling
        required_gain = np.where(lookahead_abs > ceiling_linear, ceiling_linear / lookahead_abs, 1.0)
        
        # Smooth out gain reduction (basic low-pass representation of attack/release times)
        b_smooth, a_smooth = signal.butter(1, 100.0 / (self.sample_rate * oversample_factor / 2.0), btype='low')
        smoothed_gain = signal.filtfilt(b_smooth, a_smooth, required_gain, axis=0)
        
        # Ensure we only reduce gain, never boost
        smoothed_gain = np.clip(smoothed_gain, 0.0, 1.0)
        
        # Apply gain reduction
        limited_oversampled = oversampled_data * smoothed_gain
        
        # 3. Downsample back to original rate
        limited_data = signal.resample_poly(limited_oversampled, 1, oversample_factor, axis=0)
        
        # Hard-clip the true mathematical limit to catch any interpolation overshoots
        limited_data = np.clip(limited_data, -ceiling_linear, ceiling_linear)
        
        return limited_data


class LoudnessAnalyzer:
    """
    Standard-compliant LUFS meter using ITU-R BS.1770-4.
    """
    def __init__(self, target_lufs: float = -14.0, sample_rate: int = 44100):
        self.target_lufs = target_lufs
        self.sample_rate = sample_rate
        self._meter = pyln.Meter(sample_rate)

    def analyze(self, audio_data: np.ndarray, sample_rate: int = None) -> float:
        """
        Returns the LUFS of the audio.
        """
        if sample_rate and sample_rate != self.sample_rate:
            self.sample_rate = sample_rate
            self._meter = pyln.Meter(sample_rate)
            
        # pyloudnorm requires (samples, channels)
        # If passed mono (samples,), reshape to (samples, 1)
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)
            
        # Integrated loudness calculation
        try:
            return self._meter.integrated_loudness(audio_data)
        except:
            return -np.inf

    def match_target_loudness(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Normalizes the audio to the target LUFS (e.g., -14 for streaming).
        """
        current_lufs = self.analyze(audio_data, sample_rate)
        # Use pyloudnorm's built-in normalization for better precision
        return pyln.normalize.loudness(audio_data, current_lufs, self.target_lufs)
