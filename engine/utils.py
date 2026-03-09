import numpy as np

def peak_normalize(audio_data: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    """
    Peak-normalizes the audio data to the target dBFS.
    By default, targets -1.0 dB as per requirements to ensure safe headroom.
    """
    # Ensure float processing
    if audio_data.dtype not in (np.float32, np.float64):
        audio_data = audio_data.astype(np.float32)

    # Convert target dB to linear scale
    target_linear = 10 ** (target_db / 20.0)
    
    # Find current peak magnitude
    current_peak = np.max(np.abs(audio_data))
    
    if current_peak == 0.0:
        return audio_data
        
    # Apply gain to match target peak
    gain = target_linear / current_peak
    normalized_audio = audio_data * gain
    
    return normalized_audio
