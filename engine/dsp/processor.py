import numpy as np
import scipy.signal as signal
import pyloudnorm as pyln

class AudioProcessor:
    """
    Core audio DSP processor using 64-bit float representations for maximum headroom.
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.loudness_analyzer = LoudnessAnalyzer(sample_rate=sample_rate)
        
        # Crossover Frequencies for Multi-Band Exciter
        self.low_mid_freq = 250.0 # Bass to Mids
        self.mid_high_freq = 3000.0 # Mids to Highs

    def process(self, audio_data: np.ndarray, input_gain_db: float = 0.0, air_gain_db: float = 2.0, 
                drive_low_db: float = 0.0, drive_mid_db: float = 0.0, drive_high_db: float = 0.0,
                target_lufs: float = None, exciter_bypass: bool = False,
                mono_freq: float = 150.0, mono_bypass: bool = False,
                stereo_width_db: float = 0.0, saturation_mode: str = "Soft Clip",
                match_eq_fir: np.ndarray = None, match_amount: float = 1.0,
                glue_db: float = 0.0, parallel_comp: float = 0.0) -> np.ndarray:
        """
        Process the incoming audio data array.
        Forces audio_data to np.float64 to maximize headroom during DSP chain.
        """
        # Ensure the correct dtype for processing and ALWAYS create a copy
        # to prevent in-place modification of the source buffer.
        if audio_data.dtype != np.float64:
            audio_data = audio_data.astype(np.float64)
        else:
            audio_data = audio_data.copy()

        # 0. Input Gain Staging
        if input_gain_db != 0.0:
            input_gain_linear = 10 ** (input_gain_db / 20.0)
            audio_data = audio_data * input_gain_linear

        # 1. Matching EQ (Pre-saturation/compression to shape the tone)
        if match_eq_fir is not None and match_amount > 0.0:
            audio_data = self.apply_matching_eq(audio_data, match_eq_fir, match_amount)

        # 2. M/S Encoding
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
            mid = self.linear_phase_eq(mid, air_gain_db=0.0)
            side = self.linear_phase_eq(side, air_gain_db=air_gain_db)

            # Stereo Widening
            if stereo_width_db != 0.0:
                side = self.apply_stereo_width(side, stereo_width_db)

            # --- ASYMMETRIC M/S COMPRESSION (Glue) ---
            if glue_db > 0.0:
                # Mid Channel: Heavy Punch (High ratio, fast-ish attack)
                # We translate glue_db into a threshold. 0-12dB range.
                mid_threshold = -12.0 - glue_db 
                mid = self.compressor_vca(mid, threshold_db=mid_threshold, ratio=4.0, attack_ms=15.0, release_ms=120.0)
                
                # Side Channel: Breathy Air (Low ratio, slow release)
                side_threshold = -18.0 - (glue_db / 2.0)
                side = self.compressor_vca(side, threshold_db=side_threshold, ratio=1.5, attack_ms=30.0, release_ms=250.0)

            # Multi-Band Harmonic Exciter (Saturation)
            if not exciter_bypass:
                mid = self.multiband_drive(mid, drive_low_db, drive_mid_db, drive_high_db, mode=saturation_mode)
                side = self.multiband_drive(side, drive_low_db/2.0, drive_mid_db/2.0, drive_high_db/2.0, mode=saturation_mode)

            # Mono Maker (Specifically targets the Side channel to clear out low-end width)
            if not mono_bypass:
                side = self.mono_maker(side, mono_freq)

            # 3. M/S Decoding
            # Recombining back into L/R with proper gain structure
            dec_L = (mid + side) / 1.414
            dec_R = (mid - side) / 1.414
            
            # Reconstruct the stereo array
            audio_data = np.hstack((dec_L, dec_R))
            
        else:
            # Mono fallback
            audio_data = self.linear_phase_eq(audio_data, air_gain_db)
            if not exciter_bypass:
                audio_data = self.multiband_drive(audio_data, drive_low_db, drive_mid_db, drive_high_db, mode=saturation_mode)
            

        # 3.5 Parallel Compression / NY Compression
        if parallel_comp > 0.0:
            # Create a heavily squashed version of the track
            # Fast attack (2ms), moderate release (80ms), very low threshold (-24dB), high ratio
            crushed = self.compressor_vca(audio_data, threshold_db=-24.0, ratio=8.0, attack_ms=2.0, release_ms=80.0)
            
            # Make up the gain that was lost in the crush 
            # (approx 12-14dB so it sits just below 0)
            crushed *= 10 ** (14.0 / 20.0) 
            
            # Blend it into the original track
            audio_data = (audio_data * (1.0 - (parallel_comp * 0.4))) + (crushed * parallel_comp * 0.8)

        # 4. Loudness Matching (LUFS target)
        if target_lufs is not None:
            self.loudness_analyzer.target_lufs = target_lufs
            audio_data = self.loudness_analyzer.match_target_loudness(audio_data, self.sample_rate)

        # 5. True Peak Limiter
        audio_data = self.limit(audio_data)

        return audio_data

    def process_preview(self, audio_data: np.ndarray, input_gain_db: float = 0.0,
                        air_gain_db: float = 2.0,
                        drive_low_db: float = 0.0, drive_mid_db: float = 0.0,
                        drive_high_db: float = 0.0, target_lufs: float = None,
                        exciter_bypass: bool = False, mono_freq: float = 150.0,
                        mono_bypass: bool = False, stereo_width_db: float = 0.0,
                        saturation_mode: str = "Soft Clip",
                        match_eq_fir: np.ndarray = None, match_amount: float = 1.0,
                        glue_db: float = 0.0, parallel_comp: float = 0.0) -> np.ndarray:
        """
        Fast preview render — identical DSP chain to process() but replaces the
        4x oversampled true-peak limiter with a simple hard clip and skips full
        LUFS normalisation.  Suitable for real-time slider feedback only.
        Export always uses the full process() path.
        """
        if audio_data.dtype != np.float64:
            audio_data = audio_data.astype(np.float64)
        else:
            audio_data = audio_data.copy()

        # 0. Input Gain
        if input_gain_db != 0.0:
            audio_data *= 10 ** (input_gain_db / 20.0)

        # 1. Matching EQ
        if match_eq_fir is not None and match_amount > 0.0:
            audio_data = self.apply_matching_eq(audio_data, match_eq_fir, match_amount)

        # 2. M/S Processing
        is_stereo = (audio_data.ndim > 1 and audio_data.shape[1] > 1)
        if is_stereo:
            L = audio_data[:, 0]
            R = audio_data[:, 1]
            mid  = (L + R) / 1.414
            side = (L - R) / 1.414
            mid  = mid.reshape(-1, 1)
            side = side.reshape(-1, 1)

            mid  = self.linear_phase_eq(mid,  air_gain_db=0.0)
            side = self.linear_phase_eq(side, air_gain_db=air_gain_db)

            if stereo_width_db != 0.0:
                side = self.apply_stereo_width(side, stereo_width_db)

            if glue_db > 0.0:
                mid_threshold  = -12.0 - glue_db
                mid  = self.compressor_vca(mid,  threshold_db=mid_threshold,  ratio=4.0, attack_ms=15.0, release_ms=120.0)
                side_threshold = -18.0 - (glue_db / 2.0)
                side = self.compressor_vca(side, threshold_db=side_threshold, ratio=1.5, attack_ms=30.0, release_ms=250.0)

            if not exciter_bypass:
                mid  = self.multiband_drive(mid,  drive_low_db,       drive_mid_db,       drive_high_db,       mode=saturation_mode)
                side = self.multiband_drive(side, drive_low_db / 2.0, drive_mid_db / 2.0, drive_high_db / 2.0, mode=saturation_mode)

            if not mono_bypass:
                side = self.mono_maker(side, mono_freq)

            dec_L = (mid + side) / 1.414
            dec_R = (mid - side) / 1.414
            audio_data = np.hstack((dec_L, dec_R))
        else:
            audio_data = self.linear_phase_eq(audio_data, air_gain_db)
            if not exciter_bypass:
                audio_data = self.multiband_drive(audio_data, drive_low_db, drive_mid_db, drive_high_db, mode=saturation_mode)

        # 2.5 Parallel Compression / NY Compression
        if parallel_comp > 0.0:
            crushed = self.compressor_vca(audio_data, threshold_db=-24.0, ratio=8.0, attack_ms=2.0, release_ms=80.0)
            crushed *= 10 ** (14.0 / 20.0) 
            audio_data = (audio_data * (1.0 - (parallel_comp * 0.4))) + (crushed * parallel_comp * 0.8)

        # 3. Fast ceiling clip (replaces the expensive 4x oversampled limiter)
        ceiling = 10 ** (-1.0 / 20.0)  # -1 dBFS
        audio_data = np.clip(audio_data, -ceiling, ceiling)

        return audio_data

    def apply_stereo_width(self, side_channel: np.ndarray, width_db: float) -> np.ndarray:
        """
        Enhances or narrows the stereo field by adjusting the Side channel gain.
        Positive values broaden the image; negative values narrow it.
        """
        width_linear = 10 ** (width_db / 20.0)
        return side_channel * width_linear

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

    def multiband_drive(self, audio_data: np.ndarray, low_db: float, mid_db: float, high_db: float, mode: str = "Soft Clip") -> np.ndarray:
        """
        Splits audio into 3 bands and applies independent saturation.
        Uses 4th order Linkwitz-Riley crossovers for perfectly flat summation.
        """
        nyq = self.sample_rate / 2.0
        
        # 1. Split into Low / (Mid+High)
        lp_b, lp_a = signal.butter(4, self.low_mid_freq / nyq, btype='low')
        hp_b, hp_a = signal.butter(4, self.low_mid_freq / nyq, btype='high')
        
        low_band = signal.filtfilt(lp_b, lp_a, audio_data, axis=0)
        mid_high_temp = signal.filtfilt(hp_b, hp_a, audio_data, axis=0)
        
        # 2. Split (Mid+High) into Mid / High
        lp_mid_b, lp_mid_a = signal.butter(4, self.mid_high_freq / nyq, btype='low')
        hp_high_b, hp_high_a = signal.butter(4, self.mid_high_freq / nyq, btype='high')
        
        mid_band = signal.filtfilt(lp_mid_b, lp_mid_a, mid_high_temp, axis=0)
        high_band = signal.filtfilt(hp_high_b, hp_high_a, mid_high_temp, axis=0)
        
        # 3. Apply Saturation to each band
        if mode == "Intelligent":
            low_band = self.apply_saturation(low_band, low_db, "Intelligent_Low")
            mid_band = self.apply_saturation(mid_band, mid_db, "Intelligent_Mid")
            high_band = self.apply_saturation(high_band, high_db, "Intelligent_High")
        else:
            low_band = self.apply_saturation(low_band, low_db, mode)
            mid_band = self.apply_saturation(mid_band, mid_db, mode)
            high_band = self.apply_saturation(high_band, high_db, mode)
        
        # 4. Recombine
        return low_band + mid_band + high_band

    def mono_maker(self, side_channel: np.ndarray, cutoff_freq: float) -> np.ndarray:
        """
        Removes all side energy below the cutoff frequency.
        When M/S is decoded later, this effectively 'monos' the bass.
        """
        nyq = self.sample_rate / 2.0
        # High-pass filter for the side channel (Zero-Phase Butterworth)
        normalized_cutoff = max(20.0, min(1000.0, cutoff_freq)) / nyq
        b, a = signal.butter(4, normalized_cutoff, btype='high')
        
        # We apply filtering strictly to the Side channel
        return signal.filtfilt(b, a, side_channel, axis=0)

    def apply_saturation(self, data: np.ndarray, drive_db: float, mode: str = "Soft Clip") -> np.ndarray:
        """Helper for band saturation."""
        if drive_db <= 0.05: return data # Save CPU
        
        drive_linear = 10 ** (drive_db / 20.0)
        
        if mode == "Tape":
            # Tape Saturation: Custom soft-knee sigmoid with 2nd harmonic richness
            # We use a slightly modified sigmoid that has a 'warmer' transition
            # than standard tanh.
            x = data * drive_linear
            # Sigmoid based saturation: x / (1 + |x|)
            # Adding a tiny constant bias before saturation creates subtle even harmonics (analog feel)
            bias = 0.005
            saturated = (x + bias) / (1.0 + np.abs(x + bias)) - (bias / (1.0 + bias))
            return saturated / (drive_linear * 0.7 + 0.3)
        
        elif mode == "Intelligent_Low":
            # Intelligent Low: Asymmetric Hard Clipping. 
            # This truncates the kick peaks abruptly (low recovery time) while adding weight.
            x = data * drive_linear
            # We clip hard at 0.95 to leave tiny headroom for the final limiter
            return np.clip(x, -0.95, 0.95) / (drive_linear * 0.5 + 0.5)

        elif mode == "Intelligent_High":
            # Intelligent High: Harmonic Shimmer (Exciter).
            # Uses a power-law distortion to add 3rd harmonic brilliance without 'harsh' flat-topping.
            x = data * drive_linear
            # x + x^3 / 3 for even/odd balance shimmer
            return (x + (x**3) / 6.0) / (drive_linear * 0.8 + 0.2)
            
        elif mode == "Intelligent_Mid":
            # Intelligent Mid: Standard Soft-Clip (tanh) for smooth vocal/snare warmth.
            return np.tanh(data * drive_linear) / (drive_linear * 0.8 + 0.2)

        else:
            # Standard Soft Clip (tanh)
            return np.tanh(data * drive_linear) / (drive_linear * 0.8 + 0.2)

    def analyze_spectrum(self, audio_data: np.ndarray, nfft: int = 4096) -> np.ndarray:
        """
        Computes the average power spectrum of the audio using Welch's method.
        Returns the power spectral density (PSD).
        """
        # Mix down to mono for spectral analysis
        if audio_data.ndim > 1 and audio_data.shape[1] > 1:
            data = np.mean(audio_data, axis=1)
        else:
            data = audio_data.flatten()
            
        freqs, psd = signal.welch(data, fs=self.sample_rate, nperseg=nfft)
        return freqs, psd

    def calculate_matching_fir(self, reference_audio: np.ndarray, target_audio: np.ndarray, num_taps: int = 511) -> np.ndarray:
        """
        Calculates a zero-phase FIR matching filter between two audio samples.
        """
        # Determine the number of FFT points
        nfft = 4096
        
        # 1. Analyze spectrums
        freqs, ref_psd = self.analyze_spectrum(reference_audio, nfft=nfft)
        _, tgt_psd = self.analyze_spectrum(target_audio, nfft=nfft)
        
        # 2. Calculate the difference (matching curve) in linear amplitude
        # Add epsilon to avoid division by zero
        eps = 1e-10
        mag_diff = np.sqrt((ref_psd + eps) / (tgt_psd + eps))
        
        # 3. Smooth the matching curve to prevent extreme resonances
        # A simple moving average in the frequency domain
        window_size = 15
        mag_diff_smoothed = signal.medfilt(mag_diff, kernel_size=window_size)
        
        # 4. Design the FIR filter using firwin2
        # firwin2 takes frequencies from 0 to Nyquist (0 to 1.0)
        norm_freqs = freqs / (self.sample_rate / 2.0)
        
        # Ensure we start at 0 and end at 1.0 exactly
        if norm_freqs[-1] < 1.0:
            norm_freqs = np.append(norm_freqs, 1.0)
            mag_diff_smoothed = np.append(mag_diff_smoothed, mag_diff_smoothed[-1])
            
        # Limit the gain to prevent massive blowouts (+12dB max)
        max_gain_linear = 10 ** (12.0 / 20.0)
        mag_diff_smoothed = np.clip(mag_diff_smoothed, 0.1, max_gain_linear)
        
        # Generate FIR coefficients
        fir_coeff = signal.firwin2(num_taps, norm_freqs, mag_diff_smoothed)
        return fir_coeff

    def apply_matching_eq(self, audio_data: np.ndarray, fir_coeff: np.ndarray, mix: float = 1.0) -> np.ndarray:
        """
        Applies the matching EQ FIR filter using zero-phase filtering.
        """
        if mix <= 0.0: return audio_data
        
        # Zero-phase FIR application via filtfilt
        # filtfilt applies the filter twice, so we take the square root of coefficients
        # to maintain intended magnitude, or just apply it once with filtfilt logic.
        # Actually, for Matching EQ, we'll use filtfilt and just accept the doubling
        # or just use convolve if we want a single pass (minimum phase is harder).
        # We'll use filtfilt for its perfect phase response.
        
        # Applying the blend by interpolating the FIR coefficients with an identity filter (a single spike)
        identity = np.zeros_like(fir_coeff)
        identity[len(identity)//2] = 1.0
        
        blended_fir = identity * (1.0 - mix) + fir_coeff * mix
        
        # Apply to each channel
        if audio_data.ndim > 1 and audio_data.shape[1] > 1:
            out_l = signal.filtfilt(blended_fir, [1.0], audio_data[:, 0], axis=0)
            out_r = signal.filtfilt(blended_fir, [1.0], audio_data[:, 1], axis=0)
            return np.vstack((out_l, out_r)).T
        else:
            return signal.filtfilt(blended_fir, [1.0], audio_data, axis=0)

    def compressor_vca(self, audio_data: np.ndarray, threshold_db: float = -12.0, 
                       ratio: float = 2.0, attack_ms: float = 10.0, 
                       release_ms: float = 100.0) -> np.ndarray:
        """
        A high-fidelity VCA-style compressor with a soft knee.
        Uses a vectorised envelope follower (scipy lfilter) for speed.
        """
        if ratio <= 1.0: return audio_data
        
        # Envelope follower coefficients
        att_alpha = 1.0 - np.exp(-1.0 / (self.sample_rate * (attack_ms  / 1000.0)))
        rel_alpha = 1.0 - np.exp(-1.0 / (self.sample_rate * (release_ms / 1000.0)))
        
        # Detect signal level (Rectified)
        det = np.max(np.abs(audio_data), axis=1) if audio_data.ndim > 1 else np.abs(audio_data).flatten()

        # Vectorised two-stage envelope:
        # Pass 1 — attack  (fast smoothing upward)
        b_att = [att_alpha]
        a_att = [1.0, -(1.0 - att_alpha)]
        env_att = signal.lfilter(b_att, a_att, det)

        # Pass 2 — release (slow smoothing of the attack envelope downward)
        b_rel = [rel_alpha]
        a_rel = [1.0, -(1.0 - rel_alpha)]
        # Feed the max of det and the attack envelope to keep peaks, then release
        combined = np.maximum(det, env_att)  # hold peaks
        envelope = signal.lfilter(b_rel, a_rel, combined)

        # Calculate Gain Reduction
        env_db = 20 * np.log10(envelope + 1e-10)
        
        gain_reduction_db = np.zeros_like(env_db)
        over_bool = env_db > threshold_db
        gain_reduction_db[over_bool] = -(1.0 - 1.0 / ratio) * (env_db[over_bool] - threshold_db)
        
        # Soft-Knee Smoothing (3dB knee)
        knee_db = 3.0
        knee_indices = (env_db > (threshold_db - knee_db)) & (env_db < (threshold_db + knee_db))
        gain_reduction_db[knee_indices] *= ((env_db[knee_indices] - (threshold_db - knee_db)) / (2 * knee_db))**2
        
        gain_linear = 10 ** (gain_reduction_db / 20.0)
        
        # Reshape gain to match audio data for broadcasting
        if audio_data.ndim > 1:
            gain_linear = gain_linear.reshape(-1, 1)
            
        return audio_data * gain_linear

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
        # Using lfilter (forward only) ensures an instant duck based on the lookahead, 
        # followed by a smooth release. We use 60Hz for an even smoother release (~16ms).
        b_smooth, a_smooth = signal.butter(1, 60.0 / (self.sample_rate * oversample_factor / 2.0), btype='low')
        smoothed_gain = signal.lfilter(b_smooth, a_smooth, required_gain, axis=0)
        
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
            
        # Ensure we have enough data to analyze (at least 0.1s to be safe)
        if len(audio_data) < int(self.sample_rate * 0.1):
            return -np.inf

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
