import numpy as np
import soundfile as sf
import os

def read_audio(file_path: str) -> tuple[int, np.ndarray]:
    """
    Reads an audio file (WAV, FLAC, MP3, etc.) and returns (sample_rate, audio_data) as np.float64.
    Normalizes integers to [-1.0, 1.0] float range.
    """
    data, sr = sf.read(file_path, always_2d=True, dtype='float64')
    return sr, data

def write_audio(file_path: str, sample_rate: int, audio_data: np.ndarray, format: str = 'WAV', subtype: str = 'PCM_24'):
    """
    Writes an audio file safely from np.float64 format.
    format: 'WAV', 'FLAC', 'MP3', etc.
    subtype: 'PCM_16', 'PCM_24', 'FLOAT', etc. (not used for MP3)
    """
    # Ensure it's downcast appropriately for formats like WAV/FLAC 
    # but stay 64-bit for internal processing
    # soundfile handles the dtypes natively.
    
    # Soundfile uses 'MPEG-1/2 Audio' as the MP3 string or 'MP3'
    if format.upper() == 'MP3':
        # Default bitrate is usually around 128k, but let's just write.
        # Note: minimal libsndfile support might fail for MP3 write depending on encoding libs (lame).
        # We try and if fail we let the user know.
        try:
            sf.write(file_path, audio_data, sample_rate, format='MP3')
        except Exception as e:
            # Fallback if MP3 is not supported for writing
            raise RuntimeError(f"MP3 Export failed: {e}. Ensure lame is available or choose WAV/FLAC.")
    else:
        # For WAV/FLAC/AIFF...
        sf.write(file_path, audio_data, sample_rate, format=format, subtype=subtype)
