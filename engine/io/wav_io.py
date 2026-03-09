import numpy as np
import scipy.io.wavfile as wavfile

def read_wav(file_path: str) -> tuple[int, np.ndarray]:
    """
    Reads a WAV file and returns (sample_rate, audio_data) as np.float64.
    Normalizes integers to [-1.0, 1.0] float range.
    """
    sr, data = wavfile.read(file_path)
    
    # Convert to float64 and normalize if integer
    if data.dtype == np.int16:
        data = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float64) / 2147483648.0
    elif data.dtype == np.float32:
        data = data.astype(np.float64)
        
    return sr, data

def write_wav(file_path: str, sample_rate: int, audio_data: np.ndarray):
    """
    Writes a WAV file safely from np.float64 format.
    Saves as 32-bit floating point WAV.
    """
    # Ensure it's downcast to float32 for standard 32-bit float WAV export
    export_data = audio_data.astype(np.float32)
    wavfile.write(file_path, sample_rate, export_data)
